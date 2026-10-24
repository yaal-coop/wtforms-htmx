Changes
=======

Unreleased
----------

- A field that sends the request for its targets, for instance on
  ``change``, keeps the changes made while the request was in flight.
  It is no longer re-rendered, unless it validates inline.
- A new event aborts the request in flight, so fast typing or ticking
  shows the last state.
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
