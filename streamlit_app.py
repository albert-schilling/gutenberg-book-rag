"""A small web app to ask questions about the book.

Run it from the project root with:

    uv run streamlit run streamlit_app.py
"""

import streamlit as st
from dotenv import load_dotenv

from book_rag.config import ENV_FILE

load_dotenv(ENV_FILE)  # reads GROQ_API_KEY from the .env file

st.set_page_config(page_title="Reading companion", page_icon=":material/menu_book:")

page = st.navigation(
    [
        st.Page(
            "app_pages/chat.py",
            title="Reading companion",
            icon=":material/chat:",
            help="Ask a question about the book. The answer comes with the passages it is based on.",
        ),
        st.Page(
            "app_pages/changes.py",
            title="Changes from the assignment",
            icon=":material/difference:",
            help="Where this app differs from the notebook and the original assignment, and why.",
            url_path="changes",
        ),
    ]
)

st.title(page.title, icon=page.icon)
page.run()
