"""End-to-end tests for the invoice totals example."""

from playwright.sync_api import expect


def test_invoice_quantity_updates_its_row_and_the_totals(page, open_example):
    """Typing a quantity updates that row's total and the grand total only."""
    open_example("Invoice totals")
    expect(page.locator("#grand_total")).to_have_text("55.80")

    page.locator("input#items-0-quantity").fill("5")

    expect(page.locator("input#items-0-total")).to_have_value("57.00")
    expect(page.locator("#grand_total")).to_have_text("90.00")
    expect(page.locator("input#items-1-total")).to_have_value("33.00")


def test_invoice_vat_rate_updates_its_row_and_the_totals(page, open_example):
    """Typing a VAT rate updates that row's total and the VAT total only."""
    open_example("Invoice totals")

    page.locator("input#items-1-vat_rate").fill("20")

    expect(page.locator("input#items-1-total")).to_have_value("36.00")
    expect(page.locator("#vat_total")).to_have_text("9.80")
    expect(page.locator("#grand_total")).to_have_text("58.80")
    expect(page.locator("input#items-0-total")).to_have_value("22.80")


def test_invoice_add_line(page, open_example):
    """The + button appends an empty line."""
    open_example("Invoice totals")
    rows = page.locator("#items tr")
    expect(rows).to_have_count(2)

    page.locator('[name="add_line"]').click()

    expect(rows).to_have_count(3)


def test_invoice_remove_line_updates_the_totals(page, open_example):
    """A line's × removes it and updates the grand total."""
    open_example("Invoice totals")

    page.get_by_role("button", name="Remove line 1").click()

    expect(page.locator("#items tr")).to_have_count(1)
    expect(page.locator("#grand_total")).to_have_text("33.00")


def test_invoice_enter_in_cell_saves(page, open_example):
    """Enter in a cell saves the invoice and keeps every line."""
    open_example("Invoice totals")

    page.locator("input#items-0-quantity").fill("5")
    with page.expect_navigation():
        page.locator("input#items-0-quantity").press("Enter")

    expect(page.get_by_role("status").filter(has_text="Saved invoice")).to_be_visible()
    expect(page.locator("#items tr")).to_have_count(2)
    expect(page.locator("input#items-0-total")).to_have_value("57.00")
