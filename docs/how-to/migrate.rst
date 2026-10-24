Migrate an existing WTForms app
===============================

This guide is for developers who maintain a working WTForms application
and want to add wtforms-htmx to it. It moves the application in small
steps. After each step, the application works as before, so the
migration can stop at any step, and go one form at a time.

The guide assumes knowledge of WTForms and of the basics of htmx. It
stops once the forms are ready for interactions. To add them, see
:doc:`/how-to/mutations` and :doc:`/how-to/inline_validation`.

With Flask-WTF, the flask-wtforms-htmx package does part of the work.
Its ``HtmxFlaskForm`` reads the request headers and answers htmx
requests in ``validate_on_submit()``. It covers the view changes of
:ref:`migrate-switch` and the guard of :ref:`migrate-guard`.

1. List what to change
----------------------

Look for:

- Forms that are not WTForms classes, such as a template ``<form>``
  with a CSRF token and a button. Give each one a form class. Render
  all the :mdn-tag:`form` elements through one template or macro, so the
  CSRF token comes from one place.
- Buttons written in templates, including the ones outside the
  :mdn-tag:`form` that use the :mdn-attr:`button#form` attribute.
- Forms built at runtime with :class:`~wtforms.form.BaseForm`. Build
  them as classes instead, for example with :class:`type`. The rest of
  this guide uses :class:`~wtforms.form.Form` subclasses.
- Code that already reads htmx headers. wtforms-htmx reads them from
  step 5 on.
- Forms that set an attribute after ``super().__init__()``, when a
  validator or a callback reads it. Set it before: wtforms-htmx
  validates the form and runs the callbacks inside
  ``super().__init__()``.

  .. code-block:: python

      class SubscriberForm(Form):
          def __init__(self, *args, subscriber_id=None, **kwargs):
              self.subscriber_id = subscriber_id
              super().__init__(*args, **kwargs)

Then check that the tests submit forms through the rendered HTML, for
example with WebTest's :meth:`form.submit() <webtest.forms.Form.submit>`.
A test that posts parameters by hand misses what a browser really sends, such as the empty value of a
:class:`~wtforms.fields.ButtonField`. Put the htmx headers of the tests
in a helper, so only the helper changes later.

2. Upgrade to WTForms 3.3
-------------------------

wtforms-htmx requires WTForms 3.3 or later:

.. code-block:: console

    $ uv add "wtforms>=3.3"

Run the tests. Nothing else changes yet.

3. Turn template buttons into fields
------------------------------------

wtforms-htmx only knows the buttons that are form fields. Replace each
submit button written in a template with a field, and render it with
``{{ form.save() }}``:

- Use :class:`~wtforms.fields.SubmitField` for a button whose value does
  not matter.
- Use :class:`~wtforms.fields.ButtonField` for a button that posts a
  value, such as the index of a row.
- For a button with an icon, use a ``ButtonField`` with a
  :class:`~markupsafe.Markup` ``label``: a ``SubmitField`` renders an
  :mdn-tag:`input`, which holds no markup.
- Give the field a Python name that is not ``submit`` and not
  ``action``. See :ref:`migrate-troubleshooting`.

In the view, test which button was clicked:

.. code-block:: python

    if form.save.data:                # SubmitField: True when clicked
        ...

    if form.add_row.data is not None: # ButtonField: "" when clicked
        ...

Check that each button does what it did before.

4. Render fields through a wrapper
----------------------------------

A field that htmx swaps in must look the same as on the first render.
Render every field through one function before installing wtforms-htmx.
WTForms calls :meth:`Meta.render_field <wtforms.meta.DefaultMeta.render_field>`
for each field:

.. code-block:: python

    BARE_FIELDS = {"HiddenField", "CSRFTokenField", "SubmitField", "ButtonField"}


    class BaseForm(Form):
        class Meta:
            def render_field(self, field, render_kw):
                render_kw = {**(field.render_kw or {}), **render_kw}
                if field.type in BARE_FIELDS:
                    return field.widget(field, **render_kw)

                return render_template("_field.html", field=field, render_kw=render_kw)

Hidden fields and buttons render bare. Flask-WTF's :meth:`~flask_wtf.FlaskForm.hidden_tag`
renders the CSRF token through this method too: without the bare branch,
the token gets a visible label.

The template renders the label, the widget and the errors. Its outer
element needs an :mdn-global-attr:`id`:

