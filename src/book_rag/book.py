"""Read a book from Project Gutenberg and clean it."""

import re

from langchain_core.documents import Document

from book_rag.books import Book


def load_book(book: Book) -> Document:
    """Read the book, keep only the text of the book itself, and join the wrapped lines."""
    raw_text = book.path.read_text(encoding="utf-8")

    start = re.search(r"\*\*\* START OF.*?\*\*\*", raw_text)
    end = re.search(r"\*\*\* END OF.*?\*\*\*", raw_text)
    body = raw_text[start.end():end.start()]

    if book.start:  # front matter: contents, prefaces, adverts
        match = re.search(book.start, body, flags=re.M)
        if not match:
            raise ValueError(f"{book.id}: the start of the book ({book.start!r}) was not found")
        body = body[match.start():]
    if book.end:  # back matter: index, printer's line
        matches = list(re.finditer(book.end, body, flags=re.M))
        if not matches:
            raise ValueError(f"{book.id}: the end of the book ({book.end!r}) was not found")
        body = body[:matches[-1].start()]
    body = re.sub(r"\[Illustration[^\]]*\]", "", body)

    body = re.sub(r"(?<!\n)[ \t]*\n[ \t]*(?!\n)", " ", body)  # join wrapped lines
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\s*\n\s*\n\s*", "\n\n", body).strip()  # one blank line between paragraphs, no indentation

    return Document(page_content=body, metadata={"book": book.id, "title": book.title, "author": book.author})
