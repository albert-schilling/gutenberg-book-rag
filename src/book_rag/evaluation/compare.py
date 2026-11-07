"""Turn saved evaluation reports into tables for comparing runs (no Streamlit in here)."""

import json
from pathlib import Path

import pandas as pd

from book_rag.evaluation import report as reporting

LOWER_IS_BETTER = {"empty_answer_rate"}  # for every other metric, higher is better


def list_reports(directory: Path | None = None) -> list[Path]:
    """The saved reports (JSON files), oldest first."""
    directory = directory or reporting.REPORT_DIR
    return sorted(directory.glob("*.json"))


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_label(report: dict) -> str:
    """A short name to tell reports apart: when, which mode, which embedding model.

    No colon in the time: charts use these labels as column names, and Altair reads a colon as a type.
    """
    meta = report["metadata"]
    when = meta["timestamp"][:16].replace("T", " ").replace(":", "h")
    return f"{when} · {meta['mode']} · {meta['config']['embedding_model'].split('/')[-1]}"


def flat_metrics(report: dict) -> dict[str, float | None]:
    """All the summary metrics of a report in one dict."""
    summary = report["summary"]
    return {**summary["retrieval"], **summary.get("generation", {})}


def metrics_frame(reports: dict[str, dict]) -> pd.DataFrame:
    """One row per metric, one column per report."""
    return pd.DataFrame({name: flat_metrics(r) for name, r in reports.items()})


def changed_settings(base: dict, other: dict) -> pd.DataFrame:
    """The settings (and the dataset) that differ between two reports."""
    flat = lambda r: {**r["metadata"]["config"], "dataset_sha1": r["metadata"]["dataset_sha1"]}  # noqa: E731
    before, after = flat(base), flat(other)
    rows = [(key, before.get(key), after.get(key)) for key in before if before.get(key) != after.get(key)]
    return pd.DataFrame(rows, columns=["setting", "before", "after"])


def question_frame(report: dict) -> pd.DataFrame:
    """One row per question with its scores (missing values are NaN)."""
    rows = []
    for r in report["results"]:
        retrieval, generation = r["retrieval"], r["generation"]
        rows.append(
            {
                "id": r["id"],
                "question": r["question"],
                "answerable": r["answerable"],
                "recall": retrieval["context_recall"] if retrieval else None,
                "rank": (1 / retrieval["reciprocal_rank"] if retrieval["reciprocal_rank"] else None)
                if retrieval
                else None,
                "abstained": generation["abstained"] if generation else None,
                "empty": generation["empty"] if generation else None,
                "faithfulness": generation["faithfulness"] if generation else None,
                "correctness": generation["correctness"] if generation else None,
            }
        )
    return pd.DataFrame(rows).set_index("id")


def compare_questions(base: dict, other: dict) -> pd.DataFrame:
    """For every question in both reports: how recall and correctness changed from `base` to `other`."""
    before, after = question_frame(base), question_frame(other)
    ids = [i for i in after.index if i in before.index]
    frame = pd.DataFrame(
        {
            "question": after.loc[ids, "question"],
            "recall_before": before.loc[ids, "recall"].astype(float),
            "recall_after": after.loc[ids, "recall"].astype(float),
            "correctness_before": before.loc[ids, "correctness"].astype(float),
            "correctness_after": after.loc[ids, "correctness"].astype(float),
        }
    )
    deltas = pd.DataFrame(
        {
            "recall": frame["recall_after"] - frame["recall_before"],
            "correctness": frame["correctness_after"] - frame["correctness_before"],
        }
    )

    def status(row) -> str:
        changes = row.dropna()
        if changes.empty or (changes == 0).all():
            return "same"
        if (changes >= 0).all():
            return "improved"
        return "regressed" if (changes <= 0).all() else "mixed"

    frame["change"] = deltas.apply(status, axis=1)
    return frame
