"""Two inputs that mirror each other: typing in one updates the other.
**Both directions** declare a typing-driven mutation; explicit
``→ JPY`` / ``← EUR`` buttons keep the conversion working when
JavaScript is off.

.. screencast:: |examples|/currency
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const $ = (s) => document.querySelector(s);
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     const typeIn = async (id, text) => {
       const el = $(id);
       el.focus();
       el.value = '';
       el.dispatchEvent(new Event('input', {bubbles: true}));
       await wait(150);
       for (const c of text) {
         const cur = $(id);
         cur.focus();
         cur.value = (cur.value || '') + c;
         cur.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(180);
       }
       await wait(500);
     };
     await wait(500);
     // Cycle: type 250 in EUR → JPY auto-converts; then type 16500
     // back in JPY → EUR auto-converts back to 100. End frame
     // matches the persisted (100, 16500) state.
     await typeIn('#eur', '250');
     await wait(700);
     await typeIn('#jpy', '16500');
     await wait(500);
     $('#jpy').blur();
     await wait(500);

   EUR ⇆ JPY converter. Typing in either input live-converts the
   other (htmx); ``→ JPY`` / ``← EUR`` buttons trigger the same
   conversions explicitly (works without JS).
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
from wtforms import IntegerField
from wtforms import SubmitField

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm


@dataclass
class CurrencyData:
    eur: int = 0
    jpy: int = 0


_STATE["currency"] = CurrencyData()
_INITIAL_STATE["currency"] = deepcopy(_STATE["currency"])

# Hardcoded for the demo; real apps would fetch a live rate.
JPY_PER_EUR = 165

# Not ``type="number"``: it has no selection API to keep the caret across a swap.
_NUMERIC_TEXT = {"type": "text", "inputmode": "numeric", "pattern": "[0-9]*"}


def eur_to_jpy(form, source, target):
    """Convert eur → jpy.

    Reads ``form.eur.data`` rather than ``source.data`` so the same
    callable works whether the trigger source is the EUR <input>
    or the ``→ JPY`` ButtonField (no relevant data).
    """
    target.data = (form.eur.data or 0) * JPY_PER_EUR


def jpy_to_eur(form, source, target):
    """Convert jpy → eur, rounding down to a whole euro."""
    target.data = (form.jpy.data or 0) // JPY_PER_EUR


class CurrencyForm(ExampleForm):
    """EUR ⇆ JPY converter: typing or click-to-convert."""

    eur = IntegerField("EUR", default=0, render_kw=_NUMERIC_TEXT)
    jpy = IntegerField("JPY", default=0, render_kw=_NUMERIC_TEXT)
    convert_to_jpy = ButtonField("→ JPY")
    convert_to_eur = ButtonField("← EUR")
    save = SubmitField("Save")

    # Typing in one amount converts it into the other.
    eur.triggers("jpy", eur_to_jpy)
    jpy.triggers("eur", jpy_to_eur)

    # Without JavaScript, the buttons run the same conversions.
    convert_to_jpy.triggers("jpy", eur_to_jpy)
    convert_to_eur.triggers("eur", jpy_to_eur)


@bp.route("/currency", methods=["GET", "POST"])
def currency():
    state = _STATE["currency"]
    form = CurrencyForm(request.form or None, obj=state, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("currency.html", form=form)

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("currency.html", form=form)

    form.populate_obj(state)
    flash(f"Saved {state.eur} EUR / {state.jpy} JPY.", "success")
    return redirect(url_for("main.currency"))
