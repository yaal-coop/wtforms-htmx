Mutations
=========

A *mutation* is an element re-rendered in reaction to an event. The
displayed form changes as the user types, picks, or clicks. This page
explains how you declare a mutation, what a callback receives and
returns, how a request flows from the view to the response, and which
mutations the library wires for you.

You produce a mutation with a *trigger declaration*. An event on one
field re-renders another element. Declare it from either side, with
:meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` on the
source ("events on me re-render that") or
:meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>`
on the target ("I re-render when that changes"). The source can be a
button or a field the user types in::

    ButtonField("Add tag").triggers("tags", value_add)
    StringField().triggers("slug", derive_slug)

A bare declaration with no callback already produces a mutation: a
field target is redrawn from the form's current state. This covers cases such
as a :class:`~wtforms.fields.SelectField` whose ``choices`` callable
depends on a sibling, or a widget whose markup branches on another
field's value.

A trigger declaration can also carry a *callback*, a function run
server-side just before the re-render.

.. _anatomy-of-a-callback:

Anatomy of a callback
---------------------

The shipped callbacks live in :mod:`wtforms_htmx.mutations`. You can
also write your own. Any function with this signature works::

    def my_callback(form, source, target) -> result:
        ...

- ``form``: the bound form instance. Reach for sibling fields when
  the mutation spans more than one (e.g. clear a search input when
  a chip is added).
- ``source``: the field that fired the trigger (the field carrying
  the :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` declaration, or the field referenced by
  :meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>`). ``None`` for the
  ``triggered_by("*")`` wildcard.
- ``target``: either the **resolved target field** (when the target
  matched a field) or the raw **selector string** (the DOM-target
  case).

A callback's **side effects** on ``form`` and ``target`` change form
state (typically ``target.data``), which the re-render then reflects.
Its **return value** drives how that re-render is produced. The two
are independent: a callback may change state, shape the render, or
both. The common pattern changes ``target.data`` and returns ``None``,
which keeps the default render. A string or a field replaces that
render, and an iterable adds :ref:`out-of-band <out-of-band-swaps>`
swaps. See :ref:`callback-return` for every case.

.. _dispatch-path:

The dispatch path
-----------------

:meth:`~wtforms_htmx.HtmxFormMixin.mutate` *dispatches* a mutation at
construction, running any state-change callback and recording which
target re-renders. :meth:`~wtforms_htmx.HtmxFormMixin.partial`
*renders* it at the view, whether or not a callback ran.

The same path serves htmx requests and no-JS submits. Only the
response differs:

.. mermaid::

    sequenceDiagram
        accTitle: Mutation dispatch and render, with and without htmx
        accDescr: The view builds the form, which runs mutate() during construction to run callbacks and record targets. The view then calls partial(). With htmx, partial() returns an HtmxResponse and the browser swaps the fragment. Without JavaScript, partial() returns None and the view renders the full page.
        actor User
        participant Browser
        participant View
        participant Form
        User->>Browser: types in a field or clicks a button
        alt htmx loaded
            Browser->>View: htmx POST
        else no JavaScript
            Browser->>View: full-page POST (button clicks only)
        end
        View->>+Form: Form(formdata, headers=request.headers)
        Form->>Form: mutate(): run callbacks, record targets
        Form-->>-View: form
        View->>Form: partial()
        alt htmx loaded
            Form-->>View: HtmxResponse (recorded targets)
            View-->>Browser: fragment, swapped in place
        else no JavaScript
            Form-->>View: None
            View-->>Browser: full page
        end

``mutate`` runs its passes in order:

1. **Button-driven**: for each submit source (a
   :class:`~wtforms.fields.ButtonField`, a
   :class:`~wtforms.fields.SubmitField`, or a choices field rendered as
   buttons) whose ``raw_data`` is populated (i.e. the button was the clicked submitter), records each
   ``.triggers(target)`` target for re-render and runs its callback if
   any. Reading ``raw_data`` rather than checking formdata membership
   survives WTForms' :class:`~wtforms.fields.FieldList` index
   compaction, which can rename a clicked entry post-bind. Works with
   and without JavaScript.
