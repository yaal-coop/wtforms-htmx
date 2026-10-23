"""Build the partial response of a form, as an ``HtmxResponse``."""

from __future__ import annotations

from collections.abc import Mapping
from copy import copy
from dataclasses import dataclass
from dataclasses import field
from html.parser import HTMLParser
from typing import Any
from typing import TYPE_CHECKING

from markupsafe import Markup
from wtforms.fields import Field

from .headers import _HtmxRequestInfo
from .headers import _parse_request

if TYPE_CHECKING:
    from .form import HtmxFormMixin


@dataclass(frozen=True, slots=True)
class HtmxResponse:
    """An htmx partial response.

    Pairs the body to return with any htmx response headers the
    library computed for it.
    """

    body: str
    """The rendered HTML fragment to send back to the client."""

    headers: Mapping[str, str] = field(default_factory=dict)
    """htmx response headers the library computed for this response.

    The library sets :htmx-header:`hx-retarget` (when the fragment's
    outer element is not the element htmx targeted) and
    :htmx-header:`hx-reswap` (``none`` when a selector target's callback
    returns no body). Add any other htmx response header yourself
    (:htmx-header:`hx-trigger` to fire a client event,
    :htmx-header:`hx-redirect`, :htmx-header:`hx-refresh`,
    :htmx-header:`hx-push-url`, :htmx-header:`hx-reselect`, …) by merging
    it into a new dict when you build the framework response::

        if result := form.partial():
            return Response(
                result.body,
                headers={**result.headers, "HX-Trigger": "saved"},
            )

    The mapping may be read-only, so do not assign into it.
    """


@dataclass(slots=True)
class _HtmxMutation:
    """Render plan of one request: the targets to swap, a primary override, OOB extras.

    Dispatch records the targets and the callback results. The plan applies
    the callback return-value contract (see the API reference).
    """

    targets: list[Any] = field(default_factory=list)
    primary_override: Markup | None = None
    primary_field: Any = None
    oob_extras: list[Any] = field(default_factory=list)
    selector_dispatched: bool = False

    @property
    def dispatched(self) -> bool:
        """Whether a trigger fired and left something to render."""
        return bool(
            self.targets
            or self.primary_override is not None
            or self.primary_field is not None
            or self.selector_dispatched
        )

    def add_result(self, result: Any) -> None:
        """Record a callback's return value.

        Check for a Field before an iterable: SelectFieldBase and FieldList are
        iterable too.
        """
        if result is None:
            return

        if isinstance(result, Field):
            self.primary_field = result
            return

        if isinstance(result, (str, Markup)):
            self.primary_override = Markup(result)
            return

        items = list(result)
        if not items:
            return

        primary, *rest = items
        if isinstance(primary, (str, Markup)):
            self.primary_override = Markup(primary)
        elif isinstance(primary, Field):
            self.primary_field = primary

        # primary is None → default render kept (no override set).
        self.oob_extras.extend(rest)

    def split_targets(self) -> tuple[Any, list[Any]]:
        """Return the primary field, if any, and the targets rendered out-of-band.

        A callback override replaces ``targets[0]``, unless a selector was
        dispatched: then every target is out-of-band.
        """
        if self.primary_override is None and self.primary_field is None:
            return (self.targets[0] if self.targets else None), self.targets[1:]

        rest = self.targets if self.selector_dispatched else self.targets[1:]
        return self.primary_field, [t for t in rest if t is not self.primary_field]


class _OuterTagParser(HTMLParser):
    """Locate the first opening tag of a fragment.

    ``tag`` stays ``None`` when the fragment has no tag. ``end`` is the
    offset just past the tag's ``>``.
    """

    def __init__(self, html: str) -> None:
        super().__init__()
        self.tag: str | None = None
        self.attrs: dict[str, str | None] = {}
        self.end = 0
        # getpos() counts lines on "\n" only, unlike str.splitlines().
        self._lines = html.split("\n")
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.tag is not None:
            return

        self.tag = tag
        self.attrs = dict(attrs)
        lineno, col = self.getpos()
        start = sum(len(line) + 1 for line in self._lines[: lineno - 1]) + col
        self.end = start + len(self.get_starttag_text() or "")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _extract_outer_id(html: str) -> str | None:
    """Return the ``id`` of the first opening tag in ``html``, if any."""
    return _OuterTagParser(html).attrs.get("id") or None


