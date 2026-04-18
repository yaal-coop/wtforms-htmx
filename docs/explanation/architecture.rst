Architecture
============

wtforms-htmx is one framework-agnostic core: it extends a
:class:`~wtforms.form.Form` with htmx wiring (request routing, htmx
attribute computation, and partial request dispatching),
ships no JavaScript (htmx does the swaps), and depends on nothing beyond
WTForms.

This page maps the internals: the wiring mechanisms, the library's
reach, and the design decisions behind them. To
*use* raw htmx rather than understand how the library wires it, see
:doc:`/how-to/raw_htmx`.

Where the wiring comes from
---------------------------

wtforms-htmx wires htmx onto fields through channels, organized by who
installs the wiring:

**Auto-wired by the Meta** (no per-field declaration)
   :class:`~wtforms_htmx.HtmxMeta` wires inline validation and datalist
   refresh. See :ref:`auto-wired-mutations`.

**Declared by the form author** (*trigger declarations*)
   :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` and
   its inverse
   :meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>`
   declare a *mutation*: an event on one field re-renders one or more
   other elements, optionally running a state-change callback first. See
   :doc:`mutations` for trigger declarations in depth.

**Written by the application** (raw htmx)
   Everything the library does not formalize: custom polling,
   confirmations, loading indicators. Detailed next.

Where the library stops
-----------------------

wtforms-htmx adds its ``hx-*`` attributes to each field as defaults.
Anything it does not compute is passed through untouched. Raw htmx needs
no dedicated support: it goes through the same WTForms ``render_kw`` and
:func:`~wtforms.widgets.html_params` as any other attribute. The
library's reach stops there:

- it writes **field attributes** only, and only as defaults, so
  ``render_kw`` on the declaration or call site overrides any of them
  (:ref:`precedence <attribute-precedence>`);
- it never renders the :mdn-tag:`form` tag, so **form-level attributes**
  (:htmx-attr:`hx-boost`, :htmx-attr:`hx-ext`, …) are entirely outside
  it;
- on the response it sets only :htmx-header:`hx-retarget` /
  :htmx-header:`hx-reswap`, leaving every other htmx header for the view
  to merge.

Where and how to write each is collected in the :doc:`/how-to/raw_htmx`
guide.

Why POST by default
-------------------

Every auto-wired request re-encodes the **whole form**
(:htmx-attr:`hx-include` ``="closest form"``) so the server rebuilds the
complete field state on each interaction. ``POST`` suits that
"resend everything" model. A ``GET`` would push the entire form into
the query string. The verb is configurable through
:attr:`~wtforms_htmx.HtmxMeta.htmx_method`, but the core stays
verb-agnostic on the *receiving* side: it routes by the clicked
button's posted name, or by the source element id
(:htmx-header:`hx-source` on htmx 4, :htmx-header:`hx-trigger` on
htmx 2), never by HTTP method. Switching the verb
only changes the emitted attribute. The view is then responsible for
reading the matching request data (the query string for ``get``).

Trigger declarations
--------------------

:meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>`
resolves ``target`` against the form's fields first: a field name, a
dotted path into a sub-form, or a ``"#id"`` that matches a field's id.
Any other string goes verbatim to :htmx-attr:`hx-target` as an htmx
selector, such as ``"#preview"`` or ``"closest .toast"`` (see
:ref:`dom-targets`).
See :ref:`callback-return` for what a callback may return and
:ref:`anatomy-of-a-callback` for the callback contract.

htmx 2 and htmx 4
-----------------

The library works on both versions. These points shape how:

- **Submit buttons with their own request.** htmx 4.0.0 does not send
  the :mdn-attr:`button#name` and :mdn-attr:`button#value` of a button that has its own
  :htmx-attr:`hx-post` inside a :mdn-tag:`form` (htmx #4073). The
  library adds them back with :htmx-attr:`hx-vals`.
- **Listening to another field.** Both versions resolve a ``from:``
  selector once, so ``from:#<id>`` stops firing when the
  source element is swapped. The library listens on ``body`` instead,
  with a ``target:`` filter on a ``data-wtforms-htmx-for`` attribute
  that it adds to each source. One clause per listening element and
  event avoids an htmx 2 bug where only the first ``target:`` clause of
  a given event fires (htmx #4155). The filter has no space: htmx 4
  needs a quoted value with a space (htmx #4010), which htmx 2 rejects.
  ``blur`` and ``focus`` do not bubble up to ``body``, so the library
  listens to ``focusout`` and ``focusin`` instead.
- **No** ``changed`` **on listeners.** On htmx 4.0.0, ``changed`` never
  fires on a ``from:body`` listener (htmx #4033). The default event is
  ``input delay:200ms``.
- **Focused input inside the swapped content.** On htmx 4.0.0, a swap
  empties an input that has the focus and sits inside the swapped
  content, such as a filter that re-renders its own list (htmx #4056).
  Set ``htmx.config.defaultSettleDelay`` to ``0`` to avoid it, as the
  examples do.
- **No** :htmx-header:`hx-trigger-name`. htmx 4 does not send this
  header, so the library ignores it on htmx 2 too. Routing behaves the
  same on both versions.
