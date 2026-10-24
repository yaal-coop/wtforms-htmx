"""Example app for wtforms-htmx, one feature per module."""

from __future__ import annotations

import os

from flask import Blueprint
from flask import Flask
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

bp = Blueprint("main", __name__)

#: View name to page title, in navigation order.
EXAMPLES = {
    "attendance": "Attendance grid",
    "auto_save": "Auto-save",
    "bulk_actions": "Bulk actions",
    "combobox": "Combobox",
    "currency": "Currency converter",
    "cycle_button": "Cycle button",
    "datalist": "Datalist autocomplete",
    "dual_listbox": "Dual listbox",
    "address": "Dynamic address form",
    "faceted_search": "Faceted search",
    "inline_edit": "Inline edit",
    "inline_validation": "Inline validation",
    "invoice": "Invoice totals",
    "markdown_preview": "Markdown preview",
    "pagination": "Pagination",
    "password": "Password strength indicator",
    "tag_picker": "Tag picker",
    "task_list": "Task list",
    "title_slug": "Title slug",
}


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/toggle-htmx", methods=["POST"])
def toggle_htmx():
    referer = request.form.get("referer") or url_for("main.index")
    enabled = "enabled" in request.form
    resp = redirect(referer)
    resp.set_cookie("htmx_enabled", "1" if enabled else "0", max_age=86400 * 30)
    return resp


from . import address  # noqa: E402, F401
from . import attendance  # noqa: E402, F401
from . import auto_save  # noqa: E402, F401
from . import bulk_actions  # noqa: E402, F401
from . import combobox  # noqa: E402, F401
from . import currency  # noqa: E402, F401
from . import cycle_button  # noqa: E402, F401
from . import datalist  # noqa: E402, F401
from . import dual_listbox  # noqa: E402, F401
from . import faceted_search  # noqa: E402, F401
from . import inline_edit  # noqa: E402, F401
from . import inline_validation  # noqa: E402, F401
from . import invoice  # noqa: E402, F401
from . import markdown_preview  # noqa: E402, F401
from . import pagination  # noqa: E402, F401
from . import password  # noqa: E402, F401
from . import tag_picker  # noqa: E402, F401
from . import task_list  # noqa: E402, F401
from . import title_slug  # noqa: E402, F401


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-only-not-secret"
    app.config.setdefault("HTMX_VERSION", int(os.environ.get("HTMX_VERSION", "4")))

    @app.context_processor
    def inject_htmx_enabled():
        htmx_on = request.cookies.get("htmx_enabled", "1") == "1"
        boost = htmx_on and not app.config.get("HTMX_BOOST_DISABLED", False)
        return {
            "htmx_enabled": htmx_on,
            "htmx_boost": boost,
            "htmx_version": app.config["HTMX_VERSION"],
        }

    @app.context_processor
    def inject_examples():
        view = (request.endpoint or "").removeprefix(f"{bp.name}.")
        return {"examples": EXAMPLES, "example_title": EXAMPLES.get(view)}

    app.register_blueprint(bp)
    return app


__all__ = ["create_app"]
