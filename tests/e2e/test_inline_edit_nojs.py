"""Progressive-enhancement tests for the inline edit example."""

from playwright.sync_api import expect


def _edit(page):
    with page.expect_navigation():
        page.get_by_role("button", name="Edit name").click()


def test_inline_edit_starts_in_view_mode_nojs(page_nojs, open_example):
    """The page shows the saved name and an Edit button, with no input."""
    open_example("Inline edit")

    expect(page_nojs.locator(".inline-edit-value")).to_have_text("Alice Brown")
    expect(page_nojs.get_by_role("button", name="Edit name")).to_be_visible()
    expect(page_nojs.locator(".inline-edit-input")).to_have_count(0)


def test_inline_edit_edit_reveals_focused_input_nojs(page_nojs, open_example):
    """Clicking Edit shows a focused input with Save and Cancel buttons."""
    open_example("Inline edit")

    _edit(page_nojs)

    expect(page_nojs.locator(".inline-edit-input")).to_be_focused()
    expect(page_nojs.get_by_role("button", name="Save name")).to_be_visible()
    expect(page_nojs.get_by_role("button", name="Cancel edit")).to_be_visible()


def test_inline_edit_save_persists_nojs(page_nojs, open_example):
    """Save keeps the new name and goes back to view mode."""
    open_example("Inline edit")
    _edit(page_nojs)

    page_nojs.locator(".inline-edit-input").fill("Bob Smith")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save name").click()

    expect(page_nojs.locator(".inline-edit-value")).to_have_text("Bob Smith")


def test_inline_edit_cancel_restores_nojs(page_nojs, open_example):
    """Cancel drops the typed name and shows the saved one."""
    open_example("Inline edit")
    _edit(page_nojs)

    page_nojs.locator(".inline-edit-input").fill("Trashed draft")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Cancel edit").click()

    expect(page_nojs.locator(".inline-edit-value")).to_have_text("Alice Brown")
