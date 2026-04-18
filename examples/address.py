"""A top-level select can cascade-rerender a nested address block; a
field inside that block can drive another field as the user types;
a separate checkbox can reveal an optional sibling block prefilled
from the first. Independent trigger declarations, all on one
form.

.. screencast:: |examples|/address
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const $ = (s) => document.querySelector(s);
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     const typeIn = async (id, text) => {
       const el = $(id);
       el.focus();
       el.value = '';
       el.dispatchEvent(new Event('input', {bubbles: true}));
       await wait(150);
       for (const c of text) {
         const cur = $(id);
         cur.focus();
         cur.value = (cur.value || '') + c;
         cur.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(180);
       }
       await wait(700);
     };
     await wait(500);
     // Cycle: postal 75001 → 13001 (city Paris → Marseille) → 75001 back,
     // then toggle same_billing off (billing block appears, prefilled)
     // and back on, so the end frame matches the start.
     await typeIn('#delivery_address-postal_code', '13001');
     await wait(700);
     await typeIn('#delivery_address-postal_code', '75001');
     await wait(500);
     // ``checkbox.click()`` toggles and fires a native ``change``,
     // which is what ``billing_address.triggered_by("same_billing", ...)``
     // listens for. No need to dispatch the event by hand.
     $('#same_billing').click();
     await wait(900);
     $('#same_billing').click();
     await wait(500);
     $('#delivery_address-postal_code').blur();
     await wait(500);

   Postal code → city (sample French ZIPs: ``75001``, ``13001``,
   ``69001`` …); ``city`` recomputes its choices as the user types,
   from the sibling postal value. A separate checkbox toggles the
   billing block: revealing it copies the delivery address as a
   starting point via a callback. The country select at the
   top of the form (not exercised by the loop above to keep the
   screencast cheap; see the no-JS section below) cascades a full
   address-block re-render.
"""

from __future__ import annotations

import contextlib
import re
import socket
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field as dc_field

import pgeocode
import pycountry
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from wtforms import BooleanField
from wtforms import DataList
from wtforms import DataListChoice
from wtforms import FormField
from wtforms import SelectChoice
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Optional

from . import bp
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm
from ._shared import jinja_widget


@dataclass
class AddressBlockData:
    """One address block (delivery or billing)."""

    line_1: str = ""
    line_2: str = ""
    postal_code: str = ""
    city: str = ""
    region: str = ""


@dataclass
class AddressData:
    """Top-level state for the address form.

    Mutable on purpose: ``form.populate_obj(state)`` writes the
    current form data back into this instance, including the nested
    AddressBlockData sub-objects (WTForms recurses through
    ``FormField.populate_obj``).
    """

    country: str = ""
    delivery_address: AddressBlockData = dc_field(default_factory=AddressBlockData)
    same_billing: bool = True
    billing_address: AddressBlockData = dc_field(default_factory=AddressBlockData)


_STATE["address"] = AddressData(
    country="FR",
    delivery_address=AddressBlockData(
        line_1="12 Rue de Rivoli",
        postal_code="75001",
        city="Paris",
        region="Île-de-France",
    ),
)
_INITIAL_STATE["address"] = deepcopy(_STATE["address"])

_NOMINATIM_CACHE: dict[str, pgeocode.Nominatim] = {}
_DOWNLOAD_TIMEOUT_SECONDS = 10

_SUPPORTED_COUNTRIES = sorted(
    [
        SelectChoice(c.alpha_2, c.name)
        for c in pycountry.countries
        if c.alpha_2 in pgeocode.COUNTRIES_VALID
    ],
    key=lambda ch: ch.label,
)


@contextlib.contextmanager
def _socket_timeout(seconds: float):
    """Bound a pgeocode download window via the process-wide socket timeout.

    Pgeocode calls ``urllib.request.urlopen()`` without a timeout, so
    this context manager imposes one via the process-wide default.
    """
    previous = socket.getdefaulttimeout()
    socket.setdefaulttimeout(seconds)
    try:
        yield
    finally:
        socket.setdefaulttimeout(previous)


