"""End-to-end tests for the bulk actions example."""

from playwright.sync_api import expect


def _button(page, name):
    return page.get_by_role("button", name=name, exact=True)


def test_bulk_actions_toolbar_appears_on_the_first_tick(page, open_example):
    """The toolbar replaces the message count once a box is ticked."""
    open_example("Bulk actions")
    expect(page.get_by_text("5 messages")).to_be_visible()
    expect(_button(page, "Archive")).to_be_hidden()

    page.get_by_role("checkbox", name="Select Quarterly report draft").check()

    expect(page.get_by_text("5 messages")).to_be_hidden()
    expect(_button(page, "Archive")).to_be_visible()


def test_bulk_actions_tick_updates_the_count(page, open_example):
    """Ticking messages updates the count in the toolbar."""
    open_example("Bulk actions")
    count = page.locator(".bulk-active output")

    page.get_by_role("checkbox", name="Select Quarterly report draft").check()
    expect(count).to_have_text("1 selected")

    page.get_by_role("checkbox", name="Select Invoice #2024-117").check()
    expect(count).to_have_text("2 selected")


def test_bulk_actions_tick_keeps_the_focus(page, open_example):
    """The ticked checkbox keeps the focus after the refresh."""
    open_example("Bulk actions")
    box = page.get_by_role("checkbox", name="Select Quarterly report draft")

    box.check()

    expect(page.locator(".bulk-active output")).to_have_text("1 selected")
    expect(box).to_be_focused()


def test_bulk_actions_toolbar_only_offers_useful_actions(page, open_example):
    """Only the actions that change a ticked message are offered."""
    open_example("Bulk actions")

    page.get_by_role("checkbox", name="Select Quarterly report draft").check()

    expect(_button(page, "Mark read")).to_be_visible()
    expect(_button(page, "Mark unread")).to_have_count(0)

    page.get_by_role("checkbox", name="Select Lunch on Friday?").check()

    expect(_button(page, "Mark unread")).to_be_visible()


def test_bulk_actions_select_buttons(page, open_example):
    """All, Read, Unread and None tick the matching messages."""
    open_example("Bulk actions")
    checked = page.locator("input[name='selection']:checked")

    _button(page, "All").click()
    expect(checked).to_have_count(5)

    _button(page, "Unread").click()
    expect(page.locator("tr.unread input:checked")).to_have_count(2)
    expect(checked).to_have_count(2)

    _button(page, "Read").click()
    expect(checked).to_have_count(3)

    _button(page, "None").click()
    expect(checked).to_have_count(0)


def test_bulk_actions_select_button_keeps_the_focus(page, open_example):
    """A select button keeps the focus after the refresh."""
    open_example("Bulk actions")
    button = _button(page, "Unread")

    button.click()

    expect(page.locator(".bulk-active output")).to_have_text("2 selected")
    expect(button).to_be_focused()


def test_bulk_actions_mark_as_read(page, open_example):
    """Mark read applies to every ticked message."""
    open_example("Bulk actions")
    _button(page, "Unread").click()
    expect(page.locator(".bulk-active output")).to_have_text("2 selected")

    with page.expect_navigation():
        _button(page, "Mark read").click()

    expect(page.get_by_role("status")).to_contain_text("2 marked as read.")
    expect(page.locator("tr.unread")).to_have_count(0)
    expect(page.get_by_text("5 messages")).to_be_visible()


def test_bulk_actions_archive(page, open_example):
    """Archive removes the ticked messages from the inbox."""
    open_example("Bulk actions")
    page.get_by_role("checkbox", name="Select Lunch on Friday?").check()
    expect(page.locator(".bulk-active output")).to_have_text("1 selected")

    with page.expect_navigation():
        _button(page, "Archive").click()

    expect(page.get_by_role("status")).to_contain_text("1 archived.")
    expect(page.get_by_text("4 messages")).to_be_visible()
    expect(page.get_by_text("Lunch on Friday?")).to_have_count(0)
