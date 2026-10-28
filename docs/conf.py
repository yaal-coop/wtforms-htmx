from __future__ import annotations

import shutil
import subprocess
import sys
from importlib.metadata import version as _version
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler

from pallets_sphinx_themes import ProjectLink
from sphinx.util import logging

# Make ``_app`` importable by ``screenshot_apps`` below.
sys.path.insert(0, str(Path().resolve()))

# Silence the per-request access logs that ``sphinxcontrib-screenshot``'s
# wsgiref-backed server prints for every page hit — they drown the actual
# Sphinx output during a build. The example app keeps its normal logging
# when run on its own via ``python -m examples``.
WSGIRequestHandler.log_request = lambda *args, **kwargs: None

project = "wtforms-htmx"
author = "Éloi Rivard"
release = _version("wtforms-htmx")
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx_issues",
    "pallets_sphinx_themes",
    "sphinxcontrib.mermaid",
    "sphinxcontrib.screenshot",
    "_mdn_attr_role",
]

screenshot_apps = {"examples": "_app:create_app"}

mermaid_config = {"sequence": {"mirrorActors": False}}

screenshot_default_locator_padding = "5 10 5 10"
screenshot_default_color_scheme = "auto"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "flask": ("https://flask.palletsprojects.com/en/stable/", None),
    "flask-wtf": ("https://flask-wtf.readthedocs.io/en/latest/", None),
    "markupsafe": ("https://markupsafe.palletsprojects.com/en/stable/", None),
    "webtest": ("https://docs.pylonsproject.org/projects/webtest/en/latest/", None),
    "wtforms": ("https://wtforms.readthedocs.io/en/stable/", None),
}

extlinks = {
    "htmx-attr": (
        "https://htmx.org/attributes/%s/",
        "%s",
    ),
    "htmx-header": (
        "https://htmx.org/reference/?h=%s#headers",
        "%s",
    ),
    "htmx-tag": (
        "https://four.htmx.org/reference/tags/%s",
        "<%s>",
    ),
    "mdn-tag": (
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/%s",
        "<%s>",
    ),
    "mdn-global-attr": (
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/%s",
        "%s",
    ),
    "mdn-role": (
        "https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/%s_role",
        'role="%s"',
    ),
}

issues_github_path = "yaal-coop/wtforms-htmx"

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "flask"
html_theme_options = {"index_sidebar_logo": False}
html_static_path = ["_static"]
html_css_files = ["color-scheme.css"]
html_logo = "_static/logo-light.svg"
html_favicon = "_static/favicon.svg"

html_context = {
    "project_links": [
        ProjectLink("PyPI Releases", "https://pypi.org/project/wtforms-htmx/"),
        ProjectLink("Source Code", "https://github.com/yaal-coop/wtforms-htmx/"),
        ProjectLink(
            "Issue Tracker", "https://github.com/yaal-coop/wtforms-htmx/issues/"
        ),
    ],
}
html_sidebars = {
    "index": ["project.html", "localtoc.html", "searchbox.html"],
    "**": ["home.html", "localtoc.html", "relations.html", "searchbox.html"],
}
html_show_sourcelink = False

# Screencast aliases also written as animated WebP: GitHub renders those in the
# README, and drops <video> tags.
animated_screencasts = ["title-slug-light", "title-slug-dark"]


def _write_animated_screencasts(app, exception):
    if exception is not None or app.builder.format != "html":
        return

    folder = Path(app.outdir) / "_static" / "screencasts"
    for name in animated_screencasts:
        source = folder / f"{name}.webm"
        target = folder / f"{name}.webp"
        if not source.exists():
            continue

        if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
            continue

        if (ffmpeg := shutil.which("ffmpeg")) is None:
            logging.getLogger(__name__).warning(
                "ffmpeg not found, %s.webp is not written", name
            )
            return

        subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-y",
                "-i",
                source,
                "-vf",
                "fps=15",
                "-c:v",
                "libwebp_anim",
                "-loop",
                "0",
                "-lossless",
                "1",
                "-compression_level",
                "6",
                "-an",
                target,
            ],
            check=True,
        )


def setup(app):
    app.connect("build-finished", _write_animated_screencasts)
