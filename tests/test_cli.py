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


def run_main(monkeypatch, argv, inputs=("quit",)):
    """Run the CLI with fake stores. Returns the ids of the books whose store was built."""
    built = []
    monkeypatch.setattr(cli, "build_vector_store", lambda book: built.append(book.id) or "store")
    monkeypatch.setattr(cli, "build_chain", lambda book: "chain")
    monkeypatch.setattr(cli, "ask", lambda question, store, chain: ("an answer", []))
    answers = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    cli.main(argv)
    return built


def test_the_default_book_is_the_penguins(monkeypatch):
    assert run_main(monkeypatch, []) == ["antarctic_penguins_levick"]


def test_the_book_can_be_chosen_and_is_named_in_the_greeting(monkeypatch, capsys):
    built = run_main(monkeypatch, ["--book", "frankenstein_shelley"], inputs=("Who is the monster?", "exit"))
    out = capsys.readouterr().out
    assert built == ["frankenstein_shelley"]
    assert "Frankenstein; or, The Modern Prometheus" in out
    assert "an answer" in out and "Goodbye!" in out


def test_an_unknown_book_is_rejected_with_the_choices(monkeypatch, capsys):
    with pytest.raises(SystemExit):
        run_main(monkeypatch, ["--book", "nope"])
    assert "frankenstein_shelley" in capsys.readouterr().err
