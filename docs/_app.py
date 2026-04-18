"""WSGI factory for ``sphinxcontrib-screenshot``.

The example Flask app serves as the shoot target for the docs
screenshots. ``screenshot_apps`` (in ``conf.py``) calls
``create_app`` once per build; the substitution ``|examples|``
then resolves to the temporary URL the extension allocates for it.
"""

from __future__ import annotations

import pathlib
import sys


def create_app(sphinx_app):
    # Add the project root to sys.path so ``examples`` is importable
    # (the docs builder runs from ``docs/`` only).
    project_root = pathlib.Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from examples import create_app as create_examples_app
    from examples._shared import _STATE
    from examples.task_list import TaskData

    # Pre-populate state so screenshot pages render with realistic
    # data. Slots carry dataclass instances since the populate_obj
    # refactor — set fields by attribute, not by dict key.
    _STATE["task_list"].tasks = [
        TaskData(title="Write docs"),
        TaskData(title="Take screenshots"),
    ]
    # Password is left blank in initial state; the screenshot uses
    # ``:interactions:`` to type a sample value (PasswordField hides
    # its data on render by default, for security).
    _STATE["currency"].eur = 100
    _STATE["currency"].jpy = 16500
    _STATE["address"].delivery_address.postal_code = "75001"

    app = create_examples_app()
    # Disable hx-boost on screenshot navigation so the captured URL
    # renders as a fresh page load instead of a partial swap.
    app.config["HTMX_BOOST_DISABLED"] = True
    return app
