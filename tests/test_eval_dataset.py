import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter

from book_rag.book import load_book
from book_rag.config import CHUNK_OVERLAP, CHUNK_SIZE
from book_rag.evaluation.dataset import load_dataset
from book_rag.evaluation.metrics import evidence_found

CASES = load_dataset()


def test_the_dataset_has_enough_questions_of_both_kinds():
    assert len([c for c in CASES if c.answerable]) >= 15
    assert len([c for c in CASES if not c.answerable]) >= 3


def test_ids_are_unique():
    assert len({c.id for c in CASES}) == len(CASES)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_answerable_cases_have_a_reference_and_evidence(case):
    assert case.question.endswith("?")
    if case.answerable:
        assert case.reference_answer.strip()
        assert case.evidence
    else:
        assert case.evidence == ()


@pytest.mark.parametrize("case", [c for c in CASES if c.answerable], ids=lambda c: c.id)
def test_evidence_phrases_are_in_the_cleaned_book(case):
    book = load_book().page_content
    assert all(evidence_found(case.evidence, [book])), f"{case.id}: a phrase is not in the book"


@pytest.mark.parametrize("case", [c for c in CASES if c.answerable], ids=lambda c: c.id)
def test_every_evidence_phrase_is_inside_one_chunk(case):
    """A phrase that falls on a chunk boundary could never be retrieved, whatever the retriever does."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = [c.page_content for c in splitter.split_documents([load_book()])]
    for phrase in case.evidence:
        assert any(evidence_found((phrase,), [chunk])[0] for chunk in chunks), f"{case.id}: '{phrase}' is split"
