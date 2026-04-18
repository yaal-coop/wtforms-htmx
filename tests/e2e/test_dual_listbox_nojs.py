"""Progressive-enhancement tests for the dual listbox example."""

from playwright.sync_api import expect


def test_dual_listbox_add_item_nojs(page_nojs, open_example):
    """Clicking an available row moves it to the selected pane."""
    open_example("Dual listbox")

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Add Bob Carter").click()

    expect(page_nojs.get_by_role("button", name="Remove Bob Carter")).to_be_visible()


def test_dual_listbox_remove_item_nojs(page_nojs, open_example):
    """Clicking a selected row moves it back to the available pane."""
    open_example("Dual listbox")

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Remove Alice Brown").click()

    expect(page_nojs.get_by_role("button", name="Add Alice Brown")).to_be_visible()


def test_dual_listbox_add_all_adds_the_filtered_items_nojs(page_nojs, open_example):
    """Add all adds only the available items that match the filter."""
    open_example("Dual listbox")

    page_nojs.get_by_label("Filter available items").fill("jack")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Add all visible items").click()

    expect(page_nojs.locator(".dual-row-selected .row-name")).to_have_text(
        ["Alice Brown", "Carol Davis", "Jack Klein"]
    )


def test_dual_listbox_clear_all_empties_the_selection_nojs(page_nojs, open_example):
    """Clear all moves every selected item back to the available pane."""
    open_example("Dual listbox")

    with page_nojs.expect_navigation():
        page_nojs.get_by_role(
            "button", name="Remove all visible selected items"
        ).click()

    expect(page_nojs.locator(".dual-row-selected")).to_have_count(0)
    expect(page_nojs.locator(".dual-row-available")).to_have_count(12)


def test_dual_listbox_enter_in_filter_adds_nothing_nojs(page_nojs, open_example):
    """Enter in a filter input does not move any item."""
    open_example("Dual listbox")

    page_nojs.get_by_label("Filter available items").fill("b")
    with page_nojs.expect_navigation():
        page_nojs.get_by_label("Filter available items").press("Enter")

    expect(page_nojs.locator(".dual-row-selected .row-name")).to_have_text(
        ["Alice Brown", "Carol Davis"]
    )


def test_dual_listbox_save_persists_the_selection_nojs(page_nojs, open_example):
    """Saving keeps the selection after a reload."""
    open_example("Dual listbox")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Add Bob Carter").click()

    with page_nojs.expect_navigation():
        page_nojs.locator(".save").click()

    page_nojs.goto(page_nojs.url)
    expect(page_nojs.locator(".dual-row-selected .row-name")).to_have_text(
        ["Alice Brown", "Bob Carter", "Carol Davis"]
    )
