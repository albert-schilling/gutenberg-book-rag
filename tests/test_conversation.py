import groq
import httpx
import pytest
from langchain_core.documents import Document

from book_rag import agent, conversation, rag
from book_rag.agent import AgentResult
from book_rag.memory import ChatMemory

PASSAGES = [(Document(page_content="p", metadata={"start_index": 1}), 0.8)]


def summarize(summary, question, answer):
    return f"{summary}|{question}"


def rate_limit_error(message="Rate limit reached. Please try again in 6m47.808s."):
    request = httpx.Request("POST", "https://api.groq.com/x")
    return groq.RateLimitError(message, response=httpx.Response(429, request=request), body=None)


@pytest.fixture
def calls(monkeypatch):
    """Replace the agent and the plain pipeline; record what they were asked."""
    recorded = {"agent": [], "plain": []}

    def fake_agent(question, store, step_chain, conversation_text=""):
        recorded["agent"].append((question, conversation_text))
        return AgentResult("agent answer", PASSAGES, [question, "a second search"])

    def fake_plain(question, store, chain, conversation_text=""):
        recorded["plain"].append((question, conversation_text))
        return "plain answer", PASSAGES

    monkeypatch.setattr(agent, "agent_ask", fake_agent)
    monkeypatch.setattr(rag, "ask", fake_plain)
    return recorded


def test_with_the_agent_the_model_may_search_again(calls):
    result = conversation.respond("Q?", "store", "chain", "step", ChatMemory(), summarize, agentic=True)
    assert result.answer == "agent answer" and result.queries == ["Q?", "a second search"]
    assert calls["agent"] == [("Q?", "")] and calls["plain"] == []


def test_without_the_agent_there_is_one_search_and_one_call(calls):
    result = conversation.respond("Q?", "store", "chain", "step", ChatMemory(), summarize, agentic=False)
    assert result.answer == "plain answer" and result.queries == ["Q?"] and result.passages == PASSAGES
    assert calls["plain"] == [("Q?", "")] and calls["agent"] == []


def test_the_memory_is_given_to_the_model_and_updated_after_the_answer(calls):
    memory = ChatMemory()
    conversation.respond("First?", "store", "chain", "step", memory, summarize, agentic=True)
    conversation.respond("Second?", "store", "chain", "step", memory, summarize, agentic=True)
    assert calls["agent"][0][1] == ""
    assert "Q: First?\nA: agent answer" in calls["agent"][1][1]  # the second question sees the first exchange
    assert [q for q, _ in memory.pairs] == ["First?", "Second?"]


def test_a_rate_limit_gives_a_message_and_is_not_remembered(monkeypatch):
    def failing(*args, **kwargs):
        raise rate_limit_error()

    monkeypatch.setattr(agent, "agent_ask", failing)
    memory = ChatMemory()
    result = conversation.respond("Q?", "store", "chain", "step", memory, summarize, agentic=True)
    assert result.error and result.passages == []
    assert result.answer == "The free Groq plan is at its limit for now. Please try again in 6m47s."
    assert memory.pairs == []  # an error is not part of the conversation


def test_a_rate_limit_without_a_wait_time_still_says_what_to_do():
    assert "wait a little" in conversation.error_message(rate_limit_error("Too many requests"))


def test_a_connection_error_gives_a_message_too(monkeypatch):
    def failing(*args, **kwargs):
        raise groq.APIConnectionError(request=httpx.Request("POST", "https://api.groq.com/x"))

    monkeypatch.setattr(rag, "ask", failing)
    result = conversation.respond("Q?", "store", "chain", "step", ChatMemory(), summarize, agentic=False)
    assert result.error and "could not be reached" in result.answer


def test_other_errors_are_not_hidden(monkeypatch):
    monkeypatch.setattr(agent, "agent_ask", lambda *a, **k: (_ for _ in ()).throw(ValueError("a bug")))
    with pytest.raises(ValueError):
        conversation.respond("Q?", "store", "chain", "step", ChatMemory(), summarize, agentic=True)
