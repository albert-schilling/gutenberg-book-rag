import pytest
from langchain_core.documents import Document

from book_rag import rag
from book_rag.config import NO_ANSWER, TOP_K


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
    def __init__(self):
        self.calls = []

    def invoke(self, inputs):
        self.calls.append(inputs)
        return "the answer"


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
