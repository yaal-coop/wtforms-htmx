"""Read the htmx request headers the same way on htmx 2 and htmx 4.

Both versions are normalized to element ids. ``hx-trigger-name`` is
ignored: htmx 4 has no such header.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple
from urllib.parse import unquote


class _HtmxRequestInfo(NamedTuple):
    """What an htmx request carries, whatever the htmx version."""

    htmx: bool
    boosted: bool
    source_id: str | None
    target_id: str | None
    htmx4: bool


def _element_id(identifier: str | None) -> str | None:
    """Extract the id from an htmx 4 ``tag#id`` element identifier.

    htmx 4 percent-encodes the id, so it is decoded here.
    """
    if not identifier:
        return None

    _, separator, element_id = identifier.partition("#")
    return unquote(element_id) if separator else None


def _parse_request(headers: Mapping[str, str] | None) -> _HtmxRequestInfo:
    """Normalize raw request headers, whatever the case of their names."""
    lowered = {name.lower(): value for name, value in (headers or {}).items()}
    htmx = "hx-request" in lowered
    boosted = "hx-boosted" in lowered
    # ``HX-Source`` is htmx 4 only, ``HX-Trigger`` htmx 2 only: presence picks
    # the dialect, no version flag needed.
    if (source := lowered.get("hx-source")) is not None:
        return _HtmxRequestInfo(
            htmx=htmx,
            boosted=boosted,
            source_id=_element_id(source),
            target_id=_element_id(lowered.get("hx-target")),
            htmx4=True,
        )

    return _HtmxRequestInfo(
        htmx=htmx,
        boosted=boosted,
        source_id=lowered.get("hx-trigger") or None,
        target_id=lowered.get("hx-target") or None,
        htmx4=False,
    )
