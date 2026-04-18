Writing htmx by hand
====================

wtforms-htmx renders the htmx attributes for the patterns it knows:
inline validation, :doc:`datalists <datalist>`, :ref:`trigger
declarations <trigger-declarations>`. Everything else is yours to write.
This guide shows you how to add htmx the library does not generate,
override what it does, change the request verb, and emit response
headers from your view.

For the reasoning behind where the library draws the line, see
:doc:`/explanation/architecture`. For the exact merge order, see
:ref:`attribute-precedence`.

Keep the id of a field that sends requests
------------------------------------------

The library finds the field behind a request by the
:mdn-global-attr:`id` of the element that sent it. WTForms gives every
field an :mdn-global-attr:`id`, so keep it. Do not render a field that
sends or listens to requests with ``id=False``. A :ref:`field wrapper
<field-wrapper>` must keep the :mdn-global-attr:`id` on the input.

Buttons are the exception. The library finds a clicked button by its
posted :mdn-attr:`button#name`, so a button rendered on every row can drop its
:mdn-global-attr:`id`.

An element that is not a field is not handled by the library. For a
request it sends, :meth:`~wtforms_htmx.HtmxFormMixin.partial` returns
``None``. Point such an element at a route of its own:

.. code-block:: html

    <button type="button" hx-get="/cities" hx-target="#city-list">
        Refresh
    </button>

Set or override an htmx attribute
---------------------------------

Set any htmx attribute in ``render_kw``, the WTForms argument you
already use for HTML attributes. Set it on the field declaration, or at
the call site to vary it per render.

.. code-block:: python

    from wtforms import ButtonField, FieldList, StringField
    from wtforms_htmx import HtmxForm
    from wtforms_htmx.mutations import list_remove

    class TodoForm(HtmxForm):
        items = FieldList(StringField())
        # add an attribute the library doesn't generate
        rm_item = ButtonField(
            "Delete",
            render_kw={"hx-confirm": "Delete the last item?"},
        )
        # override the hx-swap inline validation sets: wait 200 ms before the swap
        note = StringField(render_kw={"hx-swap": "outerHTML swap:200ms"})

        rm_item.triggers("items", list_remove)

A key passed at the call site wins over the declaration and over the
library's defaults, handy for a value that depends on the page, like
an :htmx-attr:`hx-indicator` spinner:

.. code-block:: jinja

    {{ form.note(**{"hx-indicator": "#note-spinner"}) }}

Those are *per-field* overrides. The computed defaults are themselves
form-wide settings on :class:`~wtforms_htmx.HtmxMeta`: the request
endpoint (:attr:`~wtforms_htmx.HtmxMeta.htmx_endpoint`), verb
(:attr:`~wtforms_htmx.HtmxMeta.htmx_method`), trigger declaration event
(:attr:`~wtforms_htmx.HtmxMeta.htmx_default_trigger`), inline-validation
trigger (:attr:`~wtforms_htmx.HtmxMeta.htmx_validation_trigger`) and swap
(:attr:`~wtforms_htmx.HtmxMeta.htmx_swap`). Set one there to retune it
across every field at once, instead of repeating ``render_kw``:

.. code-block:: python

    class ProfileForm(HtmxForm):
        class Meta:
            htmx_validation_trigger = "change delay:200ms"

Switch the request verb to GET
------------------------------

By default every auto-wired request is a ``POST``. Set
:attr:`~wtforms_htmx.HtmxMeta.htmx_method` to change the verb the
library emits everywhere (inline validation, datalist refresh,
trigger declarations, including buttons that declare one):

.. code-block:: python

    class SearchForm(HtmxForm):
        class Meta:
            htmx_method = "get"

        query = StringField()

The library only emits the attribute. Your view must read the matching
request data. A ``"get"`` form arrives with its fields in the query
string, so build it from ``request.values`` (or ``request.args``)
rather than ``request.form``. The same goes for any callback that
reads the request:

.. code-block:: python

    form = SearchForm(request.values or None, headers=request.headers)

See :doc:`/examples/faceted_search` and :doc:`/examples/pagination` for
two forms that use GET, and :doc:`/explanation/architecture` for why
``POST`` is the default.

Add an htmx response header
---------------------------

wtforms-htmx sets :htmx-header:`hx-retarget` and
:htmx-header:`hx-reswap`. Add any other htmx response header yourself,
by merging it into the framework response. This example adds an
:htmx-header:`hx-trigger` header to fire a client event after a
mutation:

.. code-block:: python

    result = form.partial()
    if result:
        return Response(
            result.body,
            headers={**result.headers, "HX-Trigger": "itemAdded"},
        )

Merge into a fresh dict rather than assigning to ``result.headers``,
which may be a read-only mapping. See
:class:`~wtforms_htmx.HtmxResponse`.

See also
--------

- :ref:`attribute-precedence`: the merge order of htmx attributes.
- :doc:`/explanation/architecture`: where the library stops.
