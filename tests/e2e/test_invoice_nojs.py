"""Progressive-enhancement tests for the invoice totals example."""

from playwright.sync_api import expect


def test_invoice_save_updates_the_totals_nojs(page_nojs, open_example):
    """Saving the invoice updates the row totals and the grand total."""
    open_example("Invoice totals")

    page_nojs.locator("input#items-0-quantity").fill("5")
    page_nojs.locator("input#items-1-vat_rate").fill("20")
    with page_nojs.expect_navigation():
        page_nojs.locator(".save").click()

    expect(page_nojs.locator("input#items-0-total")).to_have_value("57.00")
    expect(page_nojs.locator("input#items-1-total")).to_have_value("36.00")
    expect(page_nojs.locator("#grand_total")).to_have_text("93.00")


def test_invoice_add_line_nojs(page_nojs, open_example):
    """The + button appends an empty line."""
    open_example("Invoice totals")
    rows = page_nojs.locator("#items tr")
    expect(rows).to_have_count(2)

    with page_nojs.expect_navigation():
        page_nojs.locator('[name="add_line"]').click()

    expect(rows).to_have_count(3)


def test_invoice_remove_line_updates_the_totals_nojs(page_nojs, open_example):
    """A line's × removes it and updates the grand total."""
    open_example("Invoice totals")

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Remove line 1").click()

    expect(page_nojs.locator("#items tr")).to_have_count(1)
    expect(page_nojs.locator("#grand_total")).to_have_text("33.00")


def test_invoice_enter_in_cell_saves_nojs(page_nojs, open_example):
    """Enter in a cell saves the invoice and keeps every line."""
    open_example("Invoice totals")

    page_nojs.locator("input#items-0-quantity").fill("5")
    with page_nojs.expect_navigation():
        page_nojs.locator("input#items-0-quantity").press("Enter")

    expect(
        page_nojs.get_by_role("status").filter(has_text="Saved invoice")
    ).to_be_visible()
    expect(page_nojs.locator("#items tr")).to_have_count(2)
    expect(page_nojs.locator("input#items-0-total")).to_have_value("57.00")
