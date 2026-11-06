"""UI tests for streamlit_app.py. The vector stores and the language model are replaced by fakes."""

from pathlib import Path

import groq
import httpx
import pytest
import streamlit as st
from langchain_core.documents import Document
from streamlit.testing.v1 import AppTest

from book_rag import agent, llm, memory, rag, store
from book_rag.agent import AgentResult
from book_rag.books import BOOKS, DEFAULT_BOOK
from book_rag.reader import passage_page

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
FRANKENSTEIN = BOOKS["frankenstein_shelley"]


@pytest.fixture
def app(monkeypatch):
    """The app with fake vector stores and a fake `ask`.

    `app.questions` records (question, book id of the vector store) for every question,
    `app.built` the books whose vector store was built.
    """
    questions, built, conversations, summaries, paths = [], [], [], [], []

    def fake_build_vector_store(book):
        built.append(book.id)
        return ("store", book.id)

    def fake_summarizer(summary, question, answer):
        summaries.append(question)
        return f"{summary}|{question}".strip("|")

    def fake_ask(question, vector_store, chain, conversation=""):
        paths.append("plain")
        questions.append((question, vector_store[1]))
        conversations.append(conversation)
        passages = [
            (Document(page_content="Skuas prey upon the chicks.", metadata={"start_index": 147611}), 0.77),
            (Document(page_content="A perpetual feud.", metadata={"start_index": 62105}), 0.71),
        ]
        return f"Answer to: {question}", passages

    monkeypatch.setattr(store, "build_vector_store", fake_build_vector_store)
    monkeypatch.setattr(rag, "build_chain", lambda book: ("chain", book.id))

    def fake_agent_ask(question, vector_store, step_chain, conversation=""):
        if "break" in question:  # a rate limit of the language model
            request = httpx.Request("POST", "https://api.groq.com/x")
            raise groq.RateLimitError(
                "limit. Please try again in 2m5.5s.", response=httpx.Response(429, request=request), body=None
            )
        answer, passages = fake_ask(question, vector_store, step_chain, conversation)
        paths[-1] = "agent"
        queries = [question, "other words"] if "rephrase" in question else [question]
        return AgentResult(answer, passages, queries)

    monkeypatch.setattr(rag, "ask", fake_ask)
    monkeypatch.setattr(agent, "agent_ask", fake_agent_ask)
    monkeypatch.setattr(agent, "build_step_chain", lambda book: ("step", book.id))
    monkeypatch.setattr(memory, "build_summarizer", lambda: fake_summarizer)
    st.cache_resource.clear()  # load_rag() is cached for the whole process: start every test fresh

    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert at.title[0].value == "Reading companion"  # the start screen: the books
    at.switch_page("app_pages/chat.py").run()
    at.questions, at.built, at.conversations, at.summaries, at.paths = questions, built, conversations, summaries, paths
    return at


def choose_book(app, book):
    app.sidebar.selectbox[0].select(book.title).run()
    assert not app.exception


def sidebar_links(app):
    return [link.proto.label for link in app.sidebar.get("page_link")]


def test_the_page_shows_the_default_book_and_an_empty_chat(app):
    assert not app.exception
    assert app.title[0].value == BOOKS[DEFAULT_BOOK.id].title
    assert app.title[0].value == DEFAULT_BOOK.title
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
    page = lambda start: passage_page(DEFAULT_BOOK, start)  # noqa: E731
    assert [e.label for e in app.expander] == [
        f"Passage at position 147,611 (page {page(147611)}, similarity 0.77)",
        f"Passage at position 62,105 (page {page(62105)}, similarity 0.71)",
    ]
    assert app.expander[0].markdown[0].value == "Skuas prey upon the chicks."


def test_the_history_stays_and_the_model_gets_the_latest_exchanges(app):
    app.chat_input[0].set_value("First question").run()
    app.chat_input[0].set_value("Second question").run()

    assert not app.exception
    assert [q for q, _ in app.questions] == ["First question", "Second question"]
    assert [m.name for m in app.chat_message] == ["user", "assistant", "user", "assistant"]
    assert app.chat_message[0].markdown[0].value == "First question"
    assert app.chat_message[3].markdown[0].value == "Answer to: Second question"
    assert len(app.expander) == 4  # two passages per answer, the history keeps its passages
    assert app.conversations[0] == ""  # nothing was said before the first question
    assert "Q: First question\nA: Answer to: First question" in app.conversations[1]  # the second one sees the first


