"""A country input whose suggestions follow what the user types."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from wtforms import DataList
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Optional
from wtforms.validators import ValidationError

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import COUNTRY_NAMES
from ._shared import ExampleForm

_MAX_SUGGESTIONS = 10
_COUNTRY_NAMES_LOWER = {name.lower() for name in COUNTRY_NAMES}


@dataclass
class DatalistData:
    country: str = ""


_STATE["datalist"] = DatalistData()
_INITIAL_STATE["datalist"] = deepcopy(_STATE["datalist"])


def suggest_country_names(form, field):
    """Filter the country catalog against the field's current value.

    Receives ``(form, field)``. DataList aligns its callable
    signature with SelectField's ``choices`` callable.
    """
    q = (field.data or "").strip().lower()
    if not q:
        return []

    return [name for name in COUNTRY_NAMES if q in name.lower()][:_MAX_SUGGESTIONS]


def valid_country_name(form, field):
    """Reject values that don't exactly match a known country name."""
    if field.data and field.data.lower() not in _COUNTRY_NAMES_LOWER:
        raise ValidationError("Please pick a country from the list.")


class CountryForm(ExampleForm):
    """Single StringField with a server-filtered <datalist>.

    wtforms-htmx notices the callable DataList and
    wires the refresh on the <datalist> element, so
    the only declaration here is the validator that enforces "must
    be a known country" both inline (on blur) and on full submit.
    """

    country = StringField(
        "Country",
        validators=[Optional(), valid_country_name],
        datalist=DataList(suggest_country_names),
    )
    save = SubmitField("Save")


@bp.route("/datalist", methods=["GET", "POST"])
def datalist():
    state = _STATE["datalist"]
    form = CountryForm(request.form or None, obj=state, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("datalist.html", form=form)

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("datalist.html", form=form)

    form.populate_obj(state)
    flash(f"Saved country {state.country!r}.", "success")
    return redirect(url_for("main.datalist"))
