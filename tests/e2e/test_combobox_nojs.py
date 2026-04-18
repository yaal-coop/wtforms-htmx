"""Progressive-enhancement tests for the combobox example."""

from playwright.sync_api import expect


def _search(page, query):
    page.locator("input#query").fill(query)
    with page.expect_navigation():
        page.get_by_role("button", name="Search").click()


def test_combobox_search_button_filters_suggestions_nojs(page_nojs, open_example):
    """Clicking Search lists the matching countries."""
    open_example("Combobox")

    _search(page_nojs, "ger")

    expect(
        page_nojs.locator("ul#suggestions button", has_text="Germany")
    ).to_be_visible()


def test_combobox_enter_in_query_searches_nojs(page_nojs, open_example):
    """Enter in the query runs Search and keeps the chips."""
    open_example("Combobox")

    page_nojs.locator("input#query").fill("ger")
    with page_nojs.expect_navigation():
        page_nojs.locator("input#query").press("Enter")

    expect(
        page_nojs.locator("ul#suggestions button", has_text="Germany")
    ).to_be_visible()
    expect(page_nojs.locator("#countries .chip")).to_have_count(2)


def test_combobox_pick_appends_chip_nojs(page_nojs, open_example):
    """Clicking a suggestion appends a chip and clears the query."""
    open_example("Combobox")
    _search(page_nojs, "ger")

    with page_nojs.expect_navigation():
        page_nojs.locator("ul#suggestions button", has_text="Germany").click()

    expect(page_nojs.locator('#countries .chip[data-value="DE"]')).to_be_visible()
    expect(page_nojs.locator("input#query")).to_have_value("")


def test_combobox_remove_chip_nojs(page_nojs, open_example):
    """Clicking a chip's × removes it."""
    open_example("Combobox")

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Remove France").click()

    expect(page_nojs.locator("#countries .chip-label")).to_have_text(["Japan"])


def test_combobox_already_picked_shows_disabled_nojs(page_nojs, open_example):
    """A picked country shows in the suggestions as disabled."""
    open_example("Combobox")

    _search(page_nojs, "france")

    expect(
        page_nojs.locator("ul#suggestions button", has_text="France")
    ).to_be_disabled()


def test_combobox_save_persists_picks_nojs(page_nojs, open_example):
    """Saving keeps the picked countries after a reload."""
    open_example("Combobox")
    _search(page_nojs, "ger")
    with page_nojs.expect_navigation():
        page_nojs.locator("ul#suggestions button", has_text="Germany").click()

    with page_nojs.expect_navigation():
        page_nojs.locator('[name="save"]').click()

    page_nojs.goto(page_nojs.url)
    expect(page_nojs.locator("#countries .chip")).to_have_count(3)
    for code in ("FR", "JP", "DE"):
        expect(
            page_nojs.locator(f'#countries .chip[data-value="{code}"]')
        ).to_have_count(1)
