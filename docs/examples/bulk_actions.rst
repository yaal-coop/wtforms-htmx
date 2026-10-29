Bulk actions
============

A :class:`~wtforms.fields.SelectMultipleField` of checkboxes selects
rows, and the submit buttons of a toolbar apply one action to all of
them.

.. automodule:: examples.bulk_actions
   :no-members:
   :no-index:

.. literalinclude:: ../../examples/bulk_actions.py
   :pyobject: _inbox_choices

.. literalinclude:: ../../examples/bulk_actions.py
   :pyobject: select_matching

.. literalinclude:: ../../examples/bulk_actions.py
   :pyobject: ToolbarForm

.. literalinclude:: ../../examples/bulk_actions.py
   :pyobject: BulkActionsForm

``_inbox_choices`` is a callable, so the choices follow the messages
left in the inbox. The ``select`` button is rendered three times, with
the values ``all``, ``read`` and ``unread``. ``select`` and ``clear``
change the selection, then refresh the toolbar. Each button needs two
:meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` calls,
because the callback only applies to ``selection``.

The select buttons sit outside the table and the toolbar, so a click
does not replace them and they keep the keyboard focus:

.. literalinclude:: ../../examples/templates/bulk_actions.html
   :language: html+jinja
   :start-at: <div class="bulk-bar">
   :end-at: {{ form.selection() }}
   :dedent: 6

The toolbar is a :class:`~wtforms.fields.FormField`, so the count and
the three buttons refresh as one target. The ``toolbar`` macro only shows
the actions that change at least one ticked message. It does so only
for htmx requests: without JavaScript, the page cannot follow the ticks
and shows every action.

.. literalinclude:: ../../examples/templates/_bulk_actions_widgets.html
   :language: html+jinja
   :start-at: macro toolbar
   :end-at: endmacro

A CSS rule shows ``.bulk-active`` instead of ``.bulk-idle`` once a box
is ticked. It needs no JavaScript:

.. literalinclude:: ../../examples/static/bulk_actions.css
   :start-at: /* CSS, not JavaScript
   :end-at: }

The view runs the action of the clicked button.
:attr:`~wtforms_htmx.HtmxFormMixin.submitter` finds the buttons inside
the toolbar. The view skips the messages that an action would not
change, and says how many:

.. literalinclude:: ../../examples/bulk_actions.py
   :pyobject: bulk_actions

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
