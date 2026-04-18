Tag picker
==========

A :class:`~wtforms.fields.SelectMultipleField` shown as chips and a
catalog strip. It suits small catalogs, up to about 30 entries.

.. automodule:: examples.tag_picker
   :no-members:
   :no-index:

.. code-block:: python

    from wtforms import ButtonField, SelectChoice, SelectMultipleField, SubmitField
    from wtforms_htmx import HtmxForm
    from wtforms_htmx.mutations import value_add, value_remove

    TAGS = ["python", "go", "rust", "elixir", "haskell"]

    class TagPickerForm(HtmxForm):
        tags = SelectMultipleField(
            choices=[SelectChoice(s, s) for s in TAGS],
            widget=render_tags,
        )
        add_tag = ButtonField("+")
        rm_tag = ButtonField("×")
        save = SubmitField("Save")

        # A catalog click adds a chip; a chip's × removes it.
        add_tag.triggers("tags", value_add)
        rm_tag.triggers("tags", value_remove)

``render_tags`` renders a Jinja macro. It draws the catalog from
``field.iter_choices()`` and the chips from ``field.data``:

.. code-block:: jinja

    {% macro tags(field) %}
      {% set selected = field.data or [] %}
      <div id="{{ field.id }}">
        <div class="catalog">
          {% for choice in field.iter_choices() if choice.value not in selected %}
            {{ field._form.add_tag(value=choice.value, label=choice.label, id=False) }}
          {% endfor %}
        </div>
        <div class="chips">
          {% for value in selected %}
            <span>
              {{ value }}
              {{ field._form.rm_tag(value=value, label="×", id=False) }}
              <input type="hidden" name="{{ field.name }}" value="{{ value }}">
            </span>
          {% endfor %}
        </div>
      </div>
    {% endmacro %}

The hidden inputs use the *same* name as the field
(``field.name``) repeated per value, the multi-valued
formdata wire format (``name=A&name=B``) that
:class:`~wtforms.fields.SelectMultipleField` consumes natively.

Each button is rendered once per tag:

- ``label=`` gives each render its own visible text;
- ``id=False`` drops the :mdn-global-attr:`id`, which would otherwise repeat
  ``id="add_tag"`` on every button and make the HTML invalid.

Without JavaScript
------------------

A catalog button or a chip's ``×`` submits the page, and the page comes
back with the chip added or removed. ``Save`` persists the selection.

See also
--------

- :doc:`/examples/combobox`: a search-filtered catalog with ARIA
  combobox semantics, for picking from a large catalog.
- :doc:`dual_listbox`: the same wiring with two panes.
