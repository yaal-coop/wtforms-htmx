"""Progressive-enhancement tests for the currency converter example."""

from playwright.sync_api import expect


def test_currency_convert_to_jpy_button_nojs(page_nojs, open_example):
    """The → JPY button fills the JPY amount from EUR."""
    open_example("Currency converter")

    page_nojs.locator("input#eur").fill("10")
    with page_nojs.expect_navigation():
        page_nojs.locator('[name="convert_to_jpy"]').click()

    expect(page_nojs.locator("input#jpy")).to_have_value("1650")


def test_currency_convert_to_eur_button_nojs(page_nojs, open_example):
    """The ← EUR button fills the EUR amount from JPY."""
    open_example("Currency converter")

    page_nojs.locator("input#jpy").fill("330")
    with page_nojs.expect_navigation():
        page_nojs.locator('[name="convert_to_eur"]').click()

    expect(page_nojs.locator("input#eur")).to_have_value("2")


def test_currency_enter_in_jpy_saves_nojs(page_nojs, open_example):
    """Enter in an amount saves the form and keeps the typed value."""
    open_example("Currency converter")

    page_nojs.locator("input#jpy").fill("330")
    with page_nojs.expect_navigation():
        page_nojs.locator("input#jpy").press("Enter")

    expect(page_nojs.get_by_role("status")).to_contain_text("Saved")
    expect(page_nojs.locator("input#jpy")).to_have_value("330")
