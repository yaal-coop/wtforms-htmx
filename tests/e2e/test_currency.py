"""End-to-end tests for the currency converter example."""

from playwright.sync_api import expect


def test_currency_typing_eur_converts_to_jpy(page, open_example):
    """Typing an amount in EUR fills the JPY amount."""
    open_example("Currency converter")

    page.locator("input#eur").fill("10")

    expect(page.locator("input#jpy")).to_have_value("1650")


def test_currency_typing_jpy_converts_to_eur(page, open_example):
    """Typing an amount in JPY fills the EUR amount."""
    open_example("Currency converter")

    page.locator("input#jpy").fill("330")

    expect(page.locator("input#eur")).to_have_value("2")


def test_currency_enter_in_jpy_saves(page, open_example):
    """Enter in an amount saves the form and keeps the typed value."""
    open_example("Currency converter")

    page.locator("input#jpy").fill("330")
    with page.expect_navigation():
        page.locator("input#jpy").press("Enter")

    expect(page.get_by_role("status")).to_contain_text("Saved")
    expect(page.locator("input#jpy")).to_have_value("330")
