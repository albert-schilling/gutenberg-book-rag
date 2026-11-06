"""The start screen: the books of the library. A click opens the chat of that book."""

import streamlit as st

from app_pages import styles
from book_rag.books import BOOKS

COLUMNS = 3


def open_chat(book_id: str) -> None:
    st.session_state["open_book"] = book_id  # streamlit_app.py selects the book and moves to the chat


styles.inject("home")
st.caption("Choose a book and ask it questions. Every answer shows the passages of the book it is based on.")

books = list(BOOKS.values())
for row in range(0, len(books), COLUMNS):
    for column, book in zip(st.columns(COLUMNS), books[row : row + COLUMNS], strict=False):
        with column, st.container(border=True, key=f"book-{book.id}"):
            st.markdown(f"### {book.title}")
            st.caption(f"by {book.author}")
            st.write(book.blurb)
            st.button(
                "Ask this book",
                icon=":material/chat:",
                key=f"open-chat-{book.id}",
                on_click=open_chat,
                args=(book.id,),
                width="stretch",
            )