def test_the_model_sees_only_two_exchanges_and_a_summary_of_the_older_ones(app):
    for number in range(1, 5):
        app.chat_input[0].set_value(f"Question {number}").run()
    last = app.conversations[3]  # what the model saw with question 4
    assert "Q: Question 2" in last and "Q: Question 3" in last and "Q: Question 4" not in last
    assert "Q: Question 1" not in last  # too old to be word for word ...
    assert "Summary of the earlier conversation: Question 1" in last  # ... but it is in the summary
    assert app.summaries == ["Question 1", "Question 2"]  # one update for every exchange that left the window


def test_every_book_has_its_own_memory(app):
    app.chat_input[0].set_value("About the penguins").run()
    choose_book(app, FRANKENSTEIN)
    app.chat_input[0].set_value("About the monster").run()
    assert "penguins" not in app.conversations[1]  # the other book's chat is not in this prompt
    choose_book(app, DEFAULT_BOOK)
    app.chat_input[0].set_value("More about the penguins").run()
    assert "Q: About the penguins" in app.conversations[2] and "monster" not in app.conversations[2]


def test_choosing_another_book_changes_the_page_and_the_vector_store(app):
    choose_book(app, FRANKENSTEIN)

    assert app.title[0].value == FRANKENSTEIN.title
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


def test_the_sidebar_links_to_the_other_pages_with_the_settings_above_the_changes(app):
    assert sidebar_links(app) == ["All books", "Settings", "Changes from the assignment"]

    app.switch_page("app_pages/changes.py").run()
    assert not app.exception
    assert sidebar_links(app) == ["All books", "Back to the chat", "Settings"]
    assert app.sidebar.selectbox[0].label == "Book"  # the book stays selectable on every page

    app.switch_page("app_pages/settings.py").run()
    assert not app.exception
    assert sidebar_links(app) == ["All books", "Back to the chat", "Changes from the assignment"]


def test_the_changes_page_documents_the_differences_from_the_assignment(app):
    app.switch_page("app_pages/changes.py").run()

    assert not app.exception
    text = " ".join(m.value for m in app.markdown)
    assert "Embedding model" in text and "e5-small-v2" in text
    assert "Tried and rejected" in text
    assert len(app.chat_input) == 0  # a documentation page, not the chat


def test_the_app_has_a_chat_page_and_a_changes_page(app):
    assert app.title[0].value == BOOKS[DEFAULT_BOOK.id].title
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
        "book": DEFAULT_BOOK.id,
        "start": start,
        "end": start + len("A perpetual feud."),
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


def ask_many(app, count):
    for number in range(count):
        app.chat_input[0].set_value(f"Question {number}").run()
    assert not app.exception


def test_a_long_chat_draws_only_the_latest_exchanges(app):
    ask_many(app, 25)
    assert len(app.chat_message) == 20  # 10 exchanges of a question and an answer
    assert app.chat_message[0].markdown[0].value == "Question 15"  # the oldest one that is drawn
    assert app.chat_message[-1].markdown[0].value == "Answer to: Question 24"
    assert len(app.expander) == 10 * 2  # the fake answer has two passages
    assert [b.label for b in app.button if b.key == "show-earlier"] == ["Show earlier questions (15 more)"]


def test_show_earlier_draws_ten_more_exchanges_and_nothing_is_lost(app):
    ask_many(app, 25)
    next(b for b in app.button if b.key == "show-earlier").click().run()
    assert len(app.chat_message) == 40
    assert app.chat_message[0].markdown[0].value == "Question 5"
    next(b for b in app.button if b.key == "show-earlier").click().run()
    assert len(app.chat_message) == 50  # all 25 exchanges
    assert not [b for b in app.button if b.key == "show-earlier"]  # nothing left to show
    assert app.chat_message[0].markdown[0].value == "Question 0"


def test_a_short_chat_has_no_show_earlier_button(app):
    ask_many(app, 10)
    assert len(app.chat_message) == 20
    assert not [b for b in app.button if b.key == "show-earlier"]


