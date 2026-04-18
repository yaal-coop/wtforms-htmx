Core API
========

The core of wtforms-htmx is framework-agnostic: subclass
:class:`~wtforms_htmx.HtmxForm`, or mix
:class:`~wtforms_htmx.HtmxFormMixin` into your own form, and tune
rendering through its :class:`~wtforms_htmx.HtmxMeta`. The form's
:meth:`~wtforms_htmx.HtmxFormMixin.partial` method builds the
:class:`~wtforms_htmx.HtmxResponse` you return from your view.
See :doc:`overview` to wire it in.

.. module:: wtforms_htmx

.. autoclass:: HtmxForm

.. autoclass:: HtmxFormMixin
    :members:
    :exclude-members: post_process

.. autoclass:: HtmxMeta
    :members:
    :exclude-members: bind_field, render_field

.. autoclass:: HtmxResponse
    :members:

.. _attribute-precedence:

Attribute precedence
--------------------

Every field merges its htmx attributes in increasing order of
priority:

1. **Library-computed**: the ``hx-*`` attributes wtforms-htmx derives
   from the form's :class:`HtmxMeta`: the auto-wired features (inline
   validation, datalist refresh, submit buttons) and the field's
   trigger declarations
   (:meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` /
   :meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>`).
2. **Field** ``render_kw``: keys set on the field declaration
   (``StringField(render_kw={...})``) override the computed ones.
3. **Call-site** ``render_kw``: keys passed when rendering
   (``form.field(**{...})``) override both.

The rule applies to every field type: inline-validation input, trigger
source, field with a selector target, submit button,
:class:`~wtforms.fields.FieldList`. Any key the library does not
compute is passed through verbatim to
:func:`~wtforms.widgets.html_params`, so arbitrary htmx (or HTML)
attributes are available at every layer. See :doc:`/how-to/raw_htmx`.

.. _trigger-declarations:

Trigger declarations
--------------------

:meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` and :meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>` are available on any field
declaration. Each call adds to the field's trigger declarations and
returns the same field, so calls chain. A call on its own line, after
the field is declared, works too: ``query.triggers("results")``.

.. _trigger-sources:

A source field must be rendered by the library: through a ``field()``
call or the field wrapper, with ``wrapper=False`` if you need the bare
input. The library adds a ``data-wtforms-htmx-for`` attribute to it,
and the listening field waits for events from elements that carry it.
A direct ``field.widget(...)`` call in a page template skips that
attribute, so the source triggers nothing.

On htmx 4.0.0, an ``on=`` event with the :htmx-attr:`hx-trigger`
``changed`` modifier never fires when the source is another field. The
default event, ``input delay:200ms``, does not use it.

.. automethod:: wtforms.fields.core.UnboundField.triggers

.. automethod:: wtforms.fields.core.UnboundField.triggered_by

See :doc:`mutations` for the built-in callbacks. To
write your own callback, see :ref:`anatomy-of-a-callback`. For the
conceptual model and the dispatch path, see :doc:`/explanation/mutations`.

.. _callback-return:

Callback return values
~~~~~~~~~~~~~~~~~~~~~~~~

A callback's return value drives the response body. The contract is the
same across field targets (``target`` matched a field) and selector
targets (it did not):

.. list-table::
    :header-rows: 1
    :widths: 14 36 30 20

    * - ``target``
      - ``result``
      - Primary swap
      - OOB extras
    * - field
      - ``None``
      - field render, wrapper included (default)
      - —
    * - field
      - ``str``
      - the returned HTML
      - —
    * - field
      - ``Field``
      - that field's render, wrapper included
      - —
    * - field
      - iterable
      - ``items[0]`` (``None`` = default, ``str`` / ``Field`` = override)
      - ``items[1:]``
    * - selector
      - ``None``
      - none; response header :htmx-header:`hx-reswap` set to ``none``
      - —
    * - selector
      - ``str``
      - the returned HTML
      - —
    * - selector
      - ``Field``
      - that field's render, wrapper included
      - —
    * - selector
      - iterable
      - ``items[0]`` (``None`` = no primary, ``str`` / ``Field`` = override)
      - ``items[1:]``

With several field targets, a ``str`` or ``Field`` override replaces the
first target. The other targets still re-render out of band.

htmx swaps each out-of-band extra into the element with the same
:mdn-global-attr:`id` (:htmx-attr:`hx-swap-oob`). A
:class:`~wtforms.fields.Field` is rendered through its wrapper. An HTML ``str`` must be one element with
an :mdn-global-attr:`id`. The library adds ``hx-swap-oob="outerHTML"`` to both, unless
the ``str`` already sets :htmx-attr:`hx-swap-oob`.

.. _dom-targets:

DOM targets: selectors instead of field names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When ``target`` matches no field, it is a **DOM selector**, passed
verbatim to :htmx-attr:`hx-target`, and the callback supplies the
returned HTML. A field name or a ``"#id"`` matching a field is a field
target instead (see the
:meth:`triggers <wtforms.fields.core.UnboundField.triggers>` ``target``
parameter and :ref:`cross-form-targets`). Selectors look like ``".result"``,
``"closest .toast"``, ``"this"``, ``"next"``, or an ``"#id"`` that
matches no field. See :doc:`/examples/markdown_preview` for a worked
example.
