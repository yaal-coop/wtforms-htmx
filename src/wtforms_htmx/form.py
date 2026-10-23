"""Form mixin: request dispatch and partial rendering."""

from __future__ import annotations

import warnings
from typing import Any
from typing import TYPE_CHECKING

from markupsafe import Markup
from wtforms import Form
from wtforms.fields import FieldList
from wtforms.fields import FormField
from wtforms.fields.choices import SelectFieldBase
from wtforms.widgets import html_params
from wtforms.widgets import ListWidget
from wtforms.widgets import Select

from .headers import _parse_request
from .meta import _is_source_posted
from .meta import HtmxMeta
from .partial import _compute_partial
from .partial import _HtmxMutation
from .tree import _classify_target
from .tree import _resolve_field
from .tree import _resolve_field_by_id
from .tree import _root_of
from .tree import _state
from .tree import _walk_fields
from .triggers import _TriggerEntry

if TYPE_CHECKING:
    from wtforms.fields import Field


def _is_submit_source(field: Any) -> bool:
    """Whether ``field`` submits the form on click.

    True when its widget, or the option widget of a choices field, is in
    ``meta.htmx_submit_widgets``.
    """
    submit_widgets = getattr(field.meta, "htmx_submit_widgets", ())
    if not submit_widgets:
        return False

    if isinstance(field, SelectFieldBase):
        return isinstance(field.option_widget, submit_widgets)

    return isinstance(field.widget, submit_widgets)


def _iter_submit_sources(form: Any) -> Any:
    """Yield the submit-source fields of the whole form tree, nested ones included."""
    return (field for field in _walk_fields(form) if _is_submit_source(field))


def _resolve_field_by_datalist_id(container: Any, datalist_id: str):
    """Find the field whose bound DataList has the id ``datalist_id``.

    Match the DataList's actual id rather than a ``-datalist`` suffix.
    """
    for field in _walk_fields(container):
        datalist = getattr(field, "_datalist", None)
        if (
            datalist is not None
            and not isinstance(datalist, str)
            and datalist.id == datalist_id
        ):
            return field

    return None


def _resolve_source_field(container: Any, element_id: str | None) -> Field | None:
    """Find the field that owns the element whose id is ``element_id``.

    Exact ids first, which is what a FieldList entry matches. Then a single
    trailing ``-<n>`` is trimmed, so a choice option (``color-0``) routes to
    its field. The trim never repeats.
    """
    if not element_id:
        return None

    if (field := _resolve_field_by_id(container, element_id)) is not None:
        return field

    prefix, separator, tail = element_id.rpartition("-")
    if not separator or not tail.isdigit():
        return None

    return _resolve_field_by_id(container, prefix)


def _add_trigger_source(
    target: Any, source_id: str, source_name: str, entry: Any
) -> None:
    """Append ``(source_id, source_name, entry)`` to ``target._htmx_trigger_sources``."""
    incoming = _state(target, "_htmx_trigger_sources")
    if incoming is None:
        incoming = []
        target._htmx_trigger_sources = incoming

    incoming.append((source_id, source_name, entry))


def _inline_validate(form: Any, _source: Any, _target: Any) -> None:
    """Inline-validation callback: validate the whole form.

    It leaves ``target.data`` untouched, so the field keeps what the user
    typed.
    """
    form.validate()


def _inline_validation_fields(fields: Any) -> Any:
    """Yield the plain fields of ``fields``, and the rows of their FieldLists."""
    for field in fields:
        if isinstance(field, FieldList):
            yield from _inline_validation_fields(field.entries)
        elif not isinstance(field, FormField):
            yield field


_HTMX_TARGET_KEYWORDS = frozenset({"this", "next", "previous", "body"})


def _button_attrs(form: Any, holder: Any, target_name: str) -> dict[str, Any]:
    """Return the htmx attributes of a button that fires ``holder``'s mutation."""
    host = getattr(holder, "_form", None) or form
    kind, target = _classify_target(host, _root_of(form), target_name)
    # A field becomes ``#<id>``; anything else is an htmx selector, used verbatim.
    hx_target = f"#{target.id}" if kind == "field" else target_name
    return {
        "formnovalidate": True,
        form.meta._htmx_request_attr: form.meta.htmx_endpoint,
        "hx-target": hx_target,
        "hx-swap": "outerHTML",
        # htmx only adds the enclosing form for verbs other than GET/DELETE.
        "hx-include": "closest form",
    }


