"""The smallest mutation example. A single
:class:`~wtforms.fields.HiddenField` holds the current value and a
single :class:`~wtforms.fields.ButtonField` rotates it through a
fixed list on every click. The button's label is rendered from
``field.data``, so the wrapper swap on each click refreshes the
visible state without any client-side bookkeeping.

.. screencast:: |examples|/cycle-button
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const $ = (s) => document.querySelector(s);
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     await wait(700);
     // ``medium`` is the persisted state. Four clicks walk through
     // high → critical → low → medium, back to the initial label.
     for (let i = 0; i < 4; i++) {
       $('button[name="cycle"]').click();
       await wait(900);
     }
     await wait(400);

   One button, four states. Each click swaps the wrapper so the
   label and color reflect the new ``priority`` value.
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
from wtforms import SubmitField

from wtforms_htmx.mutations import value_cycle

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm
from ._shared import jinja_widget

PRIORITIES = ["low", "medium", "high", "critical"]


@dataclass
class CycleButtonData:
    priority: str = "medium"


_STATE["cycle_button"] = CycleButtonData()
_INITIAL_STATE["cycle_button"] = deepcopy(_STATE["cycle_button"])


class CycleButtonForm(ExampleForm):
    """Single hidden value rotated through PRIORITIES by one button."""

    priority = HiddenField(
        default=PRIORITIES[1],
        widget=jinja_widget("_cycle_button_widgets.html", "priority_cycle"),
    )
    cycle = ButtonField("·")
    save = SubmitField("Save")

    # Each click moves the priority to the next value.
    cycle.triggers("priority", value_cycle(PRIORITIES))


@bp.route("/cycle-button", methods=["GET", "POST"])
def cycle_button():
    state = _STATE["cycle_button"]
    form = CycleButtonForm(request.form or None, obj=state, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("cycle_button.html", form=form)

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("cycle_button.html", form=form)

    form.populate_obj(state)
    flash(f"Saved priority {state.priority!r}.", "success")
    return redirect(url_for("main.cycle_button"))
