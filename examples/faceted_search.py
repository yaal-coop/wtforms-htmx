"""Search with filters: a flat form whose populated
fields are surfaced as chips, an inline panel for adding more, and a
result list that updates on every change. Each facet is a typed
WTForms field with ``Optional()``; the chips and the filter panel are
display-only fields rendered by Jinja macros, while the results listing is a plain DOM section
re-rendered via a callback that targets ``#results`` by selector.

Cascade: ``Author``'s datalist reads ``form.genre.data`` and
``form.language.data`` directly, so the suggestions shrink as soon as
sibling facets are populated, even before the user clicks anywhere.
Same idiom as the address example's datalists, generalized.

.. screencast:: |examples|/faceted-search
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const $ = (s) => document.querySelector(s);
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     const dispatch = (el, type) =>
       el.dispatchEvent(new Event(type, {bubbles: true}));
     const waitFor = async (sel) => {
       while (!$(sel)) await wait(50);
     };
     await wait(500);
     // Open the filter dropdown.
     $('summary.facets-dropdown-summary').click();
     await wait(700);
     // Pick a genre: the chip appears, the results shrink.
     const genre = $('#genre');
     genre.value = 'Fantasy';
     dispatch(genre, 'change');
     await waitFor('.facets-bar-input .chip-remove');
     await wait(900);
     // Clear the chip: multi-target swap resets the <select>
     // OOB behind the still-open <details>.
     $('.facets-bar-input .chip-remove').click();
     await wait(700);
     // Close the dropdown, back to the initial state.
     $('summary.facets-dropdown-summary').click();
     document.activeElement.blur();
     await wait(600);

   Open the filter dropdown, pick a genre: the chip appears in
   the bar and the results shrink. Clearing the chip resets
   everything, including the ``<select>`` still mounted behind
   the open ``<details>`` (multi-target OOB swap).
"""

from __future__ import annotations

from typing import Any

from flask import current_app
from flask import render_template
from flask import request
from flask import Response
from markupsafe import Markup
from wtforms import ButtonField
from wtforms import DataList
from wtforms import DataListChoice
from wtforms import IntegerField
from wtforms import SelectChoice
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import NumberRange
from wtforms.validators import Optional

from . import bp
from ._shared import ExampleForm
from ._shared import jinja_widget

_PUSH_URL = {"hx-push-url": "true"}


GENRES = ["Fiction", "Sci-Fi", "Fantasy", "Mystery", "Non-fiction"]
LANGUAGES = ["English", "French", "Russian", "Japanese", "Spanish", "Italian"]

