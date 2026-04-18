"""Page-by-page navigation built on a single :class:`~wtforms.fields.SelectField`. The
``page`` field carries the current page number; its choices (Prev,
the numbered pages, Next) are rendered as buttons via
``option_widget=Button()``. Clicking any of them is a regular
SelectField change: the button's ``value`` becomes the new
``page.data`` on bind, so Prev/Next need no custom mutation. Their
target page is computed at render time as ``current ± 1`` clamped to
``[1, total]``. A ``repaint_results`` callback, a copy of the one in
:doc:`/examples/faceted_search`, re-renders the listing for
``#results``, while the library re-renders the nav itself
out-of-band.

.. screencast:: |examples|/pagination
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const $ = (s) => document.querySelector(s);
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     await wait(700);
     // Jump to page 3 by clicking its numbered button.
     $('nav.pagination button[value="3"]').click();
     await wait(900);
     // Click Next, advancing to page 4.
     $('nav.pagination button[aria-label="Next page"]').click();
     await wait(900);
     // Click Prev three times, back to page 1.
     for (let i = 0; i < 3; i++) {
       $('nav.pagination button[aria-label="Previous page"]').click();
       await wait(700);
     }
     document.activeElement.blur();
     await wait(300);

   Click a numbered button to jump straight to that page; click
   ``←`` / ``→`` to step one page at a time. Prev/Next are options
   of the same ``SelectField``. Their ``value`` is the target page,
   computed at render time.
"""

from __future__ import annotations

from typing import Any

from flask import current_app
from flask import render_template
from flask import request
from flask import Response
from markupsafe import Markup
from wtforms import SelectChoice
from wtforms import SelectField
from wtforms.widgets import Button

from . import bp
from ._shared import ExampleForm
from ._shared import jinja_widget

PAGE_SIZE = 10

