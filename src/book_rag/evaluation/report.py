"""Summarise the results of an evaluation run and persist them as JSON and Markdown."""

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from book_rag import config
from book_rag.books import DEFAULT_BOOK, Book
from book_rag.evaluation.dataset import DATASET_FILE
from book_rag.evaluation.metrics import mean

REPORT_DIR = config.EVAL_DIR / "reports"


def summarize(results: list[dict]) -> dict:
    """Average the per-question results. Retrieval metrics only count the answerable questions."""
    answerable = [r for r in results if r["answerable"]]
    unanswerable = [r for r in results if not r["answerable"]]
    summary = {
        "questions": len(results),
        "answerable": len(answerable),
        "unanswerable": len(unanswerable),
        "retrieval": {
            "context_recall": mean([r["retrieval"]["context_recall"] for r in answerable]),
            "hit_rate": mean([float(r["retrieval"]["hit"]) for r in answerable]),
            "mrr": mean([r["retrieval"]["reciprocal_rank"] for r in answerable]),
            "context_precision": mean([r["retrieval"]["context_precision"] for r in answerable]),
        },
    }
    if all(r["generation"] is not None for r in results):
        generation = [r["generation"] for r in results]
        summary["generation"] = {
            "abstention_accuracy": mean([float(g["abstention_correct"]) for g in generation]),
            "answered_when_answerable": mean(
                [float(not (r["generation"]["abstained"] or r["generation"]["empty"])) for r in answerable]
            ),
            "empty_answer_rate": mean([float(g["empty"]) for g in generation]),
            "searches_per_question": mean([float(len(r.get("queries", [0]))) for r in results]),  # 1.0 without the agent
            "abstained_when_unanswerable": mean([float(r["generation"]["abstained"]) for r in unanswerable]),
            "faithfulness": mean([g["faithfulness"] for g in generation]),
            "answer_correctness": mean([r["generation"]["correctness"] for r in answerable]),
        }
    return summary


def _git_state() -> dict:
    """The commit the code was at, and whether there were uncommitted changes (None if no Git)."""
    try:
        run = lambda *args: subprocess.run(  # noqa: E731
            ["git", *args], cwd=config.PROJECT_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        return {"commit": run("rev-parse", "--short", "HEAD"), "uncommitted_changes": bool(run("status", "--porcelain"))}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "uncommitted_changes": None}


def run_metadata(mode: str, book: Book = DEFAULT_BOOK) -> dict:
    """Everything needed to compare two runs later: the book, the settings of the system and the dataset."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,
        "book": book.id,
        "git": _git_state(),
        "config": {
            "chunk_size": config.CHUNK_SIZE,
            "chunk_overlap": config.CHUNK_OVERLAP,
            "top_k": config.TOP_K,
            "min_similarity": config.MIN_SIMILARITY,
            "embedding_model": config.EMBEDDING_MODEL,
            "llm_model": config.LLM_MODEL,
            "judge_model": config.JUDGE_MODEL,
            "system_prompt_sha1": hashlib.sha1(config.SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:10],
        },
        "dataset_sha1": hashlib.sha1(DATASET_FILE.read_bytes()).hexdigest()[:10],
    }


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def render_markdown(report: dict) -> str:
    meta, summary = report["metadata"], report["summary"]
    git = meta["git"]
    lines = [
        f"# Evaluation report {meta['timestamp']}",
        "",
        f"Mode: **{meta['mode']}** · commit: `{git['commit']}`"
        + (" (with uncommitted changes)" if git["uncommitted_changes"] else "")
        + f" · dataset: `{meta['dataset_sha1']}`",
        "",
        "## Settings",
        "",
        "| Setting | Value |",
        "| :-- | :-- |",
        *[f"| {key} | `{value}` |" for key, value in meta["config"].items()],
        "",
        f"## Metrics ({summary['answerable']} answerable and {summary['unanswerable']} unanswerable questions)",
        "",
        "| Metric | Score |",
        "| :-- | --: |",
        *[f"| {key} | {_fmt(value)} |" for key, value in summary["retrieval"].items()],
        *[f"| {key} | {_fmt(value)} |" for key, value in summary.get("generation", {}).items()],
        "",
        "## Questions",
        "",
        "| Question | Recall | Rank | Abstained | Faithful | Correct |",
        "| :-- | --: | --: | :-: | --: | --: |",
    ]
    problems = []
    for r in report["results"]:
        retrieval, generation = r["retrieval"], r["generation"]
        recall = _fmt(retrieval["context_recall"]) if retrieval else "-"
        rank = (f"{1 / retrieval['reciprocal_rank']:.0f}" if retrieval["reciprocal_rank"] else "miss") if retrieval else "-"
        if generation:
            row = [("EMPTY" if generation["empty"] else "yes" if generation["abstained"] else "no"), _fmt(generation["faithfulness"]), _fmt(generation["correctness"])]
        else:
            row = ["-", "-", "-"]
        lines.append(f"| {r['id']} | {recall} | {rank} | {' | '.join(row)} |")

        weak = []
        if retrieval and retrieval["context_recall"] < 1:
            weak.append(f"retrieval missed evidence (recall {retrieval['context_recall']:.2f})")
        if generation and generation["empty"]:
            weak.append("EMPTY ANSWER")
        elif generation and not generation["abstention_correct"]:
            weak.append("answered an unanswerable question" if not r["answerable"] else "abstained on an answerable question")
        if generation and generation["faithfulness"] is not None and generation["faithfulness"] < 1:
            weak.append(f"unsupported claims (faithfulness {generation['faithfulness']:.2f})")
        if generation and not generation["empty"] and generation["correctness"] is not None and generation["correctness"] < 1:
            weak.append(f"{generation['correctness_reason']} (correctness {generation['correctness']:.1f})")
        if weak:
            problems.append(f"- **{r['id']}**: {r['question']}\n  " + "; ".join(weak))

    lines += ["", "## Questions to look at", "", *(problems or ["None: every score is perfect."]), ""]
    return "\n".join(lines)


def write_report(report: dict, directory: Path = REPORT_DIR) -> tuple[Path, Path]:
    """Save the report as <timestamp>.json (for comparing runs) and <timestamp>.md (for reading)."""
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromisoformat(report["metadata"]["timestamp"]).strftime("%Y%m%d-%H%M%S")
    stem = f"{stamp}-{report['metadata']['mode']}"
    json_path, md_path = directory / f"{stem}.json", directory / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path
