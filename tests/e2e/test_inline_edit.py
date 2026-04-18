"""End-to-end tests for the inline edit example."""

from playwright.sync_api import expect


def test_inline_edit_starts_in_view_mode(page, open_example):
    """The page shows the saved name and an Edit button, with no input."""
    open_example("Inline edit")

    expect(page.locator(".inline-edit-value")).to_have_text("Alice Brown")
    expect(page.get_by_role("button", name="Edit name")).to_be_visible()
    expect(page.locator(".inline-edit-input")).to_have_count(0)


def test_inline_edit_edit_reveals_focused_input(page, open_example):
    """Clicking Edit shows a focused input with Save and Cancel buttons."""
    open_example("Inline edit")

    page.get_by_role("button", name="Edit name").click()

    expect(page.locator(".inline-edit-input")).to_be_focused()
    expect(page.get_by_role("button", name="Save name")).to_be_visible()
    expect(page.get_by_role("button", name="Cancel edit")).to_be_visible()


def test_inline_edit_save_persists(page, open_example):
    """Save keeps the new name and goes back to view mode."""
    open_example("Inline edit")
    page.get_by_role("button", name="Edit name").click()

    page.locator(".inline-edit-input").fill("Bob Smith")
    with page.expect_navigation():
        page.get_by_role("button", name="Save name").click()

    expect(page.locator(".inline-edit-value")).to_have_text("Bob Smith")


def test_inline_edit_cancel_restores(page, open_example):
    """Cancel drops the typed name and shows the saved one."""
    open_example("Inline edit")
    page.get_by_role("button", name="Edit name").click()

    page.locator(".inline-edit-input").fill("Trashed draft")
    page.get_by_role("button", name="Cancel edit").click()

    expect(page.locator(".inline-edit-value")).to_have_text("Alice Brown")


def test_inline_edit_escape_restores(page, open_example):
    """Escape in the input drops the typed name, like Cancel."""
    open_example("Inline edit")
    page.get_by_role("button", name="Edit name").click()

    page.locator(".inline-edit-input").fill("Trashed draft")
    page.locator(".inline-edit-input").press("Escape")

    expect(page.locator(".inline-edit-value")).to_have_text("Alice Brown")
