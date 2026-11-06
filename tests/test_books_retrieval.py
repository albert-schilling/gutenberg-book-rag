"""A smoke test per book with the real embedding model: an obvious question finds the right passage.

It checks that the cleaning of each book leaves searchable text. It does not measure quality: only
the penguins book has a golden question set (see evals/).
"""

import pytest

from book_rag import store
from book_rag.books import BOOKS
from book_rag.rag import retrieve

pytestmark = pytest.mark.integration

CASES = [
    ("adventures_of_pinocchio_collodi", "What happens to Pinocchio's nose when he tells lies?", "nose"),
    ("adventures_of_sherlock_holmes_doyle", "Who is Irene Adler?", "Irene Adler"),
    ("antarctic_penguins_levick", "What do skua gulls do to penguin chicks?", "Skua"),
    ("climate_in_relation_to_man_ward", "What is a monsoon?", "monsoon"),
    ("frankenstein_shelley", "Who is Henry Clerval?", "Clerval"),
    ("the_time_machine_wells", "What are the Morlocks?", "Morlock"),
    ("tom_browns_school_days_hughes", "Who is Flashman?", "Flashman"),
    ("wonderful_wizard_of_oz_baum", "Why does the Tin Woodman want a heart?", "heart"),
]


def test_there_is_a_case_for_every_book():
    assert {book_id for book_id, _, _ in CASES} == set(BOOKS)


@pytest.fixture(scope="module")
def chroma_dir(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(store, "CHROMA_DIR", tmp_path_factory.mktemp("chroma"))
        yield


@pytest.mark.parametrize(("book_id", "question", "word"), CASES, ids=[c[0] for c in CASES])
def test_an_obvious_question_finds_a_passage_about_it(chroma_dir, book_id, question, word):
    vector_store = store.build_vector_store(BOOKS[book_id])
    passages = [p.page_content for p, _ in retrieve(question, vector_store)]
    assert len(passages) == 4
    assert any(word.lower() in passage.lower() for passage in passages), f"'{word}' not in the top 4 passages"
