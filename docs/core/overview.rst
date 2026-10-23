Overview
========

wtforms-htmx lets an event on one field update another part of the
form. You declare it in Python, next to your fields. You write no
JavaScript and no extra route, and the form keeps working without
JavaScript. This page introduces the main ideas, shows a complete
example, then describes the pieces you plug into your application. It
assumes you know :external+wtforms:doc:`WTForms <index>` and roughly
what `htmx <https://htmx.org/>`_ does: swap server-rendered HTML into
the page in response to an event.

Mutations and triggers
----------------------

A **mutation** is an element re-rendered in reaction to an event:
typing a title fills a slug, picking a country refreshes a city list,
clicking "Add row" appends a row.

You declare a mutation with a **trigger declaration**. Put
:meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` on the
field that fires the event, or
:meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>`
on the field that re-renders:

.. code-block:: python

    title = StringField("Title").triggers("slug", derive_slug)

A trigger declaration can carry a **callback**, a
``(form, source, target)`` function that runs just before the
re-render. It usually changes ``target.data``. Without a callback, the
target re-renders from the current form state.
:mod:`wtforms_htmx.mutations` ships ready-made callbacks for common
cases, such as adding a row to a :class:`~wtforms.fields.FieldList`.

The library also sets up some mutations for you. Every field validates
when the user leaves it (:doc:`/how-to/inline_validation`), and a
:class:`~wtforms.DataList` with a callable refreshes as the user types
(:doc:`/how-to/datalist`).

See :doc:`/explanation/mutations` for how a mutation runs.

A complete example
------------------

A post form where the slug follows the title. The form:

.. code-block:: python

    import re

    from flask import render_template
    from wtforms import ButtonField, StringField, SubmitField
    from wtforms.validators import DataRequired
    from wtforms_htmx import HtmxForm


    def derive_slug(form, source, target):
        title = (form.title.data or "").lower()
        target.data = re.sub(r"[^a-z0-9]+", "-", title).strip("-")


    class PostForm(HtmxForm):
        class Meta:
            def field_wrapper(self, field, render_kw):
                return render_template("_field.html", field=field, render_kw=render_kw)

        title = StringField("Title", validators=[DataRequired()])
        slug = StringField("Slug", validators=[DataRequired()])
        regenerate = ButtonField("Regenerate", wrapper=False)
        save = SubmitField("Save", wrapper=False)

        # Typing a title derives the slug. Without JavaScript, Regenerate does it.
        title.triggers("slug", derive_slug)
        regenerate.triggers("slug", derive_slug)

The view, here with Flask:

.. code-block:: python

    @app.route("/post", methods=["GET", "POST"])
    def edit_post():
        form = PostForm(request.form or None, headers=request.headers)
        if result := form.partial():
            return Response(result.body, headers=result.headers)

        if form.submitter is form.save and form.validate():
            save_post(form.data)
            return redirect("/post")

        return render_template("post.html", form=form)

The templates:

.. code-block:: html+jinja
   :caption: templates/_field.html

    <div id="wrap-{{ field.id }}">
      {{ field.label() }}
      {{ field.widget(field, **render_kw) }}
      {% for error in field.errors %}<p class="error">{{ error }}</p>{% endfor %}
    </div>

.. code-block:: html+jinja
   :caption: templates/post.html

    <script src="https://cdn.jsdelivr.net/npm/htmx.org@4.0.0/dist/htmx.min.js"></script>
    <form method="post">
      {{ form.title() }}
      {{ form.slug() }}
      {{ form.regenerate() }}
      {{ form.save() }}
    </form>

With htmx, typing a title fills the slug, and leaving an empty field
shows its error. Without JavaScript, ``Regenerate`` fills the slug
through a full-page submit. ``Save`` saves in both cases.
:doc:`/examples/title_slug` runs a richer version of this form.

What you plug in
----------------

Every integration plugs in the same pieces as the example.

Form base
~~~~~~~~~

Inherit from :class:`~wtforms_htmx.HtmxForm`. Its constructor takes an
extra ``headers=`` argument: pass the request headers, so the form can
tell an htmx request from a plain one. To compose with another base
such as Flask-WTF's :class:`~flask_wtf.FlaskForm`, mix in
:class:`~wtforms_htmx.HtmxFormMixin` first:
``class PostForm(HtmxFormMixin, FlaskForm)``.

The view
~~~~~~~~

Call :meth:`~wtforms_htmx.HtmxFormMixin.partial` before your usual
form handling. For an htmx request, it returns an
:class:`~wtforms_htmx.HtmxResponse` with the HTML fragment to send
back. Otherwise it returns ``None`` and the view goes on as usual.

Save only when :attr:`~wtforms_htmx.HtmxFormMixin.submitter` is the
save button. Without JavaScript, a click on ``Regenerate`` is a
full-page POST too, and it must not save. See :doc:`/how-to/mutations`
for this check, and :doc:`/how-to/dispatch_submits` for forms with
several submit buttons.

.. _field-wrapper:

Field wrapper
~~~~~~~~~~~~~

:attr:`Meta.field_wrapper <wtforms_htmx.HtmxMeta.field_wrapper>` renders
the markup around each field: label, input and errors. A field
re-rendered by a mutation goes through the same wrapper, so its label
and errors update with it and it looks the same as on the first render.

The outer element must carry an :mdn-global-attr:`id`: that is the element htmx
replaces when the field comes back. The ``wrapper=`` argument on a field
overrides the wrapper for that field, and ``False`` skips it, as for the
buttons above. See :doc:`/how-to/render_fields` for markup that depends
on the field type.

CSRF protection
~~~~~~~~~~~~~~~

Callbacks run while the form is built, before
:meth:`~wtforms.form.Form.validate`. With CSRF protection on
(:attr:`Meta.csrf <wtforms.meta.DefaultMeta.csrf>`), the form checks the
token first. With an invalid token, no callback runs and the error is
set on the CSRF field. The view can then answer as it does for any CSRF
error.

With CSRF protection off, any POST runs the callbacks. A callback that
writes to a database or calls an external service needs CSRF protection.

Without JavaScript
------------------

A button with a trigger declaration is a plain submit button. Without
JavaScript, a click posts the whole page, and the form runs the same
callback while it is built. Typing triggers nothing, so a mutation
driven by typing needs a button next to it, like ``Regenerate`` above.
See :ref:`dispatch-path` for both paths side by side.

Installation
------------

.. code-block:: console

    $ uv add wtforms-htmx

wtforms-htmx requires WTForms 3.3.0b4 or later. It does not ship htmx. Load it yourself, from a CDN or from
your static files. It works with htmx 2 and htmx 4, with no extension.
This documentation and the examples use htmx 4.

Where to go next
----------------

- :doc:`/how-to/mutations`: recipes for common mutations.
- :doc:`/how-to/migrate`: add wtforms-htmx to an existing WTForms
  application, step by step.
- :doc:`/examples/title_slug` and the rest of the example gallery:
  runnable examples, each with a screencast.
- :doc:`/core/api`: the API reference.
- :doc:`/explanation/mutations`: how a mutation runs, with and without
  JavaScript.
- :doc:`/explanation/architecture`: where the library stops and raw
  htmx takes over.