def _warn_unbound_targets(holder: Any, targets: list[tuple]) -> None:
    """Warn about Python names that match no field and are not htmx keywords."""
    for target_name, _entry, kind, _val in targets:
        if kind == "unbound" and target_name not in _HTMX_TARGET_KEYWORDS:
            warnings.warn(
                f"{holder.name!r} triggers {target_name!r}, which matches no field. "
                "It is used as a CSS selector. Check the field name, or write "
                "the selector with a '#', '.' or other CSS syntax.",
                stacklevel=2,
            )


def _wire_button(holder: Any, form: Any, triggers: dict[str, Any]) -> None:
    """Give a button the htmx attributes of its first target.

    Raise ValueError when a declaration sets ``on=``: a button fires on click.
    A choices field renders its buttons itself, with ``htmx_submit_attrs``.
    """
    if any(entry.event for entry in triggers.values()):
        raise ValueError(
            f"{holder.name!r} is a button: it fires on click, so on= does not apply."
        )

    if not isinstance(holder, SelectFieldBase):
        attrs = _button_attrs(form, holder, next(iter(triggers)))
        holder.render_kw = {**attrs, **(holder.render_kw or {})}


def _collect_triggers(holder: Any, form: Any) -> None:
    """Record ``holder.triggers(...)`` declarations on their targets.

    A field target gets an entry in ``_htmx_trigger_sources``. A selector
    target stays on the source, in ``_htmx_selector_target``. A button sends
    its own request: it gets its htmx attributes instead. Raise ValueError
    when the source declares more than one selector target.
    """
    triggers = _state(holder, "_htmx_triggers")
    if not triggers:
        return

    root = _root_of(form)
    targets = [
        (target_name, entry, *_classify_target(form, root, target_name))
        for target_name, entry in triggers.items()
    ]
    _warn_unbound_targets(holder, targets)
    selectors = [name for name, _entry, kind, _val in targets if kind != "field"]
    if len(selectors) > 1:
        raise ValueError(
            f"{holder.name!r} declares several selector targets "
            f"({', '.join(selectors)}). Declare one, and return the other "
            "elements as out-of-band extras from its callback."
        )

    if _is_submit_source(holder):
        _wire_button(holder, form, triggers)
        return

    for target_name, entry, kind, val in targets:
        if kind == "field":
            _add_trigger_source(val, holder.id, holder.name, entry)
        else:
            # "selector", or a name matching no field: hand it to htmx
            # verbatim so the source carries its own hx-target.
            holder._htmx_selector_target = (target_name, entry)


def _check_selector_sources(form: Any) -> None:
    """Raise ValueError when a field has a selector target and listens to another field.

    Its requests could not both reach the selector and re-render the field.
    """
    for field in _walk_fields(form):
        if _state(field, "_htmx_selector_target") is None:
            continue

        sources = _state(field, "_htmx_trigger_sources") or []
        if any(source_id != field.id for source_id, _name, _entry in sources):
            raise ValueError(
                f"{field.name!r} has a selector target and listens to another "
                "field. Keep one of the two, and update the other element as "
                "an out-of-band extra from a callback."
            )


def _collect_triggered_by(holder: Any, form: Any) -> None:
    """Record ``holder.triggered_by(...)`` declarations in ``holder._htmx_trigger_sources``.

    The wildcard is kept as ``("*", "*", entry)``. Its callback gets
    ``source=None``. Warn about a source that matches no field.
    """
    triggered_by = _state(holder, "_htmx_triggered_by")
    if not triggered_by:
        return

    root = _root_of(form)
    for source_name, entry in triggered_by.items():
        if source_name == "*":
            _add_trigger_source(holder, "*", "*", entry)
            continue

        kind, val = _classify_target(form, root, source_name)
        if kind != "field":
            warnings.warn(
                f"{holder.name!r} is triggered by {source_name!r}, which matches "
                "no field. The declaration is ignored. Check the field name.",
                stacklevel=2,
            )
            continue

        _add_trigger_source(holder, val.id, val.name, entry)


