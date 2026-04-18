"""Progressive-enhancement tests for the task list example."""

from playwright.sync_api import expect


def _expect_titles(page, titles):
    inputs = page.locator("#tasks li input[type='text']")
    expect(inputs).to_have_count(len(titles))
    for index, title in enumerate(titles):
        expect(inputs.nth(index)).to_have_value(title)


def _click(page, name):
    with page.expect_navigation():
        page.get_by_role("button", name=name).click()


def test_task_list_add_task_nojs(page_nojs, open_example):
    """Add task appends an empty row."""
    open_example("Task list")

    _click(page_nojs, "+ Add task")

    _expect_titles(page_nojs, ["Buy milk", "Call mum", ""])


def test_task_list_remove_task_nojs(page_nojs, open_example):
    """A row's × removes that row, not the last one."""
    open_example("Task list")
    _click(page_nojs, "+ Add task")
    page_nojs.locator("#tasks li input[type='text']").nth(2).fill("Walk dog")

    _click(page_nojs, "Remove task 2")

    _expect_titles(page_nojs, ["Buy milk", "Walk dog"])


def test_task_list_move_up_and_down_nojs(page_nojs, open_example):
    """The ↑ and ↓ buttons move a row."""
    open_example("Task list")

    _click(page_nojs, "Move task 2 up")
    _expect_titles(page_nojs, ["Call mum", "Buy milk"])

    _click(page_nojs, "Move task 1 down")
    _expect_titles(page_nojs, ["Buy milk", "Call mum"])


def test_task_list_save_persists_nojs(page_nojs, open_example):
    """Saving keeps the tasks after the reload."""
    open_example("Task list")
    _click(page_nojs, "Move task 2 up")

    _click(page_nojs, "Save")

    expect(page_nojs.get_by_role("status")).to_contain_text("Tasks saved.")
    _expect_titles(page_nojs, ["Call mum", "Buy milk"])
