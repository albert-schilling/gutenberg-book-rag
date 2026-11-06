"""Read the book from Project Gutenberg and clean it."""

import re

from langchain_core.documents import Document

from book_rag.config import AUTHOR, BOOK, DATA_DIR, TITLE


def load_book() -> Document:
    """Read the book, keep only the text of the book itself, and join the wrapped lines."""
    raw_text = (DATA_DIR / BOOK).read_text(encoding="utf-8")

    start = re.search(r"\*\*\* START OF.*?\*\*\*", raw_text)
    end = re.search(r"\*\*\* END OF.*?\*\*\*", raw_text)
    body = raw_text[start.end():end.start()]

    # front matter: the real text starts at the last "INTRODUCTION" heading (the first is in the contents)
    intro = list(re.finditer(r"^\s*INTRODUCTION\s*$", body, flags=re.M))[-1]
    body = body[intro.start():]
    body = body[:body.rindex("PRINTED AT")]  # printer's line and transcriber's corrections
    body = re.sub(r"\[Illustration[^\]]*\]", "", body)

    body = re.sub(r"(?<!\n)[ \t]*\n[ \t]*(?!\n)", " ", body)  # join wrapped lines
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n\s*\n+", "\n\n", body).strip()

    return Document(page_content=body, metadata={"title": TITLE, "author": AUTHOR})
