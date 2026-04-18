Pagination
==========

Pagination built from one :class:`~wtforms.fields.SelectField` whose
options render as buttons. Prev and Next are options too, so a click
sets ``page.data`` directly, with no custom mutation. The form uses GET, so the
page number lives in the URL.

.. automodule:: examples.pagination
   :no-members:
   :no-index:

The core declaration is one :class:`~wtforms.fields.SelectField` with a callable
``choices`` that re-emits the whole nav on every render:

.. code-block:: python

    class PaginationForm(HtmxForm):
        class Meta:
            htmx_method = "get"

        page = SelectField(
            choices=_page_choices,
            option_widget=Button(),
            validate_choice=False,
            widget=pagination_nav_widget,
        )

        # A page click re-renders the nav and the results.
        page.triggers(["page", "#results"], repaint_results)

The choices callable builds Prev, the numbered pages, then Next.
Each option carries its own ``render_kw``, with ``aria-current`` on
the active page, ``disabled`` at the bounds, and ``aria-label`` for
screen readers:

.. code-block:: python

    def _page_choices(form, _field):
        total = total_pages()
        current = _current_page(form)

        prev_kw = {"aria-label": "Previous page", "class": "page-prev"}
        if current == 1:
            prev_kw |= {"disabled": True, "aria-disabled": "true"}

        next_kw = {"aria-label": "Next page", "class": "page-next"}
        if current == total:
            next_kw |= {"disabled": True, "aria-disabled": "true"}

        choices = [SelectChoice(str(max(1, current - 1)), "←", render_kw=prev_kw)]
        for n in range(1, total + 1):
            kw = {"aria-label": f"Go to page {n}"}
            if n == current:
                kw |= {"aria-current": "page", "disabled": True}

            choices.append(SelectChoice(str(n), str(n), render_kw=kw))

        choices.append(
            SelectChoice(str(min(total, current + 1)), "→", render_kw=next_kw)
        )
        return choices

The form has no :class:`~wtforms.fields.SubmitField`: the current
page is view state, not data to save. Each page button also carries
:htmx-attr:`hx-push-url`, so the URL follows the page: reloading it, or
going back, shows the same page.

Per-option attributes
---------------------

WTForms passes the *field-level* ``render_kw`` to every option, not
the per-choice one. The widget here merges ``opt.choice.render_kw``
with the form's :meth:`~wtforms_htmx.HtmxFormMixin.htmx_submit_attrs` so each button keeps its own
``disabled`` / ``aria-current`` / ``aria-label`` alongside the shared
``hx-*`` attributes:

.. code-block:: jinja

    {%- for opt in field -%}
      {%- set attrs = dict(opt.choice.render_kw,
                           **opt._form.htmx_submit_attrs(opt)) -%}
      {%- set _ = attrs.update({"hx-push-url": "true"}) -%}
      <li>{{ opt(label=opt.choice.label, **attrs) }}</li>
    {%- endfor -%}

Same idiom as the :doc:`combobox` listbox, where ``disabled`` is
used to mark already-picked options.

Without JavaScript
------------------

Each page button is a plain submit button. A click submits the form as
a GET, and the page comes back with that page of results and
``?page=<n>`` in its URL.

See also
--------

- :doc:`faceted_search`: same ``repaint_results`` callback shape;
  results are a plain DOM section targeted by selector.
- :doc:`combobox`: also styles each listbox option through
  ``SelectChoice.render_kw``.
- :doc:`/how-to/mutations`: when to reach for a mutation and the
  multi-form layout patterns that come with it.
