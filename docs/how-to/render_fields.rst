Render fields with a wrapper
============================

A single ``label + widget + errors`` template does not fit every field.
Use :attr:`~wtforms_htmx.HtmxMeta.field_wrapper`, the method that renders
the markup around each field (see :ref:`field-wrapper`), to pick the
markup per field family:

- :class:`~wtforms.fields.HiddenField` /
  :class:`~wtforms.csrf.core.CSRFTokenField`: bare widget, no surrounding
  markup. A label would render but serve no purpose.
- :class:`~wtforms.fields.SubmitField` /
  :class:`~wtforms.fields.ButtonField`: bare :mdn-tag:`button`. Its
  visible text already serves as the label, and a separate
  :mdn-tag:`label` is redundant.
- :class:`~wtforms.fields.BooleanField` rendered as a checkbox: label
  *after* the input, errors inline next to the control.
- :class:`~wtforms.fields.FieldList` /
  :class:`~wtforms.fields.FormField`: bare widget. It already carries
  the :mdn-global-attr:`id` that trigger declarations target, so do not wrap it.
- everything else (text, email, number, password, …): the usual
  ``<div id="wrap-…">label + input + errors</div>``.

Branch in Python
----------------

Keep the per-family decision in the wrapper itself and delegate the
markup to small templates::

    class BaseForm(HtmxForm):
        class Meta:
            def field_wrapper(self, field, render_kw):
                if field.type in {
                    "HiddenField", "CSRFTokenField", "SubmitField",
                    "ButtonField", "FieldList", "FormField",
                }:
                    return field.widget(field, **render_kw)

                if field.type == "BooleanField":
                    return render_template("_checkbox.html", field=field, render_kw=render_kw)

                return render_template("_field.html", field=field, render_kw=render_kw)

Branch in the template
----------------------

Or push the whole decision into one template, and make the wrapper
render it:

.. code-block:: jinja
   :caption: templates/_field.html

    {% if field.type in ('HiddenField', 'CSRFTokenField', 'SubmitField',
                         'ButtonField', 'FieldList', 'FormField') %}
      {{ field.widget(field, **render_kw) }}
    {% elif field.type == 'BooleanField' %}
      <div id="wrap-{{ field.id }}" class="field">
        <label for="{{ field.id }}">
          {{ field.widget(field, **render_kw) }}
          {{ field.label.text }}
        </label>
        {% for e in field.errors %}<small class="error">{{ e }}</small>{% endfor %}
      </div>
    {% else %}
      <div id="wrap-{{ field.id }}" class="field">
        {{ field.label() }}
        {{ field.widget(field, **render_kw) }}
        {{ field.datalist() }}
        {% if field.errors %}
          <ul class="errors">
            {% for e in field.errors %}<li>{{ e }}</li>{% endfor %}
          </ul>
        {% endif %}
      </div>
    {% endif %}

.. code-block:: python

    class BaseForm(HtmxForm):
        class Meta:
            def field_wrapper(self, field, render_kw):
                return render_template("_field.html", field=field, render_kw=render_kw)

Override per field
------------------

The ``wrapper=`` constructor kwarg overrides
:attr:`Meta.field_wrapper <wtforms_htmx.HtmxMeta.field_wrapper>` for
a single field. ``False`` skips the wrapper. A callable gives that
field its own layout::

    name = StringField("Name")                    # uses Meta.field_wrapper
    token = HiddenField(wrapper=False)            # bare widget, no wrapper
    rating = IntegerField(wrapper=stars_wrapper)  # this field's own wrapper

A ``wrapper=`` callable takes ``(field, render_kw)`` and returns the
HTML, like ``Meta.field_wrapper`` without ``self``.

Keep presentation options in the declaration
--------------------------------------------

A re-rendered field only knows its declaration. Options passed at the
call, such as ``{{ form.name(icon="user") }}``, reach the wrapper on the
first render, but not in the fragment that htmx swaps in. Put them in
the declaration instead, with ``render_kw=`` or ``wrapper=``::

    name = StringField("Name", render_kw={"icon": "user"})

The wrapper then gets ``icon`` in ``render_kw`` on every render. Remove
it from ``render_kw`` before calling the widget, so it does not end up
as an HTML attribute.

See also
--------

- :doc:`/examples/auto_save`: a wrapper that encodes a button's state.
- :attr:`~wtforms_htmx.HtmxMeta.field_wrapper`: the attribute reference.
