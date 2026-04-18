"""Progressive-enhancement tests for the cycle button example."""

from playwright.sync_api import expect


def test_cycle_button_click_moves_to_next_priority_nojs(page_nojs, open_example):
    """Clicking the button moves the priority to the next value."""
    open_example("Cycle button")
    button = page_nojs.locator('button[name="cycle"]')
    expect(button).to_have_text("Priority: medium")

    with page_nojs.expect_navigation():
        button.click()

    expect(button).to_have_text("Priority: high")


def test_cycle_button_wraps_around_nojs(page_nojs, open_example):
    """After the last priority, a click goes back to the first one."""
    open_example("Cycle button")
    button = page_nojs.locator('button[name="cycle"]')

    for label in ("high", "critical", "low"):
        with page_nojs.expect_navigation():
            button.click()

        expect(button).to_have_text(f"Priority: {label}")


def test_cycle_button_save_persists_nojs(page_nojs, open_example):
    """Saving keeps the chosen priority after the reload."""
    open_example("Cycle button")
    button = page_nojs.locator('button[name="cycle"]')
    with page_nojs.expect_navigation():
        button.click()

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.get_by_role("status")).to_contain_text("Saved priority 'high'.")
    expect(button).to_have_text("Priority: high")
