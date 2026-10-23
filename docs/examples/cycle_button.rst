Cycle button
============

A single button rotates a hidden value through a fixed list on every
click, built on :func:`~wtforms_htmx.mutations.value_cycle`.

.. automodule:: examples.cycle_button
   :no-members:
   :no-index:

:func:`~wtforms_htmx.mutations.value_cycle` moves ``priority`` to the
next value of the list on each click. The button needs no ``value``.

.. code-block:: python

    from wtforms import ButtonField, HiddenField, SubmitField
    from wtforms_htmx import HtmxForm
    from wtforms_htmx.mutations import value_cycle

    PRIORITIES = ["low", "medium", "high", "critical"]


    class CycleButtonForm(HtmxForm):
        priority = HiddenField(default=PRIORITIES[1], widget=render_priority)
        cycle = ButtonField("·")
        save = SubmitField("Save")

        cycle.triggers("priority", value_cycle(PRIORITIES))

``render_priority`` renders a Jinja macro: the visible button next to
the ``<input type="hidden">``. The wrapper carries the htmx attributes
computed for ``priority``, so a click swaps only this wrapper:

.. code-block:: jinja

    {% macro priority_cycle(field) %}
      {% set value = field.data or "" %}
      <div id="{{ field.id }}"{{ kwargs|xmlattr }}>
        <input type="hidden" name="{{ field.name }}" value="{{ value }}">
        {{ field._form.cycle(label="Priority: " ~ (value or "—"), id=False) }}
      </div>
    {% endmacro %}

Without JavaScript
------------------

A click submits the page. The form moves ``priority`` to the next value
while it is built, and the page comes back with the new label. ``Save``
persists the value.

See also
--------

- :doc:`inline_edit`: same primitive on a two-state cycle
  (``view`` ↔ ``edit``), with a widget that swaps in or out an
  editable input.
- :doc:`attendance`: the cycle button scaled up to a 2D grid of
  cycling cells, with a custom callback that reads a value to
  pick which entry to rotate.
- :doc:`/how-to/mutations`: when to reach for a mutation and the
  multi-form layout patterns that come with it.
