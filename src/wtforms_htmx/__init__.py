"""htmx integration for WTForms."""

from __future__ import annotations

from . import wrapper  # noqa: F401  (registers the wrapper= field argument)
from .form import HtmxForm
from .form import HtmxFormMixin
from .meta import HtmxMeta
from .partial import HtmxResponse
from .triggers import TriggerCallback

__all__ = [
    "HtmxForm",
    "HtmxFormMixin",
    "HtmxMeta",
    "HtmxResponse",
    "TriggerCallback",
]
