"""The golden questions."""

import json
from dataclasses import dataclass
from pathlib import Path

from book_rag.config import EVAL_DIR

DATASET_FILE = EVAL_DIR / "dataset.json"


@dataclass(frozen=True)
class EvalCase:
    """One golden question.

    `evidence` are phrases copied from the cleaned book. A retrieval is good when the
    retrieved passages contain them. Phrases (not chunk ids or positions) keep the dataset
    valid when the chunk size, the overlap or the cleaning change. Questions that the book
    cannot answer have no reference answer and no evidence.
    """

    id: str
    question: str
    reference_answer: str | None
    evidence: tuple[str, ...]

    @property
    def answerable(self) -> bool:
        return self.reference_answer is not None


def load_dataset(path: Path = DATASET_FILE) -> list[EvalCase]:
    items = json.loads(path.read_text(encoding="utf-8"))
    return [
        EvalCase(
            id=item["id"],
            question=item["question"],
            reference_answer=item["reference_answer"],
            evidence=tuple(item["evidence"]),
        )
        for item in items
    ]
