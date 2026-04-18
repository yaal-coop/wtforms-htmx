Datalist autocomplete
=====================

A native :mdn-tag:`datalist` is the simplest server-driven autocomplete:
the browser handles the popup, the markup, and the keyboard
navigation. The server only swaps fresh :mdn-tag:`option` children
as the user types.

A field declared with a callable :class:`~wtforms.DataList` refreshes
its suggestions as the user types, with no extra wiring. See
:doc:`/explanation/swap_strategies` for why the input itself is never
swapped.

.. automodule:: examples.datalist
   :no-members:
   :no-index:

Setup
-----

Declare the input with a :class:`~wtforms.DataList` whose
``choices`` argument is a callable receiving ``(form, field)``, the
same signature used by :class:`~wtforms.fields.SelectField`'s
``choices=`` callable. It returns the suggestions to show for the
current input:

.. code-block:: python

    from wtforms import DataList, StringField, SubmitField
    from wtforms_htmx import HtmxForm

    COUNTRIES = ["Afghanistan", ..., "Zimbabwe"]


    def suggest_countries(form, field):
        """Up to 10 ``<option>`` children matching the current input."""
        q = (field.data or "").strip().lower()
        if not q:
            return []

        return [n for n in COUNTRIES if q in n.lower()][:10]


    class CountryForm(HtmxForm):
        country = StringField(
            "Country",
            datalist=DataList(suggest_countries),
        )
        save = SubmitField("Save")

Render the input, then its :mdn-tag:`datalist`. WTForms renders them
with two separate calls. wtforms-htmx adds the htmx attributes to the
:mdn-tag:`datalist`:

.. code-block:: jinja

    {{ form.country() }}
    {{ form.country.datalist() }}

A :ref:`field wrapper <field-wrapper>` can make the second call for
every field, as in :doc:`render_fields`.

Change what refreshes the suggestions
-------------------------------------

By default the :mdn-tag:`datalist` refreshes on
``input delay:200ms from:body target:#<input-id>``: each typing pause
in its input. Override the trigger with ``render_kw`` on the
:class:`~wtforms.DataList` to listen to another event or field, typically
when the options depend on a sibling field:

.. code-block:: python

    region = StringField(
        "Region",
        datalist=DataList(
            suggest_regions,
            render_kw={"hx-trigger": "change from:body target:#country"},
        ),
    )

The :doc:`/examples/address` uses it to refresh the region suggestions when the
user picks a different country, not on every keystroke in the region
input itself. Prefer ``from:body target:#country`` to ``from:#country``:
htmx resolves ``from:`` once, so ``from:#country`` stops firing once
the country field is swapped.

No-JS fallback
--------------

Without htmx, the :mdn-tag:`datalist` still renders with the options
computed from the field's value when the page was rendered. The input
behaves as a regular text input with a static datalist. A full-form
submit re-renders the page and recomputes the options. An empty field
may get no suggestions until that first submit, as in the example on
this page.

See also
--------

- :doc:`/how-to/render_fields`: render the datalist from a field wrapper.
- :doc:`/examples/address`: datalists refreshed by another field.
- :doc:`/explanation/swap_strategies`: why the input is never swapped.
