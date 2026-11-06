"""The Settings page: the agent switch, and that the choice survives leaving the page."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.browser

SWITCH = "Search again when needed"


def open_settings(page):
    page.get_by_role("link", name="Settings").click()
    expect(page.get_by_text(SWITCH).first).to_be_visible()


def switch_state(page) -> bool:
    return page.get_by_role("switch", name=SWITCH).is_checked()


def test_the_sidebar_has_the_settings_above_the_changes_and_both_open(page):
    sidebar = page.locator('[data-testid="stSidebar"]').inner_text()
    assert sidebar.index("Settings") < sidebar.index("Changes from the assignment")  # the settings link is above
    open_settings(page)
    assert page.get_by_role("heading", name="Settings").count() >= 1
    page.get_by_role("link", name="Back to the chat").click()
    expect(page.locator("textarea").first).to_be_visible()


def test_the_agent_is_off_by_default_and_the_choice_is_kept_when_leaving_the_page(page):
    open_settings(page)
    assert switch_state(page) is False
    page.get_by_text(SWITCH).first.click()
    page.wait_for_timeout(500)
    assert switch_state(page) is True

    page.get_by_role("link", name="Back to the chat").click()
    expect(page.locator("textarea").first).to_be_visible()
    open_settings(page)
    assert switch_state(page) is True  # Streamlit forgets widgets that are not drawn; the app remembers the choice
    page.get_by_text(SWITCH).first.click()
    page.wait_for_timeout(500)
    assert switch_state(page) is False


def test_the_settings_page_names_the_language_model(page):
    open_settings(page)
    text = page.locator("body").inner_text()
    assert "mistral-small-latest" in text and "BOOK_RAG_LLM" in text and "soft" in text
