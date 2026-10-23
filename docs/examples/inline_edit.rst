Inline edit
===========

Edit one field in place, with Save and Cancel next to it.

The mode lives in a hidden ``mode`` field, as in the
:doc:`cycle button <cycle_button>` example. Its widget branches on the
current mode to render either a :mdn-tag:`span` (view) or an
:mdn-tag:`input` (edit).

.. automodule:: examples.inline_edit
   :no-members:
   :no-index:

Setup
-----

.. code-block:: python

    from wtforms import ButtonField, HiddenField, StringField, SubmitField
    from wtforms.widgets import Button
    from wtforms_htmx import HtmxForm
    from wtforms_htmx.mutations import value_cycle

    MODES = ["view", "edit"]


    def restore(form, source, target):
        form.mode.data = "view"
        form.name.data = STATE["inline_edit"].name


    class InlineEditForm(HtmxForm):
        name = StringField("Name")
        mode = HiddenField(default=MODES[0], widget=inline_edit_widget)
        edit = ButtonField("✏ Edit")
        save = SubmitField("✓ Save", widget=Button())
        cancel = ButtonField("✕ Cancel")

        # Edit switches to edit mode.
        edit.triggers("mode", value_cycle(MODES))

        # Cancel, or Escape in the input, restores the saved name.
        cancel.triggers("mode", restore)
        name.triggers("mode", restore, on="keyup[key=='Escape']")

``edit`` and ``cancel`` re-render ``mode``. ``save`` is a plain submit
button with no trigger declaration: it posts the whole page.

Widget
------

``inline_edit_widget`` renders a Jinja macro. The wrapper carries the
htmx attributes computed by :class:`~wtforms_htmx.HtmxMeta` for
``mode``, so ``edit`` and ``cancel`` swap only this wrapper:

.. code-block:: jinja

    {% macro inline_edit(field) %}
      {% set mode = field.data or "view" %}
      {% set form = field._form %}
      <div id="{{ field.id }}" class="inline-edit"{{ kwargs|xmlattr }}>
        <input type="hidden" name="{{ field.name }}" value="{{ mode }}">
        {% if mode == "edit" %}
          {{ form.name(autofocus=True) }}
          {{ form.save(id=False) }}
          {{ form.cancel(id=False) }}
        {% else %}
          <span>{{ form.name.data }}</span>
          <input type="hidden" name="{{ form.name.name }}"
                 value="{{ form.name.data }}">
          {{ form.edit(id=False) }}
        {% endif %}
      </div>
    {% endmacro %}

In view mode, a hidden input carries the ``name`` value. Every click
posts the whole form, so without it the switch to edit mode would
arrive with an empty value.

View
----

.. code-block:: python

    @bp.route("/inline-edit", methods=["GET", "POST"])
    def inline_edit():
        state = STATE["inline_edit"]
        form = InlineEditForm(request.form or None, obj=state, headers=request.headers)
        if result := form.partial():
            return Response(result.body, headers=result.headers)

        if form.submitter is form.cancel:
            return redirect(url_for("main.inline_edit"))

        if form.submitter is not form.save or not form.validate():
            return render_template("inline_edit.html", form=form)

        del form.mode
        form.populate_obj(state)
        return redirect(url_for("main.inline_edit"))

``mode`` is UI state, not data, so the view drops it before
:meth:`~wtforms.form.Form.populate_obj`.

Without JavaScript
------------------

Without htmx, every button submits the whole form:

- ``✏ Edit`` cycles ``mode`` and the page reloads in edit mode;
- ``✓ Save`` validates and saves, then redirects to the page in view
  mode;
- ``✕ Cancel`` redirects to the page, which shows the saved text.

:kbd:`Escape` does nothing without JavaScript.

See also
--------

- :doc:`cycle_button`: the underlying primitive, one button
  rotating one hidden value through a fixed list.
- :doc:`attendance`: the cycle button scaled up to a 2D grid of
  cycling cells, with a custom callback that reads a value to
  pick which entry to rotate.
- :doc:`/how-to/inline_validation`: pair with this if you want the
  edit input to validate on blur before the user clicks ``✓ Save``.
- :doc:`/how-to/mutations`: when to reach for a mutation and the
  multi-form layout patterns that come with it.
