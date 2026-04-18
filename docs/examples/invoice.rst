Invoice totals
==============

An invoice form computes each row's total from quantity × unit price ×
VAT, and refreshes the invoice totals in the same response through
out-of-band swaps.

.. automodule:: examples.invoice
   :no-members:
   :no-index:

.. code-block:: python

    def _totals_oob(form):
        t = compute_totals(form)
        return [
            f'<output id="subtotal">{t.subtotal}</output>',
            f'<output id="vat_total">{t.vat_total}</output>',
            f'<output id="grand_total">{t.grand_total}</output>',
        ]

    def recompute_total(form, source, target):
        sub = target._form
        qty = sub.quantity.data or 0
        price = sub.unit_price.data or Decimal(0)
        vat_rate = Decimal(sub.vat_rate.data or 0) / Decimal(100)
        target.data = f"{Decimal(qty) * price * (Decimal(1) + vat_rate):.2f}"
        return [None, *_totals_oob(form)]

    class LineItem(HtmxForm):
        quantity = IntegerField("Qty")
        unit_price = DecimalField("Unit price")
        vat_rate = IntegerField("VAT %")
        total = StringField("Total", render_kw={"readonly": True})

        # Each input recomputes the row total and the invoice totals.
        quantity.triggers("total", recompute_total)
        unit_price.triggers("total", recompute_total)
        vat_rate.triggers("total", recompute_total)

The row's ``total`` field is the primary swap target. The leading
``None`` in the returned iterable keeps the default widget render. The
three invoice-level totals are *not* form fields: they live as
:mdn-tag:`output` elements in the template, and each HTML fragment
follows the primary as an out-of-band swap (see
:ref:`callback-return`).

``quantity``, ``unit_price`` and ``vat_rate`` share the same callback,
yet the summary still renders once per response. See
:doc:`/explanation/swap_strategies` for how the out-of-band fragments
are deduplicated.

Without JavaScript
------------------

Typing triggers nothing, so the totals do not follow the inputs. The
``+`` and ``×`` buttons add and remove rows through a full-page
submit. ``Save`` recomputes every row total, then saves.

See also
--------

- :ref:`out-of-band-swaps`: how the extra fragments reach the page.
- :doc:`/how-to/mutations`: returning several elements from one
  callback.
