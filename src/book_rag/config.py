"""Settings shared by the command-line tool and the web app."""

import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"  # rebuilt from the book, ignored by Git
ENV_FILE = PROJECT_ROOT / ".env"  # holds GROQ_API_KEY
EVAL_DIR = PROJECT_ROOT / "evals"  # golden questions and the reports of the evaluation runs

BOOK = "antarctic_penguins_levick.txt"
TITLE = "Antarctic Penguins: A Study of Their Social Habits"
AUTHOR = "G. Murray Levick"

EMBEDDING_MODEL = "intfloat/e5-small-v2"  # found in the retrieval experiments, see evals/README.md
QUERY_PREFIX = "query: "  # e5 models expect these prefixes
PASSAGE_PREFIX = "passage: "
LLM_MODEL = "openai/gpt-oss-20b"
JUDGE_MODEL = "openai/gpt-oss-120b"  # grades the answers in the evaluation; a larger model than the generator

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 4  # passages to retrieve per question

# The collection name contains a fingerprint of everything that decides what is stored. After a change
# of the embedding model or the chunking, a new collection is built instead of reusing stale vectors.
_fingerprint = hashlib.sha1(
    f"{EMBEDDING_MODEL}|{QUERY_PREFIX}|{PASSAGE_PREFIX}|{CHUNK_SIZE}|{CHUNK_OVERLAP}".encode()
).hexdigest()[:8]
COLLECTION_NAME = f"penguins-{_fingerprint}"

MIN_SIMILARITY = 0.0  # passages below this cosine similarity are dropped; 0.0 keeps all (see README of the project)

NO_ANSWER = "The book does not answer this question."
EMPTY_ANSWER_RETRIES = 2  # gpt-oss sometimes returns an empty reply: ask again this many times
FALLBACK_ANSWER = "Sorry, the model did not return an answer. Please ask the question again."
SYSTEM_PROMPT = (
    f"You are a reading companion for the book '{TITLE}' by {AUTHOR}. "
    "Answer the question using ONLY the passages below. "
    f'If the passages do not contain the answer, say exactly: "{NO_ANSWER}" '
    "Do not use any other knowledge. Keep the answer short.\n\n"
    "Passages:\n{context}"
)
