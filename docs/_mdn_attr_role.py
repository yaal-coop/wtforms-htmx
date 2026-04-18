"""Custom Sphinx role for element-specific HTML attributes on MDN.

MDN documents element-level attributes inline on each element page with
a ``#<attr>`` anchor (no dedicated attribute page exists). The
``:mdn-attr:`<element_path>#<attr>``` role builds the full element URL
and renders only the attribute name as link text — e.g.
``:mdn-attr:`input/submit#formnovalidate``` produces a link to
``/Web/HTML/Element/input/submit#formnovalidate`` displayed as
``formnovalidate``.

A standard ``sphinx.ext.extlinks`` entry can't do this on its own
because both the URL and the caption share a single ``%s`` placeholder;
this small role splits the target on ``#`` to derive the visible label.
"""

from __future__ import annotations

from docutils import nodes
from sphinx.application import Sphinx

_BASE = "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/"


def _mdn_attr_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    target = text.strip()
    display = target.rsplit("#", 1)[1] if "#" in target else target
    node = nodes.reference(rawtext, display, refuri=_BASE + target)
    return [node], []


def setup(app: Sphinx):
    app.add_role("mdn-attr", _mdn_attr_role)
    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
