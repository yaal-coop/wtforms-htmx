Combobox
========

A combobox lets users pick values from a server-filtered list of
suggestions. This example builds one from plain WTForms fields and
trigger declarations.

For the ready-made version with single/multi/free variants, a
keyboard-navigation recipe and a ready-to-style ARIA wiring, install
`wtforms-htmx-components <https://github.com/yaal-coop/wtforms-htmx-components>`_
and pick the right composite field
(``ComboboxSingleField`` / ``ComboboxMultiField``).

.. automodule:: examples.combobox
   :no-members:
   :no-index:

The example declares every sub-field on a single
:class:`~wtforms_htmx.HtmxForm`, with no inner
:class:`~wtforms.fields.FormField`. A suggestion click appends a chip,
and the chip's ``×`` removes it.

Trigger graph
-------------

A ready-made combobox uses the same wiring:

- ``query.triggers("suggestions")``: typing in the query refreshes
  the listbox.
- ``search.triggers("suggestions")``: the *Search* button refreshes
  the listbox.
- ``suggestions.triggers("countries", value_add)``: clicking an
  option appends the picked code to the storage list.
- ``suggestions.triggers("query", value_set(""))``: also clears the
  query input.
- ``suggestions.triggers("suggestions")``: also refreshes the
  listbox itself so the next render reflects the post-pick state
  (already-picked codes show as disabled).
- ``rm_country.triggers("countries", value_remove)`` plus
  ``rm_country.triggers("suggestions")``: the chip's ``×`` drops the
  code and refreshes the listbox so the just-freed code can come
  back as a suggestion.

The "no suggestions yet" state isn't a separate flag. The ``suggest``
callable returns ``[]`` when the query is empty.

Manual recipe: multi-strict
---------------------------

.. code-block:: python

    from wtforms import (
        ButtonField, SelectChoice, SelectField, SelectMultipleField,
        StringField, SubmitField,
    )
    from wtforms.widgets import Button
    from wtforms_htmx import HtmxForm
    from wtforms_htmx.mutations import value_add, value_remove, value_set

    def suggest(form, _field):
        q = (form.query.data or "").lower()
        if not q:
            return []

        picked = set(form.countries.data or [])
        return [
            SelectChoice(c, n, render_kw={"disabled": c in picked})
            for c, n in COUNTRIES if q in n.lower()
        ][:10]

    def picked_choices(form, _field):
        return [SelectChoice(c, NAME_BY_CODE.get(c, c))
                for c in form.countries.data or []]

    class CountryPickerForm(HtmxForm):
        query = StringField("Countries")
        search = ButtonField("Search")
        suggestions = SelectField(
            choices=suggest, option_widget=Button(), validate_choice=False,
        )
        countries = SelectMultipleField(
            choices=picked_choices, validate_choice=False,
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

The ``picked_choices`` callable narrows the storage field's choices
to whatever ``countries.data`` currently holds, so iterating the
field for rendering yields exactly the picked codes, with no need to
expose the full catalog to the chip renderer.

For the single-value variant, swap
:class:`~wtforms.fields.SelectMultipleField` for
:class:`~wtforms.fields.HiddenField`, replace
:func:`~wtforms_htmx.mutations.value_add` with a pick callback that
writes the scalar, and :func:`~wtforms_htmx.mutations.value_remove`
with a :func:`~wtforms_htmx.mutations.value_set` ``("")`` clear.

Closing on blur
---------------

Add a CSS rule on the wrapper that hides the listbox when no element
inside it has focus. No JS involved:

.. code-block:: css

    .combobox-wrap:not(:focus-within) [role="listbox"] {
      display: none;
    }

Clicks on a suggestion still fire because the button briefly
receives focus during the click, so ``focus-within`` stays true for
the duration. After the swap, focus is gone and the rule kicks back in.

Without JavaScript
------------------

Every interaction is a regular form submit:

- typing in the search input + :kbd:`Enter` activates the *Search*
  button;
- clicking a suggestion button submits the form with the
  suggestion's value;
- clicking a chip's ``×`` submits the ``rm_country`` button with the
  chip's code;
- clicking ``Save`` submits the form normally and validates.

Each path returns the same re-rendered page. With htmx, only the
affected wrapper is swapped instead of the full page.

See also
--------

- :doc:`tag_picker`: the same pick and remove wiring with a fixed catalog.
- :doc:`/how-to/datalist`: native suggestions without a listbox.
