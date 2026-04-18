Contributing
============

wtforms-htmx is maintained by `Yaal Coop`_ and welcomes contributions.
Bug reports, feature requests and pull requests all go through
`GitHub`_.

.. _Yaal Coop: https://yaal.coop
.. _GitHub: https://github.com/yaal-coop/wtforms-htmx


Reporting issues
----------------

Open a ticket on the `issue tracker`_ with:

- a minimal snippet that reproduces the problem, trimmed of everything
  irrelevant and without other libraries such as ``flask-wtf``;
- the behavior you expected instead;
- your Python and wtforms-htmx versions.

.. _issue tracker: https://github.com/yaal-coop/wtforms-htmx/issues


Development environment
-----------------------

The project is managed with `uv`_. Clone the repository and install the
dependencies::

    git clone https://github.com/yaal-coop/wtforms-htmx
    cd wtforms-htmx
    uv sync

Dependencies are organized into `dependency groups`_: ``test`` for the
unit-test runner, ``e2e`` for the Playwright browser tests, ``doc`` for
Sphinx and ``example`` for the demo gallery. ``dev`` bundles the
day-to-day set.

The demo gallery, the browser tests and the documentation also need the
front-end assets of the examples: htmx 2 and 4, the htmx head-support
extension, Blades (a fork of Pico CSS), and Sortable. They are declared in ``package.json``. Install
them with `npm`_::

    npm ci

.. _uv: https://docs.astral.sh/uv/
.. _npm: https://docs.npmjs.com/
.. _dependency groups: https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups


Code style
----------

Formatting and linting are enforced with `prek`_, a drop-in
replacement for `pre-commit`_. It runs `Ruff`_ (lint and format) and
`djHTML`_ on the Jinja templates. Install the hooks once::

    prek install

and run the whole suite at any time::

    prek run --all-files

Keep naming consistent with the surrounding code, and prefer guard
clauses (early returns) over deeply nested branches.

.. _prek: https://github.com/j178/prek
.. _pre-commit: https://pre-commit.com/
.. _Ruff: https://docs.astral.sh/ruff/
.. _djHTML: https://github.com/rtts/djhtml


Tests
-----

Tests run with `pytest`_ and split into two suites:

- ``tests/unit``: fast, framework-agnostic unit tests, run by default.
- ``tests/e2e``: end-to-end tests driving the example gallery with
  `Playwright`_.

Run the unit suite against every supported Python version (3.11 through
3.15, as the CI matrix does), against the minimum dependency versions,
and the type checks with `tox`_::

    tox

The end-to-end tests need the browsers installed once::

    uv run playwright install chromium firefox

and then run on demand (CI runs them on chromium only)::

    tox -e e2e

To run the end-to-end tests on htmx 2, use the ``e2e-htmx2`` environment
(no-JS tests excluded)::

    tox -e e2e-htmx2

A patch should come with tests:

- a bug fix should add a regression test that fails without the patch;
- a new feature should add unit tests, and an end-to-end test when it
  has a browser-visible behavior. Progressive enhancement is an
  invariant: the no-JS fallback (the ``*_nojs`` tests) must keep
  working and stay visually identical to the JS rendering.

The end-to-end tests cover both modes. Each interaction of an example
has one test with htmx and one test without it. Some interactions only
exist with JavaScript, such as live typing. Without htmx, test their
fallback instead, usually a submit button. Put the htmx tests in
``test_<example>.py``. Put the no-JS tests in ``test_<example>_nojs.py``,
with the ``page_nojs`` fixture. The ``e2e-htmx2`` environment skips the
``*_nojs.py`` files: without htmx, the htmx version makes no difference.

htmx versions
~~~~~~~~~~~~~

The library supports htmx 2 and htmx 4. The end-to-end suite runs on
both with ``--htmx-version`` (``2`` or ``4``, default ``4``). To view the
example gallery on htmx 2, set the ``HTMX_VERSION=2`` environment variable.
Support for htmx 2 has no planned end.

