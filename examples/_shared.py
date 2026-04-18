"""Shared building blocks for the example feature modules."""

from __future__ import annotations

from copy import deepcopy

import pycountry
from flask import current_app
from flask import render_template
from flask import request
from wtforms import Form
from wtforms.fields import ButtonField
from wtforms.fields import SubmitField

from wtforms_htmx import HtmxFormMixin
from wtforms_htmx import HtmxMeta

#: One dataclass per example, registered at import time.
#: ``reset_state()`` restores the copies kept in ``_INITIAL_STATE``.
_STATE: dict = {}
_INITIAL_STATE: dict = {}


def reset_state():
    """Restore the example state to its seeded values."""
    _STATE.clear()
    _STATE.update(deepcopy(_INITIAL_STATE))


def jinja_widget(template, macro):
    """Return a wtforms-compatible widget that invokes a Jinja macro.

    Extra keyword arguments reach the macro only if its body uses
    ``kwargs`` or declares them; others are dropped.
    """

    def _widget(field, **kwargs):
        module = current_app.jinja_env.get_template(template).module
        macro_obj = getattr(module, macro)
        if not macro_obj.catch_kwargs:
            named = set(macro_obj.arguments)
            kwargs = {k: v for k, v in kwargs.items() if k in named}

        return macro_obj(field, **kwargs)

    return _widget


class ExampleForm(HtmxFormMixin, Form):
    """Base form for the examples, composing the mixin with wtforms Form."""

    def populate_obj(self, obj):
        # Button data is ``True`` after a click and must not reach the state.
        for name, field in self._fields.items():
            if isinstance(field, (SubmitField, ButtonField)):
                continue

            field.populate_obj(obj, name)

    class Meta(HtmxMeta):
        def field_wrapper(self, field, render_kw):
            """Wrap a field, delegating all routing to ``_field.html``."""
            return render_template("_field.html", field=field, render_kw=render_kw)

        @property
        def htmx_endpoint(self):
            # Without a hash, so htmx does not scroll to an ``#anchor`` after a swap.
            return request.path


COUNTRY_NAMES = sorted(c.name for c in pycountry.countries)

COUNTRY_BY_CODE = sorted(
    ((c.alpha_2, c.name) for c in pycountry.countries),
    key=lambda pair: pair[1],
)
NAME_BY_CODE = dict(COUNTRY_BY_CODE)
