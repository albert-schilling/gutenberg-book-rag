"""The chat page does not scroll as a whole; the book opens in a panel on the right that can be widened."""

import pytest
from test_reader_browser import ask_and_open_first_passage, open_book_from_the_sidebar

pytestmark = pytest.mark.browser

PAGE_SCROLLS = """() => [document.documentElement, ...document.querySelectorAll(
    '[data-testid="stAppViewContainer"], [data-testid="stAppScrollToBottomContainer"]')]
    .some(el => el.scrollHeight > el.clientHeight + 1 && getComputedStyle(el).overflowY !== 'hidden')"""


def test_the_page_does_not_scroll_and_the_title_stays_visible(page):
    page.set_viewport_size({"width": 1440, "height": 800})
    for question in ("What do skua gulls do?", "How big is a rookery?", "What do penguins eat?"):
        page.locator("textarea").first.fill(question)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)
    assert not page.evaluate(PAGE_SCROLLS)
    title = page.get_by_role("heading", name="Antarctic Penguins").bounding_box()
    assert title and title["y"] >= 0 and title["y"] + title["height"] <= 800


def test_the_reader_is_a_panel_on_the_right_that_can_be_widened(page):
    page.set_viewport_size({"width": 1440, "height": 800})
    ask_and_open_first_passage(page)
    panel = page.locator(".st-key-reader-panel")
    narrow = panel.bounding_box()
    assert narrow and narrow["x"] + narrow["width"] >= 1439 and narrow["x"] > 1440 * 0.5
    assert not page.evaluate(PAGE_SCROLLS)
    page.get_by_role("button", name="Wider").click()
    page.wait_for_timeout(500)
    wide = panel.bounding_box()
    assert wide["width"] > narrow["width"] * 1.4
    page.get_by_role("button", name="Narrower").click()
    page.wait_for_timeout(500)
    assert panel.bounding_box()["width"] == pytest.approx(narrow["width"], abs=2)


def test_on_a_phone_the_reader_fills_the_screen_below_the_header(page):
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator('[data-testid="stExpandSidebarButton"]').click()
    open_book_from_the_sidebar(page)
    box = page.locator(".st-key-reader-panel").bounding_box()
    assert box["width"] == pytest.approx(390, abs=2) and box["y"] >= 55
    assert page.get_by_role("button", name="Close").is_visible()
