"""A text field can normalize another field as the user types. The
``title -> slug`` example auto-derives the slug while the user hasn't
customized it, and stops touching it the moment they type their own
value.

.. screencast:: |examples|/title-slug
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     // typeInto delay > the form-wide htmx_default_trigger debounce
     // (200ms by default) so each keystroke fires its own partial and
     // the slug visibly tracks the title character by character.
     const typeInto = async (sel, text, delay = 250) => {
       const el = document.querySelector(sel);
       el.focus();
       for (const c of text) {
         el.value = (el.value || '') + c;
         el.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(delay);
       }
       await wait(500);
     };
     const clearField = async (sel, delay = 80) => {
       const el = document.querySelector(sel);
       el.focus();
       while ((el.value || '').length > 0) {
         el.value = el.value.slice(0, -1);
         el.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(delay);
       }
       await wait(300);
     };
     await wait(500);
     // 1. Auto-derive: typing the title pushes a fresh slug live.
     await typeInto('#title', 'Cafe de Paris');
     await wait(500);
     // 2. Custom override: typing in the slug switches the field
     //    out of auto mode.
     await typeInto('#slug', 'paris-by-night');
     await wait(500);
     // 3. Custom is sticky: appending to the title leaves the user's
     //    slug untouched.
     await typeInto('#title', ' (Annexe)');
     await wait(900);
     // 4. Reset for loop: clearing the slug re-arms auto mode, then
     //    clearing the title brings both fields back to empty.
     await clearField('#slug');
     await clearField('#title');
     document.querySelector('#title').blur();
     await wait(500);

   Typing in the title pushes a derived slug back through htmx. Editing
   the slug locks the field into a custom mode; the server compares the
   incoming slug against the last value it pushed to know whether the
   user has taken over.
"""

from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from dataclasses import dataclass

from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from wtforms import HiddenField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Optional

from . import bp
from ._code import Excerpt
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm


@dataclass
class TitleSlugData:
    title: str = ""
    slug: str = ""
    last_auto_slug: str = ""


_STATE["title_slug"] = TitleSlugData()
_INITIAL_STATE["title_slug"] = deepcopy(_STATE["title_slug"])

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text):
    """Return an ASCII, lowercase slug."""
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return _SLUG_RE.sub("-", ascii_text).strip("-")


def derive_slug(form, source, target):
    """Auto-derive ``slug`` from ``title`` unless the user customized it.

    The slug stays in "auto mode" while the incoming ``slug`` matches
    the hidden ``last_auto_slug``, the mirror the server posts back
    each time it pushes a fresh derivation. As soon as the user edits
    the slug client-side, the two diverge and this trigger stops
    touching either field. ``last_auto_slug`` is re-rendered OOB so
    the client's mirror stays in sync after each auto push.
    """
    user_slug = (form.slug.data or "").strip()
    last_auto = (form.last_auto_slug.data or "").strip()
    if user_slug and user_slug != last_auto:
        return None

    new_slug = slugify(form.title.data)
    target.data = new_slug
    form.last_auto_slug.data = new_slug
    return [None, form.last_auto_slug]


def slug_wrapper(field, render_kw):
    """Paint the validity cue on the auto-derived slug."""
    # A mutation-rerendered field has its raw_data cleared by the dispatch,
    # so it misses the cue _field.html keys on raw_data; re-arm it here.
    rk = dict(render_kw)
    if (
        request.method == "POST"
        and field.raw_data is None
        and field.data
        and not field.errors
    ):
        rk["aria_invalid"] = "false"

    return render_template("_field.html", field=field, render_kw=rk)


class TitleSlugForm(ExampleForm):
    """Title input driving a slug preview with a custom override."""

    title = StringField(
        "Title",
        validators=[Optional()],
        render_kw={"placeholder": "Hello world"},
    )
    slug = StringField(
        "Slug",
        validators=[Optional()],
        wrapper=slug_wrapper,
    )
    last_auto_slug = HiddenField()
    save = SubmitField("Save")

    # Typing a title derives the slug, until the user edits the slug.
    title.triggers("slug", derive_slug)


@bp.route("/title-slug", methods=["GET", "POST"])
def title_slug():
    state = _STATE["title_slug"]
    form = TitleSlugForm(request.form or None, obj=state, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("title_slug.html", form=form)

    # Without JavaScript, nothing derived the slug while the title was typed.
    if not form.slug.data:
        form.slug.data = slugify(form.title.data)

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("title_slug.html", form=form)

    form.populate_obj(state)
    flash(f"Saved slug {state.slug!r}.", "success")
    return redirect(url_for("main.title_slug"))


#: Code shown under the demo.
CODE = [
    derive_slug,
    TitleSlugForm,
    title_slug,
    Excerpt("templates/title_slug.html", "{% block content %}", "{% endblock %}"),
]