def test_every_book_counts_its_own_visible_exchanges(app):
    ask_many(app, 12)
    choose_book(app, FRANKENSTEIN)
    ask_many(app, 3)
    assert len(app.chat_message) == 6 and not [b for b in app.button if b.key == "show-earlier"]
    choose_book(app, DEFAULT_BOOK)
    assert len(app.chat_message) == 20 and [b for b in app.button if b.key == "show-earlier"]


def set_agent(app, on):
    """Switch the agent on the Settings page and go back to the chat."""
    app.switch_page("app_pages/settings.py").run()
    assert not app.exception
    next(t for t in app.toggle if t.label == "Search again when needed").set_value(on).run()
    app.switch_page("app_pages/chat.py").run()
    assert not app.exception


def test_the_settings_page_shows_the_agent_switch_off_and_the_model(app):
    app.switch_page("app_pages/settings.py").run()
    assert not app.exception
    switch = next(t for t in app.toggle if t.label == "Search again when needed")
    assert switch.value is False  # off by default
    text = " ".join(c.value for c in app.caption)
    assert llm.LLM_PROVIDER.capitalize() in text and "BOOK_RAG_LLM" in text and "1.7 to 3.2 calls" in text
    assert len(app.chat_input) == 0  # a settings page, not the chat
    assert not list(app.sidebar.toggle)  # the switch is no longer in the sidebar


def test_the_model_does_not_search_again_by_default_and_the_settings_page_can_switch_it_on(app):
    app.chat_input[0].set_value("First").run()
    set_agent(app, True)
    app.chat_input[0].set_value("Second").run()
    set_agent(app, False)
    app.chat_input[0].set_value("Third").run()
    assert not app.exception
    assert app.paths == ["plain", "agent", "plain"]


def test_the_agent_choice_survives_a_visit_to_other_pages_and_another_book(app):
    set_agent(app, True)
    app.switch_page("app_pages/changes.py").run()
    app.switch_page("app_pages/settings.py").run()
    assert next(t for t in app.toggle if t.label == "Search again when needed").value is True  # the page remembers it
    app.switch_page("app_pages/chat.py").run()
    choose_book(app, FRANKENSTEIN)
    app.chat_input[0].set_value("Q").run()
    assert app.paths == ["agent"]


def test_the_searches_of_the_model_are_shown_under_the_answer_and_stay_in_the_history(app):
    set_agent(app, True)
    app.chat_input[0].set_value("Please rephrase this").run()
    caption = [c.value for c in app.caption if c.value.startswith("Searched the book for")]
    assert caption == ["Searched the book for: “Please rephrase this” · “other words”"]
    app.chat_input[0].set_value("A plain question").run()
    captions = [c.value for c in app.caption if c.value.startswith("Searched the book for")]
    assert captions == ["Searched the book for: “Please rephrase this” · “other words”"]  # still there, only once
    assert len(app.chat_message) == 4


def test_a_question_with_one_search_shows_no_searches_line(app):
    app.chat_input[0].set_value("A plain question").run()
    assert not [c for c in app.caption if c.value.startswith("Searched the book for")]


def test_a_rate_limit_is_shown_as_a_message_and_the_chat_goes_on(app):
    set_agent(app, True)  # the fake model fails in the agent
    app.chat_input[0].set_value("please break").run()
    assert not app.exception
    assert (
        app.chat_message[1].markdown[0].value
        == f"The free {llm.LLM_PROVIDER.capitalize()} plan is at its limit for now. Please try again in 2m5s."
    )
    app.chat_input[0].set_value("Next question").run()
    assert not app.exception and app.conversations[-1] == ""  # the failed exchange is not in the memory


def test_the_start_screen_shows_every_book_and_a_click_opens_its_chat(app):
    app.switch_page("app_pages/home.py").run()
    assert not app.exception
    text = " ".join(m.value for m in app.markdown)
    assert all(book.title in text for book in BOOKS.values())
    assert len(app.chat_input) == 0
    open_buttons = [b for b in app.button if b.key and b.key.startswith("open-chat-")]
    assert len(open_buttons) == len(BOOKS)

    next(b for b in open_buttons if b.key == f"open-chat-{FRANKENSTEIN.id}").click().run()
    assert not app.exception
    assert app.title[0].value == FRANKENSTEIN.title  # moved to the chat of that book
    assert app.sidebar.selectbox[0].value == FRANKENSTEIN.id
    assert len(app.chat_input) == 1
