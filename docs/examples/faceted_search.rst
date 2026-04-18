Faceted search
==============

Several filters drive one result list, with the active filters shown as
chips. The form uses GET, so the filters live in the URL: a search can
be reloaded, bookmarked or shared.

.. automodule:: examples.faceted_search
   :no-members:
   :no-index:

The example builds one search UX:

- populated filters as chips: clicking a chip's ``×`` clears the
  corresponding facet, through a ``clear_facet`` callback;
- cascade datalists: ``Author``'s suggestions read
  ``genre.data`` and ``language.data`` directly, so the popup
  shrinks as sibling facets are typed (the standalone pattern is
  shown in :doc:`address`);
- live result list: typing in the query, or changing a facet,
  refreshes the result list.

The example introduces no new primitive. The chips and the filter
panel are fields rendered by Jinja macros. The results listing is a
plain DOM section targeted by selector (``#results``), re-rendered by a
callback on every facet and query trigger:

.. code-block:: python

    def repaint_results(form, source, target):
        if target == "#results":
            return render_results(form)

        return None


    class FacetedSearchForm(HtmxForm):
        class Meta:
            htmx_method = "get"

        query = StringField("Search", render_kw={"hx-push-url": "true"})
        genre = SelectField("Genre", choices=GENRES)
        author = StringField("Author", datalist=DataList(suggest_authors))
        # language, year_from, year_to: same shape as genre
        chips = SelectField(choices=[], widget=chips_widget)
        filters = SelectField(choices=[], widget=filters_widget)
        clear = ButtonField("×")
        apply = SubmitField("Apply")

        # Typing in the query repaints the results.
        query.triggers("#results", repaint_results)

        # A facet change repaints the results and the chips.
        genre.triggers(["#results", "chips"], repaint_results, on="change")
        author.triggers(["#results", "chips"], repaint_results, on="change")

        # Clearing a chip also re-renders the filter panel.
        clear.triggers(["#results", "chips", "filters"], clear_facet)

``htmx_method = "get"`` makes every request a GET with the form in the
query string, and :htmx-attr:`hx-push-url` copies that URL to the
address bar after each search. The view builds the form from
``request.args``. ``repaint_results`` returns the listing HTML for the
``#results`` selector, and ``None`` for the ``chips`` field, which then
re-renders with its own widget. The ``chips`` field sends its own
request, so a facet change makes two requests. ``clear_facet`` empties the facet named in the
clicked chip's ``value``, then repaints the same way.

Without JavaScript
------------------

Typing and facet changes trigger nothing. ``Apply`` submits the form
as a GET, so the page comes back filtered with the filters in its URL.
A chip's ``×`` submits the form too, with that facet cleared.

See also
--------

- :doc:`address`: the cascade datalist on its own.
- :ref:`dom-targets`: targeting ``#results``, an element that is not a
  field.
