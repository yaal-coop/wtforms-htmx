Swap strategies
===============

wtforms-htmx swaps the element an interaction affects: a field's
widget, a user-defined wrapper, or a
:class:`~wtforms.fields.FieldList` container. When that element is not
the one htmx targeted, the response carries
:htmx-header:`hx-retarget`. Each strategy tries to keep the user's
focus and caret.

This page explains why an input being typed in is never swapped, how
the retarget works for inline validation, how out-of-band swaps update
several elements at once, and what these strategies do not solve.

The htmx caveat on text inputs
------------------------------

From htmx's documentation on :htmx-attr:`hx-preserve`:

    Some elements cannot unfortunately be preserved properly, such as
    :mdn-tag:`input` ``type="text"`` (focus and caret position are
    lost), [...]

This applies to **any** swap that replaces a focused input element,
even with :htmx-attr:`hx-preserve`. The only reliable way to keep
focus and caret intact is to **not touch the input element at all**.

Which elements get swapped
--------------------------

- **Datalist suggestions** refresh as the user types, while the caret is
  still *in* the input, so the input must never be swapped. The
  trigger is wired on the :mdn-tag:`datalist` element instead
  (``hx-trigger="… from:body target:#<input-id>"``), replacing only its
  :mdn-tag:`option` set: the caret stays put and the user agent keeps
  drawing its native popup. See :doc:`/how-to/datalist`.
- **Inline validation** fires on ``blur``, once the user has left the
  input. There is no caret to preserve, so swapping the input or its
  wrapper is fine (see below).

Inline validation: retarget, not wrapper convention
---------------------------------------------------

wtforms-htmx inspects the rendered partial and reads the :mdn-global-attr:`id`
attribute of its outermost tag. It compares that id with the
request's :htmx-header:`hx-target` header, the id of the element htmx
is about to swap. If they differ, an :htmx-header:`hx-retarget`
response header is emitted:

- Vanilla rendering: the response is a bare ``<input id="email">``.
  No retarget is sent. htmx's native target (the triggering input)
  matches the response's outer id. The input is swapped in place.
- Wrapped rendering: the response is
  ``<div id="wrap-email">label + input + errors</div>``. The
  library sends ``HX-Retarget: #wrap-email``. htmx swaps the
  whole wrapper atomically, including error display updates.

The library imposes no id convention on the wrapper. Choose ids that
fit your CSS framework.

.. _out-of-band-swaps:

Out-of-band swaps
-----------------

Some interactions must re-synchronize more than the one element the
trigger points at: a chip list plus the search box that fed it, a
per-row total plus an invoice grand total (:doc:`/examples/invoice`),
a value plus a counter elsewhere on the page. htmx's
:htmx-attr:`hx-swap-oob` covers this: the response carries extra
fragments, each routed to its own :mdn-global-attr:`id` rather than into
:htmx-attr:`hx-target`. One request can then update several
non-contiguous zones without re-rendering the whole page. These zones
can be plain DOM elements that are **not** form fields, such as an
:mdn-tag:`output` or a status pill.

wtforms-htmx exposes this two ways: a multi-target declaration on a
button, ``.triggers([target1, target2], ...)``, and a callback
returning an iterable. In both, the first target is the primary swap
and the others are out-of-band. When a button also has a selector
target and its callback returns HTML, that HTML is the primary swap and
every field target is out-of-band. A field source declared on a
typing event fires one request per target instead: each target sends
its own. On another event, such as ``change``, the source sends one
request for all its targets. When the source validates inline, it is
the primary swap and every target is out-of-band. Otherwise, the first
target is the primary swap. A source has at most one selector target. See :ref:`callback-return` for the return types and
:doc:`/how-to/mutations` for recipes.

When nothing provides a primary swap, the library sends
:htmx-header:`hx-reswap` ``= none`` so htmx leaves the targeted element
untouched and applies only the OOB extras. This happens when a selector
target's callback returns ``None``, or an iterable that starts with
``None``, and the request re-renders no field. That is a full-OOB response, without the user having to know
the header exists.

One response can collect the same extra several times. A field that
listens to several sources runs the callback of each source: an invoice
row's total runs the same callback for its quantity, unit price and VAT
rate, and each call returns the invoice summary. The library sends each
extra once. It matches fields by identity and HTML fragments by their
outer :mdn-global-attr:`id`.

What this does not solve
------------------------

The swap updates the DOM of one page. It does not keep several tabs or
pages consistent.
