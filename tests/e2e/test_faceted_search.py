"""End-to-end tests for the faceted search example."""

from playwright.sync_api import expect


def test_faceted_search_typing_narrows_results(page, open_example):
    """Typing in the search bar narrows the results."""
    open_example("Faceted search")
    count = page.locator(".facets-results-header strong")
    expect(count).to_have_text("29")

    page.locator("input#query").fill("tolkien")

    expect(count).to_have_text("2")


def test_faceted_search_enter_in_query_keeps_facets(page, live_server):
    """Enter in the query applies it and keeps the active facets."""
    page.goto(f"{live_server}/faceted-search?genre=Fantasy")

    page.locator("input#query").fill("tolkien")
    with page.expect_navigation():
        page.locator("input#query").press("Enter")

    expect(page.locator(".facets-results-header strong")).to_have_text("2")
    expect(page.locator(".facets-bar-input .chip-label")).to_have_text(
        ["Genre: Fantasy"]
    )


def test_faceted_search_genre_filter_adds_chip(page, open_example):
    """Picking a genre narrows the results and adds a chip."""
    open_example("Faceted search")

    page.locator("summary.facets-dropdown-summary").click()
    page.locator("select#genre").select_option("Fantasy")

    expect(page.locator(".facets-results-header strong")).to_have_text("3")
    expect(page.locator(".facets-bar-input .chip-label")).to_have_text(
        ["Genre: Fantasy"]
    )


def test_faceted_search_chip_clear_resets_the_open_dropdown(page, open_example):
    """Clearing a chip resets the results and the genre select in the open dropdown."""
    open_example("Faceted search")
    count = page.locator(".facets-results-header strong")
    page.locator("summary.facets-dropdown-summary").click()
    page.locator("select#genre").select_option("Fantasy")
    expect(count).to_have_text("3")

    page.locator(".facets-bar-input .chip-remove").click()

    expect(count).to_have_text("29")
    expect(page.locator(".facets-bar-input .chip")).to_have_count(0)
    expect(page.locator("details.facets-dropdown")).to_have_attribute("open", "")
    expect(page.locator("select#genre")).to_have_value("")


def test_faceted_search_chip_clear_keeps_the_other_filters(page, live_server):
    """Clearing one chip keeps the other facets and the query."""
    page.goto(f"{live_server}/faceted-search?genre=Fantasy&language=English&query=the")

    page.locator(".facets-bar-input .chip-remove").first.click()

    expect(page.locator(".facets-bar-input .chip-label")).to_have_text(
        ["Language: English"]
    )
    expect(page.locator("input#query")).to_have_value("the")
