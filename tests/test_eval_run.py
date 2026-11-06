import json

import pytest
from helpers import ANSWERABLE, UNANSWERABLE, FakeChain, FakeJudge, FakeVectorStore

from book_rag.config import FALLBACK_ANSWER, NO_ANSWER
from book_rag.evaluation import run
from book_rag.evaluation.report import render_markdown, run_metadata, summarize, write_report


def test_retrieval_only_makes_no_generation_results():
    store = FakeVectorStore("The eggs are incubated for four weeks.")
    result = run.evaluate_case(ANSWERABLE, store, chain=None, judge=None)
    assert result["answer"] is None and result["generation"] is None
    assert result["retrieval"]["context_recall"] == 1.0
    assert result["retrieved"][0]["start_index"] == 7
    assert result["retrieved"][0]["similarity"] == 0.8  # distance 0.4 -> cosine 1 - 0.4 / 2


def test_full_evaluation_of_an_answerable_question():
    store = FakeVectorStore("The eggs are incubated for four weeks.")
    result = run.evaluate_case(ANSWERABLE, store, FakeChain("Four weeks."), FakeJudge())
    generation = result["generation"]
    assert generation["abstained"] is False and generation["abstention_correct"] is True
    assert generation["faithfulness"] == 0.5
    assert generation["correctness"] == 1.0 and generation["correctness_reason"] == "matches"


def test_an_abstention_on_an_answerable_question_scores_zero_without_calling_the_judge():
    store = FakeVectorStore("Unrelated text.")
    result = run.evaluate_case(
        ANSWERABLE, store, FakeChain(NO_ANSWER), judge=None
    )  # judge=None: any judge call would fail
    generation = result["generation"]
    assert generation["abstained"] and not generation["abstention_correct"]
    assert generation["correctness"] == 0.0 and generation["faithfulness"] is None


def test_an_unanswerable_question_needs_the_abstention():
    store = FakeVectorStore("Unrelated text.")
    good = run.evaluate_case(UNANSWERABLE, store, FakeChain(NO_ANSWER), judge=None)
    bad = run.evaluate_case(UNANSWERABLE, store, FakeChain("Paris."), FakeJudge())
    assert good["retrieval"] is None and good["generation"]["abstention_correct"]
    assert not bad["generation"]["abstention_correct"] and bad["generation"]["correctness"] is None


def test_summary_and_report_files(tmp_path):
    store = FakeVectorStore("The eggs are incubated for four weeks.")
    results = [
        run.evaluate_case(ANSWERABLE, store, FakeChain("Four weeks."), FakeJudge()),
        run.evaluate_case(UNANSWERABLE, store, FakeChain(NO_ANSWER), judge=None),
    ]
    summary = summarize(results)
    assert (summary["answerable"], summary["unanswerable"]) == (1, 1)
    assert summary["retrieval"]["context_recall"] == 1.0
    assert summary["generation"]["abstention_accuracy"] == 1.0
    assert summary["generation"]["faithfulness"] == 0.5
    assert summary["generation"]["abstained_when_unanswerable"] == 1.0

    report = {"metadata": run_metadata("full"), "summary": summary, "results": results}
    json_path, md_path = write_report(report, tmp_path)
    assert json.loads(json_path.read_text())["summary"] == summary
    markdown = md_path.read_text()
    assert "context_recall" in markdown and "eggs" in markdown and "Questions to look at" in markdown
    assert json_path.stem == md_path.stem and json_path.stem.endswith("-full")


def test_an_empty_answer_is_flagged_and_scores_zero_without_calling_the_judge():
    store = FakeVectorStore("The eggs are incubated for four weeks.")
    result = run.evaluate_case(ANSWERABLE, store, FakeChain("  "), judge=None)  # judge=None: any judge call would fail
    generation = result["generation"]
    assert generation["empty"] and not generation["abstained"]
    assert generation["correctness"] == 0.0 and generation["faithfulness"] is None
    assert "empty" in generation["correctness_reason"]

    summary = summarize([result])
    assert summary["generation"]["empty_answer_rate"] == 1.0
    assert summary["generation"]["answered_when_answerable"] == 0.0
    report = {"metadata": run_metadata("full"), "summary": summary, "results": [result]}
    assert "EMPTY ANSWER" in render_markdown(report)


def test_the_fallback_answer_counts_as_empty():
    store = FakeVectorStore("The eggs are incubated for four weeks.")
    result = run.evaluate_case(ANSWERABLE, store, FakeChain(""), judge=None)  # `ask` retries, then returns the fallback
    assert result["answer"] == FALLBACK_ANSWER
    assert result["generation"]["empty"] and not result["generation"]["abstained"]


def test_the_agent_mode_counts_the_searches_and_uses_the_passages_of_all_of_them():
    from book_rag.agent import Step

    class Model:
        def __init__(self):
            self.calls = 0

        def invoke(self, inputs):
            self.calls += 1
            return Step(new_queries=["more specific words"]) if self.calls == 1 else Step(answer="Four weeks.")

    store = FakeVectorStore("The eggs are incubated for four weeks.")
    result = run.evaluate_case(ANSWERABLE, store, chain=None, judge=FakeJudge(), step_chain=Model())
    assert result["queries"] == [ANSWERABLE.question, "more specific words"]
    assert result["answer"] == "Four weeks." and result["generation"]["correctness"] == 1.0
    assert result["retrieval"]["context_recall"] == 1.0
    summary = summarize([result])
    assert summary["generation"]["searches_per_question"] == 2.0


