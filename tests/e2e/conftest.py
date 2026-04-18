"""End-to-end tests for the example app, driven by Playwright.

Run with ``pytest tests/e2e --browser chromium``. The ``e2e`` dependency
group installs pytest-playwright and the example's runtime deps; run
``playwright install chromium`` once to pull the browser.
"""

from __future__ import annotations

import socket
from threading import Thread
from urllib.parse import urlparse

import pytest

pytest.importorskip("playwright")
pytest.importorskip("pytest_playwright")

from examples import create_app
from examples._shared import reset_state
from playwright.sync_api import expect
from werkzeug.serving import make_server

#: Timeout of every ``expect`` assertion, in milliseconds.
EXPECT_TIMEOUT = 5_000


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def pytest_addoption(parser):
    parser.addoption(
        "--htmx-version",
        action="store",
        default="4",
        choices=("2", "4"),
        help="htmx major version the example app boots (default: 4)",
    )


@pytest.fixture(scope="session", autouse=True)
def expect_timeout():
    """Give every ``expect`` assertion the same retry window."""
    expect.set_options(timeout=EXPECT_TIMEOUT)


@pytest.fixture(scope="session")
def htmx_version(request) -> int:
    return int(request.config.getoption("--htmx-version"))


@pytest.fixture(scope="session")
def live_server(htmx_version):
    """Serve the example app on a random port for the session.

    CSRF is off and ``hx-boost`` is disabled so Playwright's waits
    synchronize with native navigations rather than htmx body swaps.
    """
    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["HTMX_BOOST_DISABLED"] = True
    app.config["HTMX_VERSION"] = htmx_version
    port = _free_port()
    server = make_server("127.0.0.1", port, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=2)


@pytest.fixture
def page(page, live_server):
    """Playwright ``page`` pre-pointed at the live server's root."""
    page.goto(live_server)
    return page


@pytest.fixture
def nav(page):
    """Return the nav bar's locator, scoping example-link clicks to the nav."""
    return page.get_by_label("Examples")


@pytest.fixture
def open_example(page, nav):
    """Return a function that opens an example from the nav bar by its title.

    It also works with ``page_nojs``, which is the same page with htmx off.
    """

    def _open(title: str) -> None:
        with page.expect_navigation():
            nav.get_by_role("link", name=title, exact=True).click()

    return _open


@pytest.fixture
def page_nojs(page, live_server):
    """``page`` variant with htmx disabled via the example app's toggle cookie.

    Mirrors the user-facing toggle in the nav: ``htmx_enabled=0`` makes
    ``examples.create_app.inject_htmx_enabled`` skip the htmx
    ``<script>`` tag, so the page degrades to plain HTML form posts.
    Tests built on this fixture exercise the progressive-enhancement
    fallback path: submits go through full page reloads, no partial
    swaps, no live update.
    """
    parsed = urlparse(live_server)
    page.context.add_cookies(
        [{"name": "htmx_enabled", "value": "0", "domain": parsed.hostname, "path": "/"}]
    )
    page.reload()
    return page


@pytest.fixture(autouse=True)
def reset_example_state():
    """Keep the example gallery deterministic across tests and browsers."""
    reset_state()
