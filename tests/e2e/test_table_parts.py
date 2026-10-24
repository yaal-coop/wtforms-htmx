"""End-to-end test of an out-of-band target rendered as a table part."""

from markupsafe import Markup
from playwright.sync_api import expect
from werkzeug.datastructures import MultiDict
from wtforms import ButtonField
from wtforms import StringField

from wtforms_htmx import HtmxForm


def _tbody_widget(field, **kwargs):
    return Markup(f'<tbody id="{field.id}"><tr><td>{field.data}</td></tr></tbody>')


class _Form(HtmxForm):
    bar = StringField()
    rows = StringField(widget=_tbody_widget, wrapper=False)
    go = ButtonField("Go").triggers(["bar", "rows"])


def test_table_part_target_is_swapped_out_of_band(page, htmx_version):
    """A ``<tbody>`` target that follows the main swap replaces the old one."""
    source = {"HX-Source": "button#go"} if htmx_version == 4 else {"HX-Trigger": "go"}
    form = _Form(
        MultiDict({"go": "", "bar": "new", "rows": "new"}),
        headers={"HX-Request": "true", **source},
    )
    result = form.partial()
    page.route(
        "**/table-parts",
        lambda route: route.fulfill(
            content_type="text/html", body=result.body, headers=result.headers
        ),
    )
    page.evaluate(
        """() => {
            const host = document.createElement("div");
            host.innerHTML = `
                <input id="bar" value="old">
                <table><tbody id="rows"><tr><td>old</td></tr></tbody></table>
                <button id="go" hx-post="/table-parts" hx-target="#bar"
                        hx-swap="outerHTML">Go</button>`;
            document.body.appendChild(host);
            htmx.process(host);
        }"""
    )

    page.locator("#go").click()

    expect(page.locator("#bar")).to_have_value("new")
    expect(page.locator("table > #rows")).to_have_text("new")
