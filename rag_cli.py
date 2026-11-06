"""Ask questions about your book in the terminal.

Copy the code of your RAG system from the notebook into this file, then add a
loop so that librarians can ask questions in the terminal.

Run it from the project root with:

    uv run python rag_cli.py
"""

from colorama import Fore, Style, just_fix_windows_console

just_fix_windows_console()  # so that the colours also work in the Windows terminal

# Copy your code from the notebook here: imports, load_dotenv(), the vector store,
# the retriever and the RAG chain.
# Build the vector store only if it is empty, so the script does not embed the book
# again on every run.

# A coloured print: put a colour from Fore before the text and Style.RESET_ALL after it
print(Fore.CYAN + "Ask a question about the book (type quit to exit)." + Style.RESET_ALL)

# Answer questions in the terminal:
# Repeat with a while loop until the user types quit:
#     read a question with input()
#     answer it with your RAG chain
#     print the answer in green (Fore.GREEN) and the passage it is based on in grey (Style.DIM)
