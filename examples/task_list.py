"""The task-list UX everyone knows: a single form-level ``+ Add task``
appends a new row at the end, per-row ``↑`` / ``↓`` buttons move a row,
a per-row ``×`` removes it, and a drag handle on each row lets the user
reshuffle priorities. Add, move and remove use the
:func:`~wtforms_htmx.mutations.list_add`,
:func:`~wtforms_htmx.mutations.list_move` and
:func:`~wtforms_htmx.mutations.list_remove` callbacks. Dragging is
wired through a hidden field driven by a
:func:`~wtforms_htmx.mutations.list_reorder` callback.

.. screencast:: |examples|/task-list
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
     // Click ``+ Add task``: appends an empty row at the end.
     $('#add_task').click();
     await wait(900);
     // Click ``↑`` on the new (third) row: it moves to the middle.
     $("li[data-index='2'] button[name='move_up']").click();
     await wait(900);
     // Drag-to-reorder: the bridge writes a permutation of old indices
     // into ``#reorder`` and dispatches ``change``; here we set it
     // directly so the screencast doesn't depend on simulating mouse
     // drags. ``1,0,2`` = "the empty row jumps to the top".
     const reorder = $('#reorder');
     reorder.value = '1,0,2';
     reorder.dispatchEvent(new Event('change', { bubbles: true }));
     await wait(900);
     // Click ``×`` on the row that's now first (the empty one),
     // back to the original two tasks.
     $("li[data-index='0'] button[name='rm_task']").click();
     await wait(1300);

   ``+ Add task`` appends; per-row ``↑`` / ``↓`` move a row and ``×``
   removes it. The drag handle on the left of each row triggers
   Sortable.js; the reorder swap shown here is what a real drop
   fires.
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
from wtforms import FieldList
from wtforms import FormField
from wtforms import HiddenField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import DataRequired
from wtforms.validators import Length

from wtforms_htmx.mutations import list_add
from wtforms_htmx.mutations import list_move
from wtforms_htmx.mutations import list_remove
from wtforms_htmx.mutations import list_reorder

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm
from ._shared import jinja_widget


@dataclass
class TaskData:
    title: str = ""


@dataclass
class TaskListData:
    tasks: list[TaskData] = dc_field(default_factory=list)


_STATE["task_list"] = TaskListData(
    tasks=[TaskData(title="Buy milk"), TaskData(title="Call mum")],
)
_INITIAL_STATE["task_list"] = deepcopy(_STATE["task_list"])


class TaskEntryForm(ExampleForm):
    title = StringField(
        "Task",
        validators=[DataRequired(), Length(max=120)],
        render_kw={"placeholder": "What's next?"},
    )


class TaskListForm(ExampleForm):
    """Todo list: append at the end, remove any row, move rows up and down.

    A single form-level ``+ Add task`` appends a new row, and per-row
    ↑ / ↓ / × buttons move or remove that row. A drag handle on each row
    also reorders, through a hidden ``reorder`` field driven by the
    ``sortable-fieldlist.js`` bridge (see list_reorder).
    """

    tasks = FieldList(
        FormField(TaskEntryForm),
        min_entries=1,
        widget=jinja_widget("_task_list_widgets.html", "draggable_list"),
    )
    move_up = ButtonField("↑")
    move_down = ButtonField("↓")
    rm_task = ButtonField("×")
    add_task = ButtonField("+ Add task")
    reorder = HiddenField()
    save = SubmitField("Save")

    add_task.triggers("tasks", list_add)
    rm_task.triggers("tasks", list_remove)

    # The arrows move a row; a drop writes the new order into reorder.
    move_up.triggers("tasks", list_move(-1))
    move_down.triggers("tasks", list_move(+1))
    reorder.triggers("tasks", list_reorder, on="change")


@bp.route("/task-list", methods=["GET", "POST"])
def task_list():
    state = _STATE["task_list"]
    form = TaskListForm(request.form or None, obj=state, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("task_list.html", form=form)

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("task_list.html", form=form)

    while len(state.tasks) < len(form.tasks):
        state.tasks.append(TaskData())

    form.populate_obj(state)
    flash("Tasks saved.", "success")
    return redirect(url_for("main.task_list"))
