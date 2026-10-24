"""HtmxMeta: form-wide htmx settings, field binding and field rendering."""

from __future__ import annotations

import json
from typing import Any
from typing import TYPE_CHECKING

from markupsafe import Markup
from wtforms.fields.choices import SelectFieldBase
from wtforms.meta import DefaultMeta
from wtforms.widgets import Button
from wtforms.widgets import SubmitInput

from .tree import _root_of
from .tree import _state
from .tree import _walk_fields

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping


class HtmxMeta(DefaultMeta):
    """WTForms :class:`~wtforms.meta.DefaultMeta` with htmx-aware rendering defaults.

    Form-wide settings for all htmx-enhanced behaviors. Per-field behavior
    is declared on the field itself, with the
    :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` /
    :meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>`
    methods available on any field declaration.

    A sub-form, in a :class:`~wtforms.fields.FormField` or a
    :class:`~wtforms.fields.FieldList` of them, uses the ``htmx_*`` settings
    of its parent form, unless its own ``Meta`` sets them.
    """

    htmx_endpoint: str = ""
    """URL of every request the library emits. Default: the current URL."""

    htmx_method: str = "post"
    """Lowercase HTTP verb for every auto-wired request (``"post"`` by
    default → :htmx-attr:`hx-post`).

    Set to ``"get"`` / ``"put"`` / ``"patch"`` / ``"delete"`` to change
    the verb the library emits on inline validation, datalist refresh,
    :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` /
    :meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>`
    trigger declarations and submit-source buttons. The same verb is
    used everywhere. The library never mixes :htmx-attr:`hx-get` and
    :htmx-attr:`hx-post` on one element.

    The view must read the request data that matches the verb: a
    ``"get"`` form builds itself from the query string, and so must any
    callback that reads the request. See :doc:`/how-to/raw_htmx`.
    """

    field_wrapper: Callable | None = None
    """Optional ``field_wrapper(self, field, render_kw) -> str`` method
    invoked around every field whose ``wrapper=`` constructor kwarg is
    left to its default (``True``). A function without ``self`` needs
    :func:`staticmethod`. A per-field ``wrapper=`` callable takes
    ``(field, render_kw)``, without ``self``.

    It renders the markup around each field (label, input, errors)
    inside a container with an :mdn-global-attr:`id`. A field re-rendered by a mutation
    or by inline validation goes through it too. Without one, the
    ``field()`` call renders the bare widget. See :ref:`field-wrapper`.

    Per-field overrides go through the ``wrapper=`` constructor kwarg::

        name = StringField()                       # uses Meta.field_wrapper
        save = SubmitField("Save", wrapper=False)  # bare, no wrapper
        fancy = StringField(wrapper=custom_wrap)   # custom callable

    The library reads ``wrapper=`` from every field declaration, so a
    field class with its own ``wrapper`` argument does not receive it.

    A single wrapper does not fit every field family. See
    :doc:`/how-to/render_fields` for the per-family recipe.
    """

    htmx_validation_trigger: str = "blur changed"
    """Full :htmx-attr:`hx-trigger` string for inline validation (event + modifiers
    + optional ``delay:Xms``), e.g. ``"blur changed"`` (default) or
    ``"change delay:200ms"``. Selects, checkboxes, radio buttons and their
    lists always validate on ``change``. File and hidden inputs do not
    validate inline."""

    # No ``changed``: it never fires on a from:body listener on htmx 4.0.0
    # (htmx#4033, fixed by htmx#4035 and htmx#4096 but unreleased).
    htmx_default_trigger: str = "input delay:200ms"
    """Default :htmx-attr:`hx-trigger` event for
    :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` /
    :meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>`
    declarations when no ``on=`` is given."""

    htmx_swap: str = "outerHTML"
    """Default :htmx-attr:`hx-swap` for inline validation and for field
    targets of trigger declarations. Buttons and fields with a DOM
    selector target use ``outerHTML`` instead. Override either per field
    with ``render_kw``."""

    htmx_inline_validation: bool = True
    """Whether fields validate when the user leaves them.
    See :doc:`/how-to/inline_validation`."""

    htmx_submit_widgets: tuple[type, ...] = (Button, SubmitInput)
    """Tuple of widget classes recognized as submit sources.

    Extend to register custom button-emitting widgets::

        class MyForm(HtmxForm):
            class Meta:
                htmx_submit_widgets = HtmxMeta.htmx_submit_widgets + (MyButton,)

    A registered widget must render its ``value`` attribute from
    ``field._value()``, unless the template passes ``value=``. Otherwise
    the value sent with htmx differs from the one a plain submit sends.
    """

    htmx_auto_mutate: bool = True
    """Whether the form automatically calls :meth:`HtmxFormMixin.mutate` at the
    end of construction so views don't have to.

    Set to ``False`` to require explicit :meth:`form.mutate()
    <HtmxFormMixin.mutate>` calls (typically
    in tests that need to inspect pre-mutation state, or views that must
    run logic before the mutation, such as authorizing the clicked button).
    """

    @property
    def _htmx_request_attr(self) -> str:
        """The ``hx-<verb>`` attribute name derived from ``htmx_method``."""
        return f"hx-{self.htmx_method}"

    def bind_field(self, form, unbound_field, options):
        """Copy the trigger declarations and the ``wrapper=`` choice onto the bound field.

        A DataList gets its refresh attributes here, so a template that calls
        ``field.widget(...)`` keeps them.
        """
        field = super().bind_field(form, unbound_field, options)
        if triggers := getattr(unbound_field, "_htmx_triggers", None):
            field._htmx_triggers = dict(triggers)

        if triggered_by := getattr(unbound_field, "_htmx_triggered_by", None):
            field._htmx_triggered_by = dict(triggered_by)

        if hasattr(unbound_field, "_htmx_wrapper"):
            field._htmx_wrapper = unbound_field._htmx_wrapper

        self._inject_datalist_attrs(field)
        return field

    def _inject_datalist_attrs(self, field) -> None:
        """Add the refresh attributes to the field's DataList, when its choices are callable.

        The datalist sends its own request and swaps in the new ``<option>``
        children, so the input keeps focus and caret. ``render_kw`` on the
        DataList wins.
        """
        datalist = getattr(field, "_datalist", None)
        if datalist is None or isinstance(datalist, str):
            return

        if not callable(datalist._raw_choices):
            return

        rk = dict(datalist.render_kw or {})
        rk.setdefault(self._htmx_request_attr, self.htmx_endpoint)
        rk.setdefault("hx-trigger", _from_clause(_DATALIST_TRIGGER, f"#{field.id}"))
        rk.setdefault("hx-target", "this")
        rk.setdefault("hx-swap", "innerHTML")
        # Select the options, not the <datalist>, which innerHTML would nest.
        rk.setdefault("hx-select", f"#{datalist.id} > option")
        rk.setdefault("hx-include", "closest form")
        datalist.render_kw = rk

    def _compute_trigger_attrs(self, holder):
        """Build the hx-* attributes for the triggers ``holder`` listens to.

        One ``from:body target:`` clause per event group of sources, a bare
        event for a self-trigger, a selector target, or a field this one
        posts for. Return ``{}`` when there is no trigger.
        """
        attrs: dict[str, Any] = {}
        incoming = _state(holder, "_htmx_trigger_sources") or []
        selector_target = _state(holder, "_htmx_selector_target")
        outgoing = _outgoing_events(holder)
        if not incoming and selector_target is None and not outgoing:
            return attrs

        link_event = self.htmx_default_trigger
        extras = [
            _from_clause(event, f"[{_SOURCE_ATTR}~={_source_token(holder, index)}]")
            for index, (event, _names) in enumerate(_source_groups(holder, link_event))
        ]
        own_events = [
            entry.event or link_event
            for source_id, _name, entry in incoming
            if source_id == holder.id
        ]
        extras.extend(own_events)
        # One request runs every callback of this element: a second clause
        # on the same event would send a second request.
        covered = {
            _event_name(clause) for event in own_events for clause in _clauses(event)
        }
        posted = list(outgoing)
        if selector_target is not None:
            posted.extend(_clauses(selector_target[1].event or link_event))

        for event in posted:
            if (name := _event_name(event)) not in covered:
                covered.add(name)
                extras.append(event)

        # Every source posts its declaration itself: nothing to listen to.
        if not extras:
            return attrs

        attrs["hx-trigger"] = ", ".join(extras)
        # A new event aborts the request in flight, so the last response wins.
        attrs["hx-sync"] = "this:replace"

        attrs.setdefault(self._htmx_request_attr, self.htmx_endpoint)
        attrs.setdefault("hx-include", "closest form")
        if selector_target is not None:
            attrs["hx-target"] = selector_target[0]
            attrs.setdefault("hx-swap", "outerHTML")
        else:
            attrs.setdefault("hx-swap", self.htmx_swap)

        return attrs

    def render_field(self, field, render_kw):
        """Add the computed htmx attributes, then render through the field's wrapper.

        ``wrapper=True`` uses ``field_wrapper``, ``False`` the bare widget, a
        callable replaces ``field_wrapper``. The options of a choices field are
        always rendered bare.
        """
        if isinstance(field, SelectFieldBase._Option):
            merged = {**(field.render_kw or {}), **(render_kw or {})}
            self._inject_submit_vals(field, merged)
            return Markup(field.widget(field, **merged))

        # Precedence: library attrs < field render_kw < call-site render_kw.
        lib_attrs = self._compute_trigger_attrs(field)
        if tokens := _source_tokens(field):
            lib_attrs[_SOURCE_ATTR] = " ".join(tokens)

        merged = {**lib_attrs, **(field.render_kw or {}), **(render_kw or {})}
        self._inject_submit_vals(field, merged)

        wrapper = _state(field, "_htmx_wrapper", True)
        if wrapper is False:
            return Markup(field.widget(field, **merged))

        if callable(wrapper):
            return Markup(wrapper(field, merged))

        if self.field_wrapper is not None:
            return Markup(self.field_wrapper(field, merged))

        return Markup(field.widget(field, **merged))

    def _inject_submit_vals(self, field, merged) -> None:
        """Re-send a submit control's own ``name``/``value`` pair as ``hx-vals``.

        Workaround for htmx#4073. The value matches what the widget renders,
        so htmx and a plain submit send the same pair. An explicit ``hx-vals``
        is left alone.
        """
        # htmx 4 drops the pair of a submit control with its own request attribute
        # (htmx#4073, fixed but unreleased). Remove once a release has the fix.
        if not isinstance(field.widget, self.htmx_submit_widgets):
            return

        if self._htmx_request_attr not in merged:
            return

        if "hx-vals" in merged:
            return

        merged["hx-vals"] = json.dumps(
            {field.name: _rendered_submit_value(field, merged)}
        )


