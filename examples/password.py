"""One input can drive a read-only display. ``password`` live-updates a
disabled strength meter. ``confirm_password`` must match ``password``,
checked by inline validation and on submit.

.. screencast:: |examples|/password
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const pw = document.querySelector('#password');
     const confirm = document.querySelector('#confirm_password');
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     const typeInto = async (el, text, delay = 220) => {
       el.focus();
       el.value = '';
       el.dispatchEvent(new Event('input', {bubbles: true}));
       await wait(120);
       for (const c of text) {
         const cur = document.querySelector(`#${el.id}`);
         cur.focus();
         cur.value = (cur.value || '') + c;
         cur.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(delay);
       }
       await wait(500);
     };
     await wait(500);
     await typeInto(pw, 'Pass1!WordOK', 200);
     await typeInto(confirm, 'Pass1!WordOK', 180);
     await wait(700);
     // Leave the final frame equal to the initial one: clear confirm,
     // then clear password so the meter returns to "Empty". Re-query
     // the inputs every iteration. The htmx inline-validation swap
     // replaces the input wraps as soon as another field gets focus,
     // so the original ``pw`` / ``confirm`` references would point at
     // detached DOM nodes whose ``value`` never changes (infinite loop).
     while ((document.querySelector('#confirm_password')?.value || '').length > 0) {
       const cur = document.querySelector('#confirm_password');
       cur.focus();
       cur.value = cur.value.slice(0, -1);
       cur.dispatchEvent(new Event('input', {bubbles: true}));
       await wait(120);
     }
     await wait(250);
     while ((document.querySelector('#password')?.value || '').length > 0) {
       const cur = document.querySelector('#password');
       cur.focus();
       cur.value = cur.value.slice(0, -1);
       cur.dispatchEvent(new Event('input', {bubbles: true}));
       await wait(120);
     }
     await wait(500);
     document.activeElement.blur();
     await wait(500);

   Typing in ``password`` re-scores the strength meter at each
   typing pause. Leaving ``confirm_password`` checks that it matches. The
   slider is purely visual: the field has ``disabled`` so it doesn't
   submit, and ``<input type="range">`` doesn't honor ``readonly``
   per the HTML spec.
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
from wtforms import IntegerRangeField
from wtforms import PasswordField
from wtforms import SubmitField
from wtforms.validators import Disabled
from wtforms.validators import EqualTo
from wtforms.validators import NumberRange
from wtforms.validators import Optional
from wtforms.widgets import PasswordInput

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm


@dataclass
class PasswordData:
    password: str = ""
    confirm_password: str = ""


_STATE["password"] = PasswordData()
_INITIAL_STATE["password"] = deepcopy(_STATE["password"])


def score_password(pw):
    """Return a 0..4 strength score for ``pw``."""
    if not pw:
        return 0

    classes = sum(
        any(check(c) for c in pw)
        for check in (str.islower, str.isupper, str.isdigit, lambda c: not c.isalnum())
    )
    if len(pw) < 8:
        return min(1, classes)

    if len(pw) < 12:
        if classes >= 3:
            return 3

        return min(2, classes)

    return min(4, classes + 1)


def score_strength(form, source, target):
    """Recompute ``strength`` from ``password``."""
    target.data = score_password(source.data)


class PasswordStrengthForm(ExampleForm):
    """Password live-scored into a strength meter."""

    password = PasswordField(
        "Password",
        validators=[Optional()],
        render_kw={"autocomplete": "new-password"},
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[Optional(), EqualTo("password", message="Passwords must match.")],
        render_kw={"autocomplete": "new-password"},
    )
    strength = IntegerRangeField(
        "Password strength",
        default=0,
        validators=[NumberRange(min=0, max=4), Disabled()],
    )
    save = SubmitField("Save")

    # Typing re-scores the password.
    password.triggers("strength", score_strength)


@bp.route("/password", methods=["GET", "POST"])
def password():
    state = _STATE["password"]
    form = PasswordStrengthForm(
        request.form or None, obj=state, headers=request.headers
    )
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("password.html", form=form)

    if not form.validate():
        # Show what was typed and its strength, as the htmx responses do.
        form.strength.data = score_password(form.password.data)
        form.password.widget = PasswordInput(hide_value=False)
        form.confirm_password.widget = PasswordInput(hide_value=False)
        flash("Please fix the errors below.", "error")
        return render_template("password.html", form=form)

    # ``strength`` is derived from the password, which is never re-rendered.
    # Saving it would show a stale meter on the next GET.
    del form.strength
    form.populate_obj(state)
    flash("Password saved.", "success")
    return redirect(url_for("main.password"))
