Currency converter
==================

A two-way sync between two amounts. The same shape fits temperature
units, imperial and metric pairs, or any reversible derivation.

.. automodule:: examples.currency
   :no-members:
   :no-index:

.. code-block:: python

    JPY_PER_EUR = 165

    def eur_to_jpy(form, source, target):
        target.data = (form.eur.data or 0) * JPY_PER_EUR

    def jpy_to_eur(form, source, target):
        target.data = (form.jpy.data or 0) // JPY_PER_EUR

    class CurrencyForm(HtmxForm):
        eur = IntegerField(
            "EUR", default=0,
            render_kw={"type": "text", "inputmode": "numeric", "pattern": "[0-9]*"},
        )
        jpy = IntegerField(
            "JPY", default=0,
            render_kw={"type": "text", "inputmode": "numeric", "pattern": "[0-9]*"},
        )
        convert_to_jpy = ButtonField("→ JPY")
        convert_to_eur = ButtonField("← EUR")
        save = SubmitField("Save")

        # Typing in one amount converts it into the other.
        eur.triggers("jpy", eur_to_jpy)
        jpy.triggers("eur", jpy_to_eur)

        # Without JavaScript, the buttons run the same conversions.
        convert_to_jpy.triggers("jpy", eur_to_jpy)
        convert_to_eur.triggers("eur", jpy_to_eur)

The view holds no conversion logic. With htmx, typing in a field runs
its callback. Without JavaScript, a click on a convert button runs the
same callback while the form is built. The callbacks read
``form.eur.data`` and ``form.jpy.data`` rather than ``source.data``,
because a button's ``data`` is not the amount.

Swapping one amount does not fire an ``input`` event, so the two
conversions do not trigger each other in a loop.

.. note::

    Render the integer fields as ``type="text" inputmode="numeric"``
    rather than ``type="number"``: number inputs do not support
    the selection API used to preserve caret position across an
    htmx swap. Text inputs do; the ``inputmode`` still triggers
    the numeric keypad on mobile.

Without JavaScript
------------------

Typing triggers nothing. The ``→ JPY`` and ``← EUR`` buttons submit the
page, and the form runs the same callback while it is built. The page
comes back with the converted amount.

See also
--------

- :doc:`title_slug`: a one-way derivation from one field to another.
- :ref:`anatomy-of-a-callback`: the callback signature.
