import pytest
from langchain_core.documents import Document

from book_rag import rag
from book_rag.config import EMPTY_ANSWER_RETRIES, FALLBACK_ANSWER, NO_ANSWER, TOP_K


class FakeVectorStore:
    """Returns fixed (passage, squared L2 distance) pairs, like Chroma does."""

    def __init__(self, distances):
        self.results = [(Document(page_content=f"passage {i}", metadata={"start_index": i}), d)
                        for i, d in enumerate(distances)]
        self.k = None

    def similarity_search_with_score(self, question, k):
        self.k = k
        return self.results


class FakeChain:
    """Replies with the given answers one after the other (the last one is repeated)."""

    def __init__(self, *answers):
        self.answers = list(answers) or ["the answer"]
        self.calls = []

    def invoke(self, inputs):
        self.calls.append(inputs)
        return self.answers[min(len(self.calls), len(self.answers)) - 1]


def test_distance_is_converted_to_cosine_similarity():
    store = FakeVectorStore([0.0, 0.5, 1.0, 2.0])
    scores = [score for _, score in rag.retrieve("q", store)]
    assert scores == pytest.approx([1.0, 0.75, 0.5, 0.0])
    assert store.k == TOP_K


def test_weak_passages_are_dropped(monkeypatch):
    monkeypatch.setattr(rag, "MIN_SIMILARITY", 0.6)
    passages = rag.retrieve("q", FakeVectorStore([0.2, 0.8, 1.5]))  # similarities 0.9, 0.6, 0.25
    assert [p.metadata["start_index"] for p, _ in passages] == [0, 1]


def test_ask_gives_the_passages_to_the_model():
    chain = FakeChain()
    answer, passages = rag.ask("Why?", FakeVectorStore([0.2, 0.4]), chain)
    assert answer == "the answer"
    assert len(passages) == 2
    (inputs,) = chain.calls
    assert inputs["question"] == "Why?"
    assert "[Passage 1]\npassage 0" in inputs["context"]
    assert "[Passage 2]\npassage 1" in inputs["context"]


def test_ask_skips_the_model_when_no_passage_is_close_enough(monkeypatch):
    monkeypatch.setattr(rag, "MIN_SIMILARITY", 0.9)
    chain = FakeChain()
    assert rag.ask("q", FakeVectorStore([1.5, 1.8]), chain) == (NO_ANSWER, [])
    assert chain.calls == []


def test_an_empty_reply_is_asked_again():
    chain = FakeChain("", "  ", "the answer")  # empty twice, then fine
    answer, passages = rag.ask("q", FakeVectorStore([0.2]), chain)
    assert answer == "the answer"
    assert len(chain.calls) == 3 == 1 + EMPTY_ANSWER_RETRIES
    assert len(passages) == 1


def test_a_good_reply_is_not_asked_again():
    chain = FakeChain("the answer", "another answer")
    assert rag.ask("q", FakeVectorStore([0.2]), chain)[0] == "the answer"
    assert len(chain.calls) == 1


def test_the_reader_gets_a_fallback_when_every_attempt_is_empty():
    chain = FakeChain("")
    answer, passages = rag.ask("q", FakeVectorStore([0.2]), chain)
    assert answer == FALLBACK_ANSWER
    assert len(chain.calls) == 1 + EMPTY_ANSWER_RETRIES
    assert len(passages) == 1  # the passages are still shown
