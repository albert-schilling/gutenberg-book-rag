import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter

from book_rag import reader
from book_rag.book import load_book
from book_rag.books import BOOKS, DEFAULT_BOOK
from book_rag.config import CHUNK_OVERLAP, CHUNK_SIZE

PARAGRAPHS = ["First paragraph.", "Second one is longer.", "Third."]  # joined: 16 + 2 + 21 + 2 + 6 characters
TEXT = "\n\n".join(PARAGRAPHS)


def test_paragraph_starts():
    assert reader.paragraph_starts(PARAGRAPHS) == [0, 18, 41]
    assert TEXT[18:].startswith("Second") and TEXT[41:] == "Third."


@pytest.mark.parametrize(("position", "index"), [(0, 0), (15, 0), (18, 1), (30, 1), (41, 2), (46, 2), (10_000, 2)])
def test_a_position_belongs_to_a_paragraph(position, index):
    assert reader.paragraph_at(PARAGRAPHS, position) == index


@pytest.mark.parametrize("book", BOOKS.values(), ids=lambda b: b.id)
def test_the_paragraphs_make_up_the_cleaned_text_exactly(book):
    paragraphs = reader.paragraphs_of(book)
    assert reader.PARAGRAPH_SEPARATOR.join(paragraphs) == load_book(book).page_content
    assert reader.paragraph_starts(paragraphs)[-1] + len(paragraphs[-1]) == len(load_book(book).page_content)


def test_every_chunk_of_a_book_starts_inside_the_paragraph_that_is_found_for_it():
    """The reader opens at `start_index`: it must land in the paragraph where the chunk begins."""
    document = load_book(DEFAULT_BOOK)
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, add_start_index=True
    ).split_documents([document])
    paragraphs = reader.paragraphs_of(DEFAULT_BOOK)
    starts = reader.paragraph_starts(paragraphs)

    for chunk in chunks:
        start = chunk.metadata["start_index"]
        index = reader.paragraph_at(paragraphs, start)
        assert starts[index] <= start < starts[index] + len(paragraphs[index])  # not in a blank line between two
        first_paragraph_of_the_chunk = chunk.page_content.split("\n\n")[0]
        assert paragraphs[index][start - starts[index]:].startswith(first_paragraph_of_the_chunk)


def test_reader_data_for_a_passage():
    start, end = 4_000, 5_000
    data = reader.reader_data(DEFAULT_BOOK, start, end)
    paragraphs = reader.paragraphs_of(DEFAULT_BOOK)
    assert data["paragraphs"] == list(paragraphs)
    assert data["highlight"] == [start, end]
    assert data["focus"] == reader.paragraph_at(paragraphs, start) > 0
    assert data["id"] == f"{DEFAULT_BOOK.id}:{start}:{end}"


def test_reader_data_without_a_passage_opens_at_the_start_without_highlight():
    data = reader.reader_data(DEFAULT_BOOK)
    assert data["highlight"] is None and data["focus"] == 0
    assert reader.reader_data(DEFAULT_BOOK, 500, 500)["highlight"] is None  # an empty passage is no passage


def test_a_different_passage_has_a_different_id_so_the_reader_moves():
    assert reader.reader_data(DEFAULT_BOOK, 10, 20)["id"] != reader.reader_data(DEFAULT_BOOK, 10, 30)["id"]
    assert reader.reader_data(DEFAULT_BOOK, 10, 20)["id"] == reader.reader_data(DEFAULT_BOOK, 10, 20)["id"]


def test_the_number_of_pages_follows_the_length_of_the_book():
    for book in BOOKS.values():
        text_length = len(load_book(book).page_content)
        assert reader.page_count(book) == -(-text_length // reader.PAGE_CHARS)
    assert reader.page_count(DEFAULT_BOOK) == 64  # 158,680 characters


def test_a_passage_is_on_the_page_where_its_paragraph_begins():
    paragraphs = reader.paragraphs_of(DEFAULT_BOOK)
    starts = reader.paragraph_starts(paragraphs)
    index = 200
    paragraph_start = starts[index]
    expected = paragraph_start // reader.PAGE_CHARS + 1
    assert reader.passage_page(DEFAULT_BOOK, paragraph_start) == expected
    assert reader.passage_page(DEFAULT_BOOK, paragraph_start + len(paragraphs[index]) - 1) == expected  # inside the paragraph
    assert reader.passage_page(DEFAULT_BOOK, 0) == 1


def test_a_jump_target_opens_the_book_there_without_a_highlight():
    data = reader.reader_data(DEFAULT_BOOK, 50_000, 50_000)
    assert data["highlight"] is None and data["focus"] == reader.paragraph_at(reader.paragraphs_of(DEFAULT_BOOK), 50_000) > 0
    assert data["pageChars"] == reader.PAGE_CHARS
