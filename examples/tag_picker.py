"""The selected values appear as chips; the unselected ones are
buttons in a separate catalog strip. Clicking a catalog button
adds, clicking ``×`` on a chip removes.

.. screencast:: |examples|/tag-picker
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
     // Click ``javascript`` in the catalog to add a chip.
     $('button[name="add_tag"][value="javascript"]').click();
     await wait(1300);
     // Click ``×`` on the new chip, back to the persisted single
     // ``python`` selection.
     $('button[name="rm_tag"][value="javascript"]').click();
     await wait(1200);

   Tag picker: chip-shaped catalog + chips for the selection.
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
from wtforms import SubmitField

from wtforms_htmx.mutations import value_add
from wtforms_htmx.mutations import value_remove

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm
from ._shared import jinja_widget


@dataclass
class TagPickerData:
    tags: list[str] = dc_field(default_factory=list)


_STATE["tag_picker"] = TagPickerData(tags=["python"])
_INITIAL_STATE["tag_picker"] = deepcopy(_STATE["tag_picker"])

TAGS = [
    "python",
    "javascript",
    "go",
    "rust",
    "java",
    "ruby",
    "swift",
]


class TagPickerForm(ExampleForm):
    """Tag picker: chips + catalog (compact dual-list)."""

    tags = SelectMultipleField(
        choices=[SelectChoice(s, s) for s in TAGS],
        widget=jinja_widget("_tag_picker_widgets.html", "tags"),
    )
    add_tag = ButtonField("+")
    rm_tag = ButtonField("×")
    save = SubmitField("Save")

    # A catalog click adds a chip; a chip's × removes it.
    add_tag.triggers("tags", value_add)
    rm_tag.triggers("tags", value_remove)


@bp.route("/tag-picker", methods=["GET", "POST"])
def tag_picker():
    state = _STATE["tag_picker"]
    form = TagPickerForm(
        request.form or None,
        obj=state,
        headers=request.headers,
    )
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("tag_picker.html", form=form)

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("tag_picker.html", form=form)

    form.populate_obj(state)
    flash(f"Saved tags: {state.tags!r}.", "success")
    return redirect(url_for("main.tag_picker"))
