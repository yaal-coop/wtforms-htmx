"""End-to-end tests for the inline validation example."""

from playwright.sync_api import expect


def test_inline_validation_flags_bad_email_on_blur(page, open_example):
    """Leaving the email input with a bad value shows the error."""
    open_example("Inline validation")

    page.locator("input#email").fill("not-an-email")
    page.locator("input#email").blur()

    expect(page.locator("#wrap-email ul.errors")).to_contain_text("Invalid email")


def test_inline_validation_clears_error_on_fix(page, open_example):
    """Fixing a bad email removes the error on the next blur."""
    open_example("Inline validation")
    errors = page.locator("#wrap-email ul.errors")
    page.locator("input#email").fill("bad")
    page.locator("input#email").blur()
    expect(errors).to_be_visible()

    page.locator("input#email").fill("good@example.com")
    page.locator("input#email").blur()

    expect(errors).to_have_count(0)


def test_inline_validation_marks_valid_value(page, open_example):
    """A valid value gets ``aria-invalid="false"`` after blur."""
    open_example("Inline validation")

    page.locator("input#email").fill("alice@example.com")
    page.locator("input#email").blur()

    expect(page.locator("input#email")).to_have_attribute("aria-invalid", "false")


def test_inline_validation_no_aria_invalid_on_initial_load(page, open_example):
    """The first page load marks no input as valid or invalid."""
    open_example("Inline validation")

    for name in ("name", "email", "website", "age"):
        expect(page.locator(f"input#{name}")).not_to_have_attribute(
            "aria-invalid", r".*"
        )


def test_inline_validation_save_shows_errors(page, open_example):
    """Saving a bad email shows the error after the reload."""
    open_example("Inline validation")

    page.locator("input#email").fill("not-an-email")
    with page.expect_navigation():
        page.get_by_role("button", name="Save").click()

    expect(page.locator("#wrap-email ul.errors")).to_contain_text("Invalid email")


def test_inline_validation_save_redirects_on_valid(page, open_example):
    """Saving a valid form shows the success message."""
    open_example("Inline validation")

    page.locator("input#email").fill("eloi@example.org")
    with page.expect_navigation():
        page.get_by_role("button", name="Save").click()

    expect(page.get_by_role("status")).to_contain_text("Saved.")