def _rendered_submit_value(field: Any, merged: Mapping[str, Any]) -> str:
    """Return the ``value`` attribute a submit widget renders for ``field``.

    Workaround for htmx#4073. A call-time ``value=`` wins, ``SubmitInput``
    renders the label, other widgets render ``field._value()``.
    """
    if "value" in merged:
        return str(merged["value"])

    if isinstance(field.widget, SubmitInput):
        return str(field.label.text)

    return str(field._value())


# No ``changed``: see ``HtmxMeta.htmx_default_trigger``.
_DATALIST_TRIGGER = "input delay:200ms"

# An attribute selector keeps the target: value free of spaces, which have
# no syntax that both htmx 2 and htmx 4 parse (htmx#4010).
_SOURCE_ATTR = "data-wtforms-htmx-for"


_TYPING_EVENTS = frozenset({"input", "keyup", "keydown", "keypress"})


def _clauses(event: str) -> list[str]:
    """Split an ``hx-trigger`` value into its comma-separated clauses.

    A comma inside an event filter, between ``[`` and ``]``, does not split.
    """
    clauses: list[str] = []
    depth = start = 0
    for index, char in enumerate(event):
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        elif char == "," and depth == 0:
            clauses.append(event[start:index])
            start = index + 1

    clauses.append(event[start:])
    return [clause.strip() for clause in clauses if clause.strip()]


