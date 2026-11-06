"""A small web app to ask questions about the books of the library.

Run it from the project root with:

    uv run streamlit run streamlit_app.py
"""

import streamlit as st
from dotenv import load_dotenv

from book_rag.books import BOOKS, DEFAULT_BOOK
from book_rag.config import ENV_FILE
from book_rag.reader_component import open_reader
from book_rag.selection_component import text_selection

load_dotenv(ENV_FILE)  # reads GROQ_API_KEY from the .env file

st.set_page_config(page_title="Reading companion", page_icon=":material/menu_book:", layout="wide")

chat = st.Page(
    "app_pages/chat.py",
    title="Reading companion",
    icon=":material/chat:",
    help="Ask a question about the book. The answer comes with the passages it is based on.",
    default=True,
)
changes = st.Page(
    "app_pages/changes.py",
    title="Changes from the assignment",
    icon=":material/difference:",
    help="Where this app differs from the notebook and the original assignment, and why.",
    url_path="changes",
)
settings = st.Page(
    "app_pages/settings.py",
    title="Settings",
    icon=":material/settings:",
    help="Switch the agent that can search the book again, and see which language model is used.",
    url_path="settings",
)
page = st.navigation([chat, settings, changes], position="hidden")  # the sidebar below has the links

with st.sidebar:
    st.selectbox(
        "Book",
        list(BOOKS),
        index=list(BOOKS).index(DEFAULT_BOOK.id),
        format_func=lambda book_id: BOOKS[book_id].title,
        key="book_id",
        help="Every book has its own vector store. It is built the first time you open the book.",
    )
    st.caption(f"by {BOOKS[st.session_state.book_id].author}")
    if page is chat:
        st.button(
            "Read the book",
            icon=":material/auto_stories:",
            on_click=open_reader,
            args=(st.session_state.book_id,),
            help="Open the text of the book next to the chat, from the beginning.",
            width="stretch",
        )
    st.divider()
    if page is chat:
        selected = text_selection()  # a click on "Ask about this" in the page: the chat page asks it
        if selected:
            st.session_state["selected_text"] = selected
    else:
        st.page_link(chat, label="Back to the chat", icon=":material/arrow_back:")
    if page is not settings:
        st.page_link(settings, label="Settings", icon=":material/settings:")
    if page is not changes:
        st.page_link(changes, label="Changes from the assignment", icon=":material/difference:")

st.title(page.title, icon=page.icon)
page.run()