#: A small but cascading catalog. Genres span several authors,
#: authors span several languages, languages span several decades.
#: Any single facet materially shrinks the set, making the cascade
#: visible. Keep this tight; the goal is demonstration,
#: not coverage.
BOOKS: list[dict[str, Any]] = [
    {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "genre": "Sci-Fi",
        "language": "English",
        "year": 1969,
    },
    {
        "title": "The Dispossessed",
        "author": "Ursula K. Le Guin",
        "genre": "Sci-Fi",
        "language": "English",
        "year": 1974,
    },
    {
        "title": "A Wizard of Earthsea",
        "author": "Ursula K. Le Guin",
        "genre": "Fantasy",
        "language": "English",
        "year": 1968,
    },
    {
        "title": "The Lord of the Rings",
        "author": "J.R.R. Tolkien",
        "genre": "Fantasy",
        "language": "English",
        "year": 1954,
    },
    {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "genre": "Fantasy",
        "language": "English",
        "year": 1937,
    },
    {
        "title": "War and Peace",
        "author": "Leo Tolstoy",
        "genre": "Fiction",
        "language": "Russian",
        "year": 1869,
    },
    {
        "title": "Anna Karenina",
        "author": "Leo Tolstoy",
        "genre": "Fiction",
        "language": "Russian",
        "year": 1877,
    },
    {
        "title": "Crime and Punishment",
        "author": "Fyodor Dostoevsky",
        "genre": "Fiction",
        "language": "Russian",
        "year": 1866,
    },
    {
        "title": "The Brothers Karamazov",
        "author": "Fyodor Dostoevsky",
        "genre": "Fiction",
        "language": "Russian",
        "year": 1880,
    },
    {
        "title": "Norwegian Wood",
        "author": "Haruki Murakami",
        "genre": "Fiction",
        "language": "Japanese",
        "year": 1987,
    },
    {
        "title": "Kafka on the Shore",
        "author": "Haruki Murakami",
        "genre": "Fiction",
        "language": "Japanese",
        "year": 2002,
    },
    {
        "title": "1Q84",
        "author": "Haruki Murakami",
        "genre": "Fiction",
        "language": "Japanese",
        "year": 2009,
    },
    {
        "title": "Ficciones",
        "author": "Jorge Luis Borges",
        "genre": "Fiction",
        "language": "Spanish",
        "year": 1944,
    },
    {
        "title": "El Aleph",
        "author": "Jorge Luis Borges",
        "genre": "Fiction",
        "language": "Spanish",
        "year": 1949,
    },
    {
        "title": "The Stranger",
        "author": "Albert Camus",
        "genre": "Fiction",
        "language": "French",
        "year": 1942,
    },
    {
        "title": "The Plague",
        "author": "Albert Camus",
        "genre": "Fiction",
        "language": "French",
        "year": 1947,
    },
    {
        "title": "À la recherche du temps perdu",
        "author": "Marcel Proust",
        "genre": "Fiction",
        "language": "French",
        "year": 1913,
    },
    {
        "title": "The Name of the Rose",
        "author": "Umberto Eco",
        "genre": "Mystery",
        "language": "Italian",
        "year": 1980,
    },
    {
        "title": "Foucault's Pendulum",
        "author": "Umberto Eco",
        "genre": "Mystery",
        "language": "Italian",
        "year": 1988,
    },
    {
        "title": "Murder on the Orient Express",
        "author": "Agatha Christie",
        "genre": "Mystery",
        "language": "English",
        "year": 1934,
    },
    {
        "title": "The Hound of the Baskervilles",
        "author": "Arthur Conan Doyle",
        "genre": "Mystery",
        "language": "English",
        "year": 1902,
    },
    {
        "title": "Foundation",
        "author": "Isaac Asimov",
        "genre": "Sci-Fi",
        "language": "English",
        "year": 1951,
    },
    {
        "title": "Dune",
        "author": "Frank Herbert",
        "genre": "Sci-Fi",
        "language": "English",
        "year": 1965,
    },
    {
        "title": "Neuromancer",
        "author": "William Gibson",
        "genre": "Sci-Fi",
        "language": "English",
        "year": 1984,
    },
    {
        "title": "Brave New World",
        "author": "Aldous Huxley",
        "genre": "Sci-Fi",
        "language": "English",
        "year": 1932,
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "genre": "Fiction",
        "language": "English",
        "year": 1949,
    },
    {
        "title": "Sapiens",
        "author": "Yuval Noah Harari",
        "genre": "Non-fiction",
        "language": "English",
        "year": 2011,
    },
    {
        "title": "Cosmos",
        "author": "Carl Sagan",
        "genre": "Non-fiction",
        "language": "English",
        "year": 1980,
    },
    {
        "title": "A Brief History of Time",
        "author": "Stephen Hawking",
        "genre": "Non-fiction",
        "language": "English",
        "year": 1988,
    },
]


def _match(book: dict, state: dict) -> bool:
    """Return whether ``book`` satisfies every populated facet in ``state``."""
    if q := state.get("query"):
        haystack = f"{book['title']} {book['author']}".lower()
        if q.lower() not in haystack:
            return False

    if (g := state.get("genre")) and book["genre"] != g:
        return False

    if (a := state.get("author")) and a.lower() not in book["author"].lower():
        return False

    if (lang := state.get("language")) and book["language"] != lang:
        return False

    if (yf := state.get("year_from")) and book["year"] < yf:
        return False

    return not ((yt := state.get("year_to")) and book["year"] > yt)


def suggest_authors(form: Any, field: Any) -> list[DataListChoice]:
    """Cascade: authors filtered by every other populated facet.

    Demonstrates the core promise of faceted search: the value set of
    one facet tightens as siblings get populated. Reads sibling data
    via ``form.<sibling>.data`` so the autocomplete reflects the *live*
    form state, including unconfirmed edits made during the same
    request cycle.
    """
    q = (field.data or "").strip().lower()
    if not q:
        return []

    state = {
        "genre": form.genre.data or "",
        "language": form.language.data or "",
        "year_from": form.year_from.data,
        "year_to": form.year_to.data,
    }
    authors: set[str] = set()
    for book in BOOKS:
        if not _match(book, state):
            continue

        if q in book["author"].lower():
            authors.add(book["author"])

    return [DataListChoice(a) for a in sorted(authors)][:10]


def _wipe(field: Any) -> None:
    # raw_data has priority over data in StringField._value(), so a
    # mutation that only resets data leaves the input rendering the
    # user's posted text. Clear both.
    field.data = None
    field.raw_data = None


def _render_results(form: Any) -> Markup:
    """Render the ``#results`` section via the Jinja macro."""
    module = current_app.jinja_env.get_template("_faceted_search_widgets.html").module
    return Markup(module.results_section(form))


def repaint_results(form: Any, source: Any, target: Any) -> Any:
    """Re-render the ``#results`` section, and let the library render ``chips``.

    A facet change sends two requests: one for ``#results``, one from the
    ``chips`` field itself. This callback returns the listing HTML for
    the first, and ``None`` for the second so the chips widget renders.
    """
    if target == "#results":
        return _render_results(form)

    return None


