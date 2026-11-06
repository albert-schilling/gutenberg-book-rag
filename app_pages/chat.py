"""The chat page: ask questions about the book that is chosen in the sidebar."""

import streamlit as st

from book_rag.books import get_book
from book_rag.rag import ask, build_chain
from book_rag.store import build_vector_store


@st.cache_resource(show_spinner="Preparing the book (the first time takes a moment) ...")
def load_rag(book_id: str):
    """Load the vector store and the chain of a book once, not on every rerun."""
    book = get_book(book_id)
    return build_vector_store(book), build_chain(book)


def show_passages(scored_passages):
    """Show every passage the answer is based on in an expander, so the reader can check it."""
    for passage, similarity in scored_passages:
        position = passage.metadata["start_index"]
        with st.expander(f"Passage at position {position:,} (similarity {similarity:.2f})"):
            st.write(passage.page_content)


book = get_book(st.session_state.book_id)
st.caption(f"Ask a question about *{book.title}* by {book.author}. Answers are based only on the passages shown below them.")

vector_store, chain = load_rag(book.id)

# The history only lives in the browser session, one per book; every question is answered independently.
history = st.session_state.setdefault("histories", {}).setdefault(book.id, [])

for message in history:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        show_passages(message.get("passages", []))

if question := st.chat_input(f"Ask a question about {book.title}", submit_mode="disable"):
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching the book ..."):
            answer, scored_passages = ask(question, vector_store, chain)
        st.write(answer)
        show_passages(scored_passages)

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer, "passages": scored_passages})
