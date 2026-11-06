"""The books of the library: where each one is, who wrote it, and where the book itself starts and ends.

Every file from Project Gutenberg has a header and a licence around the book (removed everywhere by the
START and END lines). Inside, each book has its own front matter (contents, prefaces, adverts) and back
matter (indexes, printer's lines), so `start` and `end` are small per-book patterns.
"""

from dataclasses import dataclass

from book_rag.config import DATA_DIR


@dataclass(frozen=True)
class Book:
    id: str  # the file name without .txt
    title: str
    author: str
    start: str | None = None  # regex for the first line of the book proper; the text before it is dropped
    end: str | None = None  # regex for the first line after the book proper (the last match counts)

    @property
    def path(self):
        return DATA_DIR / f"{self.id}.txt"


_LIBRARY = [
    Book(
        "adventures_of_pinocchio_collodi", "The Adventures of Pinocchio", "Carlo Collodi",
        start=r"^CHAPTER 1\s*$",
    ),
    Book(
        "adventures_of_sherlock_holmes_doyle", "The Adventures of Sherlock Holmes", "Arthur Conan Doyle",
        start=r"^I\. A SCANDAL IN BOHEMIA\s*$",
    ),
    Book(
        "antarctic_penguins_levick", "Antarctic Penguins: A Study of Their Social Habits", "G. Murray Levick",
        start=r"^\s*INTRODUCTION\s*$", end=r"^\s*PRINTED AT\s*$",
    ),
    Book(
        "climate_in_relation_to_man_ward", "Climate, Considered Especially in Relation to Man", "Robert DeCourcy Ward",
        start=r"^\s*PREFACE\s*$", end=r"^\s*INDEX\s*$",
    ),
    Book(
        "frankenstein_shelley", "Frankenstein; or, The Modern Prometheus", "Mary Wollstonecraft Shelley",
        start=r"^Letter 1\s*$",
    ),
    Book(
        "the_time_machine_wells", "The Time Machine", "H. G. Wells",
        start=r"^\s*I\.\s*$",
    ),
    Book(
        "tom_browns_school_days_hughes", "Tom Brown's School Days", "Thomas Hughes",
        start=r"^PART I\.\s*$",
    ),
    Book(
        "wonderful_wizard_of_oz_baum", "The Wonderful Wizard of Oz", "L. Frank Baum",
        start=r"^Introduction\s*$",
    ),
]

BOOKS: dict[str, Book] = {book.id: book for book in _LIBRARY}
DEFAULT_BOOK = BOOKS["antarctic_penguins_levick"]  # the book of the evaluation and of the command line


def get_book(book_id: str) -> Book:
    try:
        return BOOKS[book_id]
    except KeyError:
        raise ValueError(f"Unknown book '{book_id}'. Choose one of: {', '.join(BOOKS)}") from None
