"""Fakes shared by the evaluation tests."""

import copy

from langchain_core.documents import Document

from book_rag.config import NO_ANSWER
from book_rag.evaluation import judge, run
from book_rag.evaluation.dataset import EvalCase
from book_rag.evaluation.report import run_metadata, summarize

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


class AnswerByQuestion:
    """Replies with the answer for the question, and with the abstention for any other question."""

    def __init__(self, answers):
        self.answers = answers

    def invoke(self, inputs):
        return self.answers.get(inputs["question"], NO_ANSWER)


class FakeJudge:
    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, prompt):
        if self.schema is judge.FaithfulnessVerdict:
            return judge.FaithfulnessVerdict(
                claims=[judge.Claim(claim="a", supported=True), judge.Claim(claim="b", supported=False)]
            )
        return judge.CorrectnessVerdict(
            key_facts=[judge.KeyFact(fact="f", stated=True)], says_the_opposite=False, reason="matches"
        )


def build_report(timestamp, *, good, embedding_model="model-a", mode="full"):
    """A real report dict made with the fakes. `good=False` retrieves the wrong text and abstains."""
    text = "The eggs are incubated for four weeks." if good else "Unrelated text."
    store, chain = FakeVectorStore(text), AnswerByQuestion({ANSWERABLE.question: "Four weeks." if good else NO_ANSWER})
    judge_model = FakeJudge()
    cases = [ANSWERABLE, UNANSWERABLE]
    retrieval_only = mode == "retrieval"
    results = [
        run.evaluate_case(case, store, None if retrieval_only else chain, None if retrieval_only else judge_model)
        for case in cases
    ]
    metadata = copy.deepcopy(run_metadata(mode))
    metadata["timestamp"] = timestamp
    metadata["config"]["embedding_model"] = embedding_model
    return {"metadata": metadata, "summary": summarize(results), "results": results}