class HtmxFormMixin:
    """Mixin exposing htmx integration helpers on a WTForms form.

    Mix it in first, before the other form base. WTForms merges the
    ``Meta`` classes of every base, and :class:`HtmxMeta` takes precedence
    over the other base's ``Meta``::

        class ProfileForm(HtmxFormMixin, FlaskForm):
            email = EmailField()
            country = StringField(datalist=DataList(...))
            region = StringField().triggered_by("country", on="change")

    The default :class:`HtmxMeta` adds htmx attributes on render, based
    on form-level defaults. Trigger declarations go through
    :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` and
    :meth:`.triggered_by() <wtforms.fields.core.UnboundField.triggered_by>`. The
    mixin itself is framework-agnostic: it does not touch request or
    response objects. Your view layer does that.

    Pass the request headers to the constructor as ``headers=``, for
    example ``ProfileForm(request.form or None, headers=request.headers)``.
    Without them, the form does not detect htmx requests.
    """

    Meta = HtmxMeta

    if TYPE_CHECKING:
        meta: HtmxMeta
        _fields: dict[str, Field]
        _parent_form: HtmxFormMixin | None
        _htmx_mutation: _HtmxMutation | None

    def __init__(self, *args, headers=None, **kwargs):
        # Set before ``super().__init__``: post_process, which dispatches,
        # runs inside it.
        self._htmx_headers = headers
        self._htmx_formdata = None
        if "meta" in kwargs:
            kwargs["meta"] = _with_parent_settings(type(self), kwargs["meta"])

        super().__init__(*args, **kwargs)
        # A nested form wires its triggers now: its post_process runs
        # after the root's mutate.
        if self._parent_form is not None:
            self._htmx_wire_triggers()

    def post_process(self, formdata=None):
        """Wire the trigger declarations, then dispatch the mutations.

        Wire before ``super()`` so dispatch sees the declarations, and
        dispatch after it so callbacks see resolved ``choices``. Nested forms
        never dispatch.
        """
        self._htmx_wire_triggers()
        self._htmx_formdata = formdata
        super().post_process(formdata)
        if self._parent_form is None and self.meta.htmx_auto_mutate:
            self.mutate()

    def partial(self):
        """Build the htmx partial response for the current request, or ``None``.

        Returns an :class:`~wtforms_htmx.HtmxResponse` carrying the body
        and the optional htmx response headers (typically
        :htmx-header:`hx-retarget`), or ``None`` when there's no partial
        to produce: non-htmx request, :htmx-attr:`hx-boost` full-page swap, or
        nothing to re-render.

        Uses the request headers captured at form construction
        (``Form(formdata, headers=request.headers)``).

        This method renders. It does not run callbacks or change the
        form's data: :meth:`mutate` does that, at construction. The
        fragment is the re-render of the triggered mutation, the inline
        validation result, or a datalist refresh.

        Typical usage::

            form = ProfileForm(request.form or None, headers=request.headers)
            if result := form.partial():
                return Response(result.body, headers=result.headers)

            if form.submitter is form.save and form.validate():
                save(form.data)              # skipped on a no-JS mutation click
                return redirect("/profile")

            return render_template("page.html", form=form)
        """
        return _compute_partial(self, self._htmx_headers)

    def _htmx_wire_triggers(self) -> None:
        """Record every trigger declaration of the form once, then wire inline validation.

        ``post_process`` can run several times: a second collection would
        duplicate the entries, but inline validation is wired again so that
        list rows added since get it. Names that match no field are skipped.
        """
        if not self.__dict__.get("_htmx_triggers_wired"):
            self._htmx_triggers_wired = True
            # The helpers record the qualified ``holder.name``, which dispatch
            # needs inside a sub-form.
            for holder in self._fields.values():
                _collect_triggers(holder, self)
                _collect_triggered_by(holder, self)

            # Nested forms collect while the root is processed, so the root
            # sees every declaration of the tree.
            if self._parent_form is None:
                _check_selector_sources(self)

        if self.meta.htmx_inline_validation:
            self._wire_inline_validation()

    def _wire_inline_validation(self) -> None:
        """Declare inline validation as a self-trigger on every eligible field.

        It covers the rows of a FieldList of plain fields. A FormField wires its
        own form. Skipped: submit sources and fields with a selector target. A
        select, and a list of radio buttons or checkboxes, validates on
        ``change``. The declaration is replaced each time, so a renumbered row
        keeps its id.
        """
        for holder in _inline_validation_fields(self._fields.values()):
            if (
                _is_submit_source(holder)
                or _state(holder, "_htmx_selector_target") is not None
            ):
                continue

            # ``blur`` never reaches the list container, ``change`` bubbles to
            # it. A select is done once the user picks an option.
            event = (
                "change"
                if isinstance(holder.widget, (ListWidget, Select))
                else self.meta.htmx_validation_trigger
            )
            sources = _state(holder, "_htmx_trigger_sources") or []
            holder._htmx_trigger_sources = [
                source
                for source in sources
                if source[2].callback is not _inline_validate
            ]
            _add_trigger_source(
                holder, holder.id, holder.name, _TriggerEntry(event, _inline_validate)
            )

    def _htmx_resolve(self, name: str):
        """Find a field by its HTML name, with or without the form's prefix.

        Return ``None`` when ``name`` matches no field.
        """
        prefix = getattr(self, "_prefix", "") or ""
        if prefix and name.startswith(prefix):
            name = name[len(prefix) :]

        return _resolve_field(self, name)

    def _htmx_resolve_datalist(self, datalist_id: str | None):
        """Find the field whose bound DataList has the id ``datalist_id``, or ``None``."""
        if not datalist_id:
            return None

        return _resolve_field_by_datalist_id(self, datalist_id)

    def htmx_submit_attrs(self, field: Any) -> dict[str, Any]:
        """Return the hx-* attributes a submit :mdn-tag:`button` needs to fire ``field``'s mutation.

        A field declared with
        :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>` posts
        the form and swaps its target through htmx attributes on the rendered
        button. The stock :class:`~wtforms.fields.SubmitField` /
        :class:`~wtforms.fields.ButtonField` widgets get them automatically.
        This helper is for a **custom widget** that renders the
        button(s) itself (typically a Jinja macro emitting one button
        per choice) and has to thread the attributes on by hand:

        .. code-block:: jinja

            {%- macro listbox(field) -%}
              <ul role="listbox" id="{{ field.id }}">
                {%- for opt in field -%}
                  {%- set attrs = dict(opt.choice.render_kw,
                                       **form.htmx_submit_attrs(opt)) -%}
                  {{ opt(label=opt.choice.label, **attrs) }}
                {%- endfor -%}
              </ul>
            {%- endmacro %}

        The dict carries :mdn-attr:`button#formnovalidate`, the request attribute
        (:htmx-attr:`hx-post` by default, see :attr:`~wtforms_htmx.HtmxMeta.htmx_method`)
        set to :attr:`~wtforms_htmx.HtmxMeta.htmx_endpoint`, :htmx-attr:`hx-target` (the first
        :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>`
        target), :htmx-attr:`hx-swap` ``outerHTML`` and
        :htmx-attr:`hx-include` ``closest form``. Merge it with
        other attributes before splatting, as above. For a formatted
        string, see :meth:`htmx_submit_params`.

        Returns ``{}`` for a field with no trigger declaration. A select
        option returns its parent field's attributes, so a macro can call
        it on each option.
        """
        triggers = _state(field, "_htmx_triggers")
        # A choice option shares its name and its form with the choices field.
        if not triggers and (parent := self._htmx_resolve(field.name)) is not None:
            triggers = _state(parent, "_htmx_triggers")

        if not triggers:
            return {}

        return _button_attrs(self, field, next(iter(triggers)))

    def htmx_submit_params(self, field: Any) -> Markup:
        """Pre-formatted version of :meth:`htmx_submit_attrs`.

        Wraps the computed dict through :func:`~wtforms.widgets.html_params`
        and returns :class:`~markupsafe.Markup`, so templates can
        splat it directly onto a :mdn-tag:`button` without iteration::

            <button ... {{ form.htmx_submit_params(field) }}>

        Returns empty :class:`~markupsafe.Markup` when ``field`` has
        no :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>`
        declaration. For composition (merging
        caller-side attrs), use :meth:`htmx_submit_attrs` and format
        yourself.
        """
        attrs = self.htmx_submit_attrs(field)
        return Markup(html_params(**attrs)) if attrs else Markup("")

    @property
    def submitter(self) -> Field | None:
        """Return the button field that submitted the form, or ``None``.

        Compare it to a field with ``is``: ``form.submitter is form.save``.
        A :class:`~wtforms.fields.ButtonField` or
        :class:`~wtforms.fields.SubmitField` nested in a
        :class:`~wtforms.fields.FieldList` or
        :class:`~wtforms.fields.FormField` is found too, as long as the
        row form uses :class:`~wtforms_htmx.HtmxMeta`, as an
        :class:`~wtforms_htmx.HtmxForm` or an :class:`~wtforms_htmx.HtmxFormMixin`
        subclass does. A row button compares to its own entry. A ``prefix=`` on the form changes nothing.

        Use it when a form has several submit buttons with different
        meanings (save, delete, prefill…), and to tell a submit from a
        mutation click. A button written in the template without a
        ``name`` leaves it at ``None``.
        """
        for btn in _iter_submit_sources(self):
            if btn.raw_data:
                return btn

        return None

    @property
    def mutated(self) -> bool:
        """Return ``True`` when the request ran a mutation.

        This is the case after a click on a button with
        :meth:`.triggers() <wtforms.fields.core.UnboundField.triggers>`, with
        or without JavaScript, and after an htmx request that re-renders a
        field. A view checks it to skip saving::

            if not form.mutated and form.validate():
                save(form.data)

        It stays ``False`` until :meth:`mutate` runs.
        """
        mutation = self.__dict__.get("_htmx_mutation")
        return mutation is not None and mutation.dispatched

    def mutate(self) -> None:
        """Dispatch the request's mutations.

        Runs the callbacks of the request and records which targets
        re-render; :meth:`partial` does the rendering. It runs the
        callbacks of the button that submitted the form, with or without
        JavaScript. For an htmx request, it then runs the callbacks
        declared towards the field that sent the request. See
        :ref:`dispatch-path`. To tell a
        mutation click from a submit in the view, read :attr:`submitter`.

        You rarely call this in a view: by default it runs automatically
        (:attr:`Meta.htmx_auto_mutate <HtmxMeta.htmx_auto_mutate>`,
        default ``True``). Call it
        explicitly when ``htmx_auto_mutate`` is off and the view must run
        logic *between* construction and the mutation, such as
        inspecting the raw submission, authorizing the clicked button, or
        loading state the mutation builds on::

            class TagsForm(HtmxForm):
                class Meta:
                    htmx_auto_mutate = False     # opt out of the automatic run

                tags = FieldList(StringField())
                add_tag = ButtonField("Add tag").triggers("tags", list_add)

            form = TagsForm(request.form or None, headers=request.headers)
            if not user_may(form.submitter):     # gate the click before applying
                abort(403)

            form.mutate()                        # then run the declared mutations

        It reads the request headers passed to the constructor, like
        :meth:`partial`.

        The first call runs the mutations. Later calls do nothing, so an
        explicit call after the automatic one is harmless.

        When a mutation fired, the form is post-processed again, so derived
        state such as ``choices`` reflects the new data.

        With CSRF protection on, a submitted form with an invalid token runs
        no callback. The error is set on the CSRF field.
        """
        if self.__dict__.get("_htmx_mutation") is not None:
            return

        # Stored even when empty: its presence marks that mutate has run.
        mutation = _HtmxMutation()
        self._htmx_mutation = mutation
        if not self._htmx_csrf_valid():
            return

        self._dispatch_button(mutation)
        self._dispatch_source_request(mutation)
        if mutation.dispatched:
            self.post_process(self._htmx_formdata)

    def _htmx_csrf_valid(self) -> bool:
        """Check the CSRF token of a submitted form, when CSRF protection is on."""
        if not self.meta.csrf or self._htmx_formdata is None:
            return True

        return self._fields[self.meta.csrf_field_name].validate(self)

    def _dispatch_button(self, mutation: _HtmxMutation) -> None:
        """Run the callbacks of the button that submitted the form."""
        button = self.submitter
        if button is None or not (triggers := _state(button, "_htmx_triggers")):
            return

        host = getattr(button, "_form", None) or self
        for target_name, entry in triggers.items():
            kind, target = _classify_target(host, self, target_name)
            if kind != "field":
                # A selector, or a name matching no field: the callback owns the HTML.
                mutation.selector_dispatched = True
                if entry.callback is not None:
                    mutation.add_result(entry.callback(self, button, target))

                continue

            if entry.callback is not None:
                self._run_field_callback(entry, button, target, mutation)

            mutation.targets.append(target)

    def _dispatch_source_request(self, mutation: _HtmxMutation) -> None:
        """Run the callbacks for the field that sent an htmx request.

        A field with a selector target runs that callback with the selector
        string as ``target``. A listening field runs every callback declared
        towards it. Then the field runs the callbacks of the declarations it
        posts itself, and their targets re-render out of band.
        """
        if not self._htmx_headers:
            return

        source_id = _parse_request(self._htmx_headers).source_id
        if (field := _resolve_source_field(self, source_id)) is None:
            return

        outgoing = self._source_posted_targets(field)
        if _state(field, "_htmx_selector_target") is not None:
            self._dispatch_selector(field, mutation)
        elif _state(field, "_htmx_trigger_sources"):
            self._dispatch_listener(field, mutation)
        elif outgoing:
            mutation.targets.append(field)

        # Inline validation of the source validates the whole form, but the
        # user has not visited the targets yet. A callback may validate them.
        for target, _entry in outgoing:
            _clear_errors(target)

        for target, entry in outgoing:
            if entry.callback is not None:
                self._run_field_callback(entry, field, target, mutation)

            mutation.targets.append(target)

    def _source_posted_targets(self, source: Any) -> list[tuple[Any, Any]]:
        """Return the fields ``source`` feeds through a declaration it posts itself."""
        found = []
        for target in _walk_fields(self):
            for source_id, source_name, entry in (
                _state(target, "_htmx_trigger_sources") or []
            ):
                if source_id == target.id or source_name != source.name:
                    continue

                if _is_source_posted(source_name, entry):
                    found.append((target, entry))

        return found

    def _dispatch_listener(self, target: Any, mutation: _HtmxMutation) -> None:
        """Run every callback declared towards ``target`` and record it for re-render."""
        for source_id, source_name, entry in _state(target, "_htmx_trigger_sources"):
            if entry.callback is None:
                continue

            # The source posts this declaration itself.
            if source_id != target.id and _is_source_posted(source_name, entry):
                continue

            # A wildcard has no single source: callbacks get ``source=None``.
            if source_name == "*":
                source = None
            elif (source := self._htmx_resolve(source_name)) is None:
                continue

            self._run_field_callback(entry, source, target, mutation)

        mutation.targets.append(target)

    def _dispatch_selector(self, source: Any, mutation: _HtmxMutation) -> None:
        """Run the callback of ``source``'s selector target."""
        mutation.selector_dispatched = True
        selector, entry = _state(source, "_htmx_selector_target")
        if entry.callback is not None:
            mutation.add_result(entry.callback(self, source, selector))

    def _run_field_callback(
        self, entry: Any, source: Any, target: Any, mutation: _HtmxMutation
    ) -> None:
        """Run ``entry``'s callback on the field ``target``.

        ``raw_data`` is cleared only when the callback changed ``target.data``:
        it would otherwise win over the new data, and a plain re-render keeps
        what the user typed.
        """
        before = target.data
        mutation.add_result(entry.callback(self, source, target))
        if target.data != before:
            target.raw_data = None


