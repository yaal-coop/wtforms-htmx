"""End-to-end tests for the dynamic address form example."""

from playwright.sync_api import expect


def test_address_postal_code_fills_city(page, open_example):
    """Typing a postal code fills the delivery city."""
    open_example("Dynamic address form")

    page.locator("input#delivery_address-postal_code").fill("69001")

    expect(page.locator("select#delivery_address-city")).to_have_value("Lyon")


def test_address_country_change_clears_city(page, open_example):
    """Emptying the country clears the delivery city."""
    open_example("Dynamic address form")
    city = page.locator("select#delivery_address-city")
    expect(city).to_have_value("Paris")

    page.locator("select#country").select_option("")

    expect(city).to_have_value("")


def test_address_billing_revealed_and_prefilled_on_uncheck(page, open_example):
    """Unchecking "same billing" reveals the billing block filled with the delivery address."""
    open_example("Dynamic address form")
    line_1 = page.locator("input#billing_address-line_1")
    expect(line_1).to_be_hidden()

    page.locator("input#same_billing").uncheck()

    expect(line_1).to_have_value("12 Rue de Rivoli")
    expect(page.locator("input#billing_address-postal_code")).to_have_value("75001")
    expect(page.locator("select#billing_address-city")).to_have_value("Paris")
