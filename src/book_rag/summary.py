"""A short summary of every book, made once and added to every prompt, so that "What is this book about?" can be answered.

A book is 40,000 to 145,000 tokens, but the free Groq plan allows 8,000 tokens per minute. So the summary is made
from evenly spaced excerpts (about 4,500 tokens) with one call per book, and saved in data/summaries/.
"""

import argparse
import logging
import time

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from book_rag.books import BOOKS, Book, get_book
from book_rag.config import DATA_DIR, ENV_FILE, JUDGE_MODEL
from book_rag.reader import paragraph_at, paragraph_starts, paragraphs_of

logger = logging.getLogger(__name__)

SUMMARY_DIR = DATA_DIR / "summaries"
PARTS = 12  # places in the book that an excerpt is taken from
OPENING_CHARS = 1200
ENDING_CHARS = 800
PART_CHARS = 900  # per excerpt in the middle of the book
PARAGRAPH_CHARS = 600  # a longer paragraph is cut
MAX_WORDS = 200  # the summary is sent with every question

PROMPT = """You write the summary of a book for a reading companion that answers questions about it.

Book: {title}, by {author}.
Below are excerpts from evenly spaced places in the book, in order (with how far into the book they are). Use only
these excerpts, not what you remember about the book.

Write a plain-text summary of at most {words} words (no markdown, no headings): what kind of book it is, what it is
about, how it is built (parts, chapters, stories), the main people or subjects, and how it ends or what it concludes.

{excerpts}"""


def summary_path(book: Book):
    return SUMMARY_DIR / f"{book.id}.md"


def load_summary(book: Book) -> str:
    """The saved summary of a book ("" if there is none yet)."""
    path = summary_path(book)
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def _take(paragraphs: list[str] | tuple[str, ...], first: int, budget: int, step: int = 1) -> str:
    """Paragraphs from `first` on (or backwards with step -1) until the budget of characters is used."""
    taken, used, index = [], 0, first
    while 0 <= index < len(paragraphs) and used < budget:
        text = paragraphs[index][:PARAGRAPH_CHARS]
        taken.append(text)
        used += len(text)
        index += step
    return "\n\n".join(taken if step > 0 else reversed(taken))


def sample_excerpts(book: Book) -> str:
    """Excerpts from the opening, from evenly spaced places and from the ending of the book."""
    paragraphs = paragraphs_of(book)
    starts = paragraph_starts(paragraphs)
    total = starts[-1] + len(paragraphs[-1])
    parts = [f"[Excerpt: opening of the book]\n{_take(paragraphs, 0, OPENING_CHARS)}"]
    for number in range(1, PARTS + 1):
        percent = round(100 * number / (PARTS + 1))
        index = paragraph_at(paragraphs, total * number // (PARTS + 1))
        parts.append(f"[Excerpt: {percent}% into the book]\n{_take(paragraphs, index, PART_CHARS)}")
    parts.append(f"[Excerpt: ending of the book]\n{_take(paragraphs, len(paragraphs) - 1, ENDING_CHARS, step=-1)}")
    return "\n\n".join(parts)


def limit_words(text: str, limit: int = MAX_WORDS + 10) -> str:
    """Cut a text that is too long after its last complete sentence within the limit.

    The model does not keep to a word limit, and the summary is sent with every question.
    """
    if len(text.split()) <= limit:
        return text.strip()
    kept = " ".join(text.split()[:limit])
    end = max(kept.rfind(mark) for mark in (". ", "? ", "! ", '." ', ".” "))
    return (kept[: end + 1] if end > len(kept) // 2 else kept.rstrip(",;: ") + " …").strip()


def make_summary(book: Book) -> str:
    """One call to the language model."""
    chain = ChatPromptTemplate.from_template(PROMPT) | ChatGroq(model=JUDGE_MODEL, temperature=0, max_retries=6, reasoning_effort="low") | StrOutputParser()
    summary = chain.invoke(
        {"title": book.title, "author": book.author, "words": MAX_WORDS, "excerpts": sample_excerpts(book)}
    ).strip()
    summary = limit_words(summary)
    if not summary:
        raise RuntimeError(f"The model returned an empty summary for {book.id}")
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Make the summaries of the books (data/summaries/).")
    parser.add_argument("--book", choices=list(BOOKS), help="only this book (default: every book without a summary)")
    parser.add_argument("--force", action="store_true", help="make the summary again, also if there is one")
    parser.add_argument("--pause", type=float, default=65, help="seconds between two books (8,000 tokens a minute)")
    args = parser.parse_args(argv)

    load_dotenv(ENV_FILE)
    books = [get_book(args.book)] if args.book else list(BOOKS.values())
    todo = [book for book in books if args.force or not load_summary(book)]
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    for number, book in enumerate(todo):
        if number:
            time.sleep(args.pause)
        print(f"[{number + 1}/{len(todo)}] {book.title} ...", flush=True)
        summary = make_summary(book)
        summary_path(book).write_text(summary + "\n", encoding="utf-8")
        print(f"    {len(summary.split())} words", flush=True)
    print(f"Done: {len(todo)} summaries made, {len(books) - len(todo)} already there.")
