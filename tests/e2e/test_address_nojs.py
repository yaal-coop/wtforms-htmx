"""Progressive-enhancement tests for the dynamic address form example."""

from playwright.sync_api import expect


def test_address_postal_code_lookup_button_fills_city_nojs(page_nojs, open_example):
    """The Lookup button fills the delivery city from the postal code."""
    open_example("Dynamic address form")

    page_nojs.locator("input#delivery_address-postal_code").fill("69001")
    with page_nojs.expect_navigation():
        page_nojs.locator('[name="delivery_address-lookup_postal"]').click()

    expect(page_nojs.locator("select#delivery_address-city")).to_have_value("Lyon")


def test_address_country_change_apply_clears_city_nojs(page_nojs, open_example):
    """Emptying the country then clicking Apply clears the delivery city."""
    open_example("Dynamic address form")
    city = page_nojs.locator("select#delivery_address-city")
    expect(city).to_have_value("Paris")

    page_nojs.locator("select#country").select_option("")
    with page_nojs.expect_navigation():
        page_nojs.locator('[name="apply_country"]').click()

    expect(city).to_have_value("")


def test_address_billing_revealed_on_uncheck_and_save_nojs(page_nojs, open_example):
    """Saving with "same billing" unchecked reveals the billing block."""
    open_example("Dynamic address form")

    page_nojs.locator("input#same_billing").uncheck()
    with page_nojs.expect_navigation():
        page_nojs.locator('[name="save"]').click()

    expect(page_nojs.locator("input#billing_address-line_1")).to_be_visible()
