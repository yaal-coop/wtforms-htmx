"""End-to-end tests for the dual listbox example."""

from playwright.sync_api import expect


def test_dual_listbox_add_item(page, open_example):
    """Clicking an available row moves it to the selected pane."""
    open_example("Dual listbox")

    page.get_by_role("button", name="Add Bob Carter").click()

    expect(page.get_by_role("button", name="Remove Bob Carter")).to_be_visible()


def test_dual_listbox_remove_item(page, open_example):
    """Clicking a selected row moves it back to the available pane."""
    open_example("Dual listbox")

    page.get_by_role("button", name="Remove Alice Brown").click()

    expect(page.get_by_role("button", name="Add Alice Brown")).to_be_visible()


def test_dual_listbox_typing_filters_available(page, open_example):
    """Typing in the available filter narrows the available pane."""
    open_example("Dual listbox")

    page.get_by_label("Filter available items").fill("jack")

    expect(page.locator(".dual-row-available .row-name")).to_have_text(["Jack Klein"])


def test_dual_listbox_filter_keeps_the_typed_text(page, open_example):
    """The filter input keeps the typed text after the panes refresh."""
    open_example("Dual listbox")
    query = page.get_by_label("Filter available items")

    query.press_sequentially("jack")

    expect(page.locator(".dual-row-available")).to_have_count(1)
    expect(query).to_have_value("jack")


def test_dual_listbox_typing_filters_selected(page, open_example):
    """Typing in the selected filter narrows the selected pane."""
    open_example("Dual listbox")

    page.get_by_label("Filter selected items").fill("carol")

    expect(page.locator(".dual-row-selected .row-name")).to_have_text(["Carol Davis"])


def test_dual_listbox_add_all_adds_the_filtered_items(page, open_example):
    """Add all adds only the available items that match the filter."""
    open_example("Dual listbox")
    page.get_by_label("Filter available items").fill("jack")
    expect(page.locator(".dual-row-available")).to_have_count(1)

    page.get_by_role("button", name="Add all visible items").click()

    expect(page.locator(".dual-row-selected .row-name")).to_have_text(
        ["Alice Brown", "Carol Davis", "Jack Klein"]
    )


def test_dual_listbox_clear_all_empties_the_selection(page, open_example):
    """Clear all moves every selected item back to the available pane."""
    open_example("Dual listbox")

    page.get_by_role("button", name="Remove all visible selected items").click()

    expect(page.locator(".dual-row-selected")).to_have_count(0)
    expect(page.locator(".dual-row-available")).to_have_count(12)


def test_dual_listbox_enter_in_filter_adds_nothing(page, open_example):
    """Enter in a filter input does not move any item."""
    open_example("Dual listbox")

    page.get_by_label("Filter available items").fill("b")
    with page.expect_navigation():
        page.get_by_label("Filter available items").press("Enter")

    expect(page.locator(".dual-row-selected .row-name")).to_have_text(
        ["Alice Brown", "Carol Davis"]
    )


def test_dual_listbox_save_persists_the_selection(page, open_example):
    """Saving keeps the selection after a reload."""
    open_example("Dual listbox")
    page.get_by_role("button", name="Add Bob Carter").click()
    expect(page.get_by_role("button", name="Remove Bob Carter")).to_be_visible()

    with page.expect_navigation():
        page.locator(".save").click()

    page.goto(page.url)
    expect(page.locator(".dual-row-selected .row-name")).to_have_text(
        ["Alice Brown", "Bob Carter", "Carol Davis"]
    )
