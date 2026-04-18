"""A Doodle-style availability grid where both axes are runtime-mutable:
rows are people, columns are dates, and every intersection is a
cycling button that rotates through ``present`` / ``unknown`` /
``absent`` on click. Cells start empty (``—``); the first click
promotes them to ``present``, then the three states cycle. A toolbar
above the grid grows it (``Add user``, ``Add date``); a discreet ``×``
on each row/column header shrinks it. The form is **never validated
or saved**. Every click is purely a state mutation, with six
custom callbacks sharing the same flat ``cells`` target.

.. screencast:: |examples|/attendance
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const $ = (s) => document.querySelector(s);
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     const cycle = (i) => $(`button[name="cycle"][value="${i}"]`);
     await wait(700);
     // Alice / 03 Jun starts at ✓. Three clicks cycle through
     // ? → ✗ → ✓, back to the initial state.
     cycle(0).click();
     await wait(700);
     cycle(0).click();
     await wait(700);
     cycle(0).click();
     await wait(900);
     // Grow the grid: append a user row, then a date column.
     $('button[name="add_user"]').click();
     await wait(900);
     $('button[name="add_date"]').click();
     await wait(900);
     // Shrink back: drop the new user row, then the new date column.
     $('button[name="rm_user"][value="3"]').click();
     await wait(900);
     $('button[name="rm_date"][value="4"]').click();
     await wait(1300);

   Cycling cells + a runtime-mutable 2D shape: custom mutations
   sharing one flat ``cells`` :class:`~wtforms.fields.FieldList` target.

The mutations here are all custom (none of the shipped
mutations matches this 2D-grid shape):

- ``cycle_cell(values)``: apply
  :func:`~wtforms_htmx.mutations.cycle_through` to the clicked entry.
  An empty cell moves to the first value.
- ``add_row`` / ``remove_row``: add or remove a user row.
- ``add_col`` / ``remove_col``: add or remove a date column.
- ``toggle_editing_user``: switch a row header between text and an
  input to rename the user.

``dates`` is stored in ``AttendanceData`` and attached *by reference*
onto ``form.cells``, so the date-axis callbacks modify both the form
(used for the partial re-render) and the example state in a single
operation. ``users`` is a :class:`~wtforms.fields.FieldList` on the
form, copied back to the state by the view.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import date
from datetime import timedelta
from typing import Any

from flask import render_template
from flask import request
from flask import Response
from wtforms import ButtonField
from wtforms import FieldList
from wtforms import HiddenField
from wtforms import StringField

from wtforms_htmx.mutations import cycle_through

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm
from ._shared import jinja_widget

CYCLE = ["present", "unknown", "absent"]


def _initial_users() -> list[str]:
    return ["Alice", "Bob", "Charlie"]


def _initial_dates() -> list[date]:
    return [
        date(2026, 6, 3),
        date(2026, 6, 10),
        date(2026, 6, 17),
        date(2026, 6, 24),
    ]


def _initial_cells() -> list[str]:
    n = len(_initial_users()) * len(_initial_dates())
    rng = random.Random(20260514)
    # Weighted population: mostly empty, a sprinkle of the three states.
    weights = ["", "", "", "", "", "present", "unknown", "absent"]
    grid = [rng.choice(weights) for _ in range(n)]
    # Three clicks on a "present" cell loop the screencast back to its start.
    grid[0] = "present"
    return grid


@dataclass
class AttendanceData:
    users: list[str] = dc_field(default_factory=_initial_users)
    dates: list[date] = dc_field(default_factory=_initial_dates)
    cells: list[str] = dc_field(default_factory=_initial_cells)


_STATE["attendance"] = AttendanceData()
_INITIAL_STATE["attendance"] = deepcopy(_STATE["attendance"])


def _check_cells(target: Any, op: str) -> None:
    if not isinstance(target, FieldList):
        raise TypeError(f"{op} requires FieldList, got {type(target).__name__}")


def _index_from(source: Any, default: int | None = None) -> int | None:
    """Return the index carried by the clicked button, ``default`` if empty."""
    raw = getattr(source, "raw_data", None)
    value = raw[0].strip() if raw else ""
    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return None


def cycle_cell(values: list[str]) -> Callable[[Any, Any, Any], None]:
    """Return a mutation that cycles the clicked cell through ``values``."""
    cycle = cycle_through(values)

    def _mutation(form: Any, source: Any, target: Any) -> None:
        _check_cells(target, "cycle_cell")
        idx = _index_from(source)
        if idx is None or not 0 <= idx < len(target.entries):
            return

        cycle(form, source, target.entries[idx])

    return _mutation


# These mutations run during ``Form.process``, before ``__init__`` attaches
# ``dates`` to ``form.cells``, so they read it from the state.


def add_row(form: Any, _source: Any, target: Any) -> None:
    """Append a new user (auto-named) and ``len(dates)`` empty cells."""
    _check_cells(target, "add_row")
    state = _STATE["attendance"]
    new_name = f"User {len(state.users) + 1}"
    state.users.append(new_name)
    form.users.append_entry(new_name)
    for _ in range(len(state.dates)):
        target.append_entry("")


def remove_row(form: Any, source: Any, target: Any) -> None:
    """Remove the user at ``value`` (or last) and their row of cells."""
    _check_cells(target, "remove_row")
    state = _STATE["attendance"]
    if len(state.users) <= 1:
        return

    u_idx = _index_from(source, default=len(state.users) - 1)
    if u_idx is None or not 0 <= u_idx < len(state.users):
        return

    n_dates = len(state.dates)
    state.users.pop(u_idx)
    form.users.pop_entry(u_idx)
    # Pop right-to-left so earlier pops don't shift indices yet to drop.
    for j in range(n_dates - 1, -1, -1):
        target.pop_entry(u_idx * n_dates + j)


def toggle_editing_user(form: Any, source: Any, target: Any) -> None:
    """Toggle ``editing_user`` between empty and the clicked row index.

    Triggered on ``cells`` (so the whole grid re-renders with the new
    mode), but the actual state lives on the form's ``editing_user``
    hidden field. The widget reads it to decide which row header
    renders as text + ``✏`` vs input + ``✓``.
    """
    _check_cells(target, "toggle_editing_user")
    idx = _index_from(source)
    if idx is None:
        return

    value = str(idx)
    editing = form.editing_user
    editing.data = "" if editing.data == value else value


def add_col(_form: Any, _source: Any, target: Any) -> None:
    """Append the next weekly date and insert one empty cell per user."""
    _check_cells(target, "add_col")
    state = _STATE["attendance"]
    n_users = len(state.users)
    n_dates_old = len(state.dates)
    next_d = (max(state.dates) if state.dates else date.today()) + timedelta(days=7)  # noqa: DTZ011 (example UI, local date)
    state.dates.append(next_d)
    # Insert bottom-up so each insert lands at the correct flat index.
    for u_idx in range(n_users - 1, -1, -1):
        target.insert_entry((u_idx + 1) * n_dates_old, "")


def remove_col(_form: Any, source: Any, target: Any) -> None:
    """Remove the date at ``value`` (or last) and its column of cells."""
    _check_cells(target, "remove_col")
    state = _STATE["attendance"]
    if len(state.dates) <= 1:
        return

    d_idx = _index_from(source, default=len(state.dates) - 1)
    if d_idx is None or not 0 <= d_idx < len(state.dates):
        return

    n_users = len(state.users)
    n_dates_old = len(state.dates)
    state.dates.pop(d_idx)
    for u_idx in range(n_users - 1, -1, -1):
        target.pop_entry(u_idx * n_dates_old + d_idx)


class AttendanceForm(ExampleForm):
    """Doodle-style availability grid with runtime-mutable dimensions."""

    cells = FieldList(
        HiddenField(),
        widget=jinja_widget("_attendance_widgets.html", "attendance_grid"),
    )
    users = FieldList(StringField())
    editing_user = HiddenField(default="")
    cycle = ButtonField("·")
    add_user = ButtonField("Add user")
    rm_user = ButtonField("×")
    add_date = ButtonField("Add date")
    rm_date = ButtonField("×")
    toggle_user = ButtonField("·")

    # Every button re-renders the whole grid.
    cycle.triggers("cells", cycle_cell(CYCLE))
    add_user.triggers("cells", add_row)
    rm_user.triggers("cells", remove_row)
    add_date.triggers("cells", add_col)
    rm_date.triggers("cells", remove_col)
    toggle_user.triggers("cells", toggle_editing_user)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Shared by reference: date-axis mutations update the state too.
        self.cells.dates = _STATE["attendance"].dates


@bp.route("/attendance", methods=["GET", "POST"])
def attendance():
    state = _STATE["attendance"]
    form = AttendanceForm(request.form or None, obj=state, headers=request.headers)
    state.users = [entry.data or "" for entry in form.users]
    state.cells = [entry.data or "" for entry in form.cells]
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    return render_template("attendance.html", form=form)
