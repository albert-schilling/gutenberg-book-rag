"""Metrics that need no language model: the same input always gives the same score."""

from book_rag.config import NO_ANSWER


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def evidence_found(evidence: tuple[str, ...], passages: list[str]) -> list[bool]:
    """For every evidence phrase: is it in at least one retrieved passage?"""
    texts = [_normalize(p) for p in passages]
    return [any(_normalize(phrase) in text for text in texts) for phrase in evidence]


def context_recall(evidence: tuple[str, ...], passages: list[str]) -> float:
    """Share of the evidence phrases that the retrieved passages contain (1.0 = all of them)."""
    found = evidence_found(evidence, passages)
    return sum(found) / len(found)


def hit(evidence: tuple[str, ...], passages: list[str]) -> bool:
    """Does at least one retrieved passage contain evidence?"""
    return any(evidence_found(evidence, passages))


def reciprocal_rank(evidence: tuple[str, ...], passages: list[str]) -> float:
    """1 / rank of the first passage that contains evidence (0.0 if none does)."""
    for rank, passage in enumerate(passages, 1):
        if any(evidence_found(evidence, [passage])):
            return 1 / rank
    return 0.0


def context_precision(evidence: tuple[str, ...], passages: list[str]) -> float:
    """Share of the retrieved passages that contain evidence (0.0 if nothing was retrieved)."""
    if not passages:
        return 0.0
    return sum(any(evidence_found(evidence, [p])) for p in passages) / len(passages)


def is_abstention(answer: str) -> bool:
    """Did the system say that the book does not answer the question?"""
    return _normalize(NO_ANSWER) in _normalize(answer)


def abstention_correct(answerable: bool, answer: str) -> bool:
    """Answerable questions should be answered, unanswerable ones should get the abstention."""
    return is_abstention(answer) != answerable


def mean(values: list[float | None]) -> float | None:
    """Average without the missing values (None if nothing is left)."""
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None