2. **Field-source**: the request carries the id of the element that
   sent it (:htmx-header:`hx-source` on htmx 4, :htmx-header:`hx-trigger`
   on htmx 2). That element is one of three kinds:

   - **A field that listens.** For a declaration on a typing event
     (``input``, ``keyup``, ``keydown``, ``keypress``) or a polling
     event (``every``), the target itself sends the request when one of
     its sources changes. A field with inline validation also sends it
     when the user leaves it. ``mutate`` runs every callback declared
     towards it for such an event, and records it for re-render. The
     request does not say which source changed, so every one of these
     callbacks runs. Inline validation is one of them: a listening field
     with inline validation is validated, and shows its errors, whenever
     one of its sources changes.
   - **A field that posts for its targets.** For a declaration on any
     other event, such as ``change``, ``blur`` or ``click``, the source
     sends the request itself. ``mutate`` runs the source's inline
     validation, then the callbacks of the declarations it posts, and
     records the source and its targets for re-render. The targets are
     swapped out of band, without the errors of this validation: the
     user has not reached them yet. When this event is also the one of
     the source's inline validation, one request does both.
   - **A field with a DOM selector target.** For
     ``.triggers("#preview", callback)``, there is no field to listen:
     the source sends the request itself, with
     :htmx-attr:`hx-target` set to the selector. ``mutate`` runs the
     callback with the selector string as ``target``, and the callback's
     return value becomes the response (see :ref:`dom-targets`). Such a
     field cannot also listen to another field: the form raises
     :exc:`ValueError` when it is built.

   A no-JS POST carries no such id, so this pass never fires without
   htmx.

``mutate`` is **idempotent**. Calling it twice in a request is safe;
the second call does nothing.

``mutate`` runs automatically at the end of form construction
(controlled by
:attr:`Meta.htmx_auto_mutate <wtforms_htmx.HtmxMeta.htmx_auto_mutate>`,
default ``True``), *after* the form's derived state
(:class:`~wtforms.fields.SelectField` ``choices`` callables, per-field
processing hooks) is computed, so a callback can rely on it (inline
validation's :meth:`form.validate() <wtforms.form.Form.validate>` needs the resolved ``choices``). After
a mutation, the form is post-processed again, so derived state that
depends on data a callback changed is refreshed before the render. The
view doesn't need to call :meth:`~wtforms_htmx.HtmxFormMixin.mutate` itself.

Headers come from those captured at form construction. Pass
``headers=request.headers`` once to the constructor. Because a no-JS
mutation click is an ordinary full-page POST, the view must keep it out
of its save branch, otherwise an "add tag" click is treated as a
submit. The view checks :attr:`~wtforms_htmx.HtmxFormMixin.submitter`
for that (see :doc:`/how-to/mutations`).

**Why field-source mutations are htmx-only.** They model an event
handler: "the user typed in #X, recompute Y". The source of the
event is the source element id that htmx sends
(:htmx-header:`hx-source` on htmx 4, :htmx-header:`hx-trigger` on htmx 2). A no-JS
full POST carries no such signal. There is no "current event", only a
snapshot of the form. Auto-firing field-source callbacks on
no-JS would risk overwriting user input in bidirectional cases (a
currency converter where ``eur ↔ jpy`` would erase whatever the user
just typed). If your view needs a derived value computed on every
render anyway (e.g. a read-only display field), call the callback
explicitly::

    score_strength(form, form.password, form.strength)

Disabling auto-mutate
---------------------

Mutations dispatch at construction so the view stays terse, but a form
class can opt out with
:attr:`Meta.htmx_auto_mutate <wtforms_htmx.HtmxMeta.htmx_auto_mutate>`
``= False``, for a test that inspects the form *before* mutations apply,
or a view that needs to interleave business logic between :meth:`~wtforms.form.BaseForm.process`
and the mutation step. The view then calls
:meth:`~wtforms_htmx.HtmxFormMixin.mutate` itself. The view's no-JS
gate (see :doc:`/how-to/mutations`) reads
:attr:`~wtforms_htmx.HtmxFormMixin.submitter`, so it keeps working
unchanged.

.. _auto-wired-mutations:

Mutations you don't declare
---------------------------

Not every mutation comes from a :meth:`.triggers()
<wtforms.fields.core.UnboundField.triggers>` declaration.
:class:`~wtforms_htmx.HtmxMeta` auto-wires two more, re-rendering a
target on an event with no declaration from you:

- **Inline validation**: every field except buttons, a
  :class:`~wtforms.fields.FieldList` or :class:`~wtforms.fields.FormField`
  container, and fields with a selector target
  re-renders itself on
  :attr:`~wtforms_htmx.HtmxMeta.htmx_validation_trigger`
  (``"blur changed"`` by default). Its callback runs
  :meth:`form.validate() <wtforms.form.Form.validate>`, so the field
  comes back with its errors. A callback, but no state change.
  :attr:`~wtforms_htmx.HtmxMeta.htmx_inline_validation` turns it off.
- **Datalist refresh**: a callable :class:`~wtforms.DataList` is
  auto-wired on the :mdn-tag:`datalist` element itself. No callback
  runs: :meth:`~wtforms_htmx.HtmxFormMixin.partial` renders the fresh
  options directly, without
  :meth:`~wtforms_htmx.HtmxFormMixin.mutate`.

These are mutations too, wired for you.

See also
--------

- :doc:`/how-to/mutations`: practical recipes for triggering
  mutations in common cases.
- :mod:`wtforms_htmx.mutations`: reference for the shipped
  callbacks.
- :doc:`architecture`: where mutations sit in the broader
  taxonomy of htmx wiring mechanisms.
