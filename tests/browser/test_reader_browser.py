"""What cannot be tested without a browser: infinite scrolling, a steady reading position, the highlight."""

import pytest
from browser_helpers import anchor, distance_from_top, scroll_and_measure_drift, window  # noqa: F401

pytestmark = pytest.mark.browser

MAX_RENDERED = 250  # the cap in reader.js


def ask_and_open_first_passage(page):
    page.locator("textarea").first.fill("What do skua gulls do to the penguins?")
    page.keyboard.press("Enter")
    page.get_by_text("Passage at position").first.wait_for(timeout=60_000)
    page.get_by_text("Passage at position").first.click()
    passage = page.locator("details").first.evaluate(  # the text of the passage, not the label or the button
        "el => [...el.querySelectorAll('p')].find(p => !p.closest('summary') && !p.closest('button')).innerText"
    )
    page.get_by_role("button", name="Read in the book").first.click()
    page.wait_for_selector(".reader mark", timeout=30_000)
    page.wait_for_timeout(500)
    return passage


def choose_book(page, title_part):
    box = page.locator('[data-testid="stSidebar"] input').first
    box.click()
    box.fill(title_part)
    page.keyboard.press("Enter")
    page.wait_for_selector(
        "text=by Arthur Conan Doyle" if title_part == "Sherlock" else f"text={title_part}", timeout=30_000
    )


def open_book_from_the_sidebar(page):
    page.get_by_role("button", name="Read the book").click()
    page.wait_for_selector(".reader p", timeout=30_000)
    page.wait_for_timeout(300)


def test_the_book_opens_at_its_beginning_with_a_small_window(page):
    open_book_from_the_sidebar(page)
    assert page.locator(".reader p").first.inner_text() == "INTRODUCTION"
    assert page.locator(".edge.top").inner_text() == "Start of the book"
    first, last, count = window(page)
    assert (first, count) == (0, last + 1) and count < 40  # not the whole book


def test_scrolling_down_loads_the_book_lazily_up_to_its_end(page):
    open_book_from_the_sidebar(page)
    biggest = 0
    for _ in range(400):
        page.locator(".reader").evaluate("root => { root.scrollTop += 3000 }")
        page.wait_for_timeout(30)
        biggest = max(biggest, page.locator(".reader p").count())
        if page.locator(".edge.bottom").inner_text():
            break
    assert page.locator(".edge.bottom").inner_text() == "End of the book"
    assert biggest <= MAX_RENDERED  # far paragraphs are dropped while reading on
    assert window(page)[0] > 0  # the start of the book is gone from the page again


def test_the_text_does_not_jump_when_paragraphs_are_dropped_while_scrolling_down_a_long_book(page):
    """Sherlock Holmes has long paragraphs at the top and short ones below: the case in which the browser
    moves the scroll position by itself when old paragraphs are dropped (a bug that was fixed in reader.js)."""
    choose_book(page, "Sherlock")
    open_book_from_the_sidebar(page)
    assert scroll_and_measure_drift(page, 800, 80) < 2  # passes several points where paragraphs are dropped
    assert window(page)[0] > 0  # ... so the start of the window really moved


def test_scrolling_up_from_a_passage_loads_earlier_text_without_jumping(page):
    ask_and_open_first_passage(page)
    first_before = window(page)[0]
    assert scroll_and_measure_drift(page, -150, 120) < 2
    assert window(page)[0] < first_before  # earlier paragraphs were loaded


def test_a_passage_opens_highlighted_and_in_view_with_text_before_it(page):
    passage = ask_and_open_first_passage(page)
    mark = page.locator(".reader mark").first
    reader_box, mark_box = page.locator(".reader").bounding_box(), mark.bounding_box()
    assert reader_box["y"] <= mark_box["y"] <= reader_box["y"] + reader_box["height"] / 2  # in the upper half
    assert mark.inner_text()[:30] == passage[:30]  # the highlight is the passage that was clicked
    marked_paragraph = int(page.locator(".reader p:has(mark)").first.get_attribute("data-i"))
    assert window(page)[0] < marked_paragraph < window(page)[1]  # text before and after it is loaded


def test_the_close_button_removes_the_book_and_keeps_the_chat(page):
    ask_and_open_first_passage(page)
    page.get_by_role("button", name="Close").click()
    page.wait_for_timeout(800)
    assert page.locator(".reader").count() == 0
    assert page.get_by_text("Passage at position").count() == 4


def test_a_long_chat_keeps_the_page_small(page):
    """Streamlit draws everything it is given: the chat only draws the latest exchanges."""
    for number in range(14):
        page.locator("textarea").first.fill(f"Question number {number}")
        page.keyboard.press("Enter")
        page.get_by_text(f"The best passages for “Question number {number}”").wait_for(timeout=30_000)
    messages = page.locator('[data-testid="stChatMessage"]')
    assert messages.count() == 20  # 10 exchanges
    assert page.get_by_role("button", name="Show earlier questions (4 more)").is_visible()
    assert (
        page.evaluate("document.querySelectorAll('*').length") < 2000
    )  # about 1,630 capped, 2,260 for 14 exchanges without the cap
    page.get_by_role("button", name="Show earlier questions (4 more)").click()
    page.wait_for_function("document.querySelectorAll('[data-testid=\"stChatMessage\"]').length === 28")
