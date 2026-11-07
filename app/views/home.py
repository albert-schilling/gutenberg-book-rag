"""The start screen: the books of the library on a shelf. A click on a spine opens the chat of that book."""

import streamlit as st
from views import styles

from book_rag.books import BOOKS

# Cloth colours of the spines, in the order of the library
SPINE_COLOURS = ["#7a2e35", "#2f4a64", "#3f5b49", "#8a5a3b", "#55486b", "#37606a", "#6e3f4d", "#4b4f55"]
SHELF_HEIGHT = 520  # pixels, only a start: home.css sets the real height from the window


def open_chat(book_id: str) -> None:
    st.session_state["open_book"] = book_id  # streamlit_app.py selects the book and moves to the chat


def spine_title(book) -> str:
    """The short title on the spine: without the subtitle ("Antarctic Penguins: A Study ...")."""
    return book.title.split(":")[0].split(";")[0]


def spine_css() -> str:
    """One cloth colour per book; all spines have the same size."""
    rules = []
    for number, book in enumerate(BOOKS.values()):
        rules.append(
            f".st-key-open-chat-{book.id} button {{ background: {SPINE_COLOURS[number % len(SPINE_COLOURS)]}; }}"
        )
    return "<style>" + "\n".join(rules) + "</style>"


styles.inject("home")
st.html(spine_css())
st.caption("Take a book from the shelf and ask it questions. Every answer shows the passages it is based on.")

# the only part of the page that scrolls: the shelf area; the shelf in it
with (
    st.container(height=SHELF_HEIGHT, border=False, key="shelf-scroll"),
    st.container(horizontal=True, vertical_alignment="bottom", gap="small", key="shelf"),
):
    for book in BOOKS.values():
        st.button(
            f"{spine_title(book)}\n\n{book.author}",
            key=f"open-chat-{book.id}",
            on_click=open_chat,
            args=(book.id,),
            help=f"{book.author}. {book.blurb}",
        )
