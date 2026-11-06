"""UI tests for streamlit_app.py. The vector stores and the language model are replaced by fakes."""

from pathlib import Path

import pytest
import streamlit as st
from langchain_core.documents import Document
from streamlit.testing.v1 import AppTest

from book_rag import rag, store
from book_rag.books import BOOKS, DEFAULT_BOOK

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
FRANKENSTEIN = BOOKS["frankenstein_shelley"]


@pytest.fixture
def app(monkeypatch):
    """The app with fake vector stores and a fake `ask`.

    `app.questions` records (question, book id of the vector store) for every question,
    `app.built` the books whose vector store was built.
    """
    questions, built = [], []

    def fake_build_vector_store(book):
        built.append(book.id)
        return ("store", book.id)

    def fake_ask(question, vector_store, chain):
        questions.append((question, vector_store[1]))
        passages = [
            (Document(page_content="Skuas prey upon the chicks.", metadata={"start_index": 147611}), 0.77),
            (Document(page_content="A perpetual feud.", metadata={"start_index": 62105}), 0.71),
        ]
        return f"Answer to: {question}", passages

    monkeypatch.setattr(store, "build_vector_store", fake_build_vector_store)
    monkeypatch.setattr(rag, "build_chain", lambda book: ("chain", book.id))
    monkeypatch.setattr(rag, "ask", fake_ask)
    st.cache_resource.clear()  # load_rag() is cached for the whole process: start every test fresh

    at = AppTest.from_file(str(APP), default_timeout=30).run()
    at.questions, at.built = questions, built
    return at


def choose_book(app, book):
    app.sidebar.selectbox[0].select(book.title).run()
    assert not app.exception


def sidebar_links(app):
    return [link.proto.label for link in app.sidebar.get("page_link")]


def test_the_page_shows_the_default_book_and_an_empty_chat(app):
    assert not app.exception
    assert app.title[0].value == "Reading companion"
    assert DEFAULT_BOOK.title in app.caption[0].value
    assert len(app.chat_message) == 0
    assert DEFAULT_BOOK.title in app.chat_input[0].placeholder


def test_the_sidebar_offers_all_eight_books(app):
    book = app.sidebar.selectbox[0]
    assert book.label == "Book"
    assert book.value == DEFAULT_BOOK.id
    assert sorted(book.options) == sorted(b.title for b in BOOKS.values())
    assert len(book.options) == 8
    assert f"by {DEFAULT_BOOK.author}" in app.sidebar.caption[0].value


def test_a_question_shows_the_answer_and_its_passages(app):
    app.chat_input[0].set_value("What do skua gulls do?").run()

    assert not app.exception
    assert app.questions == [("What do skua gulls do?", DEFAULT_BOOK.id)]
    user, assistant = app.chat_message
    assert user.markdown[0].value == "What do skua gulls do?"
    assert assistant.markdown[0].value == "Answer to: What do skua gulls do?"
    assert [e.label for e in app.expander] == [
        "Passage at position 147,611 (similarity 0.77)",
        "Passage at position 62,105 (similarity 0.71)",
    ]
    assert app.expander[0].markdown[0].value == "Skuas prey upon the chicks."


def test_the_history_stays_but_each_question_is_asked_alone(app):
    app.chat_input[0].set_value("First question").run()
    app.chat_input[0].set_value("Second question").run()

    assert not app.exception
    assert [q for q, _ in app.questions] == ["First question", "Second question"]  # no earlier turns are passed on
    assert [m.name for m in app.chat_message] == ["user", "assistant", "user", "assistant"]
    assert app.chat_message[0].markdown[0].value == "First question"
    assert app.chat_message[3].markdown[0].value == "Answer to: Second question"
    assert len(app.expander) == 4  # two passages per answer, the history keeps its passages


def test_choosing_another_book_changes_the_page_and_the_vector_store(app):
    choose_book(app, FRANKENSTEIN)

    assert FRANKENSTEIN.title in app.caption[0].value
    assert FRANKENSTEIN.title in app.chat_input[0].placeholder
    assert f"by {FRANKENSTEIN.author}" in app.sidebar.caption[0].value

    app.chat_input[0].set_value("Who is the monster?").run()
    assert app.questions == [("Who is the monster?", FRANKENSTEIN.id)]  # asked in the vector store of that book


def test_every_book_keeps_its_own_history(app):
    app.chat_input[0].set_value("About the penguins").run()
    choose_book(app, FRANKENSTEIN)
    assert len(app.chat_message) == 0  # a new book starts with an empty chat
    app.chat_input[0].set_value("About the monster").run()
    assert [m.markdown[0].value for m in app.chat_message][0] == "About the monster"

    choose_book(app, DEFAULT_BOOK)
    assert [m.markdown[0].value for m in app.chat_message][0] == "About the penguins"
    assert len(app.chat_message) == 2


