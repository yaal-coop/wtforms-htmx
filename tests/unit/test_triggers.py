from __future__ import annotations

import pytest
from werkzeug.datastructures import MultiDict
from wtforms import ButtonField
from wtforms import FieldList
from wtforms import StringField

from wtforms_htmx import HtmxForm
from wtforms_htmx.mutations import list_add
from wtforms_htmx.mutations import list_remove

from .helpers import marker_clause
from .helpers import markers


def test_triggers_returns_the_field():
    """``.triggers()`` and ``.triggered_by()`` return the field they are called on."""
    field = StringField()
    assert field.triggers("a") is field
    assert field.triggered_by("b") is field


def test_triggers_on_its_own_line_wires_the_field():
    """A ``.triggers()`` call after the declaration needs no reassignment."""

    class SearchForm(HtmxForm):
        query = StringField()
        results = StringField()

        query.triggers("results")

    form = SearchForm()
    assert marker_clause("input delay:200ms", "results") in form.results()
    assert markers(form.query()) == ["results"]


def test_triggers_later_declaration_for_a_target_wins():
    """Declaring the same target twice keeps the later callback."""

    class TagsForm(HtmxForm):
        tags = FieldList(StringField())
        edit = ButtonField().triggers("tags", list_add).triggers("tags", list_remove)

    form = TagsForm(MultiDict({"tags-0": "a", "tags-1": "b", "edit": ""}))
    assert form.tags.data == ["a"]


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "error", "match"),
    [
        ("triggers", ("a",), {"on": 1}, TypeError, r"\.triggers.*event must be str"),
        (
            "triggered_by",
            ("a", "cb"),
            {},
            TypeError,
            r"\.triggered_by.*callback must be callable",
        ),
        ("triggers", (42,), {}, TypeError, r"\.triggers.*must be str or list"),
        ("triggered_by", (42,), {}, TypeError, r"\.triggered_by.*must be str or list"),
        ("triggers", ([],), {}, ValueError, "must not be empty"),
        ("triggers", (["a", 1],), {}, TypeError, "list items must be str"),
        ("triggered_by", (["*", "a"],), {}, ValueError, "cannot be mixed in a list"),
        ("triggers", ("*",), {}, ValueError, "only supported on .triggered_by"),
    ],
    ids=[
        "event",
        "callback",
        "triggers-target",
        "triggered_by-source",
        "empty-list",
        "list-item",
        "wildcard-in-list",
        "wildcard-on-triggers",
    ],
)
def test_triggers_rejects_bad_arguments(method, args, kwargs, error, match):
    """Bad declaration arguments raise a clear error."""
    with pytest.raises(error, match=match):
        getattr(StringField(), method)(*args, **kwargs)
