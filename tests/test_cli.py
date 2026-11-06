import pytest

from book_rag import cli


def fake_input(monkeypatch, answer):
    def _input(prompt=""):
        if isinstance(answer, BaseException):
            raise answer
        return answer

    monkeypatch.setattr("builtins.input", _input)


@pytest.mark.parametrize("command", ["quit", "exit", "QUIT", "Exit", "  quit  ", "\texit\n"])
def test_exit_commands_are_not_questions(monkeypatch, command):
    fake_input(monkeypatch, command)
    assert cli.read_question() is None


@pytest.mark.parametrize("error", [EOFError(), KeyboardInterrupt()])
def test_ctrl_d_and_ctrl_c_exit(monkeypatch, error):
    fake_input(monkeypatch, error)
    assert cli.read_question() is None


def test_a_question_is_returned_stripped(monkeypatch):
    fake_input(monkeypatch, "  Why do the cocks fight?  ")
    assert cli.read_question() == "Why do the cocks fight?"


def test_empty_input_is_not_an_exit(monkeypatch):
    fake_input(monkeypatch, "   ")
    assert cli.read_question() == ""  # the loop skips it


def test_a_question_that_contains_quit_is_still_a_question(monkeypatch):
    fake_input(monkeypatch, "Why do penguins quit nesting?")
    assert cli.read_question() == "Why do penguins quit nesting?"
