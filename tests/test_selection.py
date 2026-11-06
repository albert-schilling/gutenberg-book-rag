import pytest

from book_rag.selection import question_about


def test_the_question_names_the_selected_text():
    assert question_about("the Morlocks") == "What does the book say about “the Morlocks”?"


def test_whitespace_and_quotes_are_cleaned():
    assert question_about('  "a   brave\n new world"  ') == "What does the book say about “a brave new world”?"


def test_a_long_selection_is_cut_at_a_word_boundary():
    selected = "word " * 100
    question = question_about(selected, limit=50)
    assert question.endswith(" …”?")
    assert len(question) < 90 and "wor …" not in question  # no half word


@pytest.mark.parametrize("selected", ["x", "a sentence, with punctuation."])
def test_the_question_is_always_one_line_in_quotes(selected):
    question = question_about(selected)
    assert question.startswith("What does the book say about “") and question.endswith("”?") and "\n" not in question