def _event_name(event: str) -> str:
    """Return the bare event name of an ``hx-trigger`` clause, ``blur`` as ``focusout``."""
    return _bubbling(event).split(" ", 1)[0].split("[", 1)[0]


def _is_source_posted(source_name: str, entry: Any) -> bool:
    """Tell whether the source sends the request of a declaration itself.

    It does for any event but typing and polling. The target listens for
    those, so a request is sent while the user types in the source. A
    declaration with several events is listened to as soon as one of them
    is typing or polling. The
    server cannot tell which event sent a request (htmx#4161), so a source
    cannot both validate on blur and post its typing.
    """
    if source_name == "*" or entry.event is None:
        return False

    names = {_event_name(clause) for clause in _clauses(entry.event)}
    return not names & _TYPING_EVENTS and "every" not in names


def _outgoing_events(holder: Any) -> list[str]:
    """Return the events on which ``holder`` posts for the fields it feeds."""
    events: list[str] = []
    for listener in _walk_fields(_root_of(holder._form)):
        for source_id, source_name, entry in (
            _state(listener, "_htmx_trigger_sources") or []
        ):
            if source_id == listener.id or source_name != holder.name:
                continue

            if not _is_source_posted(source_name, entry):
                continue

            events.extend(c for c in _clauses(entry.event) if c not in events)

    return events


