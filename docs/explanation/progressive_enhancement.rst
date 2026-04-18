Progressive enhancement
=======================

wtforms-htmx is designed so forms work **without JavaScript** by
default. htmx adds partial rendering on top. Without it, every button
and every submit still works. What is lost is the live behavior.

Whether an interaction works without JavaScript depends on its
**trigger source**: a button click becomes a full-page POST, and typing
triggers nothing. See :ref:`dispatch-path` for both paths side by side.

What works without JS
---------------------

**Inline validation** (see :attr:`Meta.htmx_inline_validation <wtforms_htmx.HtmxMeta.htmx_inline_validation>`)
    Without htmx, the request attribute (:htmx-attr:`hx-post` by
    default) is ignored. The
    form behaves like a standard WTForms form: the user fills fields
    and submits. Validation runs on submit.

**Button-driven mutations** (``ButtonField().triggers(target, callback)``)
    A mutation button is a plain submit button. Without htmx, a click
    submits the whole form, and the form runs the same callback while it
    is built. Only the response differs: the full page instead of a
    fragment.

**Combobox** (see :doc:`/examples/combobox`)
    The combobox is built from plain WTForms fields and renders its
    suggestion list server-side. Without htmx, typing in the search
    input and pressing :kbd:`Enter` activates the ``Search`` button, which
    reloads the page with the matching suggestions. Clicking a
    suggestion submits the form, and the server adds the value and
    re-renders the page. The result is the same, through a full-page
    reload instead of a partial swap.

What degrades without JS
------------------------

**Mutations triggered by typing**
    A mutation whose source is a field the user types in never runs
    without htmx. A submit does not run it either. Pair it with a
    button that triggers the same callback, as the
    :doc:`/examples/currency` does, or call the callback in the view.

**Datalist refresh**
    The :mdn-tag:`datalist` keeps the options computed when the page
    was rendered. A submit recomputes them.

**Inline validation**
    Errors show after a submit, not when the user leaves a field.

The :doc:`/examples/combobox` provides no arrow-key navigation in its
listbox, with or without JavaScript. :kbd:`Tab` moves focus between
suggestion buttons and :kbd:`Enter` activates the focused one.

Why it matters
--------------

- Accessibility: screen readers and keyboard-only users benefit
  from the native elements remaining functional.
- First paint and slow networks: the initial page is usable
  immediately, htmx enhances later.
- Bot-friendly: crawlers or scrapers can submit forms without
  running JS.
- Debuggability: the server-side rendering is the source of
  truth. htmx only changes how much of the page is swapped.