def test_the_rag_system_of_a_book_is_loaded_only_once(app):
    app.chat_input[0].set_value("One").run()
    app.chat_input[0].set_value("Two").run()
    assert app.built == [DEFAULT_BOOK.id]

    choose_book(app, FRANKENSTEIN)
    choose_book(app, DEFAULT_BOOK)
    choose_book(app, FRANKENSTEIN)
    assert app.built == [DEFAULT_BOOK.id, FRANKENSTEIN.id]  # each book once, then it comes from the cache


def test_the_sidebar_links_to_the_changes_page_and_back(app):
    assert sidebar_links(app) == ["Changes from the assignment"]

    app.switch_page("app_pages/changes.py").run()
    assert not app.exception
    assert sidebar_links(app) == ["Back to the chat"]
    assert app.sidebar.selectbox[0].label == "Book"  # the book stays selectable on every page


def test_the_changes_page_documents_the_differences_from_the_assignment(app):
    app.switch_page("app_pages/changes.py").run()

    assert not app.exception
    text = " ".join(m.value for m in app.markdown)
    assert "Embedding model" in text and "e5-small-v2" in text
    assert "Tried and rejected" in text
    assert len(app.chat_input) == 0  # a documentation page, not the chat


def test_the_app_has_a_chat_page_and_a_changes_page(app):
    assert app.title[0].value == "Reading companion"
    app.switch_page("app_pages/changes.py").run()
    assert app.title[0].value == "Changes from the assignment"


def test_the_selected_book_survives_a_visit_to_the_changes_page(app):
    choose_book(app, FRANKENSTEIN)
    app.switch_page("app_pages/changes.py").run()
    app.switch_page("app_pages/chat.py").run()
    assert not app.exception
    assert app.sidebar.selectbox[0].value == FRANKENSTEIN.id


def passage_buttons(app):
    return [b for b in app.button if b.label == "Read in the book"]


def book_is_open(app):
    """The book is open when its panel, with the Close button, is next to the chat."""
    return any(b.label == "Close" for b in app.button)


def test_every_passage_has_a_button_to_read_it_in_the_book(app):
    app.chat_input[0].set_value("First").run()
    app.chat_input[0].set_value("Second").run()
    assert not app.exception  # no two buttons share a key
    assert len(passage_buttons(app)) == 4  # two passages for each of the two answers


def test_the_book_is_closed_until_a_passage_is_opened(app):
    app.chat_input[0].set_value("Q").run()
    assert "reader" not in app.session_state
    assert not book_is_open(app)


def test_clicking_a_passage_opens_the_book_at_that_passage_next_to_the_chat(app):
    app.chat_input[0].set_value("Q").run()
    passage_buttons(app)[1].click().run()

    assert not app.exception
    start = 62105  # the second fake passage
    assert app.session_state["reader"] == {
        "book": DEFAULT_BOOK.id, "start": start, "end": start + len("A perpetual feud."),
    }
    assert book_is_open(app)  # the book on the right ...
    assert len(app.chat_message) == 2  # ... and the chat is still there
    assert app.markdown[-1].value == f"**{DEFAULT_BOOK.title}**" or any(
        m.value == f"**{DEFAULT_BOOK.title}**" for m in app.markdown
    )


def test_the_close_button_closes_the_book(app):
    app.chat_input[0].set_value("Q").run()
    passage_buttons(app)[0].click().run()
    next(b for b in app.button if b.label == "Close").click().run()

    assert not app.exception
    assert "reader" not in app.session_state
    assert not book_is_open(app)
    assert len(app.chat_message) == 2


def test_the_sidebar_opens_the_book_from_the_beginning(app):
    app.sidebar.button[0].click().run()

    assert not app.exception
    assert app.sidebar.button[0].label == "Read the book"
    assert app.session_state["reader"] == {"book": DEFAULT_BOOK.id, "start": 0, "end": 0}
    assert book_is_open(app)


def test_an_open_book_does_not_follow_to_another_book(app):
    app.chat_input[0].set_value("Q").run()
    passage_buttons(app)[0].click().run()
    assert book_is_open(app)

    choose_book(app, FRANKENSTEIN)
    assert not book_is_open(app)  # the open passage belongs to the penguin book

    choose_book(app, DEFAULT_BOOK)
    assert book_is_open(app)  # and is still open there
