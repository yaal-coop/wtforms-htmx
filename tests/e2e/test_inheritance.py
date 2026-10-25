"""End-to-end test of the htmx attributes of a container and the links inside it."""

from markupsafe import Markup
from playwright.sync_api import expect
from wtforms import StringField
from wtforms.widgets import html_params

from wtforms_htmx import HtmxForm


def _list_widget(field, **kwargs):
    return Markup(
        f'<div id="{field.id}" {html_params(**kwargs)}>'
        '<a id="link" href="/inheritance-link">Edit</a></div>'
    )


class _Form(HtmxForm):
    rows = StringField(widget=_list_widget, wrapper=False)
    bar = StringField(default="value").triggered_by("rows", on="change")


def test_boosted_link_in_a_container_does_not_inherit_its_attrs(page):
    """A boosted link inside a field sends a plain GET to its own target."""
    requests = []

    def _answer(route):
        requests.append(route.request)
        route.fulfill(content_type="text/html", body="<p id='landed'>landed</p>")

    page.route("**/inheritance-link*", _answer)
    page.evaluate(
        """html => {
            document.body.setAttribute("hx-boost", "true");
            document.body.innerHTML = `<form>${html}</form>`;
            htmx.process(document.body);
        }""",
        str(_Form().rows()) + str(_Form().bar()),
    )

    page.locator("#link").click()

    expect(page.locator("#landed")).to_be_visible()
    assert requests[0].url.endswith("/inheritance-link")
