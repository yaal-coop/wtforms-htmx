"""Progressive-enhancement tests for the inline validation example."""

from playwright.sync_api import expect


def test_inline_validation_save_shows_errors_nojs(page_nojs, open_example):
    """Saving a bad email shows the error after the reload."""
    open_example("Inline validation")

    page_nojs.locator("input#email").fill("not-an-email")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.locator("#wrap-email ul.errors")).to_contain_text("Invalid email")


def test_inline_validation_save_redirects_on_valid_nojs(page_nojs, open_example):
    """Saving a valid form shows the success message."""
    open_example("Inline validation")

    page_nojs.locator("input#email").fill("eloi@example.org")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.get_by_role("status")).to_contain_text("Saved.")
