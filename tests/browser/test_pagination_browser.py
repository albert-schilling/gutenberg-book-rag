"""Pages (virtual: 2,500 characters each) that follow the infinite scrolling, and a jump to any page."""

import re

import pytest
from browser_helpers import scroll_and_measure_drift, window

from book_rag import reader
from book_rag.books import DEFAULT_BOOK

pytestmark = pytest.mark.browser

PAGES = reader.page_count(DEFAULT_BOOK)


def open_book(page):
    page.get_by_role("button", name="Read the book").click()
    page.wait_for_selector(".reader p", timeout=60_000)
    page.wait_for_timeout(300)


def shown_page(page) -> int:
    return int(page.locator(".pager .page").input_value())


def put_paragraph_at_the_reading_line(page, selector):
    """Scroll so that a paragraph is a quarter of the height from the top (the reading line)."""
    page.locator(".reader").evaluate(
        """(root, selector) => { const p = root.querySelector(selector); root.scrollTop = p.offsetTop - root.clientHeight / 4 }""",
        selector,
    )
    page.wait_for_timeout(150)


def test_the_reader_shows_the_page_and_the_number_of_pages(page):
    open_book(page)
    assert shown_page(page) == 1
    assert page.locator(".pager .pages").inner_text() == str(PAGES)
    assert PAGES > 40  # a book of about 160,000 characters


def test_the_text_marks_where_a_page_starts(page):
    open_book(page)
    labels = [
        int(label) for label in page.locator(".reader p[data-page]").evaluate_all("els => els.map(e => e.dataset.page)")
    ]
    assert labels[0] == 1 and len(labels) >= 3
    assert labels == sorted(set(labels))  # increasing, no page twice


NEXT_MARKER_BELOW = """root => { const line = root.scrollTop + root.clientHeight / 4  // the reading line
    for (const p of root.querySelectorAll('p[data-page]')) if (p.offsetTop > line + 100) return [p.dataset.i, p.dataset.page]
    return null }"""
NEXT_MARKER_ABOVE = """root => { const line = root.scrollTop + root.clientHeight / 4; let found = null
    for (const p of root.querySelectorAll('p[data-page]')) if (p.offsetTop < line - 100) found = [p.dataset.i, p.dataset.page]
    return found }"""


def test_the_page_follows_the_scrolling_down_and_up(page):
    """Put a paragraph that carries a page marker on the reading line: the indicator must show that very page."""
    open_book(page)
    reader = page.locator(".reader")
    down = []
    for _ in range(8):
        reader.evaluate("root => { root.scrollTop += 5000 }")  # loads more text on the way
        page.wait_for_timeout(200)
        index, expected = reader.evaluate(NEXT_MARKER_BELOW)
        put_paragraph_at_the_reading_line(page, f'p[data-i="{index}"]')
        assert shown_page(page) == int(expected)
        down.append(int(expected))
    assert down == sorted(down) and down[-1] >= down[0] + 6  # the page grew with the scrolling

    up = []
    for _ in range(4):  # and back up
        reader.evaluate("root => { root.scrollTop -= 4000 }")
        page.wait_for_timeout(250)
        found = reader.evaluate(NEXT_MARKER_ABOVE)
        put_paragraph_at_the_reading_line(page, f'p[data-i="{found[0]}"]')
        assert shown_page(page) == int(found[1])
        up.append(int(found[1]))
    assert up == sorted(up, reverse=True) and up[0] < down[-1]  # the pages got smaller again


def test_the_progress_bar_grows_to_the_end_of_the_book(page):
    open_book(page)
    width = lambda: page.locator(".progress .fill").evaluate("el => parseFloat(el.style.width)")  # noqa: E731
    assert width() < 2
    for _ in range(300):
        page.locator(".reader").evaluate("root => { root.scrollTop += 3000 }")
        page.wait_for_timeout(25)
        if page.locator(".edge.bottom").inner_text():
            break
    page.wait_for_timeout(200)
    assert width() > 85
    assert shown_page(page) >= PAGES - 3  # the reading line is a quarter down: a few pages before the very end


def test_jumping_to_a_page_opens_the_book_there(page):
    open_book(page)
    page.locator(".pager .page").fill("30")
    page.locator(".pager .page").press("Enter")
    page.wait_for_timeout(500)
    assert shown_page(page) == 30
    first, last, count = window(page)
    assert first > 100 and count < 60  # far from the start, with a small window
    marker = page.locator('.reader p[data-page="30"]')
    assert marker.count() == 1
    reader_box, marker_box = page.locator(".reader").bounding_box(), marker.bounding_box()
    assert abs((marker_box["y"] - reader_box["y"]) - reader_box["height"] / 4) < 6  # on the reading line
    assert page.locator(".edge.top").inner_text() == ""  # not the start of the book


def test_a_jump_beyond_the_book_or_below_one_is_corrected(page):
    open_book(page)
    page.locator(".pager .page").fill("9999")
    page.locator(".pager .page").press("Enter")
    page.wait_for_timeout(500)
    assert shown_page(page) >= PAGES - 3
    page.locator(".pager .page").fill("0")
    page.locator(".pager .page").press("Enter")
    page.wait_for_timeout(500)
    assert shown_page(page) == 1 and window(page)[0] == 0


def test_after_a_jump_the_scrolling_still_loads_text_without_jumping(page):
    open_book(page)
    page.locator(".pager .page").fill("20")
    page.locator(".pager .page").press("Enter")
    page.wait_for_timeout(500)
    assert scroll_and_measure_drift(page, -150, 60) < 2
    assert scroll_and_measure_drift(page, 300, 60) < 2


def test_a_passage_opens_on_the_page_that_its_label_names(page):
    page.locator("textarea").first.fill("What do skua gulls do to the penguins?")
    page.keyboard.press("Enter")
    label = page.get_by_text("Passage at position").first
    label.wait_for(timeout=60_000)
    named = int(re.search(r"page (\d+)", label.inner_text()).group(1))
    label.click()
    page.get_by_role("button", name="Read in the book").first.click()
    page.wait_for_selector(".reader mark")
    page.wait_for_timeout(500)
    assert shown_page(page) == named


def test_the_pager_is_at_the_bottom_with_buttons_and_no_spinner(page):
    open_book(page)
    pager = page.locator(".pager").bounding_box()
    reader = page.locator(".reader").bounding_box()
    assert pager["y"] >= reader["y"] + reader["height"] - 1  # below the text
    assert page.locator(".pager .page").get_attribute("type") == "text"  # no built-in increment buttons
    page.locator(".pager .next").click()
    page.wait_for_timeout(500)
    assert shown_page(page) == 2
    page.locator(".pager .prev").click()
    page.wait_for_timeout(500)
    assert shown_page(page) == 1
