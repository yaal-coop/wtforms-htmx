"""Built-in callbacks for trigger declarations.

Each callback takes ``(form, source, target)``. ``value_set``,
``cycle_through`` and ``list_move`` build such a callback. The ones for a
SelectMultipleField or a FieldList raise TypeError on another target type.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wtforms.fields import FieldList
from wtforms.fields import SelectMultipleField


def _entry_is_padding(entry: Any) -> bool:
    """Whether ``entry`` comes from ``min_entries`` padding rather than formdata.

    A padded field has ``raw_data == []``. FormField and FieldList entries
    are checked through their sub-fields.
    """
    if hasattr(entry, "form"):
        return all(_entry_is_padding(f) for f in entry.form._fields.values())

    if hasattr(entry, "entries"):
        return all(_entry_is_padding(e) for e in entry.entries)

    return entry.raw_data == []


def _truncate_to_padding(field: FieldList) -> None:
    """Drop the trailing entries that come from ``min_entries`` padding.

    Mutations then only see the entries the user submitted.
    """
    while field.entries and _entry_is_padding(field.entries[-1]):
        field.pop_entry()


def _require(target: Any, field_class: type, name: str) -> None:
    """Raise TypeError when ``target`` is not a ``field_class``."""
    if not isinstance(target, field_class):
        raise TypeError(
            f"{name} requires {field_class.__name__}, got {type(target).__name__}"
        )


def _source_value(source: Any) -> str:
    """Return the source's value: ``raw_data[0]`` stripped, or ``""``."""
    raw = getattr(source, "raw_data", None)
    return raw[0].strip() if raw else ""


def _source_index(source: Any) -> int | None:
    """Return the source's value as an integer, or ``None`` when it is not one."""
    try:
        return int(_source_value(source))
    except ValueError:
        return None


def value_set(value: Any) -> Callable[[Any, Any, Any], None]:
    """Return a mutation that overwrites ``target.data`` with ``value``.

    Use it to clear a field (``value_set("")`` / ``value_set(None)``) or
    to reset it to a default, for example from a "clear" button::

        query = StringField()
        clear = ButtonField("Clear").triggers("query", value_set(""))
    """

    def _mutation(form: Any, source: Any, target: Any) -> None:
        target.data = value

    return _mutation


def cycle_through(values: list[Any]) -> Callable[[Any, Any, Any], None]:
    """Return a mutation that rotates ``target.data`` through ``values``.

    Each firing advances ``target.data`` to the next entry, wrapping around
    at the end. If the current ``target.data`` isn't in ``values`` (for
    example, when the field is empty), the mutation resets to ``values[0]``.

    Use it with a single :class:`~wtforms.fields.ButtonField` for status
    toggles, view/edit modes or step indicators. No value is read from
    the source.

    Cycle a status field from one button::

        STATES = ["todo", "doing", "done"]
        status = SelectField(choices=STATES)
        cycle = ButtonField("·").triggers("status", cycle_through(STATES))
    """

    def _mutation(form: Any, _source: Any, target: Any) -> None:
        current = target.data or ""
        if current not in values:
            target.data = values[0]
            return

        target.data = values[(values.index(current) + 1) % len(values)]

    return _mutation


def value_add(form: Any, source: Any, target: Any) -> None:
    """Append the source's value to a :class:`~wtforms.fields.SelectMultipleField`'s data.

    No deduplication: clicking a button whose value is already in
    ``target.data`` adds a duplicate entry. Filter at the source if
    uniqueness matters (e.g. exclude already-selected values from the
    candidate set).

    Each catalog button carries its option's value::

        tags = SelectMultipleField(choices=CATALOG)
        add_tag = ButtonField("Add").triggers("tags", value_add)

    Render one button per option and pass the value at render time:

    .. code-block:: jinja

        {% for value, label in form.tags.choices %}
          {{ form.add_tag(value=value, label=label, id=False) }}
        {% endfor %}
    """
    _require(target, SelectMultipleField, "value_add")

    value = _source_value(source)
    if not value:
        return

    target.data = [*list(target.data or []), value]


def value_remove(form: Any, source: Any, target: Any) -> None:
    """Remove the first occurrence of the source's value from a :class:`~wtforms.fields.SelectMultipleField`'s data.

    Subsequent matches (if duplicates exist) are left untouched,
    like :meth:`list.remove`.

    Each chip "×" button carries its value::

        tags = SelectMultipleField(choices=CATALOG)
        rm_tag = ButtonField("×").triggers("tags", value_remove)

    .. code-block:: jinja

        {% for value in form.tags.data or [] %}
          {{ value }} {{ form.rm_tag(value=value, id=False) }}
        {% endfor %}
    """
    _require(target, SelectMultipleField, "value_remove")

    value = _source_value(source)
    data = list(target.data or [])
    if value in data:
        data.remove(value)

    target.data = data


