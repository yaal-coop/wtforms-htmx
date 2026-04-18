"""Progressive-enhancement tests for the faceted search example."""

from playwright.sync_api import expect


def test_faceted_search_enter_in_query_keeps_facets_nojs(page_nojs, live_server):
    """Enter in the query applies it and keeps the active facets."""
    page_nojs.goto(f"{live_server}/faceted-search?genre=Fantasy")

    page_nojs.locator("input#query").fill("tolkien")
    with page_nojs.expect_navigation():
        page_nojs.locator("input#query").press("Enter")

    expect(page_nojs.locator(".facets-results-header strong")).to_have_text("2")
    expect(page_nojs.locator(".facets-bar-input .chip-label")).to_have_text(
        ["Genre: Fantasy"]
    )


def test_faceted_search_genre_filter_apply_adds_chip_nojs(page_nojs, open_example):
    """Picking a genre then clicking Apply narrows the results and adds a chip."""
    open_example("Faceted search")

    page_nojs.locator("summary.facets-dropdown-summary").click()
    page_nojs.locator("select#genre").select_option("Fantasy")
    with page_nojs.expect_navigation():
        page_nojs.locator(".facets-actions").get_by_role("button", name="Apply").click()

    expect(page_nojs.locator(".facets-results-header strong")).to_have_text("3")
    expect(page_nojs.locator(".facets-bar-input .chip-label")).to_have_text(
        ["Genre: Fantasy"]
    )


def test_faceted_search_chip_clear_keeps_the_other_filters_nojs(page_nojs, live_server):
    """Clearing one chip keeps the other facets and the query."""
    page_nojs.goto(
        f"{live_server}/faceted-search?genre=Fantasy&language=English&query=the"
    )

    with page_nojs.expect_navigation():
        page_nojs.locator(".facets-bar-input .chip-remove").first.click()

    expect(page_nojs.locator(".facets-bar-input .chip-label")).to_have_text(
        ["Language: English"]
    )
    expect(page_nojs.locator("input#query")).to_have_value("the")
