Triggering mutations
====================

A *trigger declaration* wires an event on one field to a re-render of
another. An optional callback adjusts the target first, usually its
data, but its label or any other render state too. Declare it with
:meth:`.triggers(target, callback)
<wtforms.fields.core.UnboundField.triggers>` on the source field, or
with the symmetric :meth:`.triggered_by(source, callback)
<wtforms.fields.core.UnboundField.triggered_by>` on the target.

This page collects practical recipes for the most common patterns. For
the conceptual model and the dispatch path, see
:doc:`/explanation/mutations`. For the reference of the shipped
callbacks, see :doc:`/core/mutations`.

Derive a value from a typing source
-----------------------------------

Update a target field automatically each time the user types into a
source field.

.. code-block:: python

    import re
    from wtforms import StringField
    from wtforms_htmx import HtmxForm


    def derive_slug(form, source, target):
        target.data = re.sub(
            r"[^a-z0-9]+", "-", (source.data or "").lower()
        ).strip("-")


    class PostForm(HtmxForm):
        title = StringField("Title").triggers("slug", derive_slug)
        slug = StringField("Slug")

The callback returns nothing: wtforms-htmx re-renders ``slug`` with
the new ``target.data`` value. No template change
needed.

Without JavaScript, the ``input`` event no longer triggers an htmx
swap, so the ``slug`` is never derived as the user types. Compute it on
the server instead, by calling the callback yourself when the form is
submitted::

    derive_slug(form, form.title, form.slug)

Re-render a dependent field
---------------------------

When a field's render depends on another field, declare the trigger
without a callback. The target re-renders from the current form state,
so a :class:`~wtforms.fields.SelectField` whose ``choices`` callable
reads a sibling gets fresh options:

.. code-block:: python

    CITIES = {"fr": ["Paris", "Lyon"], "jp": ["Tokyo", "Osaka"]}


    def cities(form, field):
        return CITIES.get(form.country.data, [])


    class AddressForm(HtmxForm):
        country = SelectField(
            choices=[("fr", "France"), ("jp", "Japan")], default="fr"
        )
        city = SelectField(choices=cities)

        city.triggered_by("country", on="change")

Picking a country re-renders ``city`` with the cities of that country.
Without JavaScript, nothing happens until the next submit. Add a button
that triggers the same target, like the ``Apply`` button of
:doc:`/examples/address`.

Change the triggering event
---------------------------

A field source fires on ``input delay:200ms`` by default: once the
user pauses typing for 200 ms. A button source fires on click. Pass
``on=`` to use another :htmx-attr:`hx-trigger` event:

.. code-block:: python

    country.triggers("city", on="change")
    query.triggers("results", on="input delay:500ms")
    name.triggers("mode", restore, on="keyup[key=='Escape']")

To change the default for every declaration of a form, set
:attr:`~wtforms_htmx.HtmxMeta.htmx_default_trigger` on its ``Meta``.

The event decides which field sends the request. For a typing event
(``input``, ``keyup``, ``keydown``, ``keypress``), the target listens to
the source and sends it. For any other event, the source sends it. The
target then shows no validation error, even when it is required and
still empty: the user has not reached it yet. A callback can still
validate it, for instance when it already has a value:

.. code-block:: python

    def revalidate(form, source, target):
        if target.data:
            target.validate(form)

    postal_code.triggered_by("country", revalidate, on="change")

See :doc:`/explanation/mutations` for the details.

On htmx 4.0.0, an event with the ``changed`` modifier never fires when
the source is another field (see :ref:`source rendering
<trigger-sources>`).

React to any field change
-------------------------

