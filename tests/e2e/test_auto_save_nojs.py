"""Progressive-enhancement tests for the auto-save example."""

from playwright.sync_api import expect


def test_auto_save_submit_saves_nojs(page_nojs, open_example):
    """Clicking Save saves the form and shows the success message."""
    open_example("Auto-save")

    page_nojs.locator("input#name").fill("Dora")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.get_by_role("status")).to_contain_text("Saved.")
    expect(page_nojs.locator("input#name")).to_have_value("Dora")


def test_auto_save_submit_shows_errors_nojs(page_nojs, open_example):
    """An invalid submit shows the field error and saves nothing."""
    open_example("Auto-save")

    page_nojs.locator("input#email").fill("not-an-email")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.locator("#wrap-email ul.errors")).to_be_visible()
    open_example("Auto-save")
    expect(page_nojs.locator("input#email")).to_have_value("alice@example.org")
