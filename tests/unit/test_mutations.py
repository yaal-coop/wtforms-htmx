"""Direct calls to the built-in callbacks.

Calls through a form live in ``test_dispatch``.
"""

from __future__ import annotations

import pytest
from werkzeug.datastructures import MultiDict
from wtforms import FieldList
from wtforms import Form
from wtforms import FormField
from wtforms import SelectChoice
from wtforms import SelectMultipleField
from wtforms import StringField

from wtforms_htmx.mutations import list_add
from wtforms_htmx.mutations import list_clear
from wtforms_htmx.mutations import list_move
from wtforms_htmx.mutations import list_remove
from wtforms_htmx.mutations import list_reorder
from wtforms_htmx.mutations import value_add
from wtforms_htmx.mutations import value_cycle
from wtforms_htmx.mutations import value_remove
from wtforms_htmx.mutations import value_set


class _Source:
    """Stand-in for a clicked button: callbacks only read ``raw_data``."""

    def __init__(self, value: str | None = None):
        self.raw_data = [value] if value is not None else None


class _SelectForm(Form):
    tags = SelectMultipleField(
        choices=[
            SelectChoice("a", "A"),
            SelectChoice("b", "B"),
            SelectChoice("c", "C"),
        ],
    )


class _ListForm(Form):
    tags = FieldList(StringField())


def test_value_add_appends():
    """``value_add`` appends the button value to the selected values."""
    form = _SelectForm()
    form.tags.data = ["a"]
    value_add(form, _Source("b"), form.tags)
    assert form.tags.data == ["a", "b"]


def test_value_add_keeps_duplicates():
    """``value_add`` appends a value even when it is already selected."""
    form = _SelectForm()
    form.tags.data = ["a"]
    value_add(form, _Source("a"), form.tags)
    assert form.tags.data == ["a", "a"]


def test_value_add_initializes_when_none():
    """``value_add`` starts a new list when the field has no data."""
    form = _SelectForm()
    form.tags.data = None
    value_add(form, _Source("a"), form.tags)
    assert form.tags.data == ["a"]


def test_value_add_empty_value_is_noop():
    """``value_add`` adds nothing when the button has no value."""
    form = _SelectForm()
    form.tags.data = ["a"]
    value_add(form, _Source(""), form.tags)
    assert form.tags.data == ["a"]


def test_value_remove_removes_first_match():
    """``value_remove`` removes only the first occurrence of the button value."""
    form = _SelectForm()
    form.tags.data = ["a", "b", "a"]
    value_remove(form, _Source("a"), form.tags)
    assert form.tags.data == ["b", "a"]


def test_value_remove_unknown_value_is_noop():
    """``value_remove`` leaves the data unchanged when the value is not selected."""
    form = _SelectForm()
    form.tags.data = ["a", "b"]
    value_remove(form, _Source("ghost"), form.tags)
    assert form.tags.data == ["a", "b"]


def test_value_remove_handles_none_data():
    """``value_remove`` leaves an empty list when the field has no data."""
    form = _SelectForm()
    form.tags.data = None
    value_remove(form, _Source("a"), form.tags)
    assert form.tags.data == []


def test_list_add_appends_with_empty_value():
    """``list_add`` appends an entry when the button has no value."""
    form = _ListForm()
    list_add(form, _Source(""), form.tags)
    assert len(form.tags) == 1


def test_list_add_inserts_at_index():
    """``list_add`` inserts an empty entry at the index in the button value."""
    form = _ListForm(data={"tags": ["a", "b", "c"]})
    list_add(form, _Source("1"), form.tags)
    assert [e.data for e in form.tags] == ["a", None, "b", "c"]


def test_list_add_ignores_a_non_integer_value():
    """``list_add`` leaves the list unchanged when the button value is not an index."""
    form = _ListForm(data={"tags": ["a"]})
    list_add(form, _Source("x"), form.tags)
    assert [e.data for e in form.tags] == ["a"]


def test_list_remove_pops_last_with_empty_value():
    """``list_remove`` removes the last entry when the button has no value."""
    form = _ListForm(data={"tags": ["a", "b", "c"]})
    list_remove(form, _Source(""), form.tags)
    assert [e.data for e in form.tags] == ["a", "b"]


def test_list_remove_removes_at_index():
    """``list_remove`` removes the entry at the index in the button value."""
    form = _ListForm(data={"tags": ["a", "b", "c"]})
    list_remove(form, _Source("1"), form.tags)
    assert [e.data for e in form.tags] == ["a", "c"]


@pytest.mark.parametrize("value", ["9", "x"])
def test_list_remove_without_a_valid_index_is_noop(value):
    """An out-of-range or non-integer index leaves the list unchanged."""
    form = _ListForm(data={"tags": ["a"]})
    list_remove(form, _Source(value), form.tags)
    assert [e.data for e in form.tags] == ["a"]


def test_list_reorder_applies_permutation():
    """``list_reorder`` puts the entries in the order given by the button value."""
    form = _ListForm(data={"tags": ["a", "b", "c"]})
    list_reorder(form, _Source("2,0,1"), form.tags)
    assert [e.data for e in form.tags] == ["c", "a", "b"]


