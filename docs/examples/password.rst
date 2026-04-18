Password strength indicator
===========================

A password strength indicator recomputes from a typed password:
read-only feedback driven by a typing source. The same shape fits a
live character count, or any field whose value is purely
derived from another and never edited directly.

.. automodule:: examples.password
   :no-members:
   :no-index:

.. code-block:: python

    from wtforms import IntegerRangeField, PasswordField, SubmitField
    from wtforms.validators import Disabled, EqualTo, NumberRange
    from wtforms_htmx import HtmxForm

    def score_strength(form, source, target):
        target.data = score_password(source.data)

    class PasswordStrengthForm(HtmxForm):
        password = PasswordField(
            "Password",
            render_kw={"autocomplete": "new-password"},
        )
        confirm_password = PasswordField(
            "Confirm password", validators=[EqualTo("password")]
        )
        strength = IntegerRangeField(
            "Strength", default=0,
            validators=[NumberRange(min=0, max=4), Disabled()],
        )
        save = SubmitField("Save")

        # Typing re-scores the password.
        password.triggers("strength", score_strength)

With htmx, the callback runs at each typing pause.

**Privacy on sensitive fields.** The browser sends the password to the
server at each typing pause. HTTPS protects it in transit, but it can land in
server logs or in a web application firewall. To score less often, move the trigger to blur:
``.triggers("strength", score_strength, on="blur")``.

Without JavaScript
------------------

The callback never runs, so the meter stays at its default. ``Save``
still validates and saves the password. To show the strength after a
full-page submit too, call the callback in the view:

.. code-block:: python

    score_strength(form, form.password, form.strength)

The example does not, because a successful save redirects to an empty
form. Since ``strength`` is display-only, no fallback button is
needed.

See also
--------

- :doc:`title_slug`: another value derived from a typed field.
- :doc:`/how-to/inline_validation`: the ``confirm_password`` check on
  blur.