def _source_groups(holder: Any, default_event: str) -> list[tuple[str, list[str]]]:
    """Group the fields ``holder`` listens to by event.

    Return ``(event, [source_name, ...])`` pairs in declaration order,
    without self-triggers and the declarations a source posts itself. ``"*"`` stands for every field. One clause per
    group, because htmx 2 only fires the first ``target:`` clause of an
    event (htmx#4155).
    """
    groups: dict[str, list[str]] = {}
    for source_id, source_name, entry in _state(holder, "_htmx_trigger_sources") or []:
        if source_id == holder.id or _is_source_posted(source_name, entry):
            continue

        for clause in _clauses(entry.event or default_event):
            groups.setdefault(_bubbling(clause), []).append(source_name)

    return list(groups.items())


def _source_token(holder: Any, index: int) -> str:
    """Return the marker a source carries for ``holder``'s ``index``-th event group."""
    return holder.id if index == 0 else f"{holder.id}--{index}"


def _source_tokens(field: Any) -> list[str]:
    """Return the markers of every element listening to ``field``.

    A source matches by its name, or as a descendant of a container
    source, so FieldList rows added later match too.
    """
    name = field.name
    tokens = []
    for listener in _walk_fields(_root_of(field._form)):
        if not _state(listener, "_htmx_trigger_sources"):
            continue

        # A field of a plain WTForms sub-form has no htmx meta and listens to nothing.
        default = getattr(listener.meta, "htmx_default_trigger", None)
        if default is None:
            continue

        for index, (_event, names) in enumerate(_source_groups(listener, default)):
            if any(
                source == "*" or name == source or name.startswith(f"{source}-")
                for source in names
            ):
                tokens.append(_source_token(listener, index))

    return tokens


# Events that do not bubble, mapped to their bubbling equivalents.
_BUBBLING_EVENTS = {"blur": "focusout", "focus": "focusin"}


def _bubbling(event: str) -> str:
    """Replace a non-bubbling event at the start of ``event`` with its bubbling equivalent."""
    name, sep, rest = event.partition(" ")
    bare = name.split("[", 1)[0]
    if bare in _BUBBLING_EVENTS:
        name = _BUBBLING_EVENTS[bare] + name[len(bare) :]

    return f"{name}{sep}{rest}"


def _from_clause(event: str, target: str) -> str:
    """Return an ``hx-trigger`` clause for ``event`` fired on ``target``.

    htmx resolves ``from:`` once, so ``from:#id`` breaks when the source is
    swapped. Listening on ``body`` and filtering on the target does not.
    """
    return f"{_bubbling(event)} from:body target:{target}"
