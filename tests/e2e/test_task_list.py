"""End-to-end tests for the task list example."""

from playwright.sync_api import expect


def _expect_titles(page, titles):
    inputs = page.locator("#tasks li input[type='text']")
    expect(inputs).to_have_count(len(titles))
    for index, title in enumerate(titles):
        expect(inputs.nth(index)).to_have_value(title)


def test_task_list_add_task(page, open_example):
    """Add task appends an empty row."""
    open_example("Task list")

    page.get_by_role("button", name="+ Add task").click()

    _expect_titles(page, ["Buy milk", "Call mum", ""])


def test_task_list_remove_task(page, open_example):
    """A row's × removes that row, not the last one."""
    open_example("Task list")
    page.get_by_role("button", name="+ Add task").click()
    _expect_titles(page, ["Buy milk", "Call mum", ""])
    page.locator("#tasks li input[type='text']").nth(2).fill("Walk dog")

    page.get_by_role("button", name="Remove task 2").click()

    _expect_titles(page, ["Buy milk", "Walk dog"])


def test_task_list_move_up_and_down(page, open_example):
    """The ↑ and ↓ buttons move a row."""
    open_example("Task list")

    page.get_by_role("button", name="Move task 2 up").click()
    _expect_titles(page, ["Call mum", "Buy milk"])

    page.get_by_role("button", name="Move task 1 down").click()
    _expect_titles(page, ["Buy milk", "Call mum"])


def test_task_list_drag_to_reorder(page, open_example):
    """Dragging a row above another reorders the list."""
    open_example("Task list")

    page.locator("li[data-index='1'] .drag-handle").drag_to(
        page.locator("li[data-index='0'] .drag-handle")
    )

    _expect_titles(page, ["Call mum", "Buy milk"])


def test_task_list_save_persists(page, open_example):
    """Saving keeps the tasks after the reload."""
    open_example("Task list")
    page.get_by_role("button", name="Move task 2 up").click()
    _expect_titles(page, ["Call mum", "Buy milk"])

    with page.expect_navigation():
        page.get_by_role("button", name="Save").click()

    expect(page.get_by_role("status")).to_contain_text("Tasks saved.")
    _expect_titles(page, ["Call mum", "Buy milk"])
