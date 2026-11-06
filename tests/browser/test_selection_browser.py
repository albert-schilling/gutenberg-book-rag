"""The "Ask about this" tooltip for selected text, in the chat and in the book."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.browser

TIP = "#book-rag-ask-tip"
QUESTION_START = "What does the book say about “"


def ask(page, question="How do skuas attack penguin chicks?"):
    page.locator("textarea").first.fill(question)
    page.keyboard.press("Enter")
    page.get_by_text("Passage at position").first.wait_for(timeout=60_000)
    page.wait_for_timeout(800)  # let the page finish scrolling: a scroll hides the tooltip, as intended


def user_messages(page):
    """The questions that were asked through the tooltip (not the answers, which repeat the question)."""
    return (
        page.locator('[data-testid="stChatMessage"]')
        .filter(has=page.locator('[data-testid="stChatMessageAvatarUser"]'))
        .filter(has_text=QUESTION_START)
    )


def click_tooltip_and_wait_for_the_question(page, expected_count=1):
    page.locator(TIP).get_by_role("button", name="Ask about this").click()
    expect(user_messages(page)).to_have_count(expected_count, timeout=30_000)
    return user_messages(page).last.inner_text()


def test_selecting_text_in_the_answer_offers_a_question_about_it(page):
    ask(page)
    page.get_by_text("Offline mode: no language model was called").first.click(click_count=3)  # selects the paragraph
    expect(page.locator(TIP)).to_be_visible()
    question = click_tooltip_and_wait_for_the_question(page)
    assert QUESTION_START in question and "Offline mode" in question
    expect(page.locator(TIP)).to_be_hidden()


def test_selecting_text_in_my_own_question_offers_a_question_about_it(page):
    ask(page, "Why do penguins fight?")
    page.get_by_text("Why do penguins fight?").first.click(click_count=3)
    expect(page.locator(TIP)).to_be_visible()
    assert "Why do penguins fight?" in click_tooltip_and_wait_for_the_question(page)


def test_selecting_text_in_a_passage_offers_a_question_about_it(page):
    ask(page)
    page.get_by_text("Passage at position").first.click()
    passage = page.locator("details").first.locator("p").nth(1)
    passage.click(click_count=3)
    expect(page.locator(TIP)).to_be_visible()
    question = click_tooltip_and_wait_for_the_question(page)
    assert question.count("…") <= 1 and len(question) < 260  # a long passage is cut to a short question


def test_selecting_text_in_the_book_offers_a_question_about_it(page):
    page.get_by_role("button", name="Read the book").click()
    page.wait_for_selector(".reader p")
    page.locator(".reader p").nth(2).click(click_count=3)
    expect(page.locator(TIP)).to_be_visible()
    box = page.locator(TIP).bounding_box()
    assert 0 <= box["x"] and 0 <= box["y"]  # inside the window
    assert QUESTION_START in click_tooltip_and_wait_for_the_question(page)


def test_there_is_no_tooltip_for_text_outside_the_chat_and_the_book(page):
    ask(page)
    page.locator('[data-testid="stSidebar"]').get_by_text("by G. Murray Levick").click(click_count=3)
    page.wait_for_timeout(400)
    expect(page.locator(TIP)).to_be_hidden()
    page.get_by_role("heading", name="Reading companion").click(click_count=3)
    page.wait_for_timeout(400)
    expect(page.locator(TIP)).to_be_hidden()


def test_the_tooltip_goes_away_on_escape_and_on_a_click_elsewhere(page):
    ask(page)
    answer = page.get_by_text("Offline mode: no language model was called").first
    answer.click(click_count=3)
    expect(page.locator(TIP)).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator(TIP)).to_be_hidden()

    answer.click(click_count=3)
    expect(page.locator(TIP)).to_be_visible()
    page.locator('[data-testid="stSidebar"]').click(position={"x": 100, "y": 600})
    expect(page.locator(TIP)).to_be_hidden()
    assert user_messages(page).count() == 0  # nothing was asked


def test_a_single_click_without_a_selection_shows_nothing(page):
    ask(page)
    page.get_by_text("Offline mode: no language model was called").first.click()
    page.wait_for_timeout(400)
    expect(page.locator(TIP)).to_be_hidden()
