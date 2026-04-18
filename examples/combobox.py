"""This example wires the combobox recipe by hand: a :class:`~wtforms.fields.StringField`
for the query, a :class:`~wtforms.fields.SelectField` for the suggestions, a
:class:`~wtforms.fields.SelectMultipleField` for the storage, and a chip-remove
:class:`~wtforms.fields.ButtonField`. The ``Search`` button refreshes the listbox,
clicking a suggestion fires :func:`~wtforms_htmx.mutations.value_add`
through ``.triggers()``, the chip's ``×`` runs
:func:`~wtforms_htmx.mutations.value_remove`.

.. screencast:: |examples|/combobox
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const $ = (s) => document.querySelector(s);
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     const waitFor = async (sel) => {
       while (!$(sel)) await wait(50);
     };
     await wait(600);
     // Type "German" one keystroke at a time so the typing animates.
     const input = $('#query');
     input.focus();
     for (const c of 'German') {
       input.value += c;
       await wait(80);
     }
     await wait(300);
     // Click Search to refresh the suggestions listbox.
     $('.combobox-search button[name="search"]').click();
     await waitFor('button[name="suggestions"][value="DE"]');
     await wait(700);
     // Click Germany: appends DE to the chips and clears the query.
     $('button[name="suggestions"][value="DE"]').click();
     await waitFor('button[name="rm_country"][value="DE"]');
     await wait(800);
     // Click the ``×`` on the Germany chip, back to the persisted
     // {FR, JP} pair.
     $('button[name="rm_country"][value="DE"]').click();
     await wait(600);
     document.activeElement.blur();
     await wait(400);

   Combobox bundled from primitives: typing filters, click picks,
   ``×`` drops.

With htmx, typing in the query refreshes the suggestions. Without
JavaScript, the *Search* button does the same. For a turn-key version,
see ``ComboboxMultiField`` in the ``wtforms-htmx-components`` sister
package.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field as dc_field

from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from wtforms import ButtonField
from wtforms import SelectChoice
from wtforms import SelectField
from wtforms import SelectMultipleField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.widgets import Button

from wtforms_htmx.mutations import value_add
from wtforms_htmx.mutations import value_remove
from wtforms_htmx.mutations import value_set

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import COUNTRY_BY_CODE
from ._shared import ExampleForm
from ._shared import jinja_widget
from ._shared import NAME_BY_CODE


@dataclass
class ComboboxData:
    countries: list[str] = dc_field(default_factory=lambda: ["FR", "JP"])


_STATE["combobox"] = ComboboxData()
_INITIAL_STATE["combobox"] = deepcopy(_STATE["combobox"])


def _suggest(form, _field):
    """List catalog matches; tag picked ones ``disabled`` so they read as taken."""
    q = (form.query.data or "").strip().lower()
    if not q:
        return []

    picked = set(form.countries.data or [])
    matches = [(c, n) for c, n in COUNTRY_BY_CODE if q in n.lower() or q == c.lower()]
    # Clickable matches first, picked-but-matched as disabled hints after.
    matches.sort(key=lambda cn: cn[0] in picked)
    return [
        SelectChoice(
            c,
            n,
            render_kw=(
                {"disabled": True, "aria-disabled": "true"} if c in picked else {}
            ),
        )
        for c, n in matches[:10]
    ]


def _picked_choices(form, _field):
    """Resolve currently-picked codes to SelectChoice for chip rendering."""
    return [SelectChoice(c, NAME_BY_CODE.get(c, c)) for c in form.countries.data or []]


class CountryPickerForm(ExampleForm):
    """Combobox bundled as flat sub-fields plus their triggers."""

    query = StringField("Countries", wrapper=False)
    search = ButtonField("Search")
    suggestions = SelectField(
        choices=_suggest,
        option_widget=Button(),
        validate_choice=False,
        widget=jinja_widget("_combobox_widgets.html", "listbox"),
        wrapper=False,
    )
    countries = SelectMultipleField(
        choices=_picked_choices,
        validate_choice=False,
        widget=jinja_widget("_combobox_widgets.html", "chips"),
        wrapper=False,
    )
    rm_country = ButtonField("×")
    save = SubmitField("Save")

    # Typing filters the suggestions. Without JavaScript, Search does it.
    query.triggers("suggestions")
    search.triggers("suggestions")

    # Picking a suggestion adds a chip, clears the query, and refreshes
    # the list so the picked country shows as taken.
    suggestions.triggers("countries", value_add)
    suggestions.triggers("query", value_set(""))
    suggestions.triggers("suggestions")

    # A chip's × drops the country, which becomes available again.
    rm_country.triggers("countries", value_remove)
    rm_country.triggers("suggestions")


@bp.route("/combobox", methods=["GET", "POST"])
def combobox():
    state = _STATE["combobox"]
    form = CountryPickerForm(
        request.form or None,
        obj=state,
        headers=request.headers,
    )
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("combobox.html", form=form)

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("combobox.html", form=form)

    form.populate_obj(state)
    flash(f"Saved countries: {state.countries!r}.", "success")
    return redirect(url_for("main.combobox"))
