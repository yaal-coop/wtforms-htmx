Dual listbox
============

A :class:`~wtforms.fields.SelectMultipleField` shown as two panes,
for catalogs too large for the :doc:`tag picker <tag_picker>`.

.. automodule:: examples.dual_listbox
   :no-members:
   :no-index:

.. code-block:: python

    MEMBERS = [("alice", "Alice Brown"), ("bob", "Bob Carter"), ...]

    class DualListboxForm(HtmxForm):
        items = SelectMultipleField(
            choices=[SelectChoice(id_, name) for id_, name in MEMBERS],
            widget=render_dual_listbox,
        )
        available_query = StringField()
        selected_query = StringField()
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
            ...

The widget renders both columns: catalog rows for the unselected
items on the left, selected rows on the right. A single swap on the
field's container updates both columns at once. Two
:class:`~wtforms.fields.StringField` search inputs trigger the same
partial swap as the user types. They have no callback: they only
trigger the re-render. ``visible_choices()`` filters each pane with
the current queries. ``render_dual_listbox`` is the Jinja widget that
draws both panes from it. ``add_all_filtered`` and
``remove_all_filtered`` are custom callbacks that use it too, so the
bulk buttons read "operate on what I'm looking at", not "operate on
the whole catalog".

Without JavaScript
------------------

Every button submits the page: a click on a row moves it to the other
pane, and the bulk buttons move every visible row. Typing in a search
input filters nothing until the next click on a row or a bulk button,
which posts the query with the rest of the form. :kbd:`Enter` in a
search input runs ``Save``.

See also
--------

- :doc:`tag_picker`: the same wiring with a chip layout.
- Similar components: `Ant Transfer
  <https://ant.design/components/transfer>`_, `SLDS Dueling Picklist
  <https://www.lightningdesignsystem.com/components/dueling-picklist/>`_,
  `Bootstrap Italia Transfer
  <https://italia.github.io/bootstrap-italia/docs/form/transfer/>`_.