#: A small catalog of fictional blog posts. The dataset is sized
#: so that the default 10-per-page split yields five pages, enough
#: to exercise jump-to-N alongside Prev/Next without needing an
#: ellipsis window.
POSTS: list[dict[str, Any]] = [
    {
        "id": 1,
        "title": "Why your forms should know about htmx",
        "author": "Ada Pham",
        "date": "2025-11-04",
    },
    {
        "id": 2,
        "title": "Server-rendered autocomplete in 40 lines",
        "author": "Beatriz Cordeiro",
        "date": "2025-10-29",
    },
    {
        "id": 3,
        "title": "Validating across fields without JavaScript",
        "author": "Chen Wei",
        "date": "2025-10-21",
    },
    {
        "id": 4,
        "title": "A short tour of WTForms' filters",
        "author": "Diego Larrea",
        "date": "2025-10-14",
    },
    {
        "id": 5,
        "title": "Out-of-band swaps explained",
        "author": "Elin Bergström",
        "date": "2025-10-07",
    },
    {
        "id": 6,
        "title": "From <form> to live form in three diffs",
        "author": "Farouk Halimi",
        "date": "2025-09-30",
    },
    {
        "id": 7,
        "title": "Why hx-trigger='change' beats onchange",
        "author": "Gita Rao",
        "date": "2025-09-23",
    },
    {
        "id": 8,
        "title": "FieldList: add, remove, reorder",
        "author": "Hiroshi Tanaka",
        "date": "2025-09-16",
    },
    {
        "id": 9,
        "title": "Building a chip picker with no JS",
        "author": "Ines Vieira",
        "date": "2025-09-09",
    },
    {
        "id": 10,
        "title": "The case for progressive enhancement in 2025",
        "author": "Jonas Krüger",
        "date": "2025-09-02",
    },
    {
        "id": 11,
        "title": "Why we removed our SPA",
        "author": "Kavya Menon",
        "date": "2025-08-26",
    },
    {
        "id": 12,
        "title": "Pico CSS for tiny demos",
        "author": "Lior Avraham",
        "date": "2025-08-19",
    },
    {
        "id": 13,
        "title": "Coerce vs filter — a WTForms cheat sheet",
        "author": "Margaux Renault",
        "date": "2025-08-12",
    },
    {
        "id": 14,
        "title": "Triggers, debounces and other htmx tempos",
        "author": "Noor Habibi",
        "date": "2025-08-05",
    },
    {
        "id": 15,
        "title": "Five render_kw tricks you'll keep using",
        "author": "Ola Sandberg",
        "date": "2025-07-29",
    },
    {
        "id": 16,
        "title": "Datalists are underrated",
        "author": "Priya Sharma",
        "date": "2025-07-22",
    },
    {
        "id": 17,
        "title": "Custom widgets without leaving Jinja",
        "author": "Quentin Boyer",
        "date": "2025-07-15",
    },
    {
        "id": 18,
        "title": "Submit semantics, the long version",
        "author": "Rosa Iglesias",
        "date": "2025-07-08",
    },
    {
        "id": 19,
        "title": "Reading raw_data when data lies",
        "author": "Samir El-Hashem",
        "date": "2025-07-01",
    },
    {
        "id": 20,
        "title": "Why your inline edit needs two states, not three",
        "author": "Tomás Vidal",
        "date": "2025-06-24",
    },
    {
        "id": 21,
        "title": "Cascading selects, the cheap way",
        "author": "Ula Petrović",
        "date": "2025-06-17",
    },
    {
        "id": 22,
        "title": "Wrapping FormField for reusable address blocks",
        "author": "Viktor Janošík",
        "date": "2025-06-10",
    },
    {
        "id": 23,
        "title": "Auto-save without losing keystrokes",
        "author": "Wafa Saidi",
        "date": "2025-06-03",
    },
    {
        "id": 24,
        "title": "Live error messages that don't shout",
        "author": "Xavi Puig",
        "date": "2025-05-27",
    },
    {
        "id": 25,
        "title": "A markdown preview pane in 30 lines",
        "author": "Yara Costa",
        "date": "2025-05-20",
    },
    {
        "id": 26,
        "title": "Drag-to-reorder with SortableJS and FieldList",
        "author": "Zineb Bensalah",
        "date": "2025-05-13",
    },
    {
        "id": 27,
        "title": "Faceted search without a search engine",
        "author": "Ada Pham",
        "date": "2025-05-06",
    },
    {
        "id": 28,
        "title": "Why your Save button should be a SubmitField",
        "author": "Beatriz Cordeiro",
        "date": "2025-04-29",
    },
    {
        "id": 29,
        "title": "Pagination patterns for server-rendered apps",
        "author": "Chen Wei",
        "date": "2025-04-22",
    },
    {
        "id": 30,
        "title": "When to use selectors vs field targets",
        "author": "Diego Larrea",
        "date": "2025-04-15",
    },
    {
        "id": 31,
        "title": "Per-row totals in nested FormFields",
        "author": "Elin Bergström",
        "date": "2025-04-08",
    },
    {
        "id": 32,
        "title": "Cycle buttons, presence grids, and other cell rotations",
        "author": "Farouk Halimi",
        "date": "2025-04-01",
    },
    {
        "id": 33,
        "title": "Dual listbox: shuttle UIs revisited",
        "author": "Gita Rao",
        "date": "2025-03-25",
    },
    {
        "id": 34,
        "title": "Why your form should redirect on success",
        "author": "Hiroshi Tanaka",
        "date": "2025-03-18",
    },
    {
        "id": 35,
        "title": "Composing widgets with Jinja macros",
        "author": "Ines Vieira",
        "date": "2025-03-11",
    },
    {
        "id": 36,
        "title": "Multi-target swaps, one round-trip",
        "author": "Jonas Krüger",
        "date": "2025-03-04",
    },
    {
        "id": 37,
        "title": "Custom mutations: when and why",
        "author": "Kavya Menon",
        "date": "2025-02-25",
    },
    {
        "id": 38,
        "title": "Reading sibling fields from a callable choices",
        "author": "Lior Avraham",
        "date": "2025-02-18",
    },
    {
        "id": 39,
        "title": "The shape of a good ExampleForm base class",
        "author": "Margaux Renault",
        "date": "2025-02-11",
    },
    {
        "id": 40,
        "title": "ARIA attributes for form widgets, briefly",
        "author": "Noor Habibi",
        "date": "2025-02-04",
    },
    {
        "id": 41,
        "title": "Why aria-current beats CSS-only highlighting",
        "author": "Ola Sandberg",
        "date": "2025-01-28",
    },
    {
        "id": 42,
        "title": "What I learned writing 30 wtforms-htmx demos",
        "author": "Priya Sharma",
        "date": "2025-01-21",
    },
    {
        "id": 43,
        "title": "Choices as callables: the underused trick",
        "author": "Quentin Boyer",
        "date": "2025-01-14",
    },
    {
        "id": 44,
        "title": "How SelectChoice.render_kw unlocks per-option styling",
        "author": "Rosa Iglesias",
        "date": "2025-01-07",
    },
    {
        "id": 45,
        "title": "A short note on hx-swap-oob",
        "author": "Samir El-Hashem",
        "date": "2024-12-31",
    },
    {
        "id": 46,
        "title": "Validators that read each other",
        "author": "Tomás Vidal",
        "date": "2024-12-24",
    },
    {
        "id": 47,
        "title": "Closing tabs on the SPA era",
        "author": "Ula Petrović",
        "date": "2024-12-17",
    },
]


