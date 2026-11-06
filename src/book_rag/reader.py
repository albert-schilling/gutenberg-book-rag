"""The reading view: the paragraphs of a book and where a passage lies in them.

A chunk knows its `start_index`, the position of its first character in the cleaned text of the book. The
cleaned text is made of paragraphs separated by one blank line, so a position can be turned into a paragraph.
"""

from bisect import bisect_right
from functools import lru_cache

from book_rag.book import load_book
from book_rag.books import Book

PARAGRAPH_SEPARATOR = "\n\n"


@lru_cache(maxsize=8)
def paragraphs_of(book: Book) -> tuple[str, ...]:
    """The paragraphs of the cleaned book (cached: the cleaning takes a moment)."""
    return tuple(load_book(book).page_content.split(PARAGRAPH_SEPARATOR))


def paragraph_starts(paragraphs: tuple[str, ...] | list[str]) -> list[int]:
    """The position of the first character of every paragraph in the cleaned text."""
    starts, position = [], 0
    for paragraph in paragraphs:
        starts.append(position)
        position += len(paragraph) + len(PARAGRAPH_SEPARATOR)
    return starts


def paragraph_at(paragraphs: tuple[str, ...] | list[str], position: int) -> int:
    """The index of the paragraph that contains the character at `position`."""
    return max(0, bisect_right(paragraph_starts(paragraphs), position) - 1)


def reader_data(book: Book, start: int = 0, end: int = 0) -> dict:
    """What the reader component needs to open the book at the passage [start, end).

    With `end <= start` the book opens at its beginning, without a highlight.
    """
    paragraphs = paragraphs_of(book)
    highlight = [start, end] if end > start else None
    return {
        "id": f"{book.id}:{start}:{end}",  # the component keeps the scroll position while the id stays the same
        "paragraphs": list(paragraphs),
        "highlight": highlight,
        "focus": paragraph_at(paragraphs, start) if highlight else 0,
    }
