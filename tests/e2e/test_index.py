"""End-to-end tests for the overview page."""

from examples import EXAMPLES
from playwright.sync_api import expect


def test_index_loads(page, nav):
    """The overview page has the gallery title and a nav link per example."""
    expect(page).to_have_title("wtforms-htmx examples")
    for label in ("Overview", *EXAMPLES.values()):
        expect(nav.get_by_role("link", name=label, exact=True)).to_be_visible()


def test_index_boots_the_requested_htmx_version(page, htmx_version):
    """The gallery loads the htmx build that matches ``--htmx-version``."""
    version = page.evaluate("window.htmx.version")
    assert version.startswith(f"{htmx_version}.")


def test_index_htmx_toggle_roundtrip(page):
    """The nav switch turns htmx off, then back on."""
    switch = page.get_by_role("switch")
    expect(switch).to_be_checked()

    with page.expect_navigation():
        switch.click()

    expect(switch).not_to_be_checked()
    assert page.evaluate("!!window.htmx") is False

    with page.expect_navigation():
        switch.click()

    expect(switch).to_be_checked()
    assert page.evaluate("!!window.htmx") is True
