"""The language model: Mistral (default) or Groq, chosen with BOOK_RAG_LLM. No other code names a provider."""

import re

import groq
import httpx
from langchain_core.language_models import BaseChatModel

from book_rag.config import LLM_PROVIDER

# What a provider raises when it cannot answer: a rate limit, a refused key, no connection.
PROVIDER_ERRORS = (groq.APIError, httpx.HTTPStatusError, httpx.TransportError)


def build_llm(model: str, *, max_retries: int = 2, **groq_options) -> BaseChatModel:
    """A chat model without randomness. `groq_options` (e.g. reasoning_effort) only apply to Groq."""
    if LLM_PROVIDER == "mistral":
        from langchain_mistralai import ChatMistralAI

        return ChatMistralAI(model=model, temperature=0, max_retries=max_retries)
    from langchain_groq import ChatGroq

    return ChatGroq(model=model, temperature=0, max_retries=max_retries, **groq_options)


def is_rate_limit(error: Exception) -> bool:
    return isinstance(error, groq.RateLimitError) or (
        isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 429
    )


def error_message(error: Exception) -> str:
    """A message for the reader when the language model cannot answer."""
    if is_rate_limit(error):
        wait = re.search(r"try again in ([0-9hms.]+)", str(error))  # Groq says how long
        hint = (
            f" Please try again in {re.sub(r'[.][0-9]+', '', wait.group(1).rstrip('.'))}."
            if wait
            else (" Please wait a little and ask again.")
        )
        return f"The free {LLM_PROVIDER.capitalize()} plan is at its limit for now." + hint
    if isinstance(error, httpx.HTTPStatusError) and error.response.status_code in (401, 403):
        return "The language model refused the API key. Please check the key in the .env file."
    return "The language model could not be reached. Please try again."
