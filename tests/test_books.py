import pytest

from book_rag.book import load_book
from book_rag.books import BOOKS, DEFAULT_BOOK, Book, get_book

# What the cleaned text of every book must start and end with
EXPECTED = {
    "adventures_of_pinocchio_collodi": ("CHAPTER 1\n\nHow it happened that Mastro Cherry", "a real boy!”"),
    "adventures_of_sherlock_holmes_doyle": ("I. A SCANDAL IN BOHEMIA\n\nI.\n\nTo Sherlock Holmes", "considerable success."),
    "antarctic_penguins_levick": ("INTRODUCTION\n\nThe penguins of the Antarctic", "Expedition 1901-1904."),
    "climate_in_relation_to_man_ward": ("PREFACE\n\nThe preparation of a volume", "benefit to man."),
    "frankenstein_shelley": ("Letter 1\n\n_To Mrs. Saville, England._", "lost in darkness and distance."),
    "the_time_machine_wells": ("I. Introduction\n\nThe Time Traveller", "heart of man."),
    "tom_browns_school_days_hughes": ("PART I.\n\nCHAPTER I--THE BROWN FAMILY", "perfect fullness."),
    "wonderful_wizard_of_oz_baum": ("Introduction\n\nFolklore, legends, myths", "at home again!”"),
}


def test_all_eight_books_are_registered_and_exist():
    assert set(BOOKS) == set(EXPECTED)
    assert all(book.path.is_file() for book in BOOKS.values())
    assert all(book.id == key for key, book in BOOKS.items())


def test_the_default_book_is_the_penguins():
    assert DEFAULT_BOOK.id == "antarctic_penguins_levick"


def test_an_unknown_book_names_the_choices():
    with pytest.raises(ValueError, match="Unknown book 'nope'.*frankenstein_shelley"):
        get_book("nope")


@pytest.mark.parametrize("book", BOOKS.values(), ids=lambda b: b.id)
def test_every_book_is_cleaned_from_its_first_to_its_last_line(book):
    text = load_book(book).page_content
    first, last = EXPECTED[book.id]
    assert text.startswith(first)
    assert text.endswith(last)
    assert len(text) > 150_000
    assert "gutenberg" not in text.lower()  # header, licence and credits are gone
    assert "[Illustration" not in text
    assert "  " not in text


@pytest.mark.parametrize("book", BOOKS.values(), ids=lambda b: b.id)
def test_every_book_has_paragraphs_without_wrapped_lines(book):
    paragraphs = load_book(book).page_content.split("\n\n")
    assert all("\n" not in p and p == p.strip() and p for p in paragraphs)


def test_the_index_of_the_climate_book_is_not_part_of_the_text():
    text = load_book(BOOKS["climate_in_relation_to_man_ward"]).page_content
    assert "Abbe (C.), on changes of climate" not in text


def test_a_start_pattern_that_does_not_match_is_an_error():
    broken = Book("antarctic_penguins_levick", "T", "A", start=r"^THIS LINE IS NOT IN THE BOOK$")
    with pytest.raises(ValueError, match="start of the book"):
        load_book(broken)
    broken = Book("antarctic_penguins_levick", "T", "A", end=r"^THIS LINE IS NOT IN THE BOOK$")
    with pytest.raises(ValueError, match="end of the book"):
        load_book(broken)
