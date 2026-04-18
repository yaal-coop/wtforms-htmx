"""Progressive-enhancement tests for the datalist autocomplete example."""

from playwright.sync_api import expect


def test_datalist_save_lists_matching_options_nojs(page_nojs, open_example):
    """Saving a partial name shows an error and lists the matching countries."""
    open_example("Datalist autocomplete")

    page_nojs.locator("input#country").fill("fra")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.locator("#wrap-country ul.errors")).to_have_text(
        "Please pick a country from the list."
    )
    expect(
        page_nojs.locator('datalist#country-datalist > option[value="France"]')
    ).to_be_attached()


def test_datalist_save_keeps_the_country_nojs(page_nojs, open_example):
    """Saving a known country keeps it after the reload."""
    open_example("Datalist autocomplete")

    page_nojs.locator("input#country").fill("France")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.get_by_role("status")).to_contain_text("Saved country 'France'.")
    expect(page_nojs.locator("input#country")).to_have_value("France")
