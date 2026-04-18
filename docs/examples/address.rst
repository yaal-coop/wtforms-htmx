Dynamic address form
====================

An address form where the country drives the address block, the postal
code drives the city, and a checkbox reveals a billing block. It
combines several trigger declarations with two kinds of datalist on one
form.

.. automodule:: examples.address
   :no-members:
   :no-index:

.. code-block:: python

    def prefill_billing(form, source, target):
        """Copy delivery into billing when the checkbox is unchecked."""
        if source.data:                    # billing == delivery, hide block
            return

        delivery = form.delivery_address.form
        billing = target.form
        billing.line_1.data = delivery.line_1.data or ""
        billing.postal_code.data = delivery.postal_code.data or ""
        billing.city.data = delivery.city.data or ""
        billing.region.data = delivery.region.data or ""


    class AddressBlockForm(HtmxForm):
        line_1 = StringField("Address line 1")
        postal_code = StringField(
            "Postal code",
            datalist=DataList(suggest_postal_codes),    # refreshes as you type
        )
        lookup_postal = SubmitField("Lookup")
        city = SelectField("City", choices=compute_city_choices)
        region = StringField(
            "Region",
            datalist=DataList(
                suggest_regions,
                render_kw={"hx-trigger": "change from:body target:#country"},
            ),
        )

        # Typing a postal code refreshes the cities. Without JavaScript,
        # Lookup does it.
        postal_code.triggers("city")
        lookup_postal.triggers("city")


    class AddressForm(HtmxForm):
        country = SelectField("Country", choices=SUPPORTED_COUNTRIES)
        apply_country = SubmitField("Apply")
        delivery_address = FormField(AddressBlockForm)
        same_billing = BooleanField("Billing == delivery", default=True)
        billing_address = FormField(AddressBlockForm)
        save = SubmitField("Save")

        # A country change recomputes the delivery block. Without
        # JavaScript, Apply does it.
        delivery_address.triggered_by("country", on="change")
        apply_country.triggers("delivery_address")

        # Unchecking "same billing" reveals the billing block, prefilled
        # from the delivery one.
        billing_address.triggered_by("same_billing", prefill_billing, on="change")

The trigger declarations compose on this one form:

1. **Cascade**: ``delivery_address.triggered_by("country", on="change")``
   re-renders the whole address block when the country changes.
   The block's :class:`~wtforms.fields.SelectField` ``choices`` callable for
   ``city`` and the :class:`~wtforms.DataList` callables for
   ``postal_code`` / ``region`` all re-execute against the new
   country.
2. **Sibling lookup**: ``postal_code.triggers("city")``
   re-renders ``city`` as the user types; ``city.choices`` reads
   the sibling ``postal_code.data`` to compute matching cities.
3. **Conditional prefill**:
   ``billing_address.triggered_by("same_billing", prefill_billing)``
   toggles ``billing_address`` and pre-fills it from the delivery
   block when the user opts out of the default.

The datalists show off different trigger styles. ``postal_code``'s
:class:`~wtforms.DataList` keeps the default: it refreshes as the user
types in the field, with a small prefix-matched payload.
``region``'s :class:`~wtforms.DataList` overrides :htmx-attr:`hx-trigger` to listen
to the top-level country select, a **cross-field** datalist that
re-fetches the region list when the country changes, not when the
user types in the region input itself.

Without JavaScript
------------------

Changing a field triggers nothing, so two submit buttons stand in for
the cascade. Each one re-renders the same target through a
:meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>`
declaration without a callback:

- after a country change, ``Apply`` reloads the page with the address
  block computed for the new country;
- after typing a postal code, ``Lookup`` reloads the page with the
  matching cities.

Unchecking ``same_billing`` reveals the billing block on the next
submit, without the prefill. The datalists keep the options rendered
with the page.

See also
--------

- :doc:`/how-to/datalist`: the datalist wiring used for
  ``postal_code`` and ``region``.
- :doc:`/explanation/progressive_enhancement`: why typing and change
  sources need a fallback button.
