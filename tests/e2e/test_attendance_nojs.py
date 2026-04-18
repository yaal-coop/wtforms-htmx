"""Progressive-enhancement tests for the attendance grid example."""

from playwright.sync_api import expect


def test_attendance_cell_click_cycles_state_nojs(page_nojs, open_example):
    """Clicking a cell moves it to the next state."""
    open_example("Attendance grid")
    cell = page_nojs.get_by_role("button", name="Toggle Alice on 2026-06-03")
    expect(cell).to_have_text("✓")

    with page_nojs.expect_navigation():
        cell.click()

    expect(cell).to_have_text("?")


def test_attendance_add_user_appends_a_row_nojs(page_nojs, open_example):
    """Add user appends a named row to the grid."""
    open_example("Attendance grid")
    rows = page_nojs.locator(".attendance-table tbody tr")
    expect(rows).to_have_count(3)

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Add user").click()

    expect(rows).to_have_count(4)
    expect(rows.last.locator(".attendance-rowheader-label")).to_have_text("User 4")


def test_attendance_remove_user_drops_the_row_nojs(page_nojs, open_example):
    """A row's × removes that user from the grid."""
    open_example("Attendance grid")
    labels = page_nojs.locator(".attendance-rowheader-label")

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Remove Bob").click()

    expect(labels).to_have_text(["Alice", "Charlie"])


def test_attendance_add_date_appends_a_column_nojs(page_nojs, open_example):
    """Add date appends the next weekly date as a column."""
    open_example("Attendance grid")
    columns = page_nojs.locator(".attendance-colheader-label")
    expect(columns).to_have_count(4)

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Add date").click()

    expect(columns).to_have_count(5)
    expect(columns.last).to_have_text("Wed 01 Jul")


def test_attendance_remove_date_drops_the_column_nojs(page_nojs, open_example):
    """A column's × removes that date from the grid."""
    open_example("Attendance grid")
    columns = page_nojs.locator(".attendance-colheader-label")

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Remove 2026-06-10").click()

    expect(columns).to_have_text(["Wed 03 Jun", "Wed 17 Jun", "Wed 24 Jun"])


def test_attendance_enter_in_rename_saves_the_name_nojs(page_nojs, open_example):
    """Enter in the rename input saves the name and adds no row."""
    open_example("Attendance grid")
    rows = page_nojs.locator(".attendance-table tbody tr")
    expect(rows).to_have_count(3)

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Edit name").first.click()

    name = page_nojs.locator("input.attendance-rowheader-input")
    name.fill("Alicia")
    with page_nojs.expect_navigation():
        name.press("Enter")

    expect(rows.first.locator(".attendance-rowheader-label")).to_have_text("Alicia")
    expect(rows).to_have_count(3)
