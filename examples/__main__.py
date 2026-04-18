"""Run the example gallery: ``python -m examples``."""

from __future__ import annotations

from . import create_app

if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
