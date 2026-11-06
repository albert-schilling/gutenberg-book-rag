"""The memory of a chat: the last exchanges word for word, older ones as a short rolling summary.

Everything in the memory is sent to the language model with every question, and the free Groq plan allows only
8,000 tokens per minute: the window is small (2 exchanges), answers are cut, and the summary is capped at 80 words.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from book_rag.config import FALLBACK_ANSWER, LLM_MODEL, OFFLINE

logger = logging.getLogger(__name__)

WINDOW_PAIRS = 2  # exchanges (question and answer) that are kept word for word
MAX_ANSWER_CHARS = 400  # an answer is cut to this length in the memory
SUMMARY_WORDS = 80
SUMMARY_CHARS = 600  # the limit of the crude summary used when the language model fails

# (current summary, question, answer) -> new summary
Summarizer = Callable[[str, str, str], str]

SUMMARY_PROMPT = """You keep the summary of a conversation about a book up to date.
Fold the new exchange into the summary. Keep names, places and facts the reader asked about. At most {words} words.
Reply with the new summary only.

Current summary: {summary}

New exchange:
Question: {question}
Answer: {answer}"""


def _shorten(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


def crude_summary(summary: str, question: str, answer: str) -> str:
    """Without a language model: keep the questions, newest last, within the limit."""
    return _shorten(f"{summary} Asked: {question}".strip(), SUMMARY_CHARS * 2)[-SUMMARY_CHARS:]


def build_summarizer() -> Summarizer:
    """A summarizer that asks the language model, and falls back to the crude one if that fails."""
    if OFFLINE:
        return crude_summary
    chain = ChatPromptTemplate.from_template(SUMMARY_PROMPT) | ChatGroq(model=LLM_MODEL, temperature=0) | StrOutputParser()

    def summarize(summary: str, question: str, answer: str) -> str:
        try:
            result = chain.invoke(
                {"words": SUMMARY_WORDS, "summary": summary or "(empty)", "question": question,
                 "answer": _shorten(answer, MAX_ANSWER_CHARS)}
            ).strip()
            if result:
                return result
        except Exception:  # a rate limit or a network error must not break the chat
            logger.warning("The conversation summary could not be updated", exc_info=True)
        return crude_summary(summary, question, answer)

    return summarize


@dataclass
class ChatMemory:
    summary: str = ""
    pairs: list[tuple[str, str]] = field(default_factory=list)  # the latest exchanges, oldest first

    def context(self) -> str:
        """The text that goes into the prompt ("" when nothing was said yet)."""
        parts = []
        if self.summary:
            parts.append(f"Summary of the earlier conversation: {self.summary}")
        if self.pairs:
            parts.append("Latest exchanges:\n" + "\n".join(f"Q: {q}\nA: {a}" for q, a in self.pairs))
        return "\n\n".join(parts)

    def add(self, question: str, answer: str, summarize: Summarizer) -> None:
        """Remember an exchange. The exchange that falls out of the window is folded into the summary."""
        if not answer.strip() or answer == FALLBACK_ANSWER:  # an error is not worth remembering
            return
        self.pairs.append((question, _shorten(answer, MAX_ANSWER_CHARS)))
        while len(self.pairs) > WINDOW_PAIRS:
            old_question, old_answer = self.pairs.pop(0)
            self.summary = summarize(self.summary, old_question, old_answer)
