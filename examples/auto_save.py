"""A settings-like form that posts itself after a short pause whenever the
user touches any field. The view validates the whole form; on success
it commits to the underlying state and the response is the save button
re-rendered with a fresh status. On validation failure nothing is
persisted and the button surfaces the error count instead. The user
keeps editing, the next typing burst re-attempts the save.

The save button doubles as a status indicator: a single
:class:`~wtforms.fields.SubmitField` declared with
``.triggered_by("*", ..., on="input delay:800ms")``. The wildcard
makes the button listen to every typing event in the form, and post
itself once the debounce settles. See the :ref:`limits of the
wildcard <wildcard-limits>`. The button stays ``type="submit"`` throughout: in
no-JS mode the wildcard never fires and the explicit click is the
only way to commit; with htmx the click is still available to force
an immediate commit between debounce windows.

.. screencast:: |examples|/auto-save
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     const eraseAll = async (sel, delay = 90) => {
       let cur = document.querySelector(sel);
       cur.focus();
       while ((document.querySelector(sel)?.value || '').length > 0) {
         const el = document.querySelector(sel);
         el.focus();
         el.value = el.value.slice(0, -1);
         el.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(delay);
       }
       await wait(200);
     };
     const typeInto = async (sel, text, delay = 110) => {
       const cur = document.querySelector(sel);
       cur.focus();
       for (const c of text) {
         const el = document.querySelector(sel);
         el.focus();
         el.value = (el.value || '') + c;
         el.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(delay);
       }
       await wait(300);
     };
     const settle = async (ms = 1100) => { await wait(ms); };
     await wait(700);
     await eraseAll('#email');
     await settle();
     await wait(500);
     await typeInto('#email', 'alice@example.org');
     await settle();
     document.querySelector('#email').blur();
     await wait(600);

   The save button declares ``triggered_by("*", autosave_commit,
   on="input delay:800ms")``. It auto-posts the form whenever any
   field emits an ``input`` event and the user pauses long enough
   for the debounce to settle. The callback validates, commits on
   success, and stores the result in ``target.data`` so the
   wrapper renders the appropriate label and kind class on the
   re-swapped button.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime

from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from wtforms import IntegerField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import DataRequired
from wtforms.validators import Email
from wtforms.validators import Length
from wtforms.validators import NumberRange
from wtforms.validators import Optional
from wtforms.validators import URL

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm


@dataclass
class AutoSaveData:
    name: str = ""
    email: str = ""
    website: str = ""
    age: int | None = None


_STATE["auto_save"] = AutoSaveData(name="Alice", email="alice@example.org")
_INITIAL_STATE["auto_save"] = deepcopy(_STATE["auto_save"])


@dataclass
class AutoSaveStatus:
    """Status payload stored on the save button after an auto-save attempt."""

    kind: str
    message: str


def autosave_save_wrapper(field, render_kw):
    """Per-field wrapper for the merged save button.

    Renders a real ``<button type="submit">`` whose label and kind
    class reflect ``field.data``. The action affordance and the status
    feedback share the same element.
    """
    return render_template("_auto_save_widgets.html", field=field, render_kw=render_kw)


def autosave_commit(form, source, target):
    """Wildcard-triggered mutation: validate and commit, then update the button.

    ``source`` is ``None`` with the wildcard. The event can come from
    any field of the form, so there is no single source. The callback
    only needs ``form`` (to validate and populate_obj) and ``target``
    (the save button whose ``.data`` is set to the resulting
    AutoSaveStatus).
    """
    state = _STATE["auto_save"]
    if form.validate():
        form.populate_obj(state)
        target.data = AutoSaveStatus(
            "saved",
            f"Saved at {datetime.now():%H:%M:%S}",  # noqa: DTZ005 (example UI, local time)
        )
        return

    error_count = sum(1 for f in form if f.errors)
    plural = "s" if error_count != 1 else ""
    target.data = AutoSaveStatus(
        "errors", f"Not saved: {error_count} error{plural} below."
    )


class ProfileForm(ExampleForm):
    """Same validator mix as the inline-validation example."""

    name = StringField(
        "Name",
        validators=[DataRequired(), Length(min=2, max=64)],
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()],
    )
    website = StringField(
        "Website",
        validators=[Optional(), URL()],
    )
    age = IntegerField(
        "Age",
        validators=[Optional(), NumberRange(min=13, max=120)],
    )
    save = SubmitField("Save", wrapper=autosave_save_wrapper)

    # Any field change, after a typing pause, commits the form.
    save.triggered_by("*", autosave_commit, on="input delay:800ms")


@bp.route("/auto-save", methods=["GET", "POST"])
def auto_save():
    state = _STATE["auto_save"]
    form = ProfileForm(request.form or None, obj=state, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("auto_save.html", form=form)

    # Only an explicit Save click gets here: ``form.partial()`` answers the autosave.
    if form.validate():
        form.populate_obj(state)
        flash("Saved.")
        return redirect(url_for("main.auto_save"))

    flash("Please fix the errors below.", "error")
    return render_template("auto_save.html", form=form)
