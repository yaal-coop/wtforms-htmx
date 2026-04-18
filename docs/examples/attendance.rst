Attendance grid
===============

A grid of cycling cells whose rows and columns can be added or removed.
Every operation is a callback on the same flat
:class:`~wtforms.fields.FieldList`.

.. automodule:: examples.attendance
   :no-members:
   :no-index:

In the flat ``cells`` list, adding a row appends
``len(dates)`` empty entries at the end, and removing a row pops
``len(dates)`` entries at the right offset. Adding a column inserts
one empty entry per row at the end of each row's span, and removing a
column pops the corresponding entry from each row. Iteration order
(right-to-left for pops, bottom-up for inserts) keeps the per-row
slices contiguous as the flat list mutates.

.. code-block:: python

    from datetime import date, timedelta
    from wtforms import ButtonField, FieldList, HiddenField, StringField
    from wtforms_htmx import HtmxForm
    from wtforms_htmx.mutations import cycle_through

    CYCLE = ["present", "unknown", "absent"]


    def cycle_cell(values):
        """Mutation: rotate the clicked entry of a FieldList through ``values``."""
        cycle = cycle_through(values)

        def _mutation(form, source, target):
            idx = int(source.raw_data[0])
            cycle(form, source, target.entries[idx])

        return _mutation


    def add_row(form, source, target):
        state = STATE["attendance"]
        new_name = f"User {len(state.users) + 1}"
        state.users.append(new_name)
        form.users.append_entry(new_name)
        for _ in range(len(state.dates)):
            target.append_entry("")


    def remove_row(form, source, target):
        state = STATE["attendance"]
        if len(state.users) <= 1:
            return

        value = source.raw_data[0].strip() if source.raw_data else ""
        u_idx = int(value) if value else len(state.users) - 1
        n_dates = len(state.dates)
        state.users.pop(u_idx)
        form.users.pop_entry(u_idx)
        # Pop right-to-left so earlier pops don't shift indices yet to drop.
        for j in range(n_dates - 1, -1, -1):
            target.pop_entry(u_idx * n_dates + j)


    # add_col / remove_col are symmetric (one entry per row, inserted /
    # popped bottom-up so each operation lands at the correct offset).

    class AttendanceForm(HtmxForm):
        users = FieldList(StringField())
        cells = FieldList(HiddenField())
        cycle = ButtonField("·")
        add_user = ButtonField("Add user")
        rm_user = ButtonField("×")
        add_date = ButtonField("Add date")
        rm_date = ButtonField("×")

        # Every button re-renders the whole grid.
        cycle.triggers("cells", cycle_cell(CYCLE))
        add_user.triggers("cells", add_row)
        rm_user.triggers("cells", remove_row)
        add_date.triggers("cells", add_col)
        rm_date.triggers("cells", remove_col)

The template renders some buttons many times, each with an index as
its ``value``:

- ``cycle`` once per cell, with ``value=<entry-index>``;
- ``rm_user`` once per row, with ``value=<user-index>``;
- ``rm_date`` once per column, with ``value=<date-index>``.

The add buttons render once, in a toolbar, with no ``value``: they
append. The view skips
both ``validate()`` and the save path, because a click is not a save:

.. code-block:: python

    @bp.route("/attendance", methods=["GET", "POST"])
    def attendance():
        state = STATE["attendance"]
        form = AttendanceForm(request.form or None, obj=state, headers=request.headers)
        state.users = [entry.data or "" for entry in form.users]
        state.cells = [entry.data or "" for entry in form.cells]
        if result := form.partial():
            return Response(result.body, headers=result.headers)

        return render_template("attendance.html", form=form)

The view copies the user names and the cells back to the state on
every request. The dates live on the state only, and the callbacks read
them there.

Without JavaScript
------------------

Every button submits the page: a cell click cycles that cell, and the
add and remove buttons grow or shrink the grid. The page comes back
with the new grid.

See also
--------

- :doc:`cycle_button`: one cycling value, without the grid.
- :mod:`wtforms_htmx.mutations`: ``list_add`` and ``list_remove`` for
  a one-dimensional list.
