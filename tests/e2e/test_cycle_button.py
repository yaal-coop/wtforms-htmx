"""End-to-end tests for the cycle button example."""

from playwright.sync_api import expect


def test_cycle_button_click_moves_to_next_priority(page, open_example):
    """Clicking the button moves the priority to the next value."""
    open_example("Cycle button")
    button = page.locator('button[name="cycle"]')
    expect(button).to_have_text("Priority: medium")

    button.click()

    expect(button).to_have_text("Priority: high")


def test_cycle_button_wraps_around(page, open_example):
    """After the last priority, a click goes back to the first one."""
    open_example("Cycle button")
    button = page.locator('button[name="cycle"]')

    for label in ("high", "critical", "low"):
        button.click()
        expect(button).to_have_text(f"Priority: {label}")


def test_cycle_button_save_persists(page, open_example):
    """Saving keeps the chosen priority after the reload."""
    open_example("Cycle button")
    button = page.locator('button[name="cycle"]')
    button.click()
    expect(button).to_have_text("Priority: high")

    with page.expect_navigation():
        page.get_by_role("button", name="Save").click()

    expect(page.get_by_role("status")).to_contain_text("Saved priority 'high'.")
    expect(button).to_have_text("Priority: high")