When the target should re-render on *any* sibling event rather than on
a specific source, pass the wildcard ``"*"`` to
:meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>`.

.. code-block:: python

    from wtforms import ButtonField, StringField
    from wtforms_htmx import HtmxForm


    def acknowledge(form, source, target):
        target.label.text = "Saved" if form.validate() else "Pending changes"


    class ProfileForm(HtmxForm):
        name = StringField("Name")
        email = StringField("Email")
        status = ButtonField("Save").triggered_by("*", acknowledge)

The target listens to every field of the form. A
:class:`~wtforms.fields.FieldList` counts as one field, so rows added
later are covered too. The callback receives ``source=None`` because
there is no single source field to identify.

.. _wildcard-limits:

The wildcard has limits:

- Inputs in the :mdn-tag:`form` that are not WTForms fields do not
  trigger the target.
- A field rendered by a direct ``field.widget(...)`` call does not
  trigger the target either (see :ref:`source rendering <trigger-sources>`).

Only :meth:`.triggered_by()
<wtforms.fields.core.UnboundField.triggered_by>` accepts the wildcard;
``.triggers("*")`` raises a :exc:`ValueError`. The :doc:`/examples/auto_save`
showcase builds the full pattern around this wiring.

.. _cross-form-targets:

Target a field in a sub-form, parent, or list entry
---------------------------------------------------

A trigger declaration's target can be:

- a field, by name: a Python identifier or a dotted path, like
  ``"phone_number"`` or ``"address.region"``, resolved in the form where
  the trigger is declared. A bare name is a sibling, and a dotted path
  descends into a sub-form.
- a field, by id: a ``"#id"`` matching a field's rendered :mdn-global-attr:`id`
  anywhere in the form tree, including a parent or sibling form.
- a DOM element: any other selector, handed to htmx as-is. See
  :ref:`how to wire a mutation onto your own HTML <render-into-dom>` for
  more details.

.. code-block:: python

    quantity.triggers("total", recompute)        # sibling
    country.triggers("address.region", fill)     # field of a sibling sub-form
    rm_order.triggers("#orders", list_remove)    # a field at the root form
    qty.triggers("#orders-2-total", recompute)   # a field of a specific FieldList entry

A name resolves **only within the form that declares it**. It never
climbs to the parent. To reach a field *outside* that form, address it
by ``#id``: a parent field, another branch, a specific
:class:`~wtforms.fields.FieldList` entry. By default that :mdn-global-attr:`id` is the
``-``-joined path WTForms builds, or whatever :mdn-global-attr:`id` you gave the
field.

A name or ``#id`` that matches no field is handed to htmx as a plain
selector. A typo then finds nothing client-side rather than raising.

Resolution is the same on the htmx and no-JS paths.

Add and remove rows from a FieldList
------------------------------------

Grow or shrink a :class:`~wtforms.fields.FieldList` with two button
fields that work identically on htmx and no-JS paths.

.. code-block:: python

    from wtforms import ButtonField, FieldList, StringField
    from wtforms_htmx import HtmxForm
    from wtforms_htmx.mutations import list_add, list_remove


    class TagsForm(HtmxForm):
        tags = FieldList(StringField(), min_entries=1)
        add_tag = ButtonField("Add tag").triggers("tags", list_add)
        rm_tag = ButtonField("Remove tag").triggers("tags", list_remove)

Both callbacks ship with :mod:`wtforms_htmx.mutations`, which bundles a
handful of built-in list mutations. The layouts below cover the
common cases.

Whole-list buttons
~~~~~~~~~~~~~~~~~~

Render the buttons once outside the loop, with no ``value``. Then
:func:`~wtforms_htmx.mutations.list_add` appends a fresh entry at the
end and :func:`~wtforms_htmx.mutations.list_remove` pops the last one:

.. code-block:: jinja

    {% for entry in form.tags %}
      {{ entry() }}
    {% endfor %}
    {{ form.add_tag() }}
    {{ form.rm_tag() }}

Per-row buttons
~~~~~~~~~~~~~~~

To target a *given* row, render the same buttons inside the FieldList
loop and pass that row's index as the button ``value``.
:func:`~wtforms_htmx.mutations.list_add` then inserts at that index
(shifting the rest down) and :func:`~wtforms_htmx.mutations.list_remove`
drops it:

.. code-block:: jinja

    {% for entry in form.tags %}
      {{ entry() }}
      {{ form.add_tag(value=loop.index0, id=False) }}
      {{ form.rm_tag(value=loop.index0, id=False) }}
    {% endfor %}

Each button is rendered once per row, so pass ``id=False`` to avoid
duplicating its :mdn-global-attr:`id`, or suffix it (``id="rm_tag-" ~ loop.index0``)
if you need to address them individually. The shared :mdn-attr:`button#name` stays
unambiguous: only the clicked button is submitted.

Buttons inside the row
~~~~~~~~~~~~~~~~~~~~~~~~

To keep each row self-contained, bundle the field and its buttons in a
sub-form and use that as a :class:`~wtforms.fields.FormField` entry. The
buttons now live *inside* the row, where ``"tags"`` is no longer a
sibling. Reach the parent :class:`~wtforms.fields.FieldList`
:ref:`by its id <cross-form-targets>` instead.

.. code-block:: python

    from wtforms import ButtonField, FieldList, FormField, StringField
    from wtforms_htmx import HtmxForm
    from wtforms_htmx.mutations import list_add, list_remove


    class TagRow(HtmxForm):
        value = StringField()
        add_tag = ButtonField("Add").triggers("#tags", list_add)
        rm_tag = ButtonField("Remove").triggers("#tags", list_remove)


    class TagsForm(HtmxForm):
        tags = FieldList(FormField(TagRow), min_entries=1)

