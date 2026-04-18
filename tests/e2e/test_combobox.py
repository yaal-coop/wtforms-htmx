"""End-to-end tests for the combobox example."""

from playwright.sync_api import expect


def test_combobox_typing_filters_suggestions(page, open_example):
    """Typing in the query lists the matching countries."""
    open_example("Combobox")

    page.locator("input#query").fill("ger")

    expect(page.locator("ul#suggestions button", has_text="Germany")).to_be_visible()


def test_combobox_search_button_filters_suggestions(page, open_example):
    """Clicking Search lists the matching countries."""
    open_example("Combobox")

    page.locator("input#query").fill("ger")
    page.get_by_role("button", name="Search").click()

    expect(page.locator("ul#suggestions button", has_text="Germany")).to_be_visible()


def test_combobox_enter_in_query_searches(page, open_example):
    """Enter in the query runs Search and keeps the chips."""
    open_example("Combobox")

    page.locator("input#query").fill("ger")
    page.locator("input#query").press("Enter")

    expect(page.locator("ul#suggestions button", has_text="Germany")).to_be_visible()
    expect(page.locator("#countries .chip")).to_have_count(2)


def test_combobox_pick_appends_chip(page, open_example):
    """Clicking a suggestion appends a chip and clears the query."""
    open_example("Combobox")
    page.locator("input#query").fill("ger")
    page.get_by_role("button", name="Search").click()

    page.locator("ul#suggestions button", has_text="Germany").click()

    expect(page.locator('#countries .chip[data-value="DE"]')).to_be_visible()
    expect(page.locator("input#query")).to_have_value("")


def test_combobox_remove_chip(page, open_example):
    """Clicking a chip's × removes it."""
    open_example("Combobox")

    page.get_by_role("button", name="Remove France").click()

    expect(page.locator("#countries .chip-label")).to_have_text(["Japan"])


def test_combobox_already_picked_shows_disabled(page, open_example):
    """A picked country shows in the suggestions as disabled."""
    open_example("Combobox")

    page.locator("input#query").fill("france")
    page.get_by_role("button", name="Search").click()

    expect(page.locator("ul#suggestions button", has_text="France")).to_be_disabled()


def test_combobox_save_persists_picks(page, open_example):
    """Saving keeps the picked countries after a reload."""
    open_example("Combobox")
    page.locator("input#query").fill("ger")
    page.get_by_role("button", name="Search").click()
    page.locator("ul#suggestions button", has_text="Germany").click()
    expect(page.locator('#countries .chip[data-value="DE"]')).to_be_visible()

    with page.expect_navigation():
        page.locator('[name="save"]').click()

    page.goto(page.url)
    expect(page.locator("#countries .chip")).to_have_count(3)
    for code in ("FR", "JP", "DE"):
        expect(page.locator(f'#countries .chip[data-value="{code}"]')).to_have_count(1)
