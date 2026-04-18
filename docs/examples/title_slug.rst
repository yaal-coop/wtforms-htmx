Title slug
==========

A slug field tracks a title as the user types. Once the user types
their own slug, the title stops changing it.

.. automodule:: examples.title_slug
   :no-members:
   :no-index:

.. code-block:: python

    def derive_slug(form, source, target):
        user_slug = (form.slug.data or "").strip()
        if user_slug and user_slug != form.last_auto_slug.data:
            return None

        target.data = form.last_auto_slug.data = slugify(form.title.data)
        return [None, form.last_auto_slug]

    class TitleSlugForm(HtmxForm):
        title = StringField("Title")
        slug = StringField("Slug")
        last_auto_slug = HiddenField()
        save = SubmitField("Save")

        # Typing a title derives the slug, until the user edits the slug.
        title.triggers("slug", derive_slug)

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
