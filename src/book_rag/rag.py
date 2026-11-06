"""Retrieve passages from the vector store and answer questions with them."""

import logging

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_groq import ChatGroq

from book_rag.books import Book
from book_rag.config import (
    EMPTY_ANSWER_RETRIES,
    FALLBACK_ANSWER,
    LLM_MODEL,
    MIN_SIMILARITY,
    NO_ANSWER,
    OFFLINE,
    SYSTEM_PROMPT,
    TOP_K,
)

logger = logging.getLogger(__name__)

ScoredPassages = list[tuple[Document, float]]


def build_system_prompt(book: Book) -> str:
    """The prompt of the book. {context} stays in it: the chain fills in the passages."""
    return SYSTEM_PROMPT.replace("{title}", book.title).replace("{author}", book.author)


def _offline_reply(inputs: dict) -> str:
    return f"Offline mode: no language model was called. The best passages for “{inputs['question']}” are below."


def build_chain(book: Book) -> Runnable:
    """The LCEL chain: fill the prompt, call the model, return the reply as a string."""
    if OFFLINE:
        return RunnableLambda(_offline_reply)
    prompt = ChatPromptTemplate.from_messages([("system", build_system_prompt(book)), ("human", "{question}")])
    llm = ChatGroq(model=LLM_MODEL, temperature=0)
    return prompt | llm | StrOutputParser()


def retrieve(question: str, vector_store: Chroma) -> ScoredPassages:
    """Return (passage, similarity) pairs, most similar first, without the weak matches.

    Chroma returns the squared L2 distance. The embeddings have length 1, so
    cosine similarity = 1 - distance / 2.
    """
    results = vector_store.similarity_search_with_score(question, k=TOP_K)
    scored = [(passage, 1 - distance / 2) for passage, distance in results]
    return [(passage, score) for passage, score in scored if score >= MIN_SIMILARITY]


def format_context(scored_passages: ScoredPassages) -> str:
    """The text the model sees: the numbered passages."""
    return "\n\n".join(f"[Passage {i}]\n{p.page_content}" for i, (p, _) in enumerate(scored_passages, 1))


def ask(question: str, vector_store: Chroma, chain: Runnable, conversation: str = "") -> tuple[str, ScoredPassages]:
    """Return the answer and the (passage, similarity) pairs it is based on.

    `conversation` is the memory of the chat (see memory.py). gpt-oss sometimes returns an empty reply. The question is then asked again, up to
    EMPTY_ANSWER_RETRIES more times, before the reader gets FALLBACK_ANSWER.
    """
    scored_passages = retrieve(question, vector_store)
    if not scored_passages:  # nothing in the book is close enough to the question: skip the model
        return NO_ANSWER, []
    inputs = {"context": format_context(scored_passages), "question": question, "conversation": conversation or "(none)"}
    for attempt in range(1 + EMPTY_ANSWER_RETRIES):
        answer = chain.invoke(inputs)
        if answer.strip():
            return answer, scored_passages
        logger.warning("Empty answer from the model (attempt %d of %d)", attempt + 1, 1 + EMPTY_ANSWER_RETRIES)
    return FALLBACK_ANSWER, scored_passages
