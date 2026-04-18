"""The ``wrapper=`` argument of every field declaration."""

from __future__ import annotations

from wtforms.fields.core import UnboundField

_UNSET = object()

_original_unbound_init = UnboundField.__init__


def _patched_unbound_init(self, field_class, *args, **kwargs):
    """Take the ``wrapper=`` kwarg off before WTForms sees it.

    It is stored on the unbound field, and ``bind_field`` copies it to the
    bound field.
    """
    wrapper = kwargs.pop("wrapper", _UNSET)
    _original_unbound_init(self, field_class, *args, **kwargs)
    if wrapper is not _UNSET:
        self._htmx_wrapper = wrapper


UnboundField.__init__ = _patched_unbound_init