def _with_swap_oob(html: str) -> str:
    """Add ``hx-swap-oob="outerHTML"`` to the outer element of an OOB fragment.

    Left untouched: a fragment that already sets ``hx-swap-oob``, and a
    <template> wrapper. Raise ValueError when the outer element has no id.
    """
    outer = _OuterTagParser(html)
    if outer.tag is None or outer.tag == "template":
        return html

    if "hx-swap-oob" in outer.attrs or "data-hx-swap-oob" in outer.attrs:
        return html

    if not outer.attrs.get("id"):
        raise ValueError(
            f"An out-of-band HTML fragment needs an id on its outer element: {html!r}"
        )

    head = html[: outer.end]
    close = "/>" if head.endswith("/>") else ">"
    head = head[: -len(close)].rstrip()
    return f'{head} hx-swap-oob="outerHTML"{close}{html[outer.end :]}'


def _render_mutation_target(field: Any, *, oob: bool) -> str:
    """Render one field for a partial response, through its wrapper.

    An out-of-band field gets ``hx-swap-oob`` on the outer element of its
    rendering, so the whole wrapper is swapped. A ``hide_value`` widget
    (PasswordInput) shows the typed value during this render, so the swap
    does not erase it.
    """
    html = _render_revealed(field)
    return _with_swap_oob(html) if oob else html


def _render_revealed(field: Any) -> str:
    """Render ``field``, with the value of a ``hide_value`` widget shown."""
    widget = getattr(field, "widget", None)
    if not (getattr(widget, "hide_value", False) and field.data):
        return str(field.meta.render_field(field, {}))

    # The widget is shared by every field of the class: reveal a copy.
    field.widget = copy(widget)
    field.widget.hide_value = False
    try:
        return str(field.meta.render_field(field, {}))
    finally:
        field.widget = widget


def _render_oob(form: HtmxFormMixin, extras: list[Any]) -> Markup:
    """Render out-of-band extras, each once.

    Fields are deduplicated by identity, HTML fragments by outer id.
    """
    html = Markup("")
    seen: set[Any] = set()
    for extra in extras:
        is_html = isinstance(extra, (str, Markup))
        key = _extract_outer_id(str(extra)) if is_html else id(extra)
        if key is not None and key in seen:
            continue

        seen.add(key)
        if is_html:
            html += Markup(_with_swap_oob(str(extra)))
        else:
            html += Markup(_render_mutation_target(extra, oob=True))

    return html


def _render_mutation_response(
    form: HtmxFormMixin,
    mutation: _HtmxMutation,
    request: _HtmxRequestInfo,
) -> HtmxResponse:
    """Build the response for a dispatched mutation.

    The primary swap is, in order: the callback's HTML, the callback's field,
    the first target. The other targets and the callback's extras are
    out-of-band. Without a primary swap, the body only holds the extras, with
    ``HX-Reswap: none`` and no ``HX-Retarget``.
    """
    response_headers: dict[str, str] = {}
    primary_field, rest = mutation.split_targets()
    # Keep the body a Markup: ``Markup.__radd__`` escapes a plain ``str``.
    if mutation.primary_override is not None:
        body = mutation.primary_override
    elif primary_field is not None:
        body = Markup(_render_mutation_target(primary_field, oob=False))
    else:
        oob = _render_oob(form, rest + mutation.oob_extras)
        return HtmxResponse(body=str(oob), headers={"HX-Reswap": "none"})

    body += _render_oob(form, rest + mutation.oob_extras)
    if retarget := _compute_retarget(str(body), request):
        response_headers["HX-Retarget"] = retarget

    return HtmxResponse(body=str(body), headers=response_headers)


def _compute_partial(
    form: HtmxFormMixin,
    headers: Mapping[str, str] | None,
) -> HtmxResponse | None:
    """Render the mutation plan, or a datalist refresh.

    Return ``None`` for a non-htmx or boosted request, or when there is
    nothing to render.
    """
    request = _parse_request(headers)
    if not request.htmx or request.boosted:
        return None

    mutation = getattr(form, "_htmx_mutation", None)
    if mutation is not None and mutation.dispatched:
        return _render_mutation_response(form, mutation, request)

    return _compute_datalist_partial(form, request)


def _compute_datalist_partial(
    form: HtmxFormMixin,
    request: _HtmxRequestInfo,
) -> HtmxResponse | None:
    """Render the datalist that sent the request, alone.

    Its ``hx-select`` picks the ``<option>`` children. No validation runs.
    """
    field = form._htmx_resolve_datalist(request.source_id)
    if field is None:
        return None

    return HtmxResponse(body=str(field.datalist()), headers={})


def _compute_retarget(body: str, request: _HtmxRequestInfo) -> str | None:
    """Return an ``hx-retarget`` selector for the fragment's outer id.

    ``None`` when the fragment has no outer id, or when htmx already
    targets that element.
    """
    if not (outer_id := _extract_outer_id(body)):
        return None

    if request.target_id == outer_id:
        return None

    return f"#{outer_id}"
