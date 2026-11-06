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
    cannot answer have no reference answer and no evidence. Questions about the whole book
    (`kind` "whole-book") are answerable but have no single phrase as evidence, so retrieval is not scored for them.

    `split` is "dev" for the questions that were used while the system was tuned and "test" for those that were not:
    a score on "test" is not inflated by choices made to fit the "dev" questions.
    """

    id: str
    question: str
    reference_answer: str | None
    evidence: tuple[str, ...]
    kind: str = "fact"  # "fact" (a phrase of the book answers it) or "whole-book"
    split: str = "dev"

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
            kind=item.get("kind", "fact"),
            split=item.get("split", "dev"),
        )
        for item in items
    ]
