.. rst-class:: hide-header

wtforms-htmx
============

.. image:: _static/logo-light.svg
   :align: center
   :alt: wtforms-htmx

Interactive :external+wtforms:doc:`WTForms <index>` forms declared in
Python and powered by `htmx <https://htmx.org/>`_, with no JavaScript to
write, or even any htmx.

.. screencast:: |examples|/title-slug
   :locator: .demo-area
   :locator-padding: 5 10 0 10
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :alias: title-slug
   :interactions:
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     // typeInto delay > the form-wide htmx_default_trigger debounce
     // (200ms by default) so each keystroke fires its own partial and
     // the slug visibly tracks the title character by character.
     const typeInto = async (sel, text, delay = 250) => {
       const el = document.querySelector(sel);
       el.focus();
       for (const c of text) {
         el.value = (el.value || '') + c;
         el.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(delay);
       }
       await wait(500);
     };
     const clearField = async (sel, delay = 80) => {
       const el = document.querySelector(sel);
       el.focus();
       while ((el.value || '').length > 0) {
         el.value = el.value.slice(0, -1);
         el.dispatchEvent(new Event('input', {bubbles: true}));
         await wait(delay);
       }
       await wait(300);
     };
     await wait(500);
     await typeInto('#title', 'Hello, world!');
     await wait(900);
     await clearField('#title');
     document.querySelector('#title').blur();
     await wait(500);

Here's (almost) everything wtforms-htmx adds on top of a regular form:

.. code-block:: python

   class PostForm(HtmxForm):
       title = StringField().triggers("slug", slugify)
       slug = StringField()

See :doc:`core/overview` for the view and the template.

Features
--------

- **Declare interactivity in Python.**
  Right on the field declaration, not scattered across ``hx-*``
  attributes.
- **No extra endpoints.** The form's existing view handles every
  interaction. You don't write a new route for each one.
- **Progressive enhancement.** The form works without JavaScript;
  htmx layers live updates and partial swaps on top. Same form, two
  render paths. See :doc:`explanation/progressive_enhancement`.
- **Opinionated defaults, fully overridable.** wtforms-htmx renders
  the right ``hx-*`` for you, but they're yours to tweak. See
  :ref:`attribute-precedence`.
- **Patterns built in.** Inline validation, autocomplete,
  :class:`~wtforms.fields.FieldList` add/remove/reorder, dependent fields: all declarative
  in a few lines.

Related packages
----------------

- :external+wtforms-htmx-components:doc:`wtforms-htmx-components <index>`
  provides ready-made interactive fields, such as a combobox.
- :external+flask-wtforms-htmx:doc:`flask-wtforms-htmx <index>`
  provides :class:`~flask_wtforms_htmx.HtmxFlaskForm`, a drop-in
  :class:`~flask_wtf.FlaskForm` for
  :external+flask-wtf:doc:`Flask-WTF <index>`.

.. toctree::
    :caption: Overview
    :maxdepth: 1

    core/overview

.. toctree::
    :caption: How-to guides
    :maxdepth: 1

    how-to/migrate
    how-to/inline_validation
    how-to/datalist
    how-to/mutations
    how-to/render_fields
    how-to/dispatch_submits
    how-to/raw_htmx

.. toctree::
    :caption: Reference
    :maxdepth: 1

    core/api
    core/mutations

.. toctree::
    :caption: Explanation
    :maxdepth: 1

    explanation/architecture
    explanation/mutations
    explanation/swap_strategies
    explanation/progressive_enhancement

.. toctree::
    :caption: Examples
    :maxdepth: 1

    examples/password
    examples/title_slug
    examples/markdown_preview
    examples/auto_save
    examples/currency
    examples/cycle_button
    examples/inline_edit
    examples/tag_picker
    examples/dual_listbox
    examples/bulk_actions
    examples/combobox
    examples/task_list
    examples/address
    examples/invoice
    examples/faceted_search
    examples/pagination
    examples/attendance

.. toctree::
    :caption: Project
    :maxdepth: 1

    contributing
    changes
