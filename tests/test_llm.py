import groq
import httpx

from book_rag import config, conversation, llm
from book_rag.conversation import Companion
from book_rag.memory import ChatMemory


def http_error(status, body="x"):
    request = httpx.Request("POST", "https://api.mistral.ai/v1/chat/completions")
    return httpx.HTTPStatusError(body, request=request, response=httpx.Response(status, request=request))


def test_the_provider_is_mistral_by_default_with_a_small_and_a_large_model():
    assert config.LLM_PROVIDER == "mistral"
    assert config.LLM_MODEL == "mistral-small-latest" and config.JUDGE_MODEL == "mistral-large-latest"


def test_groq_has_its_own_models():
    assert config._MODELS["groq"] == ("openai/gpt-oss-20b", "openai/gpt-oss-120b")


def test_mistral_has_its_own_models():
    assert config._MODELS["mistral"] == ("mistral-small-latest", "mistral-large-latest")


def test_the_provider_builds_the_matching_chat_model(monkeypatch):
    monkeypatch.setattr(llm, "LLM_PROVIDER", "mistral")
    mistral = llm.build_llm("mistral-small-latest", api_key="not-a-real-key")
    assert type(mistral).__name__ == "ChatMistralAI" and mistral.temperature == 0
    monkeypatch.setattr(llm, "LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "not-a-real-key")
    groq_model = llm.build_llm("openai/gpt-oss-20b", reasoning_effort="low")
    assert type(groq_model).__name__ == "ChatGroq" and groq_model.temperature < 1e-6  # Groq turns 0 into 1e-8


def test_a_rate_limit_is_recognised_for_both_providers():
    assert llm.is_rate_limit(http_error(429))
    request = httpx.Request("POST", "https://api.groq.com/x")
    assert llm.is_rate_limit(groq.RateLimitError("x", response=httpx.Response(429, request=request), body=None))
    assert not llm.is_rate_limit(http_error(500))


def test_error_messages_say_what_to_do(monkeypatch):
    monkeypatch.setattr(llm, "LLM_PROVIDER", "mistral")
    assert (
        llm.error_message(http_error(429))
        == "The free Mistral plan is at its limit for now. Please wait a little and ask again."
    )
    assert "refused the API key" in llm.error_message(http_error(401))
    assert "could not be reached" in llm.error_message(http_error(500))
    assert "could not be reached" in llm.error_message(httpx.ConnectError("no network"))


def test_the_chat_survives_a_mistral_error_and_does_not_remember_it(monkeypatch):
    def failing(*args, **kwargs):
        raise http_error(429)

    monkeypatch.setattr(conversation.agent, "agent_ask", failing)
    memory = ChatMemory()
    result = Companion("book", "store", "chain", "step", lambda *a: "").respond("Q?", memory, agentic=True)
    assert result.error and "limit" in result.answer and memory.pairs == []
