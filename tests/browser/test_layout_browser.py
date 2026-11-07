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


def test_the_reader_is_a_panel_on_the_right_that_can_fill_the_window(page):
    page.set_viewport_size({"width": 1440, "height": 800})
    ask_and_open_first_passage(page)
    panel = page.locator(".st-key-reader-panel")
    narrow = panel.bounding_box()
    assert narrow and narrow["x"] + narrow["width"] >= 1400 and narrow["x"] > 1440 * 0.5
    assert not page.evaluate(PAGE_SCROLLS)
    page.locator(".st-key-reader-expand button:visible").first.click()
    page.wait_for_timeout(500)
    full = panel.bounding_box()
    assert full["width"] > 1440 - 80 and full["x"] > 20  # a strip of the page stays visible on the left
    page.locator(".st-key-reader-expand button:visible").first.click()
    page.wait_for_timeout(500)
    assert panel.bounding_box()["width"] == pytest.approx(narrow["width"], abs=2)


def test_the_chat_scrolls_down_to_a_new_answer_even_when_it_was_scrolled_up(page):
    page.set_viewport_size({"width": 1440, "height": 700})
    for question in ("What do skua gulls do?", "How big is a rookery?", "What do penguins eat?"):
        page.locator("textarea").first.fill(question)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)
    pane = page.locator(".st-key-chat-pane")
    pane.evaluate("el => { el.scrollTop = 0 }")
    page.locator("textarea").first.fill("Do the hens leave the nest?")
    page.keyboard.press("Enter")
    page.wait_for_timeout(2500)
    assert pane.evaluate("el => el.scrollHeight - el.scrollTop - el.clientHeight") < 5


def test_on_a_phone_the_reader_fills_the_screen_below_the_header(page):
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator('[data-testid="stExpandSidebarButton"]').click()
    open_book_from_the_sidebar(page)
    box = page.locator(".st-key-reader-panel").bounding_box()
    assert box["width"] == pytest.approx(390, abs=2) and box["y"] >= 55
    assert page.locator(".st-key-close-reader button:visible").first.is_visible()


def test_the_start_screen_is_a_shelf_that_does_not_scroll_as_a_page(browser, app_url):
    context = browser.new_context(
        viewport={"width": 1000, "height": 500}
    )  # small: the shelf has to scroll inside itself
    page = context.new_page()
    page.goto(app_url)
    page.locator(".st-key-shelf button:visible").first.wait_for(timeout=60_000)
    assert page.locator(".st-key-shelf button:visible").count() == 8
    assert not page.evaluate(PAGE_SCROLLS)
    assert page.get_by_role("heading", name="Reading companion").is_visible()
    writing_mode = page.locator(".st-key-shelf button:visible").first.evaluate("el => getComputedStyle(el).writingMode")
    assert writing_mode.startswith("vertical")
    page.locator(".st-key-open-chat-frankenstein_shelley button:visible").click()
    page.wait_for_selector("textarea", timeout=60_000)
    assert page.get_by_role("heading", name="Frankenstein").is_visible()
    context.close()
