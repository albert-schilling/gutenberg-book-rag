import json

import pytest
from helpers import build_report

from book_rag.evaluation import compare

OLD = build_report("2026-01-01T10:00:00+00:00", good=False, embedding_model="org/model-a")
NEW = build_report("2026-01-02T10:00:00+00:00", good=True, embedding_model="org/model-b")


def test_report_label():
    assert compare.report_label(NEW) == "2026-01-02 10h00 · full · model-b"
    assert ":" not in compare.report_label(NEW)  # charts use labels as column names; Altair reads ":" as a type


def test_flat_metrics_joins_retrieval_and_generation():
    metrics = compare.flat_metrics(NEW)
    assert metrics["context_recall"] == 1.0 and metrics["answer_correctness"] == 1.0
    retrieval_only = compare.flat_metrics(build_report("2026-01-03T10:00:00+00:00", good=True, mode="retrieval"))
    assert "context_recall" in retrieval_only and "answer_correctness" not in retrieval_only


def test_metrics_frame_has_a_row_per_metric_and_a_column_per_report():
    frame = compare.metrics_frame({"old": OLD, "new": NEW})
    assert list(frame.columns) == ["old", "new"]
    assert frame.loc["context_recall"].tolist() == [0.0, 1.0]
    assert frame.loc["answer_correctness"].tolist() == [0.0, 1.0]


def test_changed_settings_lists_only_the_differences():
    changes = compare.changed_settings(OLD, NEW)
    assert changes.to_dict("records") == [{"setting": "embedding_model", "before": "org/model-a", "after": "org/model-b"}]
    assert compare.changed_settings(NEW, NEW).empty


def test_question_frame():
    frame = compare.question_frame(NEW)
    assert list(frame.index) == ["eggs", "france"]
    assert frame.loc["eggs", "recall"] == 1.0 and frame.loc["eggs", "rank"] == 1.0
    assert frame.loc["eggs", "correctness"] == 1.0
    assert bool(frame.loc["france", "abstained"]) is True
    assert frame["recall"].isna()["france"]  # no evidence for an unanswerable question


def test_compare_questions_labels_each_change():
    improved = compare.compare_questions(OLD, NEW)
    assert improved.loc["eggs", "change"] == "improved"
    assert improved.loc["france", "change"] == "same"  # abstained both times
    regressed = compare.compare_questions(NEW, OLD)
    assert regressed.loc["eggs", "change"] == "regressed"
    assert improved.loc["eggs", "recall_before"] == 0.0 and improved.loc["eggs", "recall_after"] == 1.0


def test_reports_are_listed_oldest_first_and_loaded(tmp_path):
    for name, report in [("20260102-new-full", NEW), ("20260101-old-full", OLD)]:
        (tmp_path / f"{name}.json").write_text(json.dumps(report))
    (tmp_path / "20260101-old-full.md").write_text("not a report")
    paths = compare.list_reports(tmp_path)
    assert [p.stem for p in paths] == ["20260101-old-full", "20260102-new-full"]
    assert compare.load_report(paths[0]) == json.loads(json.dumps(OLD))


def test_no_reports(tmp_path):
    assert compare.list_reports(tmp_path / "missing") == []


@pytest.mark.parametrize("metric", sorted(compare.LOWER_IS_BETTER))
def test_lower_is_better_metrics_exist_in_reports(metric):
    assert metric in compare.flat_metrics(NEW)
