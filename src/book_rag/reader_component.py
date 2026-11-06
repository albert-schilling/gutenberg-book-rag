"""The book reader as a Streamlit component, and the state that says which passage is open."""

from pathlib import Path

import streamlit as st

from book_rag.books import Book
from book_rag.reader import reader_data

_HERE = Path(__file__).parent

_HTML = """\
<div class="reader" tabindex="0" role="document" aria-label="Text of the book">
  <div class="edge top"></div>
  <div class="body"></div>
  <div class="edge bottom"></div>
</div>
"""

# Declared once, when the module is imported
_READER = st.components.v2.component(
    "book_reader",
    html=_HTML,
    css=(_HERE / "reader.css").read_text(encoding="utf-8"),
    js=(_HERE / "reader.js").read_text(encoding="utf-8"),
)

STATE_KEY = "reader"


def open_reader(book_id: str, start: int = 0, end: int = 0) -> None:
    """Open the reader at the passage [start, end) of a book (at the beginning of the book if end <= start)."""
    st.session_state[STATE_KEY] = {"book": book_id, "start": start, "end": end}


def close_reader() -> None:
    st.session_state.pop(STATE_KEY, None)


def current_reader(book_id: str) -> dict | None:
    """The open passage if it is in this book, else None."""
    reader = st.session_state.get(STATE_KEY)
    return reader if reader and reader["book"] == book_id else None


def book_reader(book: Book, start: int, end: int, *, height: int) -> None:
    """Show the book, opened at the passage [start, end), in a scrollable panel of the given height."""
    data = {**reader_data(book, start, end), "height": height}
    _READER(data=data, key=f"reader-{book.id}", height=height)
