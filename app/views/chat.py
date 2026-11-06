"""The chat page: ask questions about the book that is chosen in the sidebar.

A passage can be opened in the book: the page then splits in two, with the chat on the left and the text of
the book on the right, opened at the passage and highlighted.
"""

import streamlit as st
from views import styles

from book_rag import memory
from book_rag.books import get_book
from book_rag.config import AGENTIC_DEFAULT
from book_rag.conversation import build_companion
from book_rag.reader import passage_page
from book_rag.reader_component import book_reader, close_reader, current_reader, open_reader
from book_rag.scroll_component import scroll_to_newest
from book_rag.selection import question_about

VISIBLE_EXCHANGES = 10  # questions and answers drawn at first; "Show earlier" adds this many more
PANE_HEIGHT = 540  # pixels, only a start: views/chat.css sets the real height from the window
READER_WIDTH, READER_PADDING = "38vw", "calc(38vw + 2rem)"  # the book panel, and the room the chat leaves for it
FULL_WIDTH = "calc(100vw - 3rem)"  # full screen: a strip of the page stays visible


@st.cache_resource(show_spinner="Preparing the book (the first time takes a moment) ...")
def load_companion(book_id: str):
    """Open a book once (its vector store and the language models), not on every rerun."""
    return build_companion(get_book(book_id))


def show_searches(queries):
    """When the model searched the book again, say with which questions."""
    if len(queries) > 1:
        st.caption("Searched the book for: " + " · ".join(f"“{query}”" for query in queries))


def show_passages(scored_passages, message_number):
    """Show every passage the answer is based on in an expander, with a button to read it in the book."""
    for rank, (passage, similarity) in enumerate(scored_passages, 1):
        start = passage.metadata["start_index"]
        page = passage_page(book, start)
        with st.expander(f"Passage at position {start:,} (page {page}, similarity {similarity:.2f})"):
            st.write(passage.page_content)
            st.button(
                "Read in the book",
                icon=":material/menu_book:",
                key=f"open-{book.id}-{message_number}-{rank}",
                on_click=open_reader,
                args=(book.id, start, start + len(passage.page_content)),
            )


def toggle_full_screen():
    st.session_state["reader_full"] = not st.session_state.get("reader_full", False)


def show_earlier(book_id):
    st.session_state["visible_exchanges"][book_id] += VISIBLE_EXCHANGES


book = get_book(st.session_state.book_id)
styles.inject("chat")
st.title(book.title)  # outside every scrolling area: it stays in view

companion = load_companion(book.id)

# The history (what is drawn) and the memory (what the model sees) only live in the browser session, one per book.
history = st.session_state.setdefault("histories", {}).setdefault(book.id, [])
chat_memory = st.session_state.setdefault("memories", {}).setdefault(
    book.id, memory.ChatMemory()
)  # what the model sees

# At the root of the page, the input stays at the bottom of the window
question = st.chat_input(f"Ask a question about {book.title}", submit_mode="disable")
if not question and (selected := st.session_state.pop("selected_text", None)):
    question = question_about(selected)  # the reader selected text and clicked "Ask about this"

reader = current_reader(book.id)
chat_area = st.container(height=PANE_HEIGHT, border=False, key="chat-pane")  # scrolls on its own, down to the newest

# Streamlit draws every element it is given, so only the latest exchanges are drawn: a long chat would otherwise
# make every rerun slower and the page heavier (about 130 page elements per question and answer).
visible = st.session_state.setdefault("visible_exchanges", {}).setdefault(book.id, VISIBLE_EXCHANGES)
first_shown = max(0, len(history) - 2 * (visible - bool(question)))  # a new question takes one of the places

with chat_area:
    if first_shown:
        st.button(
            f"Show earlier questions ({first_shown // 2} more)",
            icon=":material/expand_less:",
            key="show-earlier",
            on_click=show_earlier,
            args=(book.id,),
        )
    for number in range(first_shown, len(history)):
        message = history[number]
        with st.chat_message(message["role"]):
            st.write(message["content"])
            show_searches(message.get("queries", []))
            show_passages(message.get("passages", []), number)

    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Searching the book ..."):
                result = companion.respond(
                    question, chat_memory, agentic=st.session_state.get("agentic_on", AGENTIC_DEFAULT)
                )
            st.write(result.answer)
            show_searches(result.queries)
            show_passages(result.passages, len(history) + 1)

        history.append({"role": "user", "content": question})
        history.append(
            {"role": "assistant", "content": result.answer, "passages": result.passages, "queries": result.queries}
        )

with st.container(key="chat-scroller"):  # hidden by chat.css
    scroll_to_newest(f"{book.id}:{len(history)}")

if reader:
    # The book is a panel fixed to the right edge of the window (views/chat.css); it can fill the window.
    full = st.session_state.get("reader_full", False)
    width, padding = (FULL_WIDTH, "0px") if full else (READER_WIDTH, READER_PADDING)
    st.html(f"<style>:root {{ --reader-width: {width}; --reader-padding: {padding}; }}</style>")
    with st.container(key="reader-panel"):
        with st.container(horizontal=True, vertical_alignment="center", key="reader-header"):
            st.markdown(f"**{book.title}**")
            st.button(
                "Exit full screen" if full else "Full screen",
                icon=":material/fullscreen_exit:" if full else ":material/fullscreen:",
                key="reader-expand",
                on_click=toggle_full_screen,
            )
            st.button("Close", icon=":material/close:", key="close-reader", on_click=close_reader)
        book_reader(book, reader["start"], reader["end"], height="stretch")
