"""Helpers shared by the unit tests."""

from __future__ import annotations

import re
from html import unescape


def htmx_headers(source_id, target_id=None):
    """Build the request headers an htmx 4 client sends."""
    headers = {"HX-Request": "true", "HX-Source": f"input#{source_id}"}
    if target_id:
        headers["HX-Target"] = f"div#{target_id}"

    return headers


def attr(html, name):
    """Return an attribute of the first element that has it, as a browser reads it."""
    match = re.search(rf'(?:^|\s){name}="([^"]*)"', str(html))
    return unescape(match.group(1)) if match else None


def marker_clause(event, token):
    """Return the hx-trigger clause a listener uses for the sources marked ``token``."""
    return f"{event} from:body target:[data-wtforms-htmx-for~={token}]"


def markers(html):
    """Return the listener markers a rendered source carries."""
    value = attr(html, "data-wtforms-htmx-for")
    return value.split() if value else []


def oob_ids(html):
    """Return the ids of the elements a partial swaps out of band, in order."""
    return [
        attr(tag, "id")
        for tag in re.findall(r"<[^>]+>", str(html))
        if "hx-swap-oob" in tag
    ]
