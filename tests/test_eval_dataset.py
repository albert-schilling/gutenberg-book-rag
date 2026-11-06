import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter

from book_rag.book import load_book
from book_rag.books import DEFAULT_BOOK
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
def test_every_case_has_a_reference_and_evidence_as_its_kind_requires(case):
    assert case.question.endswith("?")
    assert case.split in {"dev", "test"} and case.kind in {"fact", "whole-book"}
    if not case.answerable:
        assert case.evidence == ()
    elif case.kind == "whole-book":
        assert case.reference_answer.strip() and case.evidence == ()  # no single phrase of the book answers it
    else:
        assert case.reference_answer.strip() and case.evidence


def test_there_is_a_test_split_that_was_not_used_for_tuning():
    dev = [c for c in CASES if c.split == "dev"]
    test = [c for c in CASES if c.split == "test"]
    assert len(dev) >= 20 and len(test) >= 30
    assert {c.id for c in dev}.isdisjoint({c.id for c in test})
    assert any(not c.answerable for c in test) and any(c.kind == "whole-book" for c in test)


@pytest.mark.parametrize("case", [c for c in CASES if c.evidence], ids=lambda c: c.id)
def test_evidence_phrases_are_in_the_cleaned_book(case):
    book = load_book(DEFAULT_BOOK).page_content
    assert all(evidence_found(case.evidence, [book])), f"{case.id}: a phrase is not in the book"


@pytest.mark.parametrize("case", [c for c in CASES if c.evidence], ids=lambda c: c.id)
def test_every_evidence_phrase_is_inside_one_chunk(case):
    """A phrase that falls on a chunk boundary could never be retrieved, whatever the retriever does."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = [c.page_content for c in splitter.split_documents([load_book(DEFAULT_BOOK)])]
    for phrase in case.evidence:
        assert any(evidence_found((phrase,), [chunk])[0] for chunk in chunks), f"{case.id}: '{phrase}' is split"
