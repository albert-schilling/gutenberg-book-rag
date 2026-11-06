import json

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