def _get_nominatim(country_code: str) -> pgeocode.Nominatim | None:
    """Return a cached Nominatim, downloading synchronously on first hit.

    Blocks the Flask worker up to ``_DOWNLOAD_TIMEOUT_SECONDS`` for a
    cold cache. Acceptable in this example (single user, local dev),
    anti-pattern in production. Use a job queue or pre-warm the cache
    at boot. The city field dims (CSS keyed on ``.htmx-request``) while
    we wait.
    """
    if country_code in _NOMINATIM_CACHE:
        return _NOMINATIM_CACHE[country_code]

    try:
        with _socket_timeout(_DOWNLOAD_TIMEOUT_SECONDS):
            nom = pgeocode.Nominatim(country_code)
    except Exception:  # noqa: BLE001 (pgeocode download can fail in many ways: net/parse/FS; any failure → return None)
        return None

    _NOMINATIM_CACHE[country_code] = nom
    return nom


def _compute_cities(country: str | None, postal: str | None) -> list[str]:
    """Return the city names matching ``postal`` in ``country``, or empty."""
    if not country or not postal:
        return []

    nominatim = _get_nominatim(country)
    if nominatim is None:
        return []

    df = nominatim._data
    all_names = df[df["postal_code"] == postal]["place_name"].dropna().unique()
    # Filter out arrondissement sub-entries like "Paris 01", "Lyon 02".
    base_names = {
        n for n in all_names if isinstance(n, str) and not re.search(r" \d+$", n)
    }
    return sorted(
        base_names if base_names else {n for n in all_names if isinstance(n, str)}
    )


_MAX_POSTAL_SUGGESTIONS = 10


def _parent_country(form) -> str | None:
    """Return the country of the enclosing AddressForm."""
    return form._parent_form.country.data if form._parent_form else None


def suggest_postal_codes(form, field):
    """Return postal codes for the parent form's country, prefix-matched.

    Same pgeocode data source as ``_compute_cities``. The browser
    handles the substring filter natively against the rendered
    <option> set, so a tight server-side prefix match keeps the
    payload small (capped at ``_MAX_POSTAL_SUGGESTIONS``).
    """
    country = _parent_country(form)
    if not country:
        return []

    nominatim = _get_nominatim(country)
    if nominatim is None:
        return []

    prefix = (field.data or "").strip()
    codes = sorted({str(c) for c in nominatim._data["postal_code"].dropna().unique()})
    if prefix:
        codes = [c for c in codes if c.startswith(prefix)]

    return [DataListChoice(c) for c in codes[:_MAX_POSTAL_SUGGESTIONS]]


def suggest_regions(form, field):
    """Return all regions of the parent form's country, in alphabetical order.

    Datalist driven by an *external* trigger (``hx-trigger="change
    from:body target:#country"``, set in ``render_kw`` on the DataList to
    replace the default refresh on typing): refreshes only when the user
    picks a different country, not on every keystroke in the region
    field. The browser then filters the rendered <option> set
    natively as the user types, typical for short lists (FR has 13
    regions, DE 23, US 52).
    """
    country = _parent_country(form)
    if not country:
        return []

    nominatim = _get_nominatim(country)
    if nominatim is None:
        return []

    regions = sorted({str(r) for r in nominatim._data["state_name"].dropna().unique()})
    return [DataListChoice(r) for r in regions]


def _compute_city_choices(form, field):
    """Compute city options from sibling ``postal_code`` and parent ``country``.

    Called on the first read of ``choices`` after each
    ``post_process``. ``form`` is the immediate AddressBlockForm;
    ``form._parent_form`` (wtforms 3.3+) is the enclosing AddressForm
    where ``country`` lives.
    """
    country = _parent_country(form)
    cities = _compute_cities(country, form.postal_code.data)
    return [SelectChoice(c, c) for c in cities] if cities else [SelectChoice("", "—")]


class CitySelect(SelectField):
    """SelectField that auto-picks the first option when the current value is invalid.

    After ``super().post_process``, reading ``self.choices`` calls the
    callable on the current data; this override then snaps ``self.data``
    to the first available value if the persisted one no longer matches,
    e.g. when ``country`` or ``postal_code`` changed.
    """

    def post_process(self, formdata=None):
        super().post_process(formdata)
        values = [c.value for c in self.choices or []]
        if values and self.data not in values:
            self.data = values[0]


