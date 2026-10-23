Built-in mutations
==================

.. module:: wtforms_htmx.mutations

A built-in mutation is a ready-made callback: it changes
``target.data``, then the target re-renders. Pass it as the
``callback`` argument of
:meth:`.triggers(target, callback) <wtforms.fields.core.UnboundField.triggers>`
or
:meth:`.triggered_by(source, callback) <wtforms.fields.core.UnboundField.triggered_by>`.
A pure re-render needs no callback at all. See
:doc:`/explanation/mutations` for the concept and the dispatch path, and
:ref:`anatomy-of-a-callback` to write your own.

Value mutations
---------------

Assign ``target.data`` of a single-valued field (string, select).

.. autofunction:: value_set

.. autofunction:: value_cycle

Multi-select mutations
----------------------

Add or remove a value from a
:class:`~wtforms.fields.SelectMultipleField`'s selection. Both raise
:exc:`TypeError` on any other target type.

.. autofunction:: value_add

.. autofunction:: value_remove

List mutations
--------------

Mutate the entries of a :class:`~wtforms.fields.FieldList` target
(grow, shrink, reorder). Before growing, shrinking or reordering,
trailing entries left by ``min_entries`` padding are dropped, so the
operation acts on the entries the user actually saw.

.. autofunction:: list_add

.. autofunction:: list_remove

.. autofunction:: list_clear

.. autofunction:: list_reorder

.. autofunction:: list_move
