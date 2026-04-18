"""Two columns side-by-side: ``Available`` on the left, ``Selected``
on the right. Click any row to shuttle it across. Each column
carries its own search input (live server-filter) and a header
counter; bulk buttons ``Add all`` / ``Clear all`` operate on the
currently-visible subset (i.e. they honor the active filter).

.. screencast:: |examples|/dual-listbox
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const $ = (s) => document.querySelector(s);
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     await wait(600);
     // Click ``Bob`` in the Available column → shuttles right.
     $('button[name="add_item"][value="bob"]').click();
     await wait(1300);
     // Click ``Bob`` in the Selected column → shuttles back left.
     $('button[name="rm_item"][value="bob"]').click();
     await wait(1200);

   Dual listbox: Available ↔ Selected, illustrated with team
   members.
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
from wtforms import SelectMultipleField
from wtforms import StringField
from wtforms import SubmitField

from wtforms_htmx.mutations import value_add
from wtforms_htmx.mutations import value_remove

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm
from ._shared import jinja_widget


@dataclass
class DualListboxData:
    items: list[str] = dc_field(default_factory=list)


_STATE["dual_listbox"] = DualListboxData(items=["alice", "carol"])
_INITIAL_STATE["dual_listbox"] = deepcopy(_STATE["dual_listbox"])

#: Sample catalog: IDs paired with display labels. The widget
#: derives an avatar from each label's initials, so any
#: ``(id, label)`` pair works without touching the template.
MEMBERS = [
    ("alice", "Alice Brown"),
    ("bob", "Bob Carter"),
    ("carol", "Carol Davis"),
    ("dave", "Dave Evans"),
    ("eve", "Eve Foster"),
    ("frank", "Frank Garcia"),
    ("grace", "Grace Harris"),
    ("henry", "Henry Ivanov"),
    ("iris", "Iris Johnson"),
    ("jack", "Jack Klein"),
    ("kate", "Kate Lopez"),
    ("liam", "Liam Martin"),
]


def add_all_filtered(form, source, target):
    """Add every item visible in ``Available``, so the active filter applies."""
    available, _ = form.visible_choices()
    target.data = [*(target.data or []), *(c.value for c in available)]


def remove_all_filtered(form, source, target):
    """Remove every item visible in ``Selected``, so the active filter applies."""
    _, selected = form.visible_choices()
    visible = {c.value for c in selected}
    target.data = [value for value in target.data or [] if value not in visible]


class DualListboxForm(ExampleForm):
    """Dual listbox: two columns, search per pane, bulk moves."""

    items = SelectMultipleField(
        choices=[SelectChoice(id_, name) for id_, name in MEMBERS],
        widget=jinja_widget("_dual_listbox_widgets.html", "dual_listbox"),
        wrapper=False,
    )
    available_query = StringField(
        render_kw={
            "type": "search",
            "placeholder": "Filter available…",
            "aria-label": "Filter available items",
            "autocomplete": "off",
        },
    )
    selected_query = StringField(
        render_kw={
            "type": "search",
            "placeholder": "Filter selected…",
            "aria-label": "Filter selected items",
            "autocomplete": "off",
        },
    )
    add_item = ButtonField("+")
    rm_item = ButtonField("×")
    add_all = ButtonField("Add all")
    rm_all = ButtonField("Clear all")
    save = SubmitField("Save")

    # Typing in a search input re-renders both panes, filtered.
    available_query.triggers("items")
    selected_query.triggers("items")

    # Row clicks move one item; the bulk buttons move every visible item.
    add_item.triggers("items", value_add)
    rm_item.triggers("items", value_remove)
    add_all.triggers("items", add_all_filtered)
    rm_all.triggers("items", remove_all_filtered)

    def visible_choices(self):
        """Return the ``(available, selected)`` choices that match each pane's filter."""
        available_query = (self.available_query.data or "").lower()
        selected_query = (self.selected_query.data or "").lower()
        available, selected = [], []
        for choice in self.items.iter_choices():
            label = choice.label.lower()
            if choice.selected:
                if selected_query in label:
                    selected.append(choice)
            elif available_query in label:
                available.append(choice)

        return available, selected


@bp.route("/dual-listbox", methods=["GET", "POST"])
def dual_listbox():
    state = _STATE["dual_listbox"]
    form = DualListboxForm(
        request.form or None,
        obj=state,
        headers=request.headers,
    )
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("dual_listbox.html", form=form)

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("dual_listbox.html", form=form)

    form.populate_obj(state)
    flash(f"Saved items: {state.items!r}.", "success")
    return redirect(url_for("main.dual_listbox"))