_PARENT_SETTINGS = tuple(name for name in vars(HtmxMeta) if name.startswith("htmx_"))


def _with_parent_settings(form_class: Any, meta: Any) -> Any:
    """Add the htmx settings of the parent form that a sub-form does not set itself.

    A sub-form gets a meta dict with its parent form. The settings go in
    before the fields are bound, which reads some of them. WTForms passes
    only the parent form to a sub-form, not its meta (wtforms#247 proposed
    it, unmerged).
    """
    if not isinstance(meta, dict) or (parent := meta.get("_parent_form")) is None:
        return meta

    meta_class = form_class._wtforms_meta
    inherited = {
        name: getattr(parent.meta, name)
        for name in _PARENT_SETTINGS
        if name not in meta
        and hasattr(parent.meta, name)
        and not _declares(meta_class, name)
    }
    return {**inherited, **meta}


def _declares(meta_class: Any, name: str) -> bool:
    """Tell whether a Meta class of the form, above HtmxMeta, sets ``name``."""
    mro = meta_class.__mro__
    return any(name in vars(klass) for klass in mro[: mro.index(HtmxMeta)])


def _clear_errors(field: Any) -> None:
    """Remove the validation errors of ``field`` and of the fields it holds."""
    if isinstance(field, FormField):
        for sub in field.form:
            _clear_errors(sub)

        return

    if isinstance(field, FieldList):
        for entry in field.entries:
            _clear_errors(entry)

        return

    field.errors = []


class HtmxForm(HtmxFormMixin, Form):
    """Canonical :class:`~wtforms.form.Form` subclass with htmx helpers baked in.

    Convenience composition of :class:`HtmxFormMixin` and
    :class:`~wtforms.form.Form`, equivalent to::

        class MyForm(HtmxFormMixin, Form):
            ...

    Prefer this class as the base class for htmx-enabled forms.
    """
