Task list
=========

A :class:`~wtforms.fields.FieldList` of editable entries reorders with
per-row ↑ / ↓ buttons, or by drag-and-drop. A drop is committed
server-side through a hidden field that carries a permutation of old
indices.

.. automodule:: examples.task_list
   :no-members:
   :no-index:

.. code-block:: python

    from wtforms import (
        ButtonField, FieldList, FormField, HiddenField, StringField, SubmitField,
    )
    from wtforms_htmx import HtmxForm
    from wtforms_htmx.mutations import list_add, list_move, list_remove, list_reorder

    class TaskEntryForm(HtmxForm):
        title = StringField("Task")

    class TaskListForm(HtmxForm):
        tasks = FieldList(FormField(TaskEntryForm), min_entries=1)
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

The hidden ``reorder`` field is the server-side half of the drag
contract: a small client bridge (`Sortable.js
<https://sortablejs.github.io/Sortable/>`_ plus
``examples/static/sortable-fieldlist.js``) writes a
comma-separated permutation of old indices into it on drop and
fires a ``change`` event. The
``.triggers("tasks", list_reorder, on="change")`` link routes that
to :func:`~wtforms_htmx.mutations.list_reorder`, which rebuilds
``tasks.entries`` in the new order and lets htmx swap the container.
:func:`~wtforms_htmx.mutations.list_reorder` validates that the
value is a complete permutation of the current indices. A stale or
malformed string is a no-op rather than a silent truncation.

Without JavaScript
------------------

``+ Add task`` and each row's ``↑``, ``↓`` and ``×`` submit the page and
come back with the row added, moved or removed. Dragging needs
Sortable.js, so the drag handle does nothing. The ↑ / ↓ buttons cover
the same need.

See also
--------

- :func:`~wtforms_htmx.mutations.list_move` and
  :func:`~wtforms_htmx.mutations.list_reorder`: the two ways to
  reorder.
- :doc:`/how-to/mutations`: list recipes.