def clear_facet(form: Any, source: Any, target: Any) -> Any:
    """Submit-driven mutation: clear the facet named in the button's value.

    Called once per declared target. The wipe runs first on every call
    (idempotent) so the ``#results`` repaint reads the post-wipe state.
    """
    if source.raw_data:
        name = source.raw_data[0]
        if name == "year":
            _wipe(form.year_from)
            _wipe(form.year_to)
        elif (field := getattr(form, name, None)) is not None:
            _wipe(field)

    if target == "#results":
        return _render_results(form)

    return None


class FacetedSearchForm(ExampleForm):
    """Free-text ``query`` + four typed facets.

    The results listing is a plain DOM section targeted by selector
    (``#results``); ``chips`` and ``filters`` remain typed fields whose
    widgets render the active facets and the dropdown panel.

    All controls re-render the listing on change. Clearing a chip is
    multi-target: re-renders ``#results`` (selector) and ``filters``
    (field, OOB), so the <select> inside the still-open <details>
    snaps back to its cleared state. Without that, the next request
    would re-inject the old facet value from the stale DOM control.
    """

    class Meta:
        # No field here has a validator worth a re-render on blur.
        htmx_inline_validation = False
        htmx_method = "get"

    query = StringField(
        "Search",
        validators=[Optional()],
        render_kw={
            "type": "search",
            "placeholder": "Search title or author…",
            "autocomplete": "off",
            "aria-label": "Search books by title or author",
            "hx-push-url": "true",
        },
        wrapper=False,
    )

    genre = SelectField(
        "Genre",
        choices=[SelectChoice("", "Any")] + [SelectChoice(g, g) for g in GENRES],
        validators=[Optional()],
        render_kw=_PUSH_URL,
    )

    author = StringField(
        "Author",
        validators=[Optional()],
        datalist=DataList(suggest_authors),
        render_kw=_PUSH_URL,
    )

    language = SelectField(
        "Language",
        choices=[SelectChoice("", "Any")]
        + [SelectChoice(lang, lang) for lang in LANGUAGES],
        validators=[Optional()],
        render_kw=_PUSH_URL,
    )

    year_from = IntegerField(
        "From year",
        validators=[Optional(), NumberRange(min=1800, max=2100)],
        render_kw=_PUSH_URL,
    )

    year_to = IntegerField(
        "To year",
        validators=[Optional(), NumberRange(min=1800, max=2100)],
        render_kw=_PUSH_URL,
    )

    chips = SelectField(
        choices=[],
        validate_choice=False,
        widget=jinja_widget("_faceted_search_widgets.html", "chips_strip"),
        wrapper=False,
    )

    filters = SelectField(
        choices=[],
        validate_choice=False,
        widget=jinja_widget("_faceted_search_widgets.html", "filters_panel"),
        wrapper=False,
    )

    clear = ButtonField("×", render_kw=_PUSH_URL)
    apply = SubmitField("Apply")

    # Typing in the query repaints the results.
    query.triggers("#results", repaint_results, on="input changed delay:200ms")

    # A facet change repaints the results and the chips.
    genre.triggers(["#results", "chips"], repaint_results, on="change")
    author.triggers(["#results", "chips"], repaint_results, on="change")
    language.triggers(["#results", "chips"], repaint_results, on="change")
    year_from.triggers(["#results", "chips"], repaint_results, on="change")
    year_to.triggers(["#results", "chips"], repaint_results, on="change")

    # Clearing a chip also re-renders the filter panel, so its <select>s
    # do not send the cleared value again.
    clear.triggers(["#results", "chips", "filters"], clear_facet)

    def active_facets(self) -> list[tuple[str, str]]:
        """Return ``(name, chip_label)`` for every populated facet.

        ``name`` is the ``value=`` carried by the chip's ``×`` button when
        cleared; ``year_from`` and ``year_to`` collapse into a single
        ``year`` chip with a single remove action. ``query`` is *not*
        a chip. It stays visible in its own input.
        """
        out = []
        if self.genre.data:
            out.append(("genre", f"Genre: {self.genre.data}"))

        if self.author.data:
            out.append(("author", f"Author: {self.author.data}"))

        if self.language.data:
            out.append(("language", f"Language: {self.language.data}"))

        if self.year_from.data or self.year_to.data:
            yf = self.year_from.data or "…"
            yt = self.year_to.data or "…"
            out.append(("year", f"Year: {yf}–{yt}"))

        return out

    def filter_books(self) -> list[dict]:
        """Apply the free-text query + every populated facet."""
        state = {
            "query": self.query.data or "",
            "genre": self.genre.data or "",
            "author": self.author.data or "",
            "language": self.language.data or "",
            "year_from": self.year_from.data,
            "year_to": self.year_to.data,
        }
        return [b for b in BOOKS if _match(b, state)]


@bp.route("/faceted-search")
def faceted_search():
    form = FacetedSearchForm(request.args or None, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    if request.args:
        form.validate()

    return render_template("faceted_search.html", form=form)
