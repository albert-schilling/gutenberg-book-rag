"""A small web app to ask questions about the book.

Run it from the project root with:

    uv run streamlit run streamlit_app.py
"""

import streamlit as st
from dotenv import load_dotenv

from book_rag.config import AUTHOR, ENV_FILE, TITLE
from book_rag.rag import ask, build_chain
from book_rag.store import build_vector_store

load_dotenv(ENV_FILE)  # reads GROQ_API_KEY from the .env file


@st.cache_resource
def load_rag():
    """Load the embedding model, the vector store and the chain once, not on every rerun."""
    return build_vector_store(), build_chain()


def show_passages(scored_passages):
    """Show every passage the answer is based on in an expander, so the reader can check it."""
    for passage, similarity in scored_passages:
        position = passage.metadata["start_index"]
        with st.expander(f"Passage at position {position:,} (similarity {similarity:.2f})"):
            st.write(passage.page_content)


st.set_page_config(page_title="Reading companion", page_icon=":material/menu_book:")
st.title("Reading companion")
st.caption(f"Ask a question about *{TITLE}* by {AUTHOR}. Answers are based only on the passages shown below them.")

vector_store, chain = load_rag()

# The history only lives in the browser session; every question is answered independently.
if "history" not in st.session_state:
    st.session_state.history = []

for message in st.session_state.history:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        show_passages(message.get("passages", []))

if question := st.chat_input("Ask a question about the book", submit_mode="disable"):
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching the book ..."):
            answer, scored_passages = ask(question, vector_store, chain)
        st.write(answer)
        show_passages(scored_passages)

    st.session_state.history.append({"role": "user", "content": question})
    st.session_state.history.append({"role": "assistant", "content": answer, "passages": scored_passages})
