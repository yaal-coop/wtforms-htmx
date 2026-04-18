"""End-to-end tests for the pagination example."""

import re

from playwright.sync_api import expect


def _expect_current_page(page, number):
    expect(page.locator('nav.pagination button[aria-current="page"]')).to_have_text(
        str(number)
    )


def test_pagination_starts_on_page_one(page, open_example):
    """The page starts on page 1, with its button and Previous disabled."""
    open_example("Pagination")

    _expect_current_page(page, 1)
    expect(page.get_by_role("button", name="Go to page 1")).to_be_disabled()
    expect(page.get_by_role("button", name="Previous page")).to_be_disabled()


def test_pagination_number_jumps_to_page(page, open_example):
    """Clicking a page number shows that page of posts."""
    open_example("Pagination")

    page.get_by_role("button", name="Go to page 3").click()

    _expect_current_page(page, 3)
    expect(page.locator(".pagination-results-header")).to_contain_text(
        "Showing 21–30 of 47 posts"
    )
    expect(page).to_have_url(re.compile(r"/pagination\?page=3$"))


def test_pagination_next_advances(page, open_example):
    """Next goes to the following page."""
    open_example("Pagination")

    page.get_by_role("button", name="Next page").click()

    _expect_current_page(page, 2)


def test_pagination_previous_steps_back(page, open_example):
    """Previous goes back one page."""
    open_example("Pagination")
    page.get_by_role("button", name="Go to page 3").click()
    _expect_current_page(page, 3)

    page.get_by_role("button", name="Previous page").click()

    _expect_current_page(page, 2)


def test_pagination_next_disabled_on_last_page(page, open_example):
    """Next is disabled on the last page."""
    open_example("Pagination")

    page.get_by_role("button", name="Go to page 5").click()

    _expect_current_page(page, 5)
    expect(page.get_by_role("button", name="Next page")).to_be_disabled()
