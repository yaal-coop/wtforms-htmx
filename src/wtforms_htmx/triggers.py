"""Trigger declarations: the ``.triggers()`` and ``.triggered_by()`` field methods."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from typing import NamedTuple
from typing import TypeAlias

from wtforms.fields.core import UnboundField

TriggerCallback: TypeAlias = Callable[[Any, Any, Any], Any]
"""A ``(form, source, target) -> result`` callback of a trigger declaration.

``form`` is the form that holds the declaring field. ``source`` is the
field that fired, or ``None`` for the ``"*"`` wildcard. ``target`` is a
field, or the selector string of a DOM target. See :ref:`callback-return`
for the ``result``.
"""


class _TriggerEntry(NamedTuple):
    """Per-link declaration set by ``.triggers()`` / ``.triggered_by()``."""

    event: str | None = None
    """Optional ``hx-trigger`` event override.

    ``None`` defers to the form-wide ``htmx_default_trigger``.
    """

    callback: TriggerCallback | None = None
    """Optional ``(form, source, target) -> result`` callback.

    ``None`` means a plain re-render.
    """


def _normalize_trigger_args(
    target: str | list[str],
    callback: TriggerCallback | None,
    on: str | None,
    *,
    method_name: str,
) -> dict[str, _TriggerEntry]:
    """Turn ``.triggers()`` / ``.triggered_by()`` arguments into ``{name: _TriggerEntry}``.

    Raise on a wrong type, an empty list, or a misplaced wildcard.
    """
    if on is not None and not isinstance(on, str):
        raise TypeError(
            f".{method_name}(..., on=...): event must be str or None, "
            f"got {type(on).__name__}"
        )

    if callback is not None and not callable(callback):
        raise TypeError(
            f".{method_name}(..., callback): callback must be callable or None, "
            f"got {type(callback).__name__}"
        )

    if not isinstance(target, str | list):
        raise TypeError(
            f".{method_name}(...): target must be str or list[str], "
            f"got {type(target).__name__}"
        )

    if target == []:
        raise ValueError(f".{method_name}([]): target list must not be empty")

    if isinstance(target, list) and "*" in target:
        raise ValueError(
            f'.{method_name}([..., "*", ...]): wildcard "*" cannot be mixed in a list'
        )

    if target == "*" and method_name == "triggers":
        raise ValueError(
            f'.{method_name}("*", ...): wildcard is only supported on .triggered_by(...)'
        )

    names = [target] if isinstance(target, str) else target
    for name in names:
        if not isinstance(name, str):
            raise TypeError(
                f".{method_name}(...): list items must be str, "
                f"got {type(name).__name__}"
            )

    return dict.fromkeys(names, _TriggerEntry(event=on, callback=callback))


def _unbound_triggers(
    self,
    target: str | list[str],
    callback: TriggerCallback | None = None,
    *,
    on: str | None = None,
):
    """Declare what an event on this field re-renders, optionally running a callback first.

    Each call adds (or refines) one or more of this field's trigger
    declarations. Calls compose. If a target name is declared twice,
    the later call wins.

    :param target: a field name, a list of field names, or an htmx
        selector. A Python identifier resolves to a field by name. When
        no field matches, a :exc:`UserWarning` is emitted and the name is
        used as a selector, except for ``this``, ``next``, ``previous``
        and ``body``. A
        dotted ``"address.region"`` descends into a sub-form. A
        ``"#id"`` matching a field's :mdn-global-attr:`id` anywhere in
        the form re-renders that field. Any other string is passed
        through verbatim to :htmx-attr:`hx-target`: any selector htmx
        understands
        (``".result"``, ``"closest .toast"``, ``"this"``,
        ``"find .inner"``, ``"next"`` / ``"previous"``, …). See
        :ref:`dom-targets`. A source has at most one selector target
        over all its declarations, and a field with a selector target
        cannot also listen to another field. Either case raises
        :exc:`ValueError` when the form is built.
    :param callback: optional ``(form, source, target) -> result``
        callable run server-side before the target is re-rendered.
        ``target`` is a :class:`~wtforms.fields.Field` for a field
        target, or the raw selector ``str`` for a DOM target. The
        ``result`` drives the response body (see :ref:`callback-return`).
        Without a callback, the target re-renders from the current form
        state. See :mod:`wtforms_htmx.mutations` for built-in callbacks.
    :param on: optional :htmx-attr:`hx-trigger` event override. When ``None``,
        the form-wide :attr:`~wtforms_htmx.HtmxMeta.htmx_default_trigger`
        applies.

    .. code-block:: python

        country  = StringField().triggers("region")
        country  = StringField().triggers("region", on="change")
        postal   = StringField().triggers(["city", "region"])
        eur      = IntegerField().triggers("jpy", eur_to_jpy)
        add_item = ButtonField("Add item").triggers("items", list_add)
        content  = TextAreaField().triggers("#preview", render_md, on="input delay:100ms")
        # mixed events: chain
        src = StringField().triggers("a").triggers("b", on="click")
    """
    entries = _normalize_trigger_args(target, callback, on, method_name="triggers")
    self._htmx_triggers = {**getattr(self, "_htmx_triggers", {}), **entries}
    return self


def _unbound_triggered_by(
    self,
    source: str | list[str],
    callback: TriggerCallback | None = None,
    *,
    on: str | None = None,
):
    """Declare which field events re-render this field, optionally running a callback first.

    Symmetric to :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>`:
    same shapes, same ``on`` / ``callback`` / return-value semantics.

    The wildcard ``"*"``, used as a single string (not in a list), means
    *any field of the form*: nested fields, the target itself, and
    :class:`~wtforms.fields.FieldList` rows, including rows added later.
    Inputs in the form that are not WTForms fields are not covered. The
    callback receives ``source=None``, since there is no single source
    field.

    Unlike :meth:`triggers <wtforms.fields.core.UnboundField.triggers>`,
    ``triggered_by`` does *not* accept DOM selectors: the source must be
    a real field of the form. A string that matches none emits a
    :exc:`UserWarning`, and the declaration is ignored.

    .. code-block:: python

        status = ButtonField("").triggered_by("*", autosave, on="input delay:800ms")
    """
    entries = _normalize_trigger_args(source, callback, on, method_name="triggered_by")
    self._htmx_triggered_by = {**getattr(self, "_htmx_triggered_by", {}), **entries}
    return self


UnboundField.triggers = _unbound_triggers

UnboundField.triggered_by = _unbound_triggered_by
