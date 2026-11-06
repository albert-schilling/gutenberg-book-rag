from book_rag.book import load_book
from book_rag.config import AUTHOR, TITLE


def test_metadata():
    assert load_book().metadata == {"title": TITLE, "author": AUTHOR}


def test_only_the_book_remains():
    text = load_book().page_content
    assert text.startswith("INTRODUCTION")
    assert "PROJECT GUTENBERG" not in text.upper()  # header, licence and START/END lines are gone
    assert "Transcriber" not in text
    assert "PRINTED AT" not in text
    assert "[Illustration" not in text


def test_wrapped_lines_are_joined():
    paragraphs = load_book().page_content.split("\n\n")
    assert len(paragraphs) > 300
    assert all("\n" not in paragraph for paragraph in paragraphs)  # only blank lines separate paragraphs
    assert all(paragraph and paragraph == paragraph.strip() for paragraph in paragraphs)  # not empty, not indented
    assert "  " not in load_book().page_content  # repeated spaces are collapsed
