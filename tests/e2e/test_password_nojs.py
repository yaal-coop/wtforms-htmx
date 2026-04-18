"""Progressive-enhancement tests for the password strength indicator example."""

from playwright.sync_api import expect


def test_password_mismatch_shows_error_on_save_nojs(page_nojs, open_example):
    """Saving a different confirmation shows an error."""
    open_example("Password strength indicator")

    page_nojs.locator("input#password").fill("Hello1!")
    page_nojs.locator("input#confirm_password").fill("Hello2!")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.locator("#wrap-confirm_password ul.errors")).to_have_text(
        "Passwords must match."
    )


def test_password_failed_save_keeps_the_password_and_its_strength_nojs(
    page_nojs, open_example
):
    """A failed save shows the typed passwords again, with their strength."""
    open_example("Password strength indicator")

    page_nojs.locator("input#password").fill("Tr0ub4dor&3xyz!")
    page_nojs.locator("input#confirm_password").fill("other")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.locator("input#password")).to_have_value("Tr0ub4dor&3xyz!")
    expect(page_nojs.locator("input#confirm_password")).to_have_value("other")
    expect(page_nojs.locator("input#strength")).to_have_value("4")


def test_password_save_shows_success_nojs(page_nojs, open_example):
    """Saving matching passwords shows the success message."""
    open_example("Password strength indicator")

    page_nojs.locator("input#password").fill("Hello1!")
    page_nojs.locator("input#confirm_password").fill("Hello1!")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.get_by_role("status")).to_contain_text("Password saved.")