def list_add(form: Any, source: Any, target: Any) -> None:
    """Append or insert an entry into a :class:`~wtforms.fields.FieldList`.

    The insertion position is read from the source's value (typically
    the clicked button's ``value=``). An empty string appends a fresh
    entry at the end of the list. An integer inserts at that absolute
    index and shifts the following entries one slot to the right. Any
    other value does nothing.

    Append a row from an Add button::

        tasks = FieldList(StringField())
        add_task = ButtonField("+ Add task").triggers("tasks", list_add)
    """
    _require(target, FieldList, "list_add")

    _truncate_to_padding(target)
    if not _source_value(source):
        target.append_entry()
        return

    index = _source_index(source)
    if index is not None:
        target.insert_entry(index)


def list_remove(form: Any, source: Any, target: Any) -> None:
    """Remove an entry from a :class:`~wtforms.fields.FieldList`.

    The position is read from the source's value: an empty string
    pops the last entry, while an integer drops the entry at that
    absolute index. Any other value does nothing. Remaining entries are
    re-indexed contiguously. An index captured client-side before the
    call is then stale.

    Remove a row from a per-row × button::

        tasks = FieldList(StringField())
        rm_task = ButtonField("×").triggers("tasks", list_remove)
    """
    _require(target, FieldList, "list_remove")

    _truncate_to_padding(target)
    index = _source_index(source) if _source_value(source) else len(target) - 1
    if index is not None and 0 <= index < len(target):
        target.pop_entry(index)


def list_clear(form: Any, _source: Any, target: Any) -> None:
    """Empty a :class:`~wtforms.fields.FieldList` of all its entries.

    Entries added afterwards in the same request are numbered from
    ``0``.

    Empty the whole list from one button::

        tasks = FieldList(StringField())
        clear = ButtonField("Clear all").triggers("tasks", list_clear)
    """
    _require(target, FieldList, "list_clear")

    target.entries = []
    target.last_index = -1


def list_reorder(form: Any, source: Any, target: Any) -> None:
    """Reorder a :class:`~wtforms.fields.FieldList` in the order given by the source's value.

    The value is a comma-separated list of the *old* indices in their
    new order, e.g. ``"0,2,1"`` rebuilds the list as
    ``[old[0], old[2], old[1]]``. The indices must cover
    ``range(len(target))`` exactly once. A partial, duplicate or
    out-of-range permutation does nothing, so a stale client request
    cannot silently truncate or duplicate entries.

    A hidden field carries the new index order (written client-side)::

        tasks = FieldList(StringField())
        reorder = HiddenField().triggers("tasks", list_reorder, on="change")
    """
    _require(target, FieldList, "list_reorder")

    _truncate_to_padding(target)
    value = _source_value(source)
    if not value:
        return

    try:
        order = [int(part) for part in value.split(",")]
    except ValueError:
        return

    if sorted(order) != list(range(len(target.entries))):
        return

    _rebuild_in_order(target, order)


def list_move(offset: int) -> Callable[[Any, Any, Any], None]:
    """Return a mutation that moves a :class:`~wtforms.fields.FieldList` entry by ``offset``.

    The entry index is read from the source's value. ``-1`` moves the
    entry one row up, ``+1`` one row down. A move past either end of
    the list, a missing value or a value that is not an index does
    nothing. Remaining entries are re-indexed contiguously.

    Move a row from per-row ↑ / ↓ buttons, an alternative to dragging
    that works without JavaScript::

        tasks = FieldList(StringField())
        move_up = ButtonField("↑").triggers("tasks", list_move(-1))
        move_down = ButtonField("↓").triggers("tasks", list_move(+1))
    """

    def _mutation(form: Any, source: Any, target: Any) -> None:
        _require(target, FieldList, "list_move")

        _truncate_to_padding(target)
        idx = _source_index(source)
        if idx is None:
            return

        new = idx + offset
        n = len(target.entries)
        if not (0 <= idx < n and 0 <= new < n):
            return

        order = list(range(n))
        order.insert(new, order.pop(idx))
        _rebuild_in_order(target, order)

    return _mutation


def _rebuild_in_order(target: FieldList, order: list[int]) -> None:
    """Rebuild ``target`` with its entries taken in ``order`` (old indices)."""
    # Snapshot data in the desired order before draining: pop_entry
    # mutates entries in place and reindexes after each call.
    data_in_order = [target.entries[i].data for i in order]
    for _ in range(len(order)):
        target.pop_entry()

    for data in data_in_order:
        target.append_entry(data)
