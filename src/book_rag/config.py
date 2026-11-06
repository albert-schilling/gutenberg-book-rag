"""Settings shared by the command-line tool and the web app."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"  # rebuilt from the book, ignored by Git
ENV_FILE = PROJECT_ROOT / ".env"  # holds GROQ_API_KEY
EVAL_DIR = PROJECT_ROOT / "evals"  # golden questions and the reports of the evaluation runs

EMBEDDING_MODEL = "intfloat/e5-small-v2"  # found in the retrieval experiments, see evals/README.md
QUERY_PREFIX = "query: "  # e5 models expect these prefixes
PASSAGE_PREFIX = "passage: "
LLM_MODEL = "openai/gpt-oss-20b"
JUDGE_MODEL = "openai/gpt-oss-120b"  # grades the answers in the evaluation; a larger model than the generator

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 4  # passages to retrieve per question
MIN_SIMILARITY = 0.0  # passages below this cosine similarity are dropped; 0.0 keeps all (see README of the project)

NO_ANSWER = "The book does not answer this question."
EMPTY_ANSWER_RETRIES = 2  # gpt-oss sometimes returns an empty reply: ask again this many times
FALLBACK_ANSWER = "Sorry, the model did not return an answer. Please ask the question again."
SYSTEM_PROMPT = (  # {title} and {author} are filled in per book, {context} by the chain
    "You are a reading companion for the book '{title}' by {author}. "
    "Answer the question using ONLY the passages below. "
    f'If the passages do not contain the answer, say exactly: "{NO_ANSWER}" '
    "Do not use any other knowledge. Keep the answer short.\n\n"
    "Passages:\n{context}"
)
