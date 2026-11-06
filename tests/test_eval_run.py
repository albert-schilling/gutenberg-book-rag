import json

from langchain_core.documents import Document

from book_rag.config import NO_ANSWER
from book_rag.evaluation import judge, run
from book_rag.evaluation.dataset import EvalCase
from book_rag.evaluation.report import render_markdown, run_metadata, summarize, write_report

ANSWERABLE = EvalCase("eggs", "How long are eggs incubated?", "Four weeks.", ("incubated for four weeks",))
UNANSWERABLE = EvalCase("france", "What is the capital of France?", None, ())


class FakeVectorStore:
    def __init__(self, text):
        self.text = text

    def similarity_search_with_score(self, question, k):
        return [(Document(page_content=self.text, metadata={"start_index": 7}), 0.4)]


class FakeChain:
    def __init__(self, answer):
        self.answer = answer

    def invoke(self, inputs):
        return self.answer


class FakeJudge:
    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, prompt):
        if self.schema is judge.FaithfulnessVerdict:
            return judge.FaithfulnessVerdict(claims=[judge.Claim(claim="a", supported=True), judge.Claim(claim="b", supported=False)])
        return judge.CorrectnessVerdict(verdict="correct", reason="matches")


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
    result = run.evaluate_case(ANSWERABLE, store, FakeChain(NO_ANSWER), judge=None)  # judge=None: any judge call would fail
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
