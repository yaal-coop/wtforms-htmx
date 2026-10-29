Invoice totals
==============

An invoice form computes each row's total from quantity × unit price ×
VAT, and refreshes the invoice totals in the same response through
out-of-band swaps.

.. automodule:: examples.invoice
   :no-members:
   :no-index:

.. literalinclude:: ../../examples/invoice.py
   :pyobject: _totals_oob

.. literalinclude:: ../../examples/invoice.py
   :pyobject: recompute_total

.. literalinclude:: ../../examples/invoice.py
   :pyobject: LineItem

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