@pytest.mark.parametrize(
    "value",
    ["0,1,2", "", "0,1", "0,0,2", "0,5,1", "a,b,c"],
    ids=["identity", "empty", "partial", "duplicate", "out-of-range", "not-integers"],
)
def test_list_reorder_without_a_valid_permutation_is_noop(value):
    """A value that is not a new order of every index leaves the list unchanged."""
    form = _ListForm(data={"tags": ["a", "b", "c"]})
    list_reorder(form, _Source(value), form.tags)
    assert form.tags.data == ["a", "b", "c"]


@pytest.mark.parametrize(
    ("offset", "index", "expected"),
    [
        (-1, "2", ["a", "c", "b"]),
        (-1, "1", ["b", "a", "c"]),
        (+1, "0", ["b", "a", "c"]),
        (+1, "1", ["a", "c", "b"]),
        (-1, "0", ["a", "b", "c"]),
        (+1, "2", ["a", "b", "c"]),
        (+2, "1", ["a", "b", "c"]),
        (-1, "3", ["a", "b", "c"]),
        (-1, "7", ["a", "b", "c"]),
        (-1, "x", ["a", "b", "c"]),
        (-1, "", ["a", "b", "c"]),
        (-1, None, ["a", "b", "c"]),
    ],
    ids=[
        "up",
        "up-to-first",
        "down-from-first",
        "down-to-last",
        "first-up",
        "last-down",
        "past-the-end",
        "index-equal-to-length",
        "index-out-of-range",
        "not-integer",
        "empty",
        "missing",
    ],
)
def test_list_move_moves_the_entry_inside_the_list(offset, index, expected):
    """``list_move`` moves the entry by the offset, and does nothing past either end."""
    form = _ListForm(data={"tags": ["a", "b", "c"]})
    list_move(offset)(form, _Source(index), form.tags)
    assert form.tags.data == expected


def test_list_move_reindexes_entries():
    """Moved entries get names that follow their new positions."""
    form = _ListForm(data={"tags": ["a", "b", "c"]})
    list_move(-1)(form, _Source("1"), form.tags)
    assert [e.name for e in form.tags] == ["tags-0", "tags-1", "tags-2"]


class _RowForm(Form):
    a = StringField()


class _PaddedForm(Form):
    rows = FieldList(FormField(_RowForm), min_entries=2)
    grid = FieldList(FieldList(StringField(), min_entries=1), min_entries=2)


@pytest.mark.parametrize(
    ("name", "formdata"),
    [("rows", {"rows-0-a": "x"}), ("grid", {"grid-0-0": "x"})],
    ids=["formfield", "fieldlist"],
)
def test_list_add_drops_the_padding_of_nested_entries(name, formdata):
    """A padded row of sub-fields is dropped before the new one is added."""
    form = _PaddedForm(MultiDict(formdata))
    target = form[name]
    list_add(form, _Source(), target)
    assert len(target) == 2


def test_value_set_overwrites_the_data():
    """``value_set`` replaces the field data with the given value."""
    form = _SelectForm()
    form.tags.data = ["a"]
    value_set(["b"])(form, _Source(), form.tags)
    assert form.tags.data == ["b"]


@pytest.mark.parametrize(
    ("current", "expected"),
    [("todo", "doing"), ("done", "todo"), (None, "todo"), ("ghost", "todo")],
)
def test_value_cycle_advances_to_the_next_value(current, expected):
    """``value_cycle`` moves to the next value, and restarts from the first one."""
    form = _ListForm()
    target = StringField().bind(form, "status")
    target.data = current
    value_cycle(["todo", "doing", "done"])(form, _Source(), target)
    assert target.data == expected


def test_value_cycle_rejects_an_empty_list():
    """``value_cycle([])`` raises at declaration, not at the first click."""
    with pytest.raises(ValueError, match="at least one value"):
        value_cycle([])


def test_list_clear_numbers_new_entries_from_zero():
    """``list_clear`` empties the list, and the next added entry gets index 0."""
    form = _ListForm(MultiDict({"tags-0": "a", "tags-1": "b"}))
    list_clear(form, _Source(), form.tags)
    assert form.tags.entries == []
    list_add(form, _Source(), form.tags)
    assert form.tags[0].name == "tags-0"


@pytest.mark.parametrize(
    ("callback", "name", "target_form"),
    [
        (value_add, "value_add", _ListForm),
        (value_remove, "value_remove", _ListForm),
        (list_add, "list_add", _SelectForm),
        (list_remove, "list_remove", _SelectForm),
        (list_reorder, "list_reorder", _SelectForm),
        (list_move(-1), "list_move", _SelectForm),
        (list_clear, "list_clear", _SelectForm),
    ],
    ids=[
        "value_add",
        "value_remove",
        "list_add",
        "list_remove",
        "list_reorder",
        "list_move",
        "list_clear",
    ],
)
def test_callback_rejects_the_wrong_target_type(callback, name, target_form):
    """A callback raises ``TypeError`` on a target of the wrong field type."""
    form = target_form()
    with pytest.raises(TypeError, match=f"^{name} requires "):
        callback(form, _Source("0"), form.tags)
