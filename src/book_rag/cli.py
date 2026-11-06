"""Ask questions about the book in the terminal."""

import logging

from colorama import Fore, Style, just_fix_windows_console
from dotenv import load_dotenv

from book_rag.config import ENV_FILE
from book_rag.rag import ScoredPassages, ask, build_chain
from book_rag.store import build_vector_store

EXIT_COMMANDS = {"quit", "exit"}


def print_answer(answer: str, scored_passages: ScoredPassages) -> None:
    """Print the answer in green and its passages, with their similarity, in grey."""
    print("\n" + Fore.GREEN + answer + Style.RESET_ALL)
    for passage, similarity in scored_passages:
        text = f"[start_index {passage.metadata['start_index']} | similarity {similarity:.2f}]\n{passage.page_content}"
        print("\n" + Style.DIM + text + Style.RESET_ALL)


def read_question() -> str | None:
    """Read a question from the terminal. Returns None when the user wants to exit."""
    try:
        question = input(Fore.CYAN + "\n> " + Style.RESET_ALL).strip()
    except (EOFError, KeyboardInterrupt):  # Ctrl+D / Ctrl+C
        return None
    return None if question.lower() in EXIT_COMMANDS else question


def main() -> None:
    just_fix_windows_console()  # so that the colours also work in the Windows terminal
    logging.basicConfig(format=Style.DIM + "%(message)s" + Style.RESET_ALL)  # libraries: warnings only
    logging.getLogger("book_rag").setLevel(logging.INFO)  # but show our own progress messages
    load_dotenv(ENV_FILE)  # reads GROQ_API_KEY from the .env file

    vector_store = build_vector_store()
    chain = build_chain()

    print(Fore.CYAN + "Ask a question about the book (type quit or exit to leave)." + Style.RESET_ALL)
    while (question := read_question()) is not None:
        if question:  # ignore empty input
            print_answer(*ask(question, vector_store, chain))

    print(Fore.CYAN + "Goodbye!" + Style.RESET_ALL)
