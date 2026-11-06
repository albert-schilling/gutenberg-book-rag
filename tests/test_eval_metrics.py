import pytest

from book_rag.config import FALLBACK_ANSWER, NO_ANSWER
from book_rag.evaluation import metrics

EVIDENCE = ("incubated for four weeks", "brownish olive")
PASSAGES = [
    "Unrelated text about skuas.",
    "The two eggs are brownish  olive and\nare incubated for four weeks.",
    "More text.",
]


def test_phrases_are_found_regardless_of_case_and_whitespace():
    assert metrics.evidence_found(EVIDENCE, PASSAGES) == [True, True]
    assert metrics.evidence_found(("INCUBATED FOR FOUR WEEKS",), PASSAGES) == [True]


def test_context_recall_is_the_share_of_evidence_found():
    assert metrics.context_recall(EVIDENCE, PASSAGES) == 1.0
    assert metrics.context_recall(EVIDENCE + ("not in the book",), PASSAGES) == pytest.approx(2 / 3)
    assert metrics.context_recall(EVIDENCE, ["nothing here"]) == 0.0


def test_evidence_in_different_passages_counts_for_recall():
    assert metrics.context_recall(EVIDENCE, ["incubated for four weeks", "brownish olive"]) == 1.0


def test_hit_needs_one_phrase_in_one_passage():
    assert metrics.hit(EVIDENCE + ("not in the book",), PASSAGES)
    assert not metrics.hit(EVIDENCE, ["nothing", "here"])


def test_reciprocal_rank_uses_the_first_passage_with_evidence():
    assert metrics.reciprocal_rank(EVIDENCE, PASSAGES) == pytest.approx(1 / 2)
    assert metrics.reciprocal_rank(EVIDENCE, ["brownish olive", "x"]) == 1.0
    assert metrics.reciprocal_rank(EVIDENCE, ["x", "y"]) == 0.0
    assert metrics.reciprocal_rank(EVIDENCE, []) == 0.0


def test_context_precision_is_the_share_of_useful_passages():
    assert metrics.context_precision(EVIDENCE, PASSAGES) == pytest.approx(1 / 3)
    assert metrics.context_precision(EVIDENCE, []) == 0.0


@pytest.mark.parametrize("answer", [NO_ANSWER, f'"{NO_ANSWER}"', NO_ANSWER.lower(), f"  {NO_ANSWER}\n"])
def test_abstention_is_recognised(answer):
    assert metrics.is_abstention(answer)


def test_a_real_answer_is_not_an_abstention():
    assert not metrics.is_abstention("Skuas prey on the chicks.")


def test_abstention_correct():
    assert metrics.abstention_correct(answerable=True, answer="Two eggs.")
    assert not metrics.abstention_correct(answerable=True, answer=NO_ANSWER)
    assert metrics.abstention_correct(answerable=False, answer=NO_ANSWER)
    assert not metrics.abstention_correct(answerable=False, answer="Paris.")


def test_mean_ignores_missing_values():
    assert metrics.mean([1.0, None, 0.0]) == 0.5
    assert metrics.mean([None, None]) is None
    assert metrics.mean([]) is None


def test_empty_answers():
    assert metrics.is_empty_answer("")
    assert metrics.is_empty_answer("  \n")
    assert metrics.is_empty_answer(FALLBACK_ANSWER)  # what `ask` returns when every retry was empty
    assert not metrics.is_empty_answer("Two eggs.")
    assert not metrics.is_empty_answer(NO_ANSWER)
