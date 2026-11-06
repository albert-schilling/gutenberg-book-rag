"""Retrieve passages from the vector store and answer questions with them."""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq

from book_rag.config import LLM_MODEL, MIN_SIMILARITY, NO_ANSWER, SYSTEM_PROMPT, TOP_K

ScoredPassages = list[tuple[Document, float]]


def build_chain() -> Runnable:
    """The LCEL chain: fill the prompt, call the model, return the reply as a string."""
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{question}")])
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


def ask(question: str, vector_store: Chroma, chain: Runnable) -> tuple[str, ScoredPassages]:
    """Return the answer and the (passage, similarity) pairs it is based on."""
    scored_passages = retrieve(question, vector_store)
    if not scored_passages:  # nothing in the book is close enough to the question: skip the model
        return NO_ANSWER, []
    context = "\n\n".join(f"[Passage {i}]\n{p.page_content}" for i, (p, _) in enumerate(scored_passages, 1))
    return chain.invoke({"context": context, "question": question}), scored_passages