.. code-block:: jinja

    {% for entry in form.tags %}
      {{ entry.value() }}
      {{ entry.add_tag(value=loop.index0) }}
      {{ entry.rm_tag(value=loop.index0) }}
    {% endfor %}

Each row is its own sub-form instance, so the buttons already carry
distinct ids (``tags-0-rm_tag``, ``tags-1-rm_tag``…): no ``id=False``
is needed, unlike the form-level variant above. Pass
``value=loop.index0`` so the stock callbacks know which row to act on.

Move rows up and down
---------------------

:func:`~wtforms_htmx.mutations.list_move` moves a row by an offset.
Render a ↑ and a ↓ button per row, with the row index as the button
``value``:

.. code-block:: python

    from wtforms_htmx.mutations import list_move


    class TasksForm(HtmxForm):
        tasks = FieldList(StringField(), min_entries=1)
        move_up = ButtonField("↑").triggers("tasks", list_move(-1))
        move_down = ButtonField("↓").triggers("tasks", list_move(+1))

.. code-block:: jinja

    {% for entry in form.tasks %}
      {{ entry() }}
      {{ form.move_up(value=loop.index0, id=False, disabled=loop.first) }}
      {{ form.move_down(value=loop.index0, id=False, disabled=loop.last) }}
    {% endfor %}

A move past either end of the list does nothing, so ``disabled`` only
tells the user. The buttons work without JavaScript. Keep them next to
any drag-and-drop: dragging needs a pointer, and these buttons also
work from the keyboard. See :doc:`/examples/task_list` for both together.

Tell a mutation click from a submit
-----------------------------------

Without JavaScript, clicking "Add tag" is an ordinary full-page
POST, indistinguishable by HTTP method from a submit. A plain
``if request.method == "POST"`` save branch would treat the mutation
click as a submit. Give the form a save button, and save only when
:attr:`~wtforms_htmx.HtmxFormMixin.submitter` is that button:

.. code-block:: python
   :emphasize-lines: 4,13

    class TagsForm(HtmxForm):
        tags = FieldList(StringField(), min_entries=1)
        add_tag = ButtonField("Add tag").triggers("tags", list_add)
        save = SubmitField("Save")


    def tags_view(request):
        form = TagsForm(request.form or None, headers=request.headers)

        if result := form.partial():
            return Response(result.body, headers=result.headers)

        if form.submitter is form.save and form.validate():
            save(form.data)
            return redirect("/tags")

        return render_template("tags.html", form=form)

A click on "Add tag" sets :attr:`~wtforms_htmx.HtmxFormMixin.submitter` to
``form.add_tag``, so the view skips the save and re-renders the form. The
mutation was already applied during form construction, so the page
shows the new row.

If the save button is a ``<button type="submit">`` written in the
template without a :mdn-attr:`button#name`, a submit leaves ``submitter`` at ``None``.
A GET does too, so test for a POST as well:
``request.method == "POST" and form.submitter is None``. To route among several submit
buttons, see :doc:`/how-to/dispatch_submits`.

To skip the save on any mutation, without naming the save button, check
:attr:`~wtforms_htmx.HtmxFormMixin.mutated` instead:

.. code-block:: python

    if request.method == "POST" and not form.mutated and form.validate():
        save(form.data)

.. _render-into-dom:

Render into a DOM element that is not a form field
--------------------------------------------------

When the target is a piece of HTML you maintain yourself (a live
preview, a status panel, a derived display), pass an htmx selector to
:meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` instead
of a field name, and return the rendered HTML from the callback.

.. code-block:: python

    from wtforms import TextAreaField
    from wtforms_htmx import HtmxForm


    def render_preview(form, source, target):
        return markdown_to_html(form.content.data or "")


    class MarkdownForm(HtmxForm):
        content = TextAreaField(render_kw={"hx-swap": "innerHTML"})

        content.triggers("#preview", render_preview, on="input delay:100ms")

.. code-block:: jinja

    {{ form.content() }}
    <div id="preview"></div>

With ``hx-swap="innerHTML"``, the returned string goes inside
``#preview``. The element itself stays in the template. By default, the
swap uses ``outerHTML`` and replaces the whole element. The returned
HTML must then carry the same outer :mdn-global-attr:`id`, or the next trigger has
nothing left to target.

See :ref:`dom-targets` for the full selector vocabulary, and the
:ref:`return-value contract <callback-return>` for the ``None``-return
convention (OOB-only responses) and the other return types.

Replace a field's rendering
---------------------------

When you want a field target rendered as something other than its
widget, have the callback return the HTML as a string, as for a
:ref:`DOM target <render-into-dom>`. That string replaces the field's
default render.

.. code-block:: python

    from markupsafe import Markup, escape
    from wtforms import ButtonField, StringField
    from wtforms_htmx import HtmxForm


    def lock(form, source, target):
        value = escape(target.data or "")
        return Markup(
            f'<div id="{target.id}">{value}'
            f'<input type="hidden" name="{target.name}" value="{value}"></div>'
        )


    class CheckoutForm(HtmxForm):
        coupon = StringField()
        apply = ButtonField("Apply").triggers("coupon", lock)

For the swapped-in markup to stay a working field:

- **Keep the field's id**: the swap lands on it, and a later trigger
  can re-target it (to unlock, say).
- **Keep the value submittable**: render a hidden :mdn-tag:`input` with the
  field's :mdn-attr:`input#name`. Only the posted :mdn-attr:`input#name`
  and :mdn-attr:`input#value` matter.
