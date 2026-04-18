Markdown preview
================

A textarea drives a server-rendered markdown preview into a
``<div id="preview">`` that is **not** a WTForms field. The pattern
exercises the htmx selector syntax of :meth:`.triggers`: when the
target name does not match a field, it's passed through to
:htmx-attr:`hx-target` verbatim and any htmx-recognized selector works
(``#preview``, ``.result``, ``closest .toast``, …).

.. automodule:: examples.markdown_preview
   :no-members:
   :no-index:

Setup
-----

The textarea declares its trigger with an htmx selector instead of a
field name. wtforms-htmx places the resolved :htmx-attr:`hx-target` on the
source field. The :htmx-attr:`hx-swap` ``"innerHTML"`` override makes htmx put the
response inside the element instead of replacing it:

.. code-block:: python

    from wtforms import SubmitField, TextAreaField
    from wtforms_htmx import HtmxForm


    def render_preview(form, source, target):
        return md_to_html(form.content.data or "")


    class MarkdownPreviewForm(HtmxForm):
        content = TextAreaField("Content", render_kw={"hx-swap": "innerHTML"})
        save = SubmitField("Save")

        # A typing pause renders the markdown into #preview.
        content.triggers("#preview", render_preview, on="input delay:100ms")

(``md_to_html`` is a placeholder for your markdown renderer of choice. It
returns :class:`~markupsafe.Markup`, so the template does not escape the
HTML.)

A few things to note about ``render_preview``:

- ``target`` here is the raw selector string (``"#preview"``), not a
  :class:`~wtforms.fields.Field`.
- The returned ``str`` is the response body verbatim. wtforms-htmx does
  not wrap it.
- The callback returns only the rendered markdown. The
  ``<div id="preview">`` stays in the template, so its :mdn-global-attr:`id` and
  classes survive every swap.

Template & view
---------------

The form template carries a plain ``<form method="post">`` and the
target element. ``preview`` is the server-rendered HTML for the
initial GET and for the no-JS submit path:

.. code-block:: jinja

    <form method="post">
      {{ form.content() }}
      <div id="preview" class="md-preview">{{ preview }}</div>
      {{ form.save() }}
    </form>

.. code-block:: python

    @bp.route("/markdown-preview", methods=["GET", "POST"])
    def markdown_preview():
        state = STATE["markdown_preview"]
        form = MarkdownPreviewForm(request.form or None, obj=state, headers=request.headers)
        if result := form.partial():
            return Response(result.body, headers=result.headers)

        if form.submitter is form.save:
            form.populate_obj(state)

        preview = md_to_html(form.content.data or "")
        return render_template("markdown_preview.html", form=form, preview=preview)

How the wiring looks in HTML
----------------------------

The textarea renders with these htmx attributes:

.. code-block:: html

    <textarea id="content" name="content"
              hx-post="/markdown-preview"
              hx-trigger="input delay:100ms"
              hx-target="#preview"
              hx-include="closest form"
              hx-swap="innerHTML">…</textarea>

    <div id="preview" class="md-preview">…</div>

The textarea posts the form after each 100 ms typing pause. The server
returns the rendered HTML, and htmx puts it inside
``<div id="preview">``.

Pitfalls
--------

- Without the ``hx-swap="innerHTML"`` override, the swap uses the
  default ``outerHTML`` and replaces the whole element. The returned
  HTML would then need ``id="preview"`` on its outermost element.
  Without it, the second swap silently finds nothing.
- Unsanitized markdown is an XSS vector: the returned ``str`` is
  inserted verbatim and wtforms-htmx does not escape it. Pass the
  user-supplied text through a markdown library that escapes HTML by
  default. If yours does not, sanitize the output (e.g.
  ``bleach.clean``) before returning.
- ``input`` without ``delay:Xms`` fires on every keystroke and floods
  the server. ``delay:100ms`` keeps the preview visually live without
  flooding. Raise it for expensive renders, lower it for trivial ones.

Without JavaScript
------------------

Without JavaScript, typing triggers nothing. Users submit the form
through the ``Save`` button. The view shown above stores the content
and renders the preview on the server.

Both modes render the same markdown into the same template element.

See also
--------

- :ref:`dom-targets`: full reference for the selector syntax and the
  callback contract.
- :doc:`/how-to/mutations`: the same mechanic applied to *field*
  targets (the more common case).
