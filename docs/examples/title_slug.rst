Title slug
==========

A slug field tracks a title as the user types. Once the user types
their own slug, the title stops changing it.

.. automodule:: examples.title_slug
   :no-members:
   :no-index:

.. literalinclude:: ../../examples/title_slug.py
   :pyobject: derive_slug

.. literalinclude:: ../../examples/title_slug.py
   :pyobject: TitleSlugForm

``last_auto_slug`` holds the last slug the server derived. When the
posted slug differs from it, the user has edited the slug, and the
callback leaves it alone. The callback returns ``last_auto_slug`` as an
out-of-band extra, so the hidden value stays in sync in the page.

Without JavaScript
------------------

Typing in the title triggers nothing, so the slug is not derived. The
user types the slug, and ``Save`` saves both fields.

See also
--------

- :doc:`currency`: two fields derived from each other.
- :ref:`out-of-band-swaps`: how ``last_auto_slug`` reaches the page.
