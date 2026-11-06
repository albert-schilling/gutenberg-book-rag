"""Settings shared by the command-line tool and the web app."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = Path(
    os.environ.get("BOOK_RAG_CHROMA_DIR", PROJECT_ROOT / "chroma_db")
)  # rebuilt from the book, ignored by Git
ENV_FILE = PROJECT_ROOT / ".env"  # holds GROQ_API_KEY
EVAL_DIR = PROJECT_ROOT / "evals"  # golden questions and the reports of the evaluation runs

# Offline mode (BOOK_RAG_OFFLINE=1): the language model is replaced by a fixed reply, so the app can be tried and
# tested without a Groq key, without rate limits and without cost. Retrieval still runs.
OFFLINE = os.environ.get("BOOK_RAG_OFFLINE") == "1"

# The agent may search the book again before it answers (agent.py). It can use two or three times the tokens of a
# plain answer, and the free Groq plan allows only 8,000 tokens a minute and 200,000 a day: switchable in the sidebar.
AGENTIC_DEFAULT = os.environ.get("BOOK_RAG_AGENT", "1") != "0"

EMBEDDING_MODEL = "intfloat/e5-small-v2"  # found in the retrieval experiments, see evals/README.md
QUERY_PREFIX = "query: "  # e5 models expect these prefixes
PASSAGE_PREFIX = "passage: "
# The language model: BOOK_RAG_LLM=mistral (default) or groq. The second model grades the answers in the evaluation
# and writes the book summaries: a larger model than the one that answers.
LLM_PROVIDER = os.environ.get("BOOK_RAG_LLM", "mistral")
_MODELS = {
    "groq": ("openai/gpt-oss-20b", "openai/gpt-oss-120b"),
    "mistral": ("mistral-small-latest", "mistral-large-latest"),
}
if LLM_PROVIDER not in _MODELS:
    raise ValueError(f"BOOK_RAG_LLM must be one of {sorted(_MODELS)}, not '{LLM_PROVIDER}'")
LLM_MODEL, JUDGE_MODEL = _MODELS[LLM_PROVIDER]
LLM_MODEL = os.environ.get("BOOK_RAG_MODEL", LLM_MODEL)  # e.g. mistral-medium-latest, to compare answer models

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 4  # passages to retrieve per question
MIN_SIMILARITY = 0.0  # passages below this cosine similarity are dropped; 0.0 keeps all (see README of the project)

NO_ANSWER = "The book does not answer this question."
EMPTY_ANSWER_RETRIES = 2  # gpt-oss sometimes returns an empty reply: ask again this many times
FALLBACK_ANSWER = "Sorry, the model did not return an answer. Please ask the question again."
STRICT_REFUSAL_RULE = f'If the passages do not contain the answer, say exactly: "{NO_ANSWER}"'
SOFT_REFUSAL_RULE = (
    "Answer from the passages and the summary whenever they contain the information, even if only in part or in other "
    f'words. Only if they contain nothing relevant to the question, say exactly: "{NO_ANSWER}"'
)
REFUSAL_RULE = SOFT_REFUSAL_RULE if os.environ.get("BOOK_RAG_REFUSAL", "soft") == "soft" else STRICT_REFUSAL_RULE
SYSTEM_PROMPT = (  # {title} and {author} are filled in per book, {context} by the chain
    "You are a reading companion for the book '{title}' by {author}. "
    "Answer the question using ONLY the passages and the summary of the book below. "
    "{refusal_rule} "
    "Do not use any other knowledge. Keep the answer short.\n\n"
    "Summary of the whole book (use it for questions about the book as a whole, such as what it is about):\n"
    "{book_summary}\n\n"
    "Conversation so far, only to understand follow-up questions (facts must come from the passages):\n"
    "{conversation}\n\n"
    "Passages:\n{context}"
)
