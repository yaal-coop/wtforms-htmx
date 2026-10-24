Dispatching submits
===================

A single view often has to tell apart more than one way of submitting:
one form carrying several submit buttons, or several forms sharing a
page.

Both cases work with a plain full-page POST, through
:attr:`~wtforms_htmx.HtmxFormMixin.submitter`.

Multi-button forms
------------------

A single form with multiple submit buttons (Save / Delete)
dispatches in the view through
:attr:`form.submitter <wtforms_htmx.HtmxFormMixin.submitter>`, which
returns the clicked button field. Compare it with ``is``:

.. code-block:: python

    if form.submitter is form.delete:
        delete(post)
        return redirect(url_for("blog.index"))

    if form.submitter is form.save and form.validate():
        save(post, form.data)
        return redirect(url_for("blog.post", id=post.id))

:attr:`~wtforms_htmx.HtmxFormMixin.submitter` also finds a clicked
:class:`~wtforms.fields.ButtonField` nested inside a
:class:`~wtforms.fields.FieldList` or
:class:`~wtforms.fields.FormField`, as long as the row form uses
:class:`~wtforms_htmx.HtmxMeta`, as an :class:`~wtforms_htmx.HtmxForm`
or an :class:`~wtforms_htmx.HtmxFormMixin` subclass does. A row button compares to its own
entry:

.. code-block:: python

    for row in form.rows:
        if form.submitter is row.form.archive:
            archive(row.form.data)

In a text field, Enter clicks the first submit button of the form. To
choose another button, see :ref:`migrate-enter-key`.

Multi-form pages
----------------

The same :attr:`~wtforms_htmx.HtmxFormMixin.submitter` tells *which
form* was submitted when several share a page. Give each form a
distinct :class:`~wtforms.form.Form` ``prefix=`` to avoid collisions:
it namespaces every name (buttons, CSRF token, …), so the form that
was posted is the only one whose ``submitter`` is not ``None``. The
others see none of their buttons in the request. The prefix does not
change the comparison:

.. code-block:: python

    formdata = request.form or None
    profile = ProfileForm(formdata, prefix="profile", headers=request.headers)
    settings = SettingsForm(formdata, prefix="settings", headers=request.headers)

    if result := profile.partial() or settings.partial():
        return Response(result.body, headers=result.headers)

    if profile.submitter is profile.save and profile.validate():
        save(profile.data)
        return redirect(url_for("account", _anchor="profile"))

    if settings.submitter is settings.save and settings.validate():
        save(settings.data)
        return redirect(url_for("account", _anchor="settings"))

Each form answers only the requests sent by its own fields:
:meth:`~wtforms_htmx.HtmxFormMixin.partial` returns ``None`` on the
other one.

Compare with the save button rather than testing ``profile.submitter``
alone. A mutation button also sets ``submitter``, and its click must not
save.

See also
--------

- :attr:`~wtforms_htmx.HtmxFormMixin.submitter`: the attribute reference.
- :doc:`/how-to/mutations`: when a button also carries a
  :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` declaration, keeping its no-JS click out of the save branch.
