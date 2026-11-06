"""Tests with the real language model on Groq. They catch what fakes cannot (for example, two prompts that contradict
each other). They are skipped unless you ask for them:

    BOOK_RAG_LIVE=1 uv run pytest -m live

One run is about 7 calls and 15,000 tokens. The free plan allows 200,000 tokens a day, so a rate limit skips the test.
"""

import os

import pytest
from dotenv import load_dotenv

from book_rag import store
from book_rag.books import BOOKS, DEFAULT_BOOK
from book_rag.config import ENV_FILE, NO_ANSWER
from book_rag.conversation import build_companion
from book_rag.memory import ChatMemory

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("BOOK_RAG_LIVE") != "1", reason="set BOOK_RAG_LIVE=1 to call the real model"),
]


def respond(companion, question, memory, *, agentic):
    """Ask the real model. A rate limit of the free plan skips the test: it says nothing about the code."""
    result = companion.respond(question, memory, agentic=agentic)
    if result.error:
        pytest.skip(result.answer)
    return result


@pytest.fixture(scope="module")
def chroma_dir(tmp_path_factory):
    load_dotenv(ENV_FILE)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(store, "CHROMA_DIR", tmp_path_factory.mktemp("chroma"))
        yield


@pytest.fixture(scope="module")
def penguins(chroma_dir):
    return build_companion(DEFAULT_BOOK)


def test_a_question_about_the_whole_book_is_answered_from_its_summary(chroma_dir):
    oz = build_companion(BOOKS["wonderful_wizard_of_oz_baum"])
    result = respond(oz, "What is this book about?", ChatMemory(), agentic=False)
    assert result.answer != NO_ANSWER and "Dorothy" in result.answer


@pytest.mark.parametrize("agentic", [False, True])
def test_a_question_that_the_book_cannot_answer_is_refused(penguins, agentic):
    result = respond(penguins, "What is the capital of France?", ChatMemory(), agentic=agentic)
    assert result.answer == NO_ANSWER


@pytest.mark.parametrize("agentic", [False, True])
def test_a_question_that_the_passages_answer_gets_an_answer(penguins, agentic):
    result = respond(penguins, "How many eggs does an Adelie penguin lay?", ChatMemory(), agentic=agentic)
    assert result.answer != NO_ANSWER and "two" in result.answer.lower()
    assert result.queries[0] == "How many eggs does an Adelie penguin lay?"  # the first search is the question itself
    assert 1 <= len(result.queries) <= 3  # never more than the rounds of the agent


def test_a_follow_up_question_is_understood_through_the_memory(penguins):
    memory = ChatMemory()
    respond(penguins, "What do skua gulls do to the penguin chicks?", memory, agentic=False)
    result = respond(penguins, "Do they also attack the adult penguins?", memory, agentic=False)
    assert result.answer != NO_ANSWER and "skua" not in NO_ANSWER.lower()
    assert len(memory.pairs) == 2


def test_the_summarizer_folds_an_exchange_into_a_short_summary(penguins):
    summary = penguins.summarizer("", "What do skuas eat?", "Skuas eat penguin eggs and chicks.")
    assert "Asked:" not in summary  # that is the crude fallback of memory.py, not the model
    assert summary and len(summary.split()) <= 100 and "skua" in summary.lower()
