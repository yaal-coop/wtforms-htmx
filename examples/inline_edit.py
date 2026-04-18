"""A read-only label paired with an edit button. Clicking ``✏ Edit``
flips the wrapper into edit mode: the label becomes an editable
:class:`~wtforms.fields.StringField`, and a pair of confirm/discard
controls appears next to it. Clicking ``✓ Save`` validates the form,
persists the new value through :meth:`~wtforms.form.Form.populate_obj`,
and returns to read-only. Clicking ``✕ Cancel`` (or pressing the
``Escape`` key while the input is focused) restores the previously
saved value and returns to read-only without touching state.

This is the pattern Jira, Linear and Notion implement: in edit mode
the confirm action is co-located with the field and acts as the
form submit; the wrapping page does not carry a separate ``Save``
button at the bottom.

The mutations all cooperate on a single ``mode``
:class:`~wtforms.fields.HiddenField`:

* :func:`~wtforms_htmx.mutations.cycle_through` on ``[view, edit]``
  drives the ``✏ Edit`` button (one-way: from view, the only
  reachable state is edit).
* A restore callback flips ``mode`` back to ``view``
  *and* resets ``name`` to the canonical state value, wired both to
  ``✕ Cancel`` and to a ``keyup[key=='Escape']`` trigger on the
  input itself.
* The ``✓ Save`` :class:`~wtforms.fields.SubmitField` submits the
  whole form; on success the handler ``populate_obj`` /redirect
  cycle leaves the page back in view mode by default.

.. screencast:: |examples|/inline-edit
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     const click = (sel) => document.querySelector(sel).click();
     const waitFor = async (sel) => {
       while (!document.querySelector(sel)) await wait(50);
     };
     const typeInto = async (sel, text) => {
       const cur = document.querySelector(sel);
       cur.focus();
       cur.value = '';
       cur.dispatchEvent(new Event('input', {bubbles: true}));
       await wait(200);
       for (const c of text) {
         const el = document.querySelector(sel);
         el.focus();
         el.value = (el.value || '') + c;
         el.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(110);
       }
       await wait(400);
     };
     await wait(600);
     // Edit → type → Cancel: the unsaved value rolls back to the
     // canonical "Alice Brown" and view mode resumes, a clean loop.
     click('button[name="edit"]');
     await waitFor('#name');
     await wait(400);
     await typeInto('#name', 'Bob Smith');
     await wait(300);
     click('button[name="cancel"]');
     await wait(1100);

   Edit and Cancel are htmx interactions: each swaps only the
   inline-edit wrapper, with no full-page load. The ``Cancel`` path
   runs a server-side mutation that re-reads the canonical name from
   state and re-injects it as the field value before re-rendering, so
   the typed-but-unsaved value rolls back. ``Save`` is a plain form
   submit that persists and reloads the page (the progressive-
   enhancement path); the looping demo above shows the edit-and-
   rollback rather than the navigation.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from wtforms import ButtonField
from wtforms import HiddenField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.widgets import Button

from wtforms_htmx.mutations import cycle_through

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm
from ._shared import jinja_widget

MODES = ["view", "edit"]


@dataclass
class InlineEditData:
    name: str = "Alice Brown"


_STATE["inline_edit"] = InlineEditData()
_INITIAL_STATE["inline_edit"] = deepcopy(_STATE["inline_edit"])


def _restore(form, source, target):
    """Discard the uncommitted edit: flip back to view and re-read state."""
    form.mode.data = "view"
    form.name.data = _STATE["inline_edit"].name


class InlineEditForm(ExampleForm):
    """Read-only label + ✏ Edit; in edit mode, input + ✓ Save + ✕ Cancel."""

    class Meta:
        htmx_inline_validation = False

    name = StringField("Name", wrapper=False)
    mode = HiddenField(
        default=MODES[0],
        widget=jinja_widget("_inline_edit_widgets.html", "inline_edit"),
    )
    edit = ButtonField("✏ Edit")
    save = SubmitField("✓ Save", widget=Button())
    cancel = ButtonField("✕ Cancel")

    # Edit switches to edit mode.
    edit.triggers("mode", cycle_through(MODES))

    # Cancel, or Escape in the input, restores the saved name.
    cancel.triggers("mode", _restore)
    name.triggers("mode", _restore, on="keyup[key=='Escape']")


@bp.route("/inline-edit", methods=["GET", "POST"])
def inline_edit():
    state = _STATE["inline_edit"]
    form = InlineEditForm(request.form or None, obj=state, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    # No-JS fallback: a plain Cancel POST round-trips through GET so the
    # page snaps back to the canonical state.
    if form.submitter is form.cancel:
        return redirect(url_for("main.inline_edit"))

    if form.submitter is not form.save:
        return render_template("inline_edit.html", form=form)

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("inline_edit.html", form=form)

    # ``mode`` is UI state, not data: drop it before populate_obj so
    # the state dataclass keeps a tidy schema.
    del form.mode
    form.populate_obj(state)
    flash(f"Saved name {state.name!r}.", "success")
    return redirect(url_for("main.inline_edit"))