def prefill_billing(form, source, target):
    """Copy delivery address into billing when revealed (checkbox unchecked).

    ``source`` is ``same_billing``: False means "billing differs", which is
    when the block is revealed and the pre-fill should happen. The city
    choices are then recomputed against the copied postal code, so the
    CitySelect auto-pick keeps the ``city.data`` set here.
    """
    if source.data:
        return

    delivery = form.delivery_address.form
    billing = target.form
    billing.line_1.data = delivery.line_1.data or ""
    billing.line_2.data = delivery.line_2.data or ""
    billing.postal_code.data = delivery.postal_code.data or ""
    billing.city.data = delivery.city.data or ""
    billing.region.data = delivery.region.data or ""


class AddressBlockForm(ExampleForm):
    """Address block: two free-text lines, postal code, city (auto-filled)."""

    line_1 = StringField(
        "Address line 1",
        validators=[Optional()],
        render_kw={"placeholder": "12 Rue de Rivoli"},
    )
    line_2 = StringField(
        "Address line 2",
        validators=[Optional()],
        render_kw={"placeholder": "Bâtiment B, Apt. 4"},
    )
    postal_code = StringField(
        "Postal code",
        validators=[Optional()],
        wrapper=False,
        datalist=DataList(suggest_postal_codes),
        render_kw={
            "placeholder": "75001",
            "inputmode": "numeric",
            "maxlength": "5",
        },
    )
    lookup_postal = SubmitField("Lookup")
    city = CitySelect(
        "City",
        choices=_compute_city_choices,
        validate_choice=False,
        validators=[Optional()],
        render_kw={"class": "address-city"},
    )
    region = StringField(
        "Region",
        validators=[Optional()],
        datalist=DataList(
            suggest_regions,
            # Override the auto-wired ``hx-trigger`` (which defaults to
            # typing in this field) so the
            # listbox refreshes when *another* field (the top-level
            # country select) changes, not on keystrokes here.
            render_kw={"hx-trigger": "change from:body target:#country"},
        ),
        render_kw={"placeholder": "Île-de-France"},
    )

    # Typing a postal code refreshes the cities. Without JavaScript,
    # Lookup does it.
    postal_code.triggers("city")
    lookup_postal.triggers("city")


class AddressForm(ExampleForm):
    """Delivery address with country, live postal lookup, optional billing block."""

    country = SelectField(
        "Country",
        choices=[SelectChoice("", "— Select a country —"), *_SUPPORTED_COUNTRIES],
        validators=[Optional()],
        wrapper=False,
    )
    apply_country = SubmitField("Apply")
    delivery_address = FormField(
        AddressBlockForm,
        widget=jinja_widget("_address_widgets.html", "delivery_address"),
    )
    same_billing = BooleanField(
        "Billing address is the same as my delivery address",
        default=True,
    )
    billing_address = FormField(
        AddressBlockForm,
        widget=jinja_widget("_address_widgets.html", "billing_address"),
    )
    save = SubmitField("Save")

    # A country change recomputes the delivery block. Without
    # JavaScript, Apply does it.
    delivery_address.triggered_by("country", on="change")
    apply_country.triggers("delivery_address")

    # Unchecking "same billing" reveals the billing block, prefilled
    # from the delivery one.
    billing_address.triggered_by("same_billing", prefill_billing, on="change")


@bp.route("/address", methods=["GET", "POST"])
def address():
    state = _STATE["address"]
    form = AddressForm(request.form or None, obj=state, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if form.submitter is not form.save:
        return render_template("address.html", form=form)

    if not form.validate():
        flash("Please fix the errors below.", "error")
        return render_template("address.html", form=form)

    form.populate_obj(state)
    flash(
        f"Saved {state.delivery_address.postal_code} "
        f"({state.delivery_address.city}, {state.delivery_address.region}).",
        "success",
    )
    return redirect(url_for("main.address"))
