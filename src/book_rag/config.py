"""Settings shared by the command-line tool and the web app."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"  # rebuilt from the book, ignored by Git
ENV_FILE = PROJECT_ROOT / ".env"  # holds GROQ_API_KEY
EVAL_DIR = PROJECT_ROOT / "evals"  # golden questions and the reports of the evaluation runs

BOOK = "antarctic_penguins_levick.txt"
TITLE = "Antarctic Penguins: A Study of Their Social Habits"
AUTHOR = "G. Murray Levick"

COLLECTION_NAME = "penguins"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "openai/gpt-oss-20b"
JUDGE_MODEL = "openai/gpt-oss-120b"  # grades the answers in the evaluation; a larger model than the generator

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 4  # passages to retrieve per question
MIN_SIMILARITY = 0.0  # passages below this cosine similarity are dropped; 0.0 keeps all (see README of the project)

NO_ANSWER = "The book does not answer this question."
SYSTEM_PROMPT = (
    f"You are a reading companion for the book '{TITLE}' by {AUTHOR}. "
    "Answer the question using ONLY the passages below. "
    f'If the passages do not contain the answer, say exactly: "{NO_ANSWER}" '
    "Do not use any other knowledge. Keep the answer short.\n\n"
    "Passages:\n{context}"
)
