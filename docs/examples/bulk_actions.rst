Bulk actions
============

A :class:`~wtforms.fields.SelectMultipleField` of checkboxes selects
rows, and the submit buttons of a toolbar apply one action to all of
them.

.. automodule:: examples.bulk_actions
   :no-members:
   :no-index:

.. code-block:: python

    from wtforms import ButtonField, FormField, SelectChoice, SelectMultipleField, SubmitField
    from wtforms.widgets import CheckboxInput
    from wtforms_htmx import HtmxForm
    from wtforms_htmx.mutations import value_set


    def inbox_choices(form, field):
        return [SelectChoice(message.id, message.subject) for message in form.inbox()]


    def select_matching(form, source, target):
        value = source.raw_data[0]  # "all", "read" or "unread"
        target.data = [
            message.id
            for message in form.inbox()
            if value == "all" or message.read == (value == "read")
        ]


    class ToolbarForm(HtmxForm):
        mark_read = SubmitField("Mark read")
        mark_unread = SubmitField("Mark unread")
        archive = SubmitField("Archive")


    class BulkActionsForm(HtmxForm):
        selection = SelectMultipleField(
            choices=inbox_choices,
            option_widget=CheckboxInput(),
            widget=render_inbox,
        )
        select = ButtonField("Select")
        clear = ButtonField("None")
        toolbar = FormField(ToolbarForm, widget=render_toolbar)

        # Every tick refreshes the toolbar.
        selection.triggers("toolbar", on="change")

        select.triggers("selection", select_matching).triggers("toolbar")
        clear.triggers("selection", value_set([])).triggers("toolbar")

        def inbox(self):
            """Return the messages that are not archived."""
            ...

``inbox_choices`` is a callable, so the choices follow the messages
left in the inbox. The ``select`` button is rendered three times, with
the values ``all``, ``read`` and ``unread``. ``select`` and ``clear``
change the selection, then refresh the toolbar. Each button needs two
:meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` calls,
because the callback only applies to ``selection``.

The select buttons sit outside the table and the toolbar, so a click
does not replace them and they keep the keyboard focus:

.. code-block:: jinja

    <div role="group" aria-labelledby="select-label">
      {% for value, label in [("all", "All"), ("read", "Read"), ("unread", "Unread")] %}
        {{ form.select(value=value, label=label, id=False) }}
      {% endfor %}
      {{ form.clear() }}
    </div>
    {{ form.toolbar() }}
    {{ form.selection() }}

The toolbar is a :class:`~wtforms.fields.FormField`, so the count and
the three buttons refresh as one target. ``render_toolbar`` only shows
the actions that change at least one ticked message. It does so only
for htmx requests: without JavaScript, the page cannot follow the ticks
and shows every action.

.. code-block:: jinja

    {% macro toolbar(field) %}
      {% set form = field._form %}
      {% set count = form.selected_messages() | length %}
      {% set useful = form.useful_actions() %}
      {% set live = request.headers.get("HX-Request") %}
      <div id="{{ field.id }}"{{ kwargs|xmlattr }}>
        <span class="bulk-idle">{{ form.inbox() | length }} messages</span>
        <div class="bulk-active">
          {% if count %}<output aria-live="polite">{{ count }} selected</output>{% endif %}
          {% for action in (field.mark_read, field.mark_unread, field.archive) %}
            {% if useful[action] or not live %}{{ action() }}{% endif %}
          {% endfor %}
        </div>
      </div>
    {% endmacro %}

A CSS rule shows ``.bulk-active`` instead of ``.bulk-idle`` once a box
is ticked. It needs no JavaScript:

.. code-block:: css

    .demo-area:not(:has(input[name="selection"]:checked)) .bulk-active,
    .demo-area:has(input[name="selection"]:checked) .bulk-idle {
      display: none;
    }

The view runs the action of the clicked button.
:attr:`~wtforms_htmx.HtmxFormMixin.submitter` finds the buttons inside
the toolbar. The view skips the messages that an action would not
change, and says how many:

.. code-block:: python

    form = BulkActionsForm(request.form or None, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    toolbar = form.toolbar
    actions = (toolbar.mark_read, toolbar.mark_unread, toolbar.archive)
    if not any(form.submitter is action for action in actions):
        return render_template("bulk_actions.html", form=form)

    messages = form.selected_messages()
    if not messages:
        flash("Select at least one message.", "warning")
        return render_template("bulk_actions.html", form=form)

    if form.submitter is toolbar.archive:
        ...

    read = form.submitter is toolbar.mark_read
    changed = [message for message in messages if message.read != read]
    ...
    flash("1 marked as read, 1 already read.", "success")

Without JavaScript
------------------

The toolbar appears on the first tick, through CSS. It shows every
action, and the count of the last submitted page. ``All``, ``Read``,
``Unread`` and ``None`` submit the page, and the page comes back with
the boxes ticked or cleared. An action submits the ticked boxes.

See also
--------

- :doc:`dual_listbox`: bulk moves between two panes, with ``Add all``
  and ``Clear all`` callbacks.
- :doc:`/how-to/dispatch_submits`: how
  :attr:`~wtforms_htmx.HtmxFormMixin.submitter` tells the submit
  buttons apart.
