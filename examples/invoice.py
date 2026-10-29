"""Trigger declarations also work inside nested ``FormField`` rows. The
invoice example keeps each line local while returning the invoice
summary as out-of-band extras.

.. screencast:: |examples|/invoice
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const $ = (s) => document.querySelector(s);
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     await wait(500);
     // Initial state:
     //   row 0 = 2 × 9.50 @ 20% = 22.80
     //   row 1 = 1 × 30.00 @ 10% = 33.00
     // Cycle row 0 qty 2 → 5 → 2 so the loop closes cleanly.
     $('#items-0-quantity').focus();
     $('#items-0-quantity').value = '5';
     $('#items-0-quantity').dispatchEvent(new Event('input', {bubbles: true}));
     await wait(900);
     $('#items-0-quantity').focus();
     $('#items-0-quantity').value = '2';
     $('#items-0-quantity').dispatchEvent(new Event('input', {bubbles: true}));
     await wait(900);
     $('#items-0-quantity').blur();
     await wait(500);

   The row total updates in place while the invoice subtotal, VAT and
   grand total arrive in the same response as out-of-band extras.
   Editing row 0 does not disturb row 1.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field as dc_field
from decimal import Decimal

from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from markupsafe import Markup
from wtforms import ButtonField
from wtforms import DecimalField
from wtforms import FieldList
from wtforms import FormField
from wtforms import IntegerField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import NumberRange

from wtforms_htmx.mutations import list_add
from wtforms_htmx.mutations import list_remove

from . import bp
from ._code import Excerpt
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm
from ._shared import jinja_widget


@dataclass
class LineItemData:
    """One invoice line: quantity × unit price + VAT."""

    name: str = ""
    quantity: int = 1
    unit_price: Decimal = dc_field(default_factory=lambda: Decimal(0))
    vat_rate: int = 20
    total: str = "0.00"


@dataclass
class InvoiceData:
    """Invoice state, with totals derived and recomputed at render."""

    items: list[LineItemData] = dc_field(default_factory=list)


_STATE["invoice"] = InvoiceData(
    items=[
        LineItemData(
            name="Espresso, single",
            quantity=2,
            unit_price=Decimal("9.50"),
            vat_rate=20,
            total="22.80",
        ),
        LineItemData(
            name="Bag of beans, 1kg",
            quantity=1,
            unit_price=Decimal("30.00"),
            vat_rate=10,
            total="33.00",
        ),
    ],
)
_INITIAL_STATE["invoice"] = deepcopy(_STATE["invoice"])


def _row_subtotal(line) -> Decimal:
    qty = line.quantity.data or 0
    price = line.unit_price.data or Decimal(0)
    return Decimal(qty) * price


def _row_tax(line) -> Decimal:
    rate = Decimal(line.vat_rate.data or 0) / Decimal(100)
    return _row_subtotal(line) * rate


@dataclass
class InvoiceTotals:
    """Derived invoice-level aggregates, recomputed at every render."""

    subtotal: str
    vat_total: str
    grand_total: str


def _compute_totals(form) -> InvoiceTotals:
    subtotal = sum((_row_subtotal(entry.form) for entry in form.items), Decimal(0))
    vat_total = sum((_row_tax(entry.form) for entry in form.items), Decimal(0))
    return InvoiceTotals(
        subtotal=f"{subtotal:.2f}",
        vat_total=f"{vat_total:.2f}",
        grand_total=f"{subtotal + vat_total:.2f}",
    )


def _totals_oob(form):
    """Render the three invoice-level totals as out-of-band extras.

    Each fragment carries its own id, so htmx swaps the matching DOM
    element on the client. The targets live in the template as plain
    <output> elements, not WTForms fields.
    """
    t = _compute_totals(form)
    return [
        Markup(f'<output id="subtotal">{t.subtotal}</output>'),
        Markup(f'<output id="vat_total">{t.vat_total}</output>'),
        Markup(f'<output id="grand_total">{t.grand_total}</output>'),
    ]


def recompute_total(form, source, target):
    """``target = quantity * unit_price * (1 + vat_rate)`` within the row.

    Reads the entry's sibling fields via ``target._form`` (the inner
    LineItem instance), so the same callback works whether the
    typing source is ``quantity``, ``unit_price`` or ``vat_rate``. The
    three invoice-level totals ride along as out-of-band Markup
    extras returned alongside the row total.
    """
    line = target._form
    target.data = f"{_row_subtotal(line) + _row_tax(line):.2f}"
    return [None, *_totals_oob(form)]


def add_line_and_refresh(form, source, target):
    """Append a new line and refresh the invoice summary in the same swap."""
    list_add(form, source, target)
    return [None, *_totals_oob(form)]


def rm_line_and_refresh(form, source, target):
    """Remove a line and refresh the invoice summary in the same swap."""
    list_remove(form, source, target)
    return [None, *_totals_oob(form)]


class LineItem(ExampleForm):
    """A single invoice line: quantity × unit price + VAT = total."""

    name = StringField("Item")
    quantity = IntegerField(
        "Qty",
        default=1,
        validators=[NumberRange(min=0)],
    )
    unit_price = DecimalField(
        "Unit price",
        default=Decimal(0),
        places=2,
        validators=[NumberRange(min=0)],
    )
    vat_rate = IntegerField(
        "VAT %",
        default=20,
        validators=[NumberRange(min=0, max=100)],
    )
    # The view recomputes the total on save, so a tampered value is ignored.
    total = StringField("Total", default="0.00", render_kw={"readonly": True})

    # Each input recomputes the row total and the invoice totals.
    quantity.triggers("total", recompute_total)
    unit_price.triggers("total", recompute_total)
    vat_rate.triggers("total", recompute_total)


class InvoiceForm(ExampleForm):
    """A small invoice: add / remove lines, live totals with VAT.

    ``subtotal`` / ``vat_total`` / ``grand_total`` are not form fields:
    they live in the template as ``<output id="...">`` elements and are
    swapped via ``_totals_oob`` returned by every callback. They
    are projections of the row state, not user-editable data.
    """

    items = FieldList(
        FormField(
            LineItem,
            widget=jinja_widget("_invoice_widgets.html", "line_entry"),
        ),
        min_entries=1,
        widget=jinja_widget("_invoice_widgets.html", "line_list"),
    )
    rm_line = ButtonField("×")
    add_line = ButtonField("+")
    save = SubmitField("Save")

    # Adding or removing a line also refreshes the invoice totals.
    rm_line.triggers("items", rm_line_and_refresh)
    add_line.triggers("items", add_line_and_refresh)


@bp.route("/invoice", methods=["GET", "POST"])
def invoice():
    state = _STATE["invoice"]
    form = InvoiceForm(request.form or None, obj=state, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("invoice.html", form=form, totals=_compute_totals(form))

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("invoice.html", form=form, totals=_compute_totals(form))

    # Without JavaScript, the submitted totals are stale: recompute them.
    for entry in form.items:
        recompute_total(form, entry.form.quantity, entry.form.total)

    totals = _compute_totals(form)

    # New rows need a dataclass for ``populate_obj`` to write into.
    while len(state.items) < len(form.items):
        state.items.append(LineItemData())

    form.populate_obj(state)
    flash(f"Saved invoice: grand total {totals.grand_total}.", "success")
    return redirect(url_for("main.invoice"))


#: Code shown under the demo.
CODE = [
    _totals_oob,
    recompute_total,
    add_line_and_refresh,
    rm_line_and_refresh,
    LineItem,
    InvoiceForm,
    invoice,
    Excerpt("templates/invoice.html", "<tfoot>", "</tfoot>"),
    Excerpt("templates/_invoice_widgets.html", "macro line_list", "endmacro"),
]
