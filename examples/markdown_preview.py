r"""A textarea drives a server-side markdown render into a DOM element
that is *not* a form field. ``content.triggers("#preview", ...)`` posts
the form on each typing pause and the callback returns the rendered
HTML; htmx swaps it into ``#preview``. Without JavaScript, the
``Save`` submit button re-renders the page with the preview rendered
server-side.

.. screencast:: |examples|/markdown-preview
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     const typeInto = async (sel, text, delay = 50) => {
       const el = document.querySelector(sel);
       el.focus();
       for (const c of text) {
         el.value = (el.value || '') + c;
         el.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(delay);
       }
       await wait(400);
     };
     const backspace = async (sel, count, delay = 15) => {
       const el = document.querySelector(sel);
       el.focus();
       for (let i = 0; i < count; i++) {
         el.value = el.value.slice(0, -1);
         el.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(delay);
       }
       await wait(400);
     };
     await wait(300);
     const tail = '\n\nSome **bold** and _italic_.';
     await typeInto('#content', tail);
     await wait(600);
     await backspace('#content', tail.length);
     document.querySelector('#content').blur();
     await wait(300);

   Typing inside ``content`` posts the form after each 100 ms typing
   pause; the server renders the markdown with mistune and returns
   the HTML. The DOM target is declared with the htmx selector syntax
   (``#preview``), so wtforms-htmx places ``hx-target="#preview"`` on the
   textarea. ``hx-swap="innerHTML"`` puts the response inside the
   ``#preview`` element, which stays in the template.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

import mistune
from flask import render_template
from flask import request
from flask import Response
from markupsafe import Markup
from wtforms import SubmitField
from wtforms import TextAreaField

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm


@dataclass
class MarkdownData:
    content: str = "# Hello"


_STATE["markdown_preview"] = MarkdownData()
_INITIAL_STATE["markdown_preview"] = deepcopy(_STATE["markdown_preview"])


def _render_markdown(text):
    """Render ``text`` (markdown) to HTML."""
    return Markup(mistune.html(text or ""))


def render_preview(form, source, target):
    """Trigger callback: rebuild the preview from the current content.

    ``target`` is the raw selector string (``"#preview"``). It is ignored
    here (the callback always rebuilds the same element), but a callback
    shared across multiple selectors would branch on it.
    """
    return _render_markdown(form.content.data)


class MarkdownPreviewForm(ExampleForm):
    """Textarea posting markdown to a ``#preview`` DOM target."""

    content = TextAreaField(
        "Content",
        render_kw={
            "rows": 8,
            "placeholder": "Write some Markdown…",
            "hx-swap": "innerHTML",
        },
    )
    save = SubmitField("Save")

    # A typing pause renders the markdown into #preview.
    content.triggers("#preview", render_preview, on="input delay:100ms")


@bp.route("/markdown-preview", methods=["GET", "POST"])
def markdown_preview():
    state = _STATE["markdown_preview"]
    form = MarkdownPreviewForm(request.form or None, obj=state, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is form.save:
        form.populate_obj(state)

    preview = _render_markdown(form.content.data)
    return render_template("markdown_preview.html", form=form, preview=preview)
