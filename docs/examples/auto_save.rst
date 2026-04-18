Auto-save
=========

Auto-save commits the form on every typing pause: the user types,
htmx waits for the input flurry to settle, posts the whole form to
the current URL, and the server decides whether to persist. This
page covers the *basic* policy: save only when the whole form
validates, otherwise leave the underlying state untouched. That keeps
every visible state derivable from the server (no client-side "unsaved
changes" buffer) and avoids ever writing partial data.

Auto-save suits editing an existing object, such as notes or
preferences. For a one-off submission such as a signup or a payment,
keep an explicit Save button.

.. automodule:: examples.auto_save
   :no-members:
   :no-index:

Setup
-----

The save button also serves as the auto-save indicator. It is declared
as a single :class:`~wtforms.fields.SubmitField` wired with
``.triggered_by("*", ...)``. The wildcard means *"an event on any field
of the form re-renders me"*. This includes nested fields and the button
itself:

.. code-block:: python

    from datetime import datetime
    from dataclasses import dataclass

    from wtforms import IntegerField, StringField, SubmitField
    from wtforms.validators import (
        DataRequired, Email, Length, NumberRange, Optional, URL,
    )
    from wtforms_htmx import HtmxForm


    @dataclass
    class AutoSaveStatus:
        kind: str
        message: str


    def autosave_commit(form, source, target):
        """Validate the form, commit on success, update the button's data."""
        state = STATE["auto_save"]
        if form.validate():
            form.populate_obj(state)
            target.data = AutoSaveStatus(
                "saved", f"Saved at {datetime.now():%H:%M:%S}"
            )
            return

        n = sum(1 for f in form if f.errors)
        target.data = AutoSaveStatus(
            "errors", f"Not saved: {n} error{'s' if n != 1 else ''} below."
        )


    class ProfileForm(HtmxForm):
        name = StringField("Name", validators=[DataRequired(), Length(min=2, max=64)])
        email = StringField("Email", validators=[DataRequired(), Email()])
        website = StringField("Website", validators=[Optional(), URL()])
        age = IntegerField("Age", validators=[Optional(), NumberRange(min=13, max=120)])
        save = SubmitField("Save", wrapper=autosave_save_wrapper)

        # Any field change, after a typing pause, commits the form.
        save.triggered_by("*", autosave_commit, on="input delay:800ms")

The button listens to every field of the form, whichever one fired the
event. The callback receives ``source=None``, since there is no single
source field. The wildcard has limits, listed in
:ref:`the how-to <wildcard-limits>`.

The button wrapper
------------------

The wrapper renders a ``<button type="submit">`` whose label and CSS
class encode ``field.data`` (see :attr:`~wtforms_htmx.HtmxMeta.field_wrapper`):

.. code-block:: jinja
   :caption: templates/_auto_save_widgets.html

    {%- set status = field.data if field.data and field.data.kind is defined else None -%}
    {%- set kind = status.kind if status else 'idle' -%}
    {%- set label = status.message if status else field.label.text -%}
    <button id="{{ field.id }}"
            type="submit"
            name="{{ field.name }}"
            value="{{ field.label.text }}"
            class="auto-save-status auto-save-status-{{ kind }}"
            aria-live="polite"
            {{ render_kw|xmlattr }}>
      {{ label }}
    </button>

.. code-block:: python

    from flask import render_template

    def autosave_save_wrapper(field, render_kw):
        return render_template(
            "_auto_save_widgets.html", field=field, render_kw=render_kw
        )

Notes:

- ``type="submit"`` is kept in every state so the button remains
  actionable. The no-JS submit path goes through the same element, and
  with htmx the user can force an immediate commit between debounce
  windows.
- ``aria-live="polite"`` makes screen readers announce status changes
  without stealing focus from whatever the user is currently typing.
- ``{{ render_kw|xmlattr }}`` splats the htmx attrs computed by the
  library (:htmx-attr:`hx-post`, :htmx-attr:`hx-trigger`,
  ``hx-include="closest form"``) onto the :mdn-tag:`button`.

Template & view
---------------

The form template is a plain ``<form method="post">`` with no
``hx-*`` attributes to write manually:

.. code-block:: jinja

    <form method="post">
      {{ form.name() }}
      {{ form.email() }}
      {{ form.website() }}
      {{ form.age() }}
      {{ form.save() }}
    </form>

The view is small. The auto-save round-trip is handled by
:meth:`form.partial() <wtforms_htmx.HtmxFormMixin.partial>`.
wtforms-htmx resolves the wildcard mutation and renders the swapped
button. The explicit ``Save`` click is the only path that reaches the
view's submit branch:

.. code-block:: python

    @bp.route("/auto-save", methods=["GET", "POST"])
    def auto_save():
        state = STATE["auto_save"]
        form = ProfileForm(request.form or None, obj=state, headers=request.headers)
        if result := form.partial():
            return Response(result.body, headers=result.headers)

        if form.submitter is not form.save:
            return render_template("auto_save.html", form=form)

        if form.validate():
            form.populate_obj(state)
            flash("Saved.")
            return redirect(url_for("main.auto_save"))

        flash("Please fix the errors below.", "error")
        return render_template("auto_save.html", form=form)

Pitfalls
--------

- Network drops, server errors and validation failures must all reach
  the user, or a save fails silently. The button label is the single
  channel. Never assume a missing acknowledgement means success.
- Two tabs editing the same object will last-write-wins. If that
  matters, version the underlying state and reject stale POSTs with a
  clear button label.
- A genuinely empty form (first visit, nothing filled) will flip the
  button to "Not saved: N errors" on the first typing pause, which can
  read as alarming. Either seed defaults that already validate, or
  treat the empty initial state as ``idle`` in the wrapper rather than
  "N errors".
- The button says "N errors" but the field-level error markers only
  appear after the inline-validation blur trigger fires. If you want
  errors to materialize immediately alongside the button, the callback
  can return an iterable of out-of-band fragments, at the cost of
  moving the swap out of the field-level cycle.
- A delay under about 200 ms sends a request per keystroke. Raise
  ``delay:800ms`` for long text, lower it for short fields.

Without JavaScript
------------------

The wildcard trigger never fires, so nothing saves while the user
types. The same button is a plain submit: a click validates the form,
saves it when it is valid, and shows the errors otherwise.

See also
--------

- :doc:`/how-to/inline_validation`: per-field blur validation, the
  typical visual companion to auto-save.
- :attr:`~wtforms_htmx.HtmxMeta.field_wrapper`: the ``wrapper=`` kwarg used to render
  the save button.
