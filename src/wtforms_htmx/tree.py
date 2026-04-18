"""Walk the field tree of a form and resolve fields by name or id."""

from __future__ import annotations

import re
from typing import Any
from typing import TYPE_CHECKING

from wtforms.fields import FieldList
from wtforms.fields import FormField

if TYPE_CHECKING:
    from collections.abc import Iterator

    from wtforms import Field


_PY_PATH_RE = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")

_PLAIN_ID_RE = re.compile(r"[A-Za-z_][\w-]*")


def _state(field: Any, name: str, default: Any = None) -> Any:
    """Return the wtforms-htmx attribute ``name`` set on ``field``, or ``default``.

    It reads ``__dict__``: ``FormField.__getattr__`` recurses while its form
    is being built.
    """
    return field.__dict__.get(name, default)


def _looks_like_python_path(name: str) -> bool:
    """Whether ``name`` is a Python identifier path (``"a"``, ``"a.b.c"``).

    Anything else (``#id``, ``.class``, ``closest form``, a dashed name) is
    a selector.
    """
    return _PY_PATH_RE.fullmatch(name) is not None


def _fields_of(container: Any) -> dict[str, Any]:
    """Return the direct fields of a form, a FormField or a FieldList."""
    # A sub-form still being built must not recurse through FormField.__getattr__.
    if isinstance(container, FormField):
        form = container.__dict__.get("form")
        return form._fields if form is not None else {}

    if isinstance(container, FieldList):
        entries = container.__dict__.get("entries")
        return {entry.name: entry for entry in entries} if entries else {}

    return container._fields


def _walk_fields(container: Any) -> Iterator[Any]:
    """Yield every field of ``container``, descending into FieldList and FormField."""
    for field in _fields_of(container).values():
        yield field
        if isinstance(field, FieldList | FormField):
            yield from _walk_fields(field)


def _root_of(form: Any) -> Any:
    """Walk up ``_parent_form`` links to the top-level form."""
    while form._parent_form is not None:
        form = form._parent_form

    return form


def _resolve_field_by_id(container: Any, field_id: str) -> Field | None:
    """Find the field whose ``id`` is ``field_id`` anywhere in the form tree."""
    return next(
        (f for f in _walk_fields(container) if getattr(f, "id", None) == field_id),
        None,
    )


def _resolve_field(container: Any, name: str) -> Field | None:
    """Find a field by its HTML ``name``, descending into FormField and FieldList."""
    fields = _fields_of(container)
    if name in fields:
        return fields[name]

    remaining = name
    while True:
        dash = remaining.rfind("-")
        if dash == -1:
            return None

        prefix = remaining[:dash]
        remaining = prefix
        if prefix not in fields:
            continue

        field = fields[prefix]
        tail = name[len(prefix) + 1 :]
        if isinstance(field, FieldList):
            return _descend_into_fieldlist(field, tail)

        if isinstance(field, FormField):
            return _resolve_field(field, tail)

        return None


def _descend_into_fieldlist(field: Any, tail: str) -> Field | None:
    """Walk into a FieldList's entries from the remaining ``<index>[-rest]`` tail."""
    idx_str, sep, rest = tail.partition("-")
    try:
        idx = int(idx_str)
    except ValueError:
        return None

    if idx < 0 or idx >= len(field):
        return None

    entry = field[idx]
    if not sep:
        return entry

    if isinstance(entry, FormField):
        return _resolve_field(entry, rest)

    return None


def _classify_target(host: Any, root: Any, target: str):
    """Classify a trigger target string.

    Return ``("field", field)`` for a Python path resolved in the *host*
    scope, or a ``"#id"`` matching a field from the *root*;
    ``("selector", target)`` for any other selector; ``("unbound", target)``
    for a Python path that matches no field.
    """
    if _looks_like_python_path(target):
        field = _resolve_field(host, target.replace(".", "-"))
        return ("field", field) if field is not None else ("unbound", target)

    if (
        target.startswith("#")
        and _PLAIN_ID_RE.fullmatch(target[1:])
        and (field := _resolve_field_by_id(root, target[1:])) is not None
    ):
        return ("field", field)

    return ("selector", target)
