"""One turn of a conversation: answer a question (with or without the agent) and update the memory.

The web app and the command line both use this, so they behave the same.
"""

import logging
import re

import groq
from langchain_chroma import Chroma
from langchain_core.runnables import Runnable

from book_rag import agent, rag
from book_rag.agent import AgentResult
from book_rag.config import AGENTIC_DEFAULT
from book_rag.memory import ChatMemory, Summarizer

logger = logging.getLogger(__name__)


def error_message(error: groq.APIError) -> str:
    """A message for the reader when the language model cannot answer (a rate limit, or no connection)."""
    if isinstance(error, groq.RateLimitError):
        wait = re.search(r"try again in ([0-9hms.]+)", str(error))
        hint = f" Please try again in {re.sub(r'[.][0-9]+', '', wait.group(1).rstrip('.'))}." if wait else " Please wait a little and ask again."
        return "The free Groq plan is at its limit for now." + hint
    return "The language model could not be reached. Please try again."


def respond(
    question: str,
    vector_store: Chroma,
    chain: Runnable,
    step_chain: Runnable,
    memory: ChatMemory,
    summarizer: Summarizer,
    *,
    agentic: bool = AGENTIC_DEFAULT,
) -> AgentResult:
    """Answer the question and remember the exchange. Never raises because of the language model."""
    conversation = memory.context()
    try:
        if agentic:
            result = agent.agent_ask(question, vector_store, step_chain, conversation)
        else:
            answer, passages = rag.ask(question, vector_store, chain, conversation)
            result = AgentResult(answer, passages, [question])
    except groq.APIError as error:
        logger.warning("The language model failed: %s", error)
        return AgentResult(error_message(error), [], [question], error=True)
    memory.add(question, result.answer, summarizer)
    return result
