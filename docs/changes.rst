Changes
=======

Version 0.1.2
-------------

Released 2026-10-25

- A field that sends the request for its targets, for instance on
  ``change``, keeps the changes made while the request was in flight.
  It is no longer re-rendered, unless it validates inline.
- A new event aborts the request in flight, so fast typing or ticking
  shows the last state.
- Out-of-band extras come in ``<hx-partial>`` elements on htmx 4 and in
  ``<template>`` elements on htmx 2. A target rendered as a table part,
  such as a ``<tbody>``, is now swapped too.
- ``value_add`` does not add a value that is already selected.
- ``on=`` accepts several events, separated by commas, for instance
  ``on="input delay:200ms, focus"``.

Version 0.1.1
-------------

Released 2026-10-24

- A :class:`~wtforms.fields.BooleanField` validates inline when it is
  checked or unchecked.
- File and hidden inputs, including the CSRF token, no longer validate
  inline.

Version 0.1.0
-------------

Released 2026-10-23

- Initial release.
