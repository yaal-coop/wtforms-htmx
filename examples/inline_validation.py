"""Inline validation re-validates each :class:`~wtforms.fields.Field` on
the server when the user leaves it. The errors show next to the field,
without a full form submission.

.. screencast:: |examples|/inline-validation
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     const typeInto = async (v, delay = 110) => {
       const cur = document.querySelector('#email');
       cur.focus();
       cur.value = '';
       cur.dispatchEvent(new Event('input', {bubbles: true}));
       await wait(120);
       for (const c of v) {
         const el = document.querySelector('#email');
         el.focus();
         el.value = (el.value || '') + c;
         el.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(delay);
       }
       await wait(300);
     };
     const blurAndWait = async (ms = 900) => {
       const el = document.querySelector('#email');
       el.dispatchEvent(new Event('change', {bubbles: true}));
       // Use the native blur(). A synthetic blur event would fire htmx
       // but leave document.activeElement on the input, and
       // ``.field:has(input:focus) .errors`` would keep the message
       // hidden for the whole scenario.
       el.blur();
       await wait(ms);
     };
     // Linger on the initial valid state so the loop start is readable.
     await wait(600);
     // Break it: type an invalid value char by char + blur. The error
     // appears via htmx swap.
     await typeInto('not-an-email');
     await blurAndWait();
     await wait(700);
     // Fix it: type the valid value back char by char. The error
     // clears on the swap.
     await typeInto('alice@example.org');
     await blurAndWait();
     await wait(500);

   Blur with an invalid value triggers an htmx round-trip that
   re-renders the wrapper with errors; restoring a valid value swaps
   the error away. No full form submit on either swap.
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
class InlineData:
    name: str = ""
    email: str = ""
    website: str = ""
    age: int | None = None


_STATE["inline"] = InlineData(name="Alice", email="alice@example.org")
_INITIAL_STATE["inline"] = deepcopy(_STATE["inline"])


class SignupForm(ExampleForm):
    """Settings-like form exercising native wtforms validators."""

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
    save = SubmitField("Save")


@bp.route("/inline-validation", methods=["GET", "POST"])
def inline_validation():
    state = _STATE["inline"]
    form = SignupForm(request.form or None, obj=state, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("inline_validation.html", form=form)

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("inline_validation.html", form=form)

    form.populate_obj(state)
    flash("Saved.")

    return redirect(url_for("main.inline_validation"))
