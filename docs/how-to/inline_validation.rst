Inline validation
=================

.. automodule:: examples.inline_validation
   :no-members:
   :no-index:

Setup
-----

Inline validation is on by default (see :doc:`/core/overview`): each
:class:`~wtforms_htmx.HtmxForm` field is validated when the user leaves
it. Selects, checkboxes and radio buttons validate when they change.
File and hidden inputs do not validate inline. Declare your validators:

.. code-block:: python

    from wtforms import EmailField, StringField, SubmitField
    from wtforms.validators import DataRequired, Email
    from wtforms_htmx import HtmxForm

    class SignupForm(HtmxForm):
        name = StringField("Name", validators=[DataRequired()])
        email = EmailField("Email", validators=[DataRequired(), Email()])
        save = SubmitField("Save")

Answer the validation requests from the view, with
:meth:`~wtforms_htmx.HtmxFormMixin.partial`:

.. code-block:: python

    form = SignupForm(request.form or None, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

Render fields
-------------

.. code-block:: jinja

    <form method="post">
      {{ form.name() }}
      {{ form.email() }}
      {{ form.save() }}
    </form>

Without a field wrapper, the ``email`` field above renders as a bare
input that posts the form on blur and replaces itself with the
validated version:

.. code-block:: html

    <input id="email" name="email" type="email" required
           hx-post="" hx-trigger="blur changed" hx-swap="outerHTML"
           hx-include="closest form">

To update the label and the errors with the input, set
:attr:`Meta.field_wrapper <wtforms_htmx.HtmxMeta.field_wrapper>` as shown
in :ref:`the overview <field-wrapper>`.

Customize the trigger
---------------------

Override ``Meta`` attributes on the form to tweak what triggers
inline validation:

.. code-block:: python

    class SignupForm(HtmxForm):
        class Meta:
            htmx_validation_trigger = "change delay:300ms"

Or override per-field via ``render_kw``:

.. code-block:: python

    email = EmailField(render_kw={"hx-trigger": "change"})

``render_kw`` overrides the form-wide setting (see
:ref:`attribute-precedence`).

See :htmx-attr:`hx-trigger` for the full syntax: events,
modifiers, ``delay:Xms``, ``throttle:Xms``, polling and so on.

Skip inline validation entirely
-------------------------------

Set :attr:`~wtforms_htmx.HtmxMeta.htmx_inline_validation` to ``False``
on the form's ``Meta``. Fields no longer validate on blur, and your
trigger declarations keep working:

.. code-block:: python

    class ProfileForm(HtmxForm):
        class Meta:
            htmx_inline_validation = False

        email = EmailField()

See also
--------

- :doc:`/core/overview`: the full view, with the save branch.
- :doc:`/how-to/render_fields`: show the errors next to each field.
