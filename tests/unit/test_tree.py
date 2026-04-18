from __future__ import annotations

import pytest
from wtforms import DataList
from wtforms import FieldList
from wtforms import Form
from wtforms import FormField
from wtforms import RadioField
from wtforms import SelectChoice
from wtforms import StringField

from wtforms_htmx import HtmxForm
from wtforms_htmx.form import _resolve_source_field
from wtforms_htmx.tree import _resolve_field

from .helpers import htmx_headers


class _AddressForm(Form):
    street = StringField()


class _EmailEntry(HtmxForm):
    address = StringField()
    domain = StringField()


class _InnerListForm(Form):
    items = FieldList(StringField(), min_entries=2)


class _TreeForm(HtmxForm):
    email = StringField()
    address = FormField(_AddressForm)
    tags = FieldList(StringField(), min_entries=2)
    emails = FieldList(FormField(_EmailEntry), min_entries=1)
    outer = FieldList(FormField(_InnerListForm), min_entries=1)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("email", lambda form: form.email),
        ("address", lambda form: form.address),
        ("address-street", lambda form: form.address.form.street),
        ("tags-1", lambda form: form.tags[1]),
        ("emails-0-domain", lambda form: form.emails[0].form.domain),
        ("outer-0-items-1", lambda form: form.outer[0].form.items[1]),
    ],
)
def test_resolve_field_finds_the_field_by_name(name, expected):
    """A dashed HTML name resolves to its field, through sub-forms and list entries."""
    form = _TreeForm()
    assert _resolve_field(form, name) is expected(form)


@pytest.mark.parametrize(
    "name",
    [
        "",
        "nope",
        "-",
        "--",
        "address-",
        "address-nope",
        "emails-",
        "emails--0",
        "tags-5",
        "tags-nope",
        "email-x",
        "tags-0-x",
    ],
)
def test_resolve_field_returns_none_for_unknown_names(name):
    """A name that matches no field resolves to ``None``."""
    assert _resolve_field(_TreeForm(), name) is None


class _SourceForm(HtmxForm):
    email = StringField()
    renamed = StringField(id="custom-id")
    items = FieldList(StringField(), min_entries=2)
    color = RadioField(choices=[SelectChoice("r", "Red"), SelectChoice("g", "Green")])


@pytest.mark.parametrize(
    ("element_id", "expected"),
    [
        ("email", lambda form: form.email),
        ("custom-id", lambda form: form.renamed),
        ("items-0", lambda form: form.items[0]),
        ("color-1", lambda form: form.color),
        ("color-0-0", lambda form: None),
        ("color-datalist", lambda form: None),
        ("unknown", lambda form: None),
        ("", lambda form: None),
        (None, lambda form: None),
    ],
)
def test_resolve_source_field_finds_the_element_owner(element_id, expected):
    """A request source id resolves to its field, and a choice option id to its parent field."""
    form = _SourceForm()
    assert _resolve_source_field(form, element_id) is expected(form)


class _CityRow(Form):
    city = StringField(datalist=DataList(lambda form, field: ["Paris"]))


class _CitiesForm(HtmxForm):
    rows = FieldList(FormField(_CityRow), min_entries=2)


def test_datalist_refresh_resolves_a_datalist_in_a_list_row():
    """A refresh request from a datalist in a ``FieldList`` row answers with that datalist."""
    form = _CitiesForm(headers=htmx_headers("rows-1-city-datalist"))
    assert form.partial().body == (
        '<datalist id="rows-1-city-datalist"><option value="Paris"></datalist>'
    )
