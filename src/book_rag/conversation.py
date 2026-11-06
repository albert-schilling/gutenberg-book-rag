"""A reading companion for one book, and one turn of a conversation with it.

The web app and the command line both use this, so they behave the same.
"""

import logging
from dataclasses import dataclass

from langchain_chroma import Chroma
from langchain_core.runnables import Runnable

from book_rag import agent, memory, rag, store
from book_rag.agent import AgentResult
from book_rag.books import Book
from book_rag.config import AGENTIC_DEFAULT
from book_rag.llm import PROVIDER_ERRORS, error_message
from book_rag.memory import ChatMemory, Summarizer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Companion:
    """Everything needed to answer questions about one book."""

    book: Book
    vector_store: Chroma
    chain: Runnable  # one call: the passages go in, the answer comes out
    step_chain: Runnable  # the agent: answers, or asks for another search
    summarizer: Summarizer  # folds old exchanges into the summary of the chat

    def respond(self, question: str, memory: ChatMemory, *, agentic: bool = AGENTIC_DEFAULT) -> AgentResult:
        """Answer the question and remember the exchange. Never raises because of the language model."""
        conversation = memory.context()
        try:
            if agentic:
                result = agent.agent_ask(question, self.vector_store, self.step_chain, conversation)
            else:
                answer, passages = rag.ask(question, self.vector_store, self.chain, conversation)
                result = AgentResult(answer, passages, [question])
        except PROVIDER_ERRORS as error:
            logger.warning("The language model failed: %s", error)
            return AgentResult(error_message(error), [], [question], error=True)
        memory.add(question, result.answer, self.summarizer)
        return result


def build_companion(book: Book) -> Companion:
    """Open the vector store of the book and set up the language models."""
    return Companion(
        book=book,
        vector_store=store.build_vector_store(book),
        chain=rag.build_chain(book),
        step_chain=agent.build_step_chain(book),
        summarizer=memory.build_summarizer(),
    )
