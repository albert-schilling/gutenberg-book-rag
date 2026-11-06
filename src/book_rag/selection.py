"""Turn a piece of selected text into a question."""

import re

MAX_LENGTH = 200  # characters of the selection that go into the question


def question_about(selected: str, limit: int = MAX_LENGTH) -> str:
    """The question to ask when the reader selects text and clicks "Ask about this"."""
    text = re.sub(r"\s+", " ", selected).strip().strip("“”\"'")
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + " …"
    return f"What does the book say about “{text}”?"