def test_without_the_agent_there_is_one_search_per_question():
    store = FakeVectorStore("The eggs are incubated for four weeks.")
    result = run.evaluate_case(ANSWERABLE, store, FakeChain("Four weeks."), FakeJudge())
    assert result["queries"] == [ANSWERABLE.question]
    assert summarize([result])["generation"]["searches_per_question"] == 1.0


def test_a_rate_limit_is_waited_out_and_other_errors_are_not(monkeypatch):
    import httpx

    monkeypatch.setattr(run.time, "sleep", lambda seconds: None)
    request = httpx.Request("POST", "https://api.mistral.ai/x")
    limited = httpx.HTTPStatusError("x", request=request, response=httpx.Response(429, request=request))
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise limited
        return "done"

    assert run.with_retries(flaky, attempts=5) == "done" and len(calls) == 3  # waited twice

    def always():
        raise limited

    with pytest.raises(httpx.HTTPStatusError):
        run.with_retries(always, attempts=2)  # gives up after the last attempt

    def broken():
        raise httpx.HTTPStatusError("x", request=request, response=httpx.Response(500, request=request))

    with pytest.raises(httpx.HTTPStatusError):
        run.with_retries(broken, attempts=5)  # a server error is not retried


def test_rejudge_grades_the_given_answers_again_and_keeps_the_rest():
    from helpers import build_report

    from book_rag.evaluation import judge as judging

    class Strict(FakeJudge):
        def invoke(self, prompt):
            if self.schema is judging.FaithfulnessVerdict:
                return super().invoke(prompt)
            return judging.CorrectnessVerdict(
                key_facts=[judging.KeyFact(fact="a", stated=True), judging.KeyFact(fact="b", stated=False)],
                says_the_opposite=False,
                reason="one fact missing",
            )

    original = build_report("2026-01-01T10:00:00+00:00", good=True)
    assert original["results"][0]["generation"]["correctness"] == 1.0
    again = run.rejudge(original, Strict())

    eggs, france = again["results"]
    assert eggs["generation"]["correctness"] == 0.5 and eggs["generation"]["correctness_reason"] == "one fact missing"
    assert eggs["answer"] == original["results"][0]["answer"]  # no new answer
    assert eggs["generation"]["faithfulness"] == original["results"][0]["generation"]["faithfulness"]
    assert france["generation"]["correctness"] is None  # an abstention on an unanswerable question: nothing to grade
    assert again["summary"]["generation"]["answer_correctness"] == 0.5
    assert again["metadata"]["mode"] == "full-rejudged"
    assert again["metadata"]["rejudged_from"] == "2026-01-01T10:00:00+00:00"
    assert again["metadata"]["config"]["judge_rubric"] == judging.RUBRIC_VERSION
    assert original["results"][0]["generation"]["correctness"] == 1.0  # the saved report is not changed


def test_rejudge_leaves_an_abstention_on_an_answerable_question_at_zero():
    from helpers import build_report

    report = build_report("2026-01-01T10:00:00+00:00", good=False)  # the system refused
    again = run.rejudge(report, judge=None)  # a judge would fail if it were asked
    assert again["results"][0]["generation"]["correctness"] == 0.0


def test_the_summary_is_given_per_split_and_whole_book_questions_have_no_retrieval_score():
    from book_rag.evaluation.dataset import EvalCase

    whole = EvalCase("whole", "What is it about?", "Penguins.", (), kind="whole-book", split="test")
    store = FakeVectorStore("The eggs are incubated for four weeks.")
    results = [
        run.evaluate_case(ANSWERABLE, store, FakeChain("Four weeks."), FakeJudge()),
        run.evaluate_case(whole, store, FakeChain("Penguins."), FakeJudge()),
    ]
    assert results[1]["retrieval"] is None and results[1]["split"] == "test" and results[1]["kind"] == "whole-book"

    summary = summarize(results)
    assert summary["retrieval"]["context_recall"] == 1.0  # only the question that has evidence counts
    assert set(summary["by_split"]) == {"dev", "test"}
    assert summary["by_split"]["dev"]["questions"] == 1 and summary["by_split"]["test"]["questions"] == 1
    assert summary["by_split"]["test"]["answer_correctness"] == 1.0
    assert summary["by_split"]["test"]["context_recall"] is None  # nothing to score for retrieval in this split

    report = {"metadata": run_metadata("full"), "summary": summary, "results": results}
    markdown = render_markdown(report)
    assert "## By split" in markdown and "| test | 1 |" in markdown and "| dev | 1 |" in markdown


def test_one_split_gives_no_split_table():
    store = FakeVectorStore("The eggs are incubated for four weeks.")
    result = run.evaluate_case(ANSWERABLE, store, FakeChain("Four weeks."), FakeJudge())
    assert "by_split" not in summarize([result])