.. code-block:: jinja

    {# _field.html #}
    <div id="wrap-{{ field.id }}" class="field">
      {{ field.label() }}
      {{ field.widget(field, **render_kw) }}
      {% for error in field.errors %}<p class="error">{{ error }}</p>{% endfor %}
    </div>

An existing macro can become this template. See
:doc:`/how-to/render_fields` to pick the markup per field type.

Then call ``{{ form.name() }}`` in the templates. Move the presentation
options passed at the call, such as ``{{ form.name(icon="user") }}``,
into the declaration: ``StringField(render_kw={"icon": "user"})``. The
wrapper removes them from ``render_kw`` before it calls the widget. A
field re-rendered by htmx only knows its declaration. A button that no
trigger targets is never re-rendered: its label can stay at the call.

This step can go one form at a time. Check that each page renders the
same markup as before.

.. _migrate-switch:

5. Switch to HtmxForm
---------------------

Install wtforms-htmx:

.. code-block:: console

    $ uv add wtforms-htmx

Then, form by form:

1. Inherit from :class:`~wtforms_htmx.HtmxForm`. To keep another base
   such as Flask-WTF's :class:`~flask_wtf.FlaskForm`, put
   :class:`~wtforms_htmx.HtmxFormMixin` first:
   ``class BaseForm(HtmxFormMixin, FlaskForm)``.
2. Rename ``render_field`` to
   :attr:`field_wrapper <wtforms_htmx.HtmxMeta.field_wrapper>`, and
   remove the line that merges ``field.render_kw``: ``render_kw`` comes
   merged. A ``render_field`` left in the ``Meta`` replaces the one of
   wtforms-htmx, and no htmx attribute renders.
3. Turn inline validation off for now, with
   ``htmx_inline_validation = False`` in the ``Meta``. Step 8 turns it on.
4. Pass the request headers to the form, and return the partial
   response first in the view:

   .. code-block:: python

       form = ProfileForm(request.form or None, headers=request.headers)
       if result := form.partial():
           return Response(result.body, headers=result.headers)

Render the CSRF token inside the :mdn-tag:`form`: an htmx request sends
the fields of the closest form. With an invalid token, no callback runs,
see :doc:`/core/overview`.

If the application already has its own htmx protocol, remove it now:
the ``hx-*`` attributes written in the wrapper or in the templates, and
the view code that reads the htmx headers. Attributes written by hand
override the ones of wtforms-htmx.

When imported, wtforms-htmx adds ``.triggers()``, ``.triggered_by()``
and the ``wrapper=`` argument to every WTForms field of the process,
including the fields of other packages such as Flask-Admin. A field
class that takes its own ``wrapper`` argument no longer receives it.

Check that the pages and the submits work as before.

.. _migrate-guard:

6. Guard the save branches
--------------------------

Without JavaScript, a click on a button with
:meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` is a
full-page POST. The view must not save on it. Test the save button with
:attr:`~wtforms_htmx.HtmxFormMixin.submitter`:

.. code-block:: python

    if form.submitter is form.save and form.validate():
        save(form.data)

Without a single save button, check
:attr:`~wtforms_htmx.HtmxFormMixin.mutated` instead:
``if request.method == "POST" and not form.mutated and form.validate():``.
Do this step before the first trigger declaration.

7. Load htmx
------------

Skip this step if the application already loads htmx. Otherwise, load
htmx 2 or htmx 4 on the pages with forms. See :doc:`/core/overview`.

JavaScript attached to an element loses its handlers when htmx swaps the
element. Attach it to the document, or run it again in
``htmx.onLoad()``. With :htmx-attr:`hx-boost`, a boosted submit still
gets the whole page: ``partial()`` returns ``None`` for it.

Check the pages with and without JavaScript.

8. Turn on inline validation
----------------------------

Remove ``htmx_inline_validation = False``, form by form. A field then
shows its errors when the user changes it and leaves it. Each time, the
whole form validates, including the validators that query a database.
See :doc:`/how-to/inline_validation`.

A field posts to :attr:`~wtforms_htmx.HtmxMeta.htmx_endpoint`, the URL of
the current page by default. It ignores the ``action`` and the
:htmx-attr:`hx-post` of the :mdn-tag:`form`. For a form posted to another
URL, such as a form in a dialog, set ``htmx_endpoint`` to that URL, or
turn inline validation off for this form.

Check that a field with an invalid value shows its error when the user
leaves it.

9. Declare triggers
-------------------

The forms are ready. Add interactions with
:meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` and
:meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>`.
See :doc:`/how-to/mutations`, and :doc:`/how-to/dispatch_submits` for
forms with several submit buttons.

.. _migrate-troubleshooting:

Troubleshooting
---------------

A click on a mutation button saves the form
    The view saves on any POST. Guard the save branch, see
    :ref:`migrate-guard`.

``form.add_row.data`` is false after a click
    A :class:`~wtforms.fields.ButtonField` posts an empty string. Test
    ``is not None``, or compare
    :attr:`~wtforms_htmx.HtmxFormMixin.submitter` with the field.

A button overwrites an attribute of the model
    :meth:`~wtforms.form.Form.populate_obj` writes every field, buttons
    included. A model attribute with the name of a button gets the button
    data. Rename the button, or copy the fields to the model one by one.

A template loop renders the buttons
    ``{% for field in form %}`` now includes the button fields. Skip them
    by ``field.type``.

Two elements have the same id
    A field rendered several times on a page needs ``id=False``. Two
    forms on a page with the same field name need different ``prefix=``.
    wtforms-htmx finds fields by id.

A field loses its classes or its icon after an htmx request
    The option was passed at the call. Move it into the declaration, see
    step 4.

htmx swaps a whole page into a field
    The view does not return the partial response. See
    :ref:`migrate-switch`. If the form posts to another URL than the
    page, set :attr:`~wtforms_htmx.HtmxMeta.htmx_endpoint`, see step 8.

A field gets a 405 error when the user leaves it
    The form posts to another URL than the page, and the page only
    accepts GET. Set :attr:`~wtforms_htmx.HtmxMeta.htmx_endpoint`, see
    step 8.

``AttributeError`` in a validator when the user leaves a field
    The validator reads an attribute that ``__init__`` sets after
    ``super().__init__()``. Set it before, see step 1.

No htmx attribute renders
    The ``Meta`` still defines ``render_field``. Rename it to
    ``field_wrapper``.

The htmx attributes of wtforms-htmx have no effect
    The wrapper, the template or the field declaration writes its own
    ``hx-*`` attributes, which override them. Remove them.

The CSRF token shows a label
    The wrapper wraps hidden fields. Render them bare, see step 4.

An unknown attribute shows in the HTML, such as ``icon="user"``
    The field is rendered without the wrapper, for example with
    ``field.widget(...)``, so its presentation options reach the widget.
    Render it with ``field()``.

``form.submit is not a function`` in JavaScript, or ``form.action`` is an element
    In the DOM, a form control named ``submit`` or ``action`` hides the
    form's property of the same name. Rename the field.
