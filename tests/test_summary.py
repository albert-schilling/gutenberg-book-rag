import pytest
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from book_rag import rag, summary
from book_rag.book import load_book
from book_rag.books import BOOKS, DEFAULT_BOOK


@pytest.fixture
def summary_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(summary, "SUMMARY_DIR", tmp_path)
    return tmp_path


@pytest.mark.parametrize("book", BOOKS.values(), ids=lambda b: b.id)
def test_the_excerpts_of_every_book_fit_the_token_budget_and_come_from_the_book(book):
    excerpts = summary.sample_excerpts(book)
    assert len(excerpts) < 18_000  # about 4,500 tokens: one call stays far below 8,000 tokens a minute
    assert excerpts.count("[Excerpt:") == summary.PARTS + 2  # the opening, the places in between, the ending
    text = load_book(book).page_content
    for block in excerpts.split("[Excerpt: ")[1:]:
        first_paragraph = block.split("]\n", 1)[1].split("\n\n")[0]
        assert first_paragraph[:60] in text


def test_the_excerpts_are_spread_over_the_book_in_order():
    excerpts = summary.sample_excerpts(DEFAULT_BOOK)
    percents = [int(line.split("%")[0].split()[-1]) for line in excerpts.splitlines() if "% into the book" in line]
    assert percents == sorted(percents) and len(percents) == summary.PARTS
    assert 5 <= percents[0] <= 10 and 90 <= percents[-1] <= 95
    assert excerpts.index("opening of the book") < excerpts.index("% into the book") < excerpts.index("ending of the book")


def test_the_sampling_is_deterministic():
    assert summary.sample_excerpts(DEFAULT_BOOK) == summary.sample_excerpts(DEFAULT_BOOK)


def test_a_missing_summary_is_an_empty_string(summary_dir):
    assert summary.load_summary(DEFAULT_BOOK) == ""


def test_a_saved_summary_is_loaded(summary_dir):
    summary.summary_path(DEFAULT_BOOK).write_text("About penguins.\n", encoding="utf-8")
    assert summary.load_summary(DEFAULT_BOOK) == "About penguins."


def test_the_summary_is_part_of_the_prompt_of_the_book(summary_dir):
    summary.summary_path(DEFAULT_BOOK).write_text("A study of Adelie penguins.", encoding="utf-8")
    prompt = rag.build_system_prompt(DEFAULT_BOOK)
    assert "A study of Adelie penguins." in prompt and "{book_summary}" not in prompt
    assert "{context}" in prompt and "{conversation}" in prompt


def test_without_a_summary_the_prompt_says_so(summary_dir):
    assert "(not available)" in rag.build_system_prompt(DEFAULT_BOOK)


def test_braces_in_a_summary_do_not_break_the_prompt_template(summary_dir):
    summary.summary_path(DEFAULT_BOOK).write_text("It has a {curly} part and a } stray brace.", encoding="utf-8")
    template = ChatPromptTemplate.from_messages([("system", rag.build_system_prompt(DEFAULT_BOOK)), ("human", "{question}")])
    messages = template.invoke({"context": "C", "conversation": "(none)", "question": "Q"}).to_messages()
    assert "It has a {curly} part and a } stray brace." in messages[0].content


@pytest.fixture
def fake_model(monkeypatch):
    monkeypatch.setattr(summary, "ChatGroq", lambda **kwargs: RunnableLambda(lambda prompt: "A fake summary."))
    monkeypatch.setattr(summary, "load_dotenv", lambda *args: None)


def test_the_command_makes_only_the_missing_summaries(summary_dir, fake_model):
    summary.summary_path(DEFAULT_BOOK).write_text("Existing.", encoding="utf-8")
    summary.main(["--pause", "0"])
    assert summary.load_summary(DEFAULT_BOOK) == "Existing."  # not overwritten
    assert all(summary.load_summary(book) for book in BOOKS.values())
    assert summary.load_summary(BOOKS["frankenstein_shelley"]) == "A fake summary."


def test_force_makes_a_summary_again(summary_dir, fake_model):
    summary.summary_path(DEFAULT_BOOK).write_text("Old.", encoding="utf-8")
    summary.main(["--book", DEFAULT_BOOK.id, "--force"])
    assert summary.load_summary(DEFAULT_BOOK) == "A fake summary."


def test_an_empty_reply_is_an_error_and_nothing_is_saved(summary_dir, monkeypatch):
    monkeypatch.setattr(summary, "ChatGroq", lambda **kwargs: RunnableLambda(lambda prompt: "  "))
    with pytest.raises(RuntimeError, match="empty summary"):
        summary.make_summary(DEFAULT_BOOK)


def test_a_short_summary_is_left_alone():
    assert summary.limit_words("One. Two.") == "One. Two."


def test_a_long_summary_is_cut_after_a_complete_sentence():
    text = " ".join(f"Sentence number {n} has some words." for n in range(100))
    cut = summary.limit_words(text)
    assert len(cut.split()) <= summary.MAX_WORDS + 10
    assert cut.endswith("words.") and cut.startswith("Sentence number 0")  # no half sentence


def test_a_long_text_without_sentence_ends_is_cut_with_an_ellipsis():
    cut = summary.limit_words("word " * 500)
    assert cut.endswith("…") and len(cut.split()) <= summary.MAX_WORDS + 11


def test_the_model_reply_is_limited_before_it_is_saved(summary_dir, monkeypatch):
    long_reply = " ".join(f"Sentence {n} is here." for n in range(200))
    monkeypatch.setattr(summary, "ChatGroq", lambda **kwargs: RunnableLambda(lambda prompt: long_reply))
    assert len(summary.make_summary(DEFAULT_BOOK).split()) <= summary.MAX_WORDS + 10
