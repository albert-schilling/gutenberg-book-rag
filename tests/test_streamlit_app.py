"""UI tests for streamlit_app.py. The vector store and the language model are replaced by fakes."""

from pathlib import Path

import pytest
import streamlit as st
from langchain_core.documents import Document
from streamlit.testing.v1 import AppTest

from book_rag import rag, store

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


@pytest.fixture
def app(monkeypatch):
    """The app with a fake vector store and a fake `ask`. `questions` records what the app asked."""
    questions = []

    def fake_ask(question, vector_store, chain):
        questions.append(question)
        passages = [
            (Document(page_content="Skuas prey upon the chicks.", metadata={"start_index": 147611}), 0.77),
            (Document(page_content="A perpetual feud.", metadata={"start_index": 62105}), 0.71),
        ]
        return f"Answer to: {question}", passages

    monkeypatch.setattr(store, "build_vector_store", lambda: object())
    monkeypatch.setattr(rag, "build_chain", lambda: object())
    monkeypatch.setattr(rag, "ask", fake_ask)
    st.cache_resource.clear()  # load_rag() is cached for the whole process: start every test fresh

    at = AppTest.from_file(str(APP), default_timeout=30).run()
    at.questions = questions
    return at


def test_the_page_shows_the_book_and_an_empty_chat(app):
    assert not app.exception
    assert app.title[0].value == "Reading companion"
    assert "Antarctic Penguins" in app.caption[0].value
    assert len(app.chat_message) == 0
    assert app.chat_input[0].placeholder == "Ask a question about the book"


def test_a_question_shows_the_answer_and_its_passages(app):
    app.chat_input[0].set_value("What do skua gulls do?").run()

    assert not app.exception
    assert app.questions == ["What do skua gulls do?"]
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
    assert app.questions == ["First question", "Second question"]  # no earlier turns are passed on
    assert [m.name for m in app.chat_message] == ["user", "assistant", "user", "assistant"]
    assert app.chat_message[0].markdown[0].value == "First question"
    assert app.chat_message[3].markdown[0].value == "Answer to: Second question"
    assert len(app.expander) == 4  # two passages per answer, the history keeps its passages


def test_the_app_loads_the_rag_system_only_once(app, monkeypatch):
    calls = []
    monkeypatch.setattr(store, "build_vector_store", lambda: calls.append(1) or object())
    st.cache_resource.clear()

    at = AppTest.from_file(str(APP), default_timeout=30).run()
    at.chat_input[0].set_value("One").run()
    at.chat_input[0].set_value("Two").run()

    assert calls == [1]


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
