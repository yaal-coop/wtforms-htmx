"""Progressive-enhancement tests for the bulk actions example."""

from playwright.sync_api import expect


def _button(page, name):
    return page.get_by_role("button", name=name, exact=True)


def test_bulk_actions_toolbar_appears_on_the_first_tick_nojs(page_nojs, open_example):
    """The toolbar shows every action once a box is ticked."""
    open_example("Bulk actions")
    expect(_button(page_nojs, "Archive")).to_be_hidden()

    page_nojs.get_by_role("checkbox", name="Select Quarterly report draft").check()

    for name in ("Mark read", "Mark unread", "Archive"):
        expect(_button(page_nojs, name)).to_be_visible()


def test_bulk_actions_select_unread_nojs(page_nojs, open_example):
    """Unread reloads the page with the unread messages ticked."""
    open_example("Bulk actions")

    with page_nojs.expect_navigation():
        _button(page_nojs, "Unread").click()

    expect(page_nojs.locator(".bulk-active output")).to_have_text("2 selected")
    expect(page_nojs.locator("tr.unread input:checked")).to_have_count(2)
    expect(page_nojs.locator("input[name='selection']:checked")).to_have_count(2)


def test_bulk_actions_select_none_nojs(page_nojs, open_example):
    """None reloads the page with no message ticked."""
    open_example("Bulk actions")
    page_nojs.get_by_role("checkbox", name="Select Lunch on Friday?").check()

    with page_nojs.expect_navigation():
        _button(page_nojs, "None").click()

    expect(page_nojs.locator("input[name='selection']:checked")).to_have_count(0)
    expect(page_nojs.get_by_text("5 messages")).to_be_visible()


def test_bulk_actions_mark_as_read_skips_read_messages_nojs(page_nojs, open_example):
    """Mark read changes the unread messages and counts the others."""
    open_example("Bulk actions")
    page_nojs.get_by_role("checkbox", name="Select Quarterly report draft").check()
    page_nojs.get_by_role("checkbox", name="Select Lunch on Friday?").check()

    with page_nojs.expect_navigation():
        _button(page_nojs, "Mark read").click()

    expect(page_nojs.get_by_role("status")).to_contain_text(
        "1 marked as read, 1 already read."
    )
    expect(page_nojs.locator("tr.unread")).to_have_count(1)
