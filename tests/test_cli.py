import pytest

from book_rag import cli
from book_rag.agent import AgentResult


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
    built, asked = [], []

    class FakeCompanion:
        def respond(self, question, memory, agentic):
            asked.append((question, agentic))
            queries = [question, "other words"] if "again" in question else [question]
            return AgentResult("an answer", [], queries)

    monkeypatch.setattr(cli, "build_companion", lambda book: built.append(book.id) or FakeCompanion())
    cli.asked = asked
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


def test_the_agent_is_used_unless_the_user_switches_it_off(monkeypatch):
    run_main(monkeypatch, [], inputs=("A question", "quit"))
    assert cli.asked == [("A question", True)]
    run_main(monkeypatch, ["--no-agent"], inputs=("A question", "quit"))
    assert cli.asked == [("A question", False)]


def test_the_searches_of_the_model_are_printed(monkeypatch, capsys):
    run_main(monkeypatch, [], inputs=("Ask again", "quit"))
    assert "Searched the book for: “Ask again” · “other words”" in capsys.readouterr().out
    run_main(monkeypatch, [], inputs=("Plain", "quit"))
    assert "Searched the book for" not in capsys.readouterr().out
