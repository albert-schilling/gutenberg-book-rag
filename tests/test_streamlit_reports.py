"""UI tests for app/reports.py with two small reports in a temporary folder."""

import json
from pathlib import Path

import pytest
from helpers import build_report
from streamlit.testing.v1 import AppTest

from book_rag.evaluation import report as reporting

APP = Path(__file__).resolve().parents[1] / "app" / "reports.py"


def write(directory, name, report):
    (directory / f"{name}.json").write_text(json.dumps(report))


@pytest.fixture
def reports_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(reporting, "REPORT_DIR", tmp_path)
    return tmp_path


def run_app():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception
    return at


def test_without_reports_the_app_says_how_to_create_one(reports_dir):
    at = run_app()
    assert "book-rag-eval" in at.info[0].value
    assert len(at.metric) == 0


def test_the_newest_report_is_compared_with_the_one_before(reports_dir):
    write(
        reports_dir,
        "20260101-100000-full",
        build_report("2026-01-01T10:00:00+00:00", good=False, embedding_model="org/model-a"),
    )
    write(
        reports_dir,
        "20260102-100000-full",
        build_report("2026-01-02T10:00:00+00:00", good=True, embedding_model="org/model-b"),
    )
    at = run_app()

    report, compare_with = at.sidebar.selectbox
    assert report.value == "20260102-100000-full"
    assert compare_with.value == "20260101-100000-full"

    metrics = {m.label: (m.value, m.delta) for m in at.metric}
    assert metrics["Context recall"] == ("1.00", "1.0")  # from 0.00
    assert metrics["Answer correctness"] == ("1.00", "1.0")

    settings = next(df for df in at.dataframe if "setting" in df.value.columns)
    assert settings.value["setting"].tolist() == ["embedding_model"]


def test_selecting_no_comparison_hides_the_deltas(reports_dir):
    write(reports_dir, "20260101-100000-full", build_report("2026-01-01T10:00:00+00:00", good=False))
    write(reports_dir, "20260102-100000-full", build_report("2026-01-02T10:00:00+00:00", good=True))
    at = run_app()
    at.sidebar.selectbox[1].select_index(0).run()  # "Nothing"
    assert not at.exception
    assert all(m.delta in (None, "") for m in at.metric)
    assert len(at.warning) == 0


def test_question_details_show_the_answer_and_the_passages(reports_dir):
    write(reports_dir, "20260102-100000-full", build_report("2026-01-02T10:00:00+00:00", good=True))
    at = run_app()
    question = next(s for s in at.selectbox if s.label == "Question")
    question.select("eggs").run()
    assert not at.exception
    markdown = " ".join(m.value for m in at.markdown)
    assert "Four weeks." in markdown  # the reference answer and the system answer
    assert any("position 7" in e.label for e in at.expander)  # the retrieved passage


def test_a_single_retrieval_only_report_works(reports_dir):
    write(
        reports_dir, "20260102-100000-retrieval", build_report("2026-01-02T10:00:00+00:00", good=True, mode="retrieval")
    )
    at = run_app()
    labels = [m.label for m in at.metric]
    assert "Context recall" in labels and "Answer correctness" not in labels
