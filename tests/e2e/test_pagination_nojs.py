"""Progressive-enhancement tests for the pagination example."""

import re

from playwright.sync_api import expect


def _expect_current_page(page, number):
    expect(page.locator('nav.pagination button[aria-current="page"]')).to_have_text(
        str(number)
    )


def _click(page, name):
    with page.expect_navigation():
        page.get_by_role("button", name=name).click()


def test_pagination_starts_on_page_one_nojs(page_nojs, open_example):
    """The page starts on page 1, with its button and Previous disabled."""
    open_example("Pagination")

    _expect_current_page(page_nojs, 1)
    expect(page_nojs.get_by_role("button", name="Go to page 1")).to_be_disabled()
    expect(page_nojs.get_by_role("button", name="Previous page")).to_be_disabled()


def test_pagination_number_jumps_to_page_nojs(page_nojs, open_example):
    """Clicking a page number shows that page of posts."""
    open_example("Pagination")

    _click(page_nojs, "Go to page 3")

    _expect_current_page(page_nojs, 3)
    expect(page_nojs.locator(".pagination-results-header")).to_contain_text(
        "Showing 21–30 of 47 posts"
    )
    expect(page_nojs).to_have_url(re.compile(r"/pagination\?page=3$"))


def test_pagination_next_advances_nojs(page_nojs, open_example):
    """Next goes to the following page."""
    open_example("Pagination")

    _click(page_nojs, "Next page")

    _expect_current_page(page_nojs, 2)


def test_pagination_previous_steps_back_nojs(page_nojs, open_example):
    """Previous goes back one page."""
    open_example("Pagination")
    _click(page_nojs, "Go to page 3")

    _click(page_nojs, "Previous page")

    _expect_current_page(page_nojs, 2)


def test_pagination_next_disabled_on_last_page_nojs(page_nojs, open_example):
    """Next is disabled on the last page."""
    open_example("Pagination")

    _click(page_nojs, "Go to page 5")

    _expect_current_page(page_nojs, 5)
    expect(page_nojs.get_by_role("button", name="Next page")).to_be_disabled()