- Examples must render the same on htmx 2 and htmx 4.
- Version-specific differences live in
  ``examples/templates/_htmx_boot.html`` and nowhere else.
- A scenario that needs an htmx 4 feature is skipped on htmx 2, with
  ``pytest.mark.skipif("config.getoption('--htmx-version') == '2'")``.
  Do not branch a template for it.

.. _pytest: https://docs.pytest.org/
.. _Playwright: https://playwright.dev/python/
.. _tox: https://tox.wiki/


Coverage
~~~~~~~~

We aim for **100%** test coverage. Measure both suites together with::

    tox -e coverage

New code must be exercised by tests. Avoid ``# pragma: no cover``. When
a line genuinely cannot be covered, justify it in the pull request.


Minimum dependency versions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The version specifiers in ``pyproject.toml`` are a commitment: the
project must keep working with the *lowest* versions they allow. The
``minversions`` environment re-resolves dependencies down to their
lowest declared versions and runs the tests against them::

    tox -e minversions

When a dependency floor turns out to be too low, raise it in
``pyproject.toml`` so that ``minversions`` stays green.


Type checking
~~~~~~~~~~~~~~

Static typing is checked with `mypy`_::

    tox -e typing

.. _mypy: https://mypy-lang.org/


Documentation
--------------

The documentation is built with `Sphinx`_. Its product pages follow the
`Diátaxis`_ framework: *how-to guides*, *reference* and *explanation*.
There is no tutorial yet. A few sections deliberately sit outside those
quadrants, as Diátaxis allows: the overview, the example gallery, the
changelog and this contributing guide. Add a new page to the quadrant
that fits its purpose (or to the relevant out-of-quadrant section) and
wire it into the matching toctree in ``docs/index.rst``.

An example page opens with a short introduction followed by the
``automodule`` of its example. It ends with a "Without JavaScript"
section, then a "See also" section.

Write in plain, short American English: one idea per sentence, the
active voice, and each term defined once and then used the same way.
The `Google Technical Writing`_ courses and the `Write the Docs
principles`_ are the references for wording and structure.

Build it locally::

    uv run --group doc sphinx-build -b html docs docs/_build

Cross-referencing conventions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- WTForms objects link through intersphinx (e.g. :class:`~wtforms.form.Form`)
  and the project's own API through internal cross-references
  (e.g. :class:`~wtforms_htmx.HtmxForm`), never plain text.
- HTML elements use the ``:mdn-tag:`` role. Global attributes such as
  ``id`` use the ``:mdn-global-attr:`` role. Element attributes use
  the ``:mdn-attr:`` role, written ``element/path#attr`` (e.g.
  ``:mdn-attr:`button#formnovalidate```). ARIA roles use the
  ``:mdn-role:`` role. htmx attributes and headers use the
  ``:htmx-attr:`` and ``:htmx-header:`` roles.
- These rules apply inside docstrings too, but only the ones Sphinx
  renders: link objects, use the
  MDN/htmx roles, and never surface a private name (``_foo``). Describe
  the observable behavior instead. Underscore-prefixed helpers are not
  rendered, with a few exceptions: check whether a docstring is rendered
  before writing it. Keep unrendered docstrings plain text, with no RST
  roles.
- Add ``.. versionadded::`` / ``.. versionchanged::`` directives to the
  relevant docstrings and pages when behavior changes.

.. _Sphinx: https://www.sphinx-doc.org/
.. _Diátaxis: https://diataxis.fr/
.. _Google Technical Writing: https://developers.google.com/tech-writing
.. _Write the Docs principles: https://www.writethedocs.org/guide/writing/docs-principles/


Changelog
---------

Add a changelog entry to the "Unreleased" section of
``docs/changes.rst`` for any change that affects the code, so the
release notes stay complete.


API stability
-------------

wtforms-htmx has not had a release yet. Until ``1.0`` the public API
(see :doc:`/core/api`) may change without a deprecation period, so feel
free to propose a cleaner interface when the current one gets in the
way, rather than working around it.
