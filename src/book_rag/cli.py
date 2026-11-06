"""Ask questions about the book in the terminal."""

import argparse
import logging

from colorama import Fore, Style, just_fix_windows_console
from dotenv import load_dotenv

from book_rag.agent import AgentResult
from book_rag.books import BOOKS, DEFAULT_BOOK, get_book
from book_rag.config import AGENTIC_DEFAULT, ENV_FILE
from book_rag.conversation import build_companion
from book_rag.memory import ChatMemory

EXIT_COMMANDS = {"quit", "exit"}


def print_answer(result: AgentResult) -> None:
    """Print the answer in green, the searches and the passages, with their similarity, in grey."""
    print("\n" + Fore.GREEN + result.answer + Style.RESET_ALL)
    if len(result.queries) > 1:
        print(
            Style.DIM
            + "Searched the book for: "
            + " · ".join(f"“{query}”" for query in result.queries)
            + Style.RESET_ALL
        )
    for passage, similarity in result.passages:
        text = f"[start_index {passage.metadata['start_index']} | similarity {similarity:.2f}]\n{passage.page_content}"
        print("\n" + Style.DIM + text + Style.RESET_ALL)


def read_question() -> str | None:
    """Read a question from the terminal. Returns None when the user wants to exit."""
    try:
        question = input(Fore.CYAN + "\n> " + Style.RESET_ALL).strip()
    except (EOFError, KeyboardInterrupt):  # Ctrl+D / Ctrl+C
        return None
    return None if question.lower() in EXIT_COMMANDS else question


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ask questions about a book in the terminal.")
    parser.add_argument("--book", default=DEFAULT_BOOK.id, choices=list(BOOKS), help="the book to ask about")
    parser.add_argument(
        "--agent",
        action=argparse.BooleanOptionalAction,
        default=AGENTIC_DEFAULT,
        help="let the model search the book again before it answers (off by default: it uses more tokens)",
    )
    args = parser.parse_args(argv)
    book = get_book(args.book)

    just_fix_windows_console()  # so that the colours also work in the Windows terminal
    logging.basicConfig(format=Style.DIM + "%(message)s" + Style.RESET_ALL)  # libraries: warnings only
    logging.getLogger("book_rag").setLevel(logging.INFO)  # but show our own progress messages
    load_dotenv(ENV_FILE)  # reads GROQ_API_KEY from the .env file

    companion = build_companion(book)
    chat_memory = ChatMemory()  # the last exchanges and a summary of the older ones go into every question

    print(Fore.CYAN + f"Ask a question about {book.title} (type quit or exit to leave)." + Style.RESET_ALL)
    while (question := read_question()) is not None:
        if question:  # ignore empty input
            print_answer(companion.respond(question, chat_memory, agentic=args.agent))

    print(Fore.CYAN + "Goodbye!" + Style.RESET_ALL)
