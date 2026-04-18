"""End-to-end tests for the password strength indicator example."""

from playwright.sync_api import expect


def test_password_strength_updates_on_keystroke(page, open_example):
    """Typing a password updates the strength meter."""
    open_example("Password strength indicator")

    page.locator("input#password").fill("Hello1!world")

    expect(page.locator("input#strength")).to_have_value("4")


def test_password_value_survives_inline_validation(page, open_example):
    """Leaving the password input re-renders it with the typed password."""
    open_example("Password strength indicator")
    password = page.locator("input#password")
    password.fill("Hello1!")
    password.evaluate("el => el.setAttribute('data-pre-swap', '')")

    page.locator("input#confirm_password").click()

    expect(page.locator("input#password[data-pre-swap]")).to_have_count(0)
    expect(password).to_have_value("Hello1!")


def test_password_mismatch_shows_error_on_blur(page, open_example):
    """Leaving the confirmation with a different password shows an error."""
    open_example("Password strength indicator")

    page.locator("input#password").fill("Hello1!")
    page.locator("input#confirm_password").fill("Hello2!")
    page.locator("input#confirm_password").blur()

    expect(page.locator("#wrap-confirm_password ul.errors")).to_have_text(
        "Passwords must match."
    )


def test_password_save_shows_success(page, open_example):
    """Saving matching passwords shows the success message."""
    open_example("Password strength indicator")

    page.locator("input#password").fill("Hello1!")
    page.locator("input#confirm_password").fill("Hello1!")
    with page.expect_navigation():
        page.get_by_role("button", name="Save").click()

    expect(page.get_by_role("status")).to_contain_text("Password saved.")