- **Copy the field's htmx attributes**: the default render includes
  the field's :htmx-attr:`hx-trigger`, raw HTML does not. Without it,
  the field stops reacting to its sources.

Update multiple targets at once
-------------------------------

Several targets in one declaration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a list of targets to update several fields from one source:

.. code-block:: python

    postal_code = StringField().triggers(["city", "region"])
    lookup = ButtonField("Look up").triggers(["city", "region"])

A button sends one request: the first target is swapped as usual, and
the others are swapped out of band. A field source declared on a typing
event sends one request per target, so a callback runs once for each
target. On another event, such as ``change``, it sends one request, and
every target is swapped out of band.

A source can have several field targets, but at most one selector
target, whether in one list or in chained calls. More raise a
:exc:`ValueError` when the form is built. To update several DOM
elements, declare one and return the others from its callback, as
described next.

Several elements from one callback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A callback can return an iterable to refresh more than one element in
a single response. The first item is the primary swap: ``None`` keeps
the default render of ``target``, and an HTML ``str`` overrides it. The
other items are *out-of-band* extras. htmx places each one by its own
:mdn-global-attr:`id` (:htmx-attr:`hx-swap-oob`), not in the primary target.

Each extra can be a :class:`~wtforms.fields.Field` or an HTML ``str``.
The library adds ``hx-swap-oob="outerHTML"`` to both. Pick the variant
that matches the extra: a form field whose value should change, or a
DOM element that lives only in the template.

Form fields as extras
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from decimal import Decimal
    from wtforms import IntegerField, StringField
    from wtforms_htmx import HtmxForm


    def recompute(form, source, target):
        form.subtotal.data = compute_subtotal(form)
        form.tax.data = form.subtotal.data * Decimal("0.2")
        target.data = form.subtotal.data + form.tax.data
        return None, form.subtotal, form.tax


    class CartForm(HtmxForm):
        qty = IntegerField().triggers("total", recompute)
        subtotal = StringField()
        tax = StringField()
        total = StringField()

``None`` as the first item keeps the default render of the target,
``form.total``. ``form.subtotal`` and ``form.tax`` follow as
out-of-band swaps. Each field is rendered through its wrapper, so classes and
error markup stay consistent with the initial page render.

HTML fragments as extras
^^^^^^^^^^^^^^^^^^^^^^^^

When the target lives in the template as a plain DOM element (an
:mdn-tag:`output`, a counter, a status pill), return HTML strings
instead. Each string is one element with an :mdn-global-attr:`id`.

.. code-block:: python

    def recompute(form, source, target):
        target.data = compute_total(form)
        subtotal_html = f'<output id="subtotal">{compute_subtotal(form)}</output>'
        tax_html = f'<output id="tax">{compute_tax(form)}</output>'
        # None keeps the default primary render for `target`
        return None, subtotal_html, tax_html


    class CartForm(HtmxForm):
        qty = IntegerField().triggers("total", recompute)
        total = StringField()

As before, the leading ``None`` keeps ``form.total`` as the primary
swap. htmx swaps each fragment into the element with the same :mdn-global-attr:`id`.
The matching ``<output id="subtotal">`` and ``<output id="tax">`` live
in the template, not the form schema.

A string without an :mdn-global-attr:`id` on its outer element raises
:exc:`ValueError`. When a fragment sets :htmx-attr:`hx-swap-oob` itself,
or wraps its content in a :mdn-tag:`template`, the library leaves it
as is.

See also
--------

- :doc:`/explanation/mutations`: concept, dispatch path, and the
  callback anatomy.
- :doc:`/core/mutations`: reference for the shipped callbacks.
