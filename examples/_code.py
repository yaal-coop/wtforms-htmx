"""Source code shown under each demo of the gallery."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path

from flask import current_app
from markupsafe import Markup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from ._shared import ExampleForm

ROOT = Path(__file__).parent

_LEXERS = {".py": "python", ".html": "html+jinja", ".css": "css"}


@dataclass(frozen=True)
class Excerpt:
    """Lines of a file under ``examples/``.

    The excerpt starts at the first line that contains ``start_at``, and
    ends at the next line that contains ``end_at``. These are the
    ``:start-at:`` and ``:end-at:`` options of Sphinx's ``literalinclude``.
    """

    path: str
    start_at: str | None = None
    end_at: str | None = None

    def text(self) -> str:
        lines = (ROOT / self.path).read_text().splitlines()
        if self.start_at:
            lines = lines[_line_index(lines, self.start_at) :]

        if self.end_at:
            lines = lines[: _line_index(lines, self.end_at) + 1]

        return "\n".join(lines)


@dataclass(frozen=True)
class Snippet:
    path: str
    html: Markup


def _line_index(lines, needle):
    return next(i for i, line in enumerate(lines) if needle in line)


def _source(item):
    """Return the path and the code of an object or an excerpt."""
    if isinstance(item, Excerpt):
        return item.path, item.text()

    path = Path(inspect.getsourcefile(item)).relative_to(ROOT).as_posix()
    return path, inspect.getsource(item).rstrip()


def default_code(module):
    """Return the forms, the views and the templates of a module without ``CODE``.

    The templates are the content block of ``<name>.html``, and
    ``_<name>_widgets.html`` when it exists.
    """
    views = set(current_app.view_functions.values())
    items = [
        item
        for item in vars(module).values()
        if getattr(item, "__module__", None) == module.__name__
        and (
            (inspect.isfunction(item) and item in views)
            or (inspect.isclass(item) and issubclass(item, ExampleForm))
        )
    ]
    name = module.__name__.rpartition(".")[2]
    items.append(
        Excerpt(f"templates/{name}.html", "{% block content %}", "{% endblock %}")
    )
    widgets = f"templates/_{name}_widgets.html"
    if (ROOT / widgets).exists():
        items.append(Excerpt(widgets))

    return items


def snippets(items):
    """Highlight the items, merging the ones that follow in the same file."""
    formatter = HtmlFormatter()
    result = []
    for path, group in groupby((_source(item) for item in items), key=lambda s: s[0]):
        code = "\n\n\n".join(text for _, text in group)
        lexer = get_lexer_by_name(_LEXERS[Path(path).suffix])
        result.append(Snippet(path, Markup(highlight(code, lexer, formatter))))

    return result


def stylesheet():
    """Return the Pygments rules, with a dark variant."""
    light = HtmlFormatter(style="xcode").get_style_defs(".highlight")
    dark = HtmlFormatter(style="github-dark").get_style_defs(".highlight")
    return f"{light}\n@media (prefers-color-scheme: dark) {{\n{dark}\n}}\n"
