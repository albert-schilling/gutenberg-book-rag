from book_rag import memory
from book_rag.config import FALLBACK_ANSWER
from book_rag.memory import ChatMemory


class FakeSummarizer:
    """Records what was folded into the summary and returns a summary that shows it."""

    def __init__(self):
        self.calls = []

    def __call__(self, summary, question, answer):
        self.calls.append((summary, question, answer))
        return f"{summary}+{question}".strip("+")


def test_an_empty_memory_has_no_context():
    assert ChatMemory().context() == ""


def test_the_latest_exchanges_are_kept_word_for_word():
    chat, summarize = ChatMemory(), FakeSummarizer()
    chat.add("Q1", "A1", summarize)
    chat.add("Q2", "A2", summarize)
    assert chat.context() == "Latest exchanges:\nQ: Q1\nA: A1\nQ: Q2\nA: A2"
    assert summarize.calls == []  # nothing fell out of the window yet


def test_the_exchange_that_leaves_the_window_goes_into_the_summary():
    chat, summarize = ChatMemory(), FakeSummarizer()
    for number in range(1, 5):
        chat.add(f"Q{number}", f"A{number}", summarize)
    assert chat.pairs == [("Q3", "A3"), ("Q4", "A4")]  # a window of two
    assert chat.summary == "Q1+Q2"
    assert summarize.calls == [("", "Q1", "A1"), ("Q1", "Q2", "A2")]  # each one folded in once, in order
    assert chat.context().startswith("Summary of the earlier conversation: Q1+Q2\n\nLatest exchanges:\nQ: Q3")


def test_long_answers_are_cut_to_save_tokens():
    chat = ChatMemory()
    chat.add("Q", "word " * 500, FakeSummarizer())
    answer = chat.pairs[0][1]
    assert len(answer) <= memory.MAX_ANSWER_CHARS + 3 and answer.endswith("…")


def test_an_error_or_an_empty_answer_is_not_remembered():
    chat, summarize = ChatMemory(), FakeSummarizer()
    chat.add("Q1", FALLBACK_ANSWER, summarize)
    chat.add("Q2", "   ", summarize)
    assert chat.pairs == [] and chat.context() == ""


def test_the_crude_summary_keeps_the_questions_within_a_limit():
    summary = ""
    for number in range(100):
        summary = memory.crude_summary(summary, f"What about topic number {number}?", "answer")
    assert len(summary) <= memory.SUMMARY_CHARS
    assert summary.endswith("topic number 99?")  # the newest question is kept


def test_a_failing_language_model_does_not_break_the_summary(monkeypatch):
    class Broken:
        def __or__(self, other):
            return self

        def invoke(self, inputs):
            raise RuntimeError("rate limit")

    monkeypatch.setattr(memory, "OFFLINE", False)
    monkeypatch.setattr(memory, "ChatGroq", lambda **kwargs: Broken())
    monkeypatch.setattr(memory, "ChatPromptTemplate", type("P", (), {"from_template": staticmethod(lambda t: Broken())}))
    monkeypatch.setattr(memory, "StrOutputParser", lambda: Broken())
    summarize = memory.build_summarizer()
    assert "What is a rookery?" in summarize("", "What is a rookery?", "A breeding place.")  # the crude summary