def total_pages() -> int:
    return max(1, (len(POSTS) + PAGE_SIZE - 1) // PAGE_SIZE)


def _current_page(form: Any) -> int:
    try:
        n = int(form.page.data or 1)
    except (TypeError, ValueError):
        n = 1

    return max(1, min(n, total_pages()))


def _page_choices(form: Any, _field: Any) -> list[SelectChoice]:
    """Build the nav: Prev, numbered pages, Next.

    Prev/Next are *options* of the same SelectField. Their ``value``
    is the target page (``current ± 1`` clamped). At the boundaries
    the corresponding choice is rendered ``disabled`` via its
    ``render_kw``; clicking the active page is also disabled.
    """
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
        kw: dict[str, Any] = {
            "aria-label": f"Go to page {n}",
            "class": "page-number",
        }
        if n == current:
            kw |= {
                "aria-current": "page",
                "disabled": True,
                "aria-disabled": "true",
            }

        choices.append(SelectChoice(str(n), str(n), render_kw=kw))

    choices.append(SelectChoice(str(min(total, current + 1)), "→", render_kw=next_kw))
    return choices


def _current_posts(form: Any) -> list[dict]:
    start = (_current_page(form) - 1) * PAGE_SIZE
    return POSTS[start : start + PAGE_SIZE]


def _render_results(form: Any) -> Markup:
    module = current_app.jinja_env.get_template("_pagination_widgets.html").module
    return Markup(module.results_list(form))


def repaint_results(form: Any, source: Any, target: Any) -> Any:
    """Re-render ``#results``, and let the library re-render the nav.

    Return ``None`` for the ``page`` target, so its own widget renders it.
    """
    if target == "#results":
        return _render_results(form)

    return None


class PaginationForm(ExampleForm):
    """Pagination form whose ``page`` options render the whole nav.

    The options are Prev, the numbered pages and Next.
    """

    class Meta:
        # No field on this form has a validator worth a blur-time swap.
        htmx_inline_validation = False
        htmx_method = "get"

    page = SelectField(
        choices=_page_choices,
        option_widget=Button(),
        validate_choice=False,
        widget=jinja_widget("_pagination_widgets.html", "pagination_nav"),
        wrapper=False,
    )

    # A page click re-renders the nav and the results.
    page.triggers(["page", "#results"], repaint_results)

    def current_posts(self) -> list[dict]:
        return _current_posts(self)

    def current_page(self) -> int:
        return _current_page(self)

    def total_pages(self) -> int:
        return total_pages()

    def posts_range(self) -> tuple[int, int, int]:
        """``(first, last, total)``: 1-indexed range of the current slice."""
        start = (_current_page(self) - 1) * PAGE_SIZE
        end = min(start + PAGE_SIZE, len(POSTS))
        return start + 1, end, len(POSTS)


@bp.route("/pagination")
def pagination():
    form = PaginationForm(request.args or None, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    return render_template("pagination.html", form=form)
