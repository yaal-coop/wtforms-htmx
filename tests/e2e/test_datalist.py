"""End-to-end tests for the datalist autocomplete example."""

from playwright.sync_api import expect


def test_datalist_typing_filters_options(page, open_example):
    """Typing in the input lists the matching countries in the datalist."""
    open_example("Datalist autocomplete")

    page.locator("input#country").fill("fra")

    expect(page.locator("datalist#country-datalist > option")).to_have_count(1)
    expect(
        page.locator('datalist#country-datalist > option[value="France"]')
    ).to_be_attached()


def test_datalist_unknown_country_shows_error_on_blur(page, open_example):
    """Leaving the input with an unknown country shows an error."""
    open_example("Datalist autocomplete")

    page.locator("input#country").fill("Atlantis")
    page.locator("input#country").blur()

    expect(page.locator("#wrap-country ul.errors")).to_have_text(
        "Please pick a country from the list."
    )


def test_datalist_save_keeps_the_country(page, open_example):
    """Saving a known country keeps it after the reload."""
    open_example("Datalist autocomplete")

    page.locator("input#country").fill("France")
    with page.expect_navigation():
        page.get_by_role("button", name="Save").click()

    expect(page.get_by_role("status")).to_contain_text("Saved country 'France'.")
    expect(page.locator("input#country")).to_have_value("France")
