from __future__ import annotations

import pytest
from werkzeug.datastructures import MultiDict
from wtforms import ButtonField
from wtforms import FieldList
from wtforms import FormField
from wtforms import SelectChoice
from wtforms import SelectField
from wtforms import SelectMultipleField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import widgets
from wtforms.csrf.session import SessionCSRF

from wtforms_htmx import HtmxForm
from wtforms_htmx.mutations import list_add
from wtforms_htmx.mutations import list_remove
from wtforms_htmx.mutations import value_add

from .helpers import htmx_headers


class _TagsForm(HtmxForm):
    tags = FieldList(StringField())
    add_tag = ButtonField("+").triggers("tags", list_add)
    pop_tag = ButtonField("-").triggers("tags", list_remove)


def test_list_add_button_appends_an_entry():
    """A click on the add button appends an entry after the posted ones."""
    form = _TagsForm(MultiDict({"tags-0": "a", "tags-1": "b", "add_tag": ""}))
    assert form.tags.data == ["a", "b", None]


def test_list_remove_button_pops_the_last_entry():
    """A click on the remove button without value drops the last entry."""
    form = _TagsForm(MultiDict({"tags-0": "a", "tags-1": "b", "pop_tag": ""}))
    assert form.tags.data == ["a"]


def test_list_remove_button_reindexes_formfield_rows():
    """Removing a ``FormField`` row by value renumbers the rows after it."""

    class _Entry(HtmxForm):
        address = StringField()

    class _Form(HtmxForm):
        emails = FieldList(FormField(_Entry))
        rm_email = ButtonField("-").triggers("emails", list_remove)

    form = _Form(
        MultiDict(
            {
                "emails-0-address": "a",
                "emails-1-address": "b",
                "emails-2-address": "c",
                "rm_email": "1",
            }
        )
    )
    assert [(e.form.address.name, e.form.address.data) for e in form.emails] == [
        ("emails-0-address", "a"),
        ("emails-1-address", "c"),
    ]


def test_list_add_button_drops_min_entries_padding():
    """An add click on a list padded by ``min_entries`` yields one entry, not two."""

    class _Form(HtmxForm):
        tags = FieldList(StringField(), min_entries=1)
        add_tag = ButtonField("+").triggers("tags", list_add)

    form = _Form(MultiDict({"add_tag": ""}))
    assert [entry.name for entry in form.tags] == ["tags-0"]


def test_button_with_several_targets_runs_the_callback_on_each():
    """A button with several targets runs its callback once per target."""

    class _Form(HtmxForm):
        tags = FieldList(StringField())
        notes = FieldList(StringField())
        add_both = ButtonField("+").triggers(["tags", "notes"], list_add)

    form = _Form(MultiDict({"add_both": ""}))
    assert (len(form.tags), len(form.notes)) == (1, 1)


def test_choices_field_with_button_options_dispatches_on_click():
    """A click on an option button of a choices field runs its callback."""

    class _Form(HtmxForm):
        picker = SelectField(
            choices=[SelectChoice("FR", "France"), SelectChoice("DE", "Germany")],
            option_widget=widgets.Button(),
            validate_choice=False,
        ).triggers("dest", lambda form, source, target: setattr(target, "data", "x"))
        dest = StringField()

    form = _Form(MultiDict({"picker": "FR"}))
    assert form.dest.data == "x"


def test_select_with_default_widget_does_not_dispatch_on_post():
    """A ``<select>`` source is not a button: posting its value runs no callback."""
    calls = []

    class _Form(HtmxForm):
        picker = SelectField(choices=[SelectChoice("FR", "France")]).triggers(
            "dest", lambda form, source, target: calls.append(target)
        )
        dest = StringField()

    _Form(MultiDict({"picker": "FR"}))
    assert calls == []


class _MultiSubmitForm(HtmxForm):
    name = StringField()
    save = SubmitField("Save")
    delete = SubmitField("Delete")


@pytest.mark.parametrize(
    ("formdata", "expected"),
    [
        ({"name": "alice", "save": ""}, "save"),
        ({"name": "alice", "delete": ""}, "delete"),
        ({"save": "", "delete": ""}, "save"),
    ],
    ids=["save", "delete", "first-declared"],
)
def test_submitter_returns_the_clicked_button(formdata, expected):
    """``submitter`` returns the posted button, or the first declared one."""
    form = _MultiSubmitForm(MultiDict(formdata))
    assert form.submitter is form[expected]


@pytest.mark.parametrize("formdata", [None, MultiDict({"name": "alice"})])
def test_submitter_is_none_without_a_posted_button(formdata):
    """``submitter`` is ``None`` when no button is posted."""
    assert _MultiSubmitForm(formdata).submitter is None


def test_submitter_ignores_a_form_with_another_prefix():
    """Two prefixed forms on one page: only the posted one has a submitter."""
    formdata = MultiDict({"profile-name": "alice", "profile-save": ""})
    profile = _MultiSubmitForm(formdata, prefix="profile")
    settings = _MultiSubmitForm(formdata, prefix="settings")
    assert profile.submitter is profile.save
    assert settings.submitter is None


class _RowForm(HtmxForm):
    label = StringField()
    rm_row = ButtonField()


class _RowsForm(HtmxForm):
    rows = FieldList(FormField(_RowForm))
    save = SubmitField()


def test_submitter_finds_a_button_in_a_list_row():
    """A row button is the submitter, and compares to its own row."""
    form = _RowsForm(
        MultiDict({"rows-0-label": "a", "rows-1-label": "b", "rows-1-rm_row": ""})
    )
    assert form.submitter is form.rows[1].form.rm_row


def test_submitter_finds_a_row_after_index_compaction():
    """Posted row indices with gaps are compacted, and the clicked row is still found."""
    form = _RowsForm(
        MultiDict({"rows-0-label": "a", "rows-5-label": "b", "rows-5-rm_row": ""})
    )
    assert form.submitter is form.rows[1].form.rm_row


def test_submitter_tells_a_subform_button_from_a_parent_button():
    """A sub-form button is told apart from a parent button with the same name."""

    class _Address(HtmxForm):
        city = StringField()
        save = SubmitField()

    class _Form(HtmxForm):
        address = FormField(_Address)
        save = SubmitField()

    form = _Form(MultiDict({"address-city": "Paris", "address-save": ""}))
    assert form.submitter is form.address.form.save


def test_submitter_reports_a_mutation_button():
    """A mutation click sets ``submitter`` to the button."""
    form = _TagsForm(MultiDict({"add_tag": ""}))
    assert form.submitter is form.add_tag


def test_mutate_runs_at_construction():
    """The mutation has run when the constructor returns."""
    form = _TagsForm(MultiDict({"add_tag": ""}))
    assert len(form.tags) == 1


def test_mutate_called_again_does_nothing():
    """An explicit ``mutate()`` after the automatic one does not apply the mutation twice."""
    form = _TagsForm(MultiDict({"add_tag": ""}))
    form.mutate()
    assert len(form.tags) == 1


def test_mutate_explicit_call_without_auto_mutate():
    """With ``htmx_auto_mutate`` off, the mutation runs on the explicit ``mutate()``."""

    class _Form(_TagsForm):
        class Meta:
            htmx_auto_mutate = False

    form = _Form(MultiDict({"add_tag": ""}))
    assert len(form.tags) == 0
    form.mutate()
    assert len(form.tags) == 1


def test_mutate_uses_the_constructor_headers():
    """An explicit ``mutate()`` dispatches from the headers given to the constructor."""
    calls = []

    class _Form(HtmxForm):
        class Meta:
            htmx_auto_mutate = False

        country = StringField()
        city = StringField().triggered_by(
            "country", lambda form, source, target: calls.append(target.name)
        )

    form = _Form(MultiDict({"country": "FR", "city": ""}), headers=htmx_headers("city"))
    assert calls == []
    form.mutate()
    assert calls == ["city"]


def _picked(form, _field):
    return [SelectChoice(c, c.lower()) for c in form.picked.data or []]


class _PickedForm(HtmxForm):
    picked = SelectMultipleField(choices=_picked, validate_choice=False)
    add = ButtonField("+").triggers("picked", value_add)


def test_mutate_refreshes_callable_choices():
    """After a mutation, callable choices reflect the new data."""
    form = _PickedForm(MultiDict({"picked": "A", "add": "B"}))
    assert [c.value for c in form.picked.choices] == ["A", "B"]


def test_mutate_explicit_call_refreshes_callable_choices():
    """An explicit ``mutate()`` refreshes callable choices too."""

    class _Form(_PickedForm):
        class Meta:
            htmx_auto_mutate = False

    form = _Form(MultiDict({"picked": "A", "add": "B"}))
    assert [c.value for c in form.picked.choices] == ["A"]
    form.mutate()
    assert [c.value for c in form.picked.choices] == ["A", "B"]


def test_mutate_reruns_a_form_post_process_override():
    """A ``post_process`` override of the form runs again after a mutation."""
    seen = []

    class _Form(_PickedForm):
        def post_process(self, formdata=None):
            super().post_process(formdata)
            seen.append(list(self.picked.data or []))

    _Form(MultiDict({"picked": "A", "add": "B"}))
    assert seen[-1] == ["A", "B"]


def test_button_callback_gets_the_form_the_button_and_the_target():
    """A button callback receives the form, the button and the target field."""
    seen = []

    class _Form(HtmxForm):
        dest = StringField()
        go = ButtonField().triggers("dest", lambda *args: seen.append(args))

    form = _Form(MultiDict({"go": ""}))
    assert seen == [(form, form.go, form.dest)]


def test_button_selector_callback_gets_the_selector_as_target():
    """A button callback for a selector target receives the selector string."""
    seen = []

    class _Form(HtmxForm):
        save = ButtonField("Save").triggers("#preview", lambda *args: seen.append(args))

    form = _Form(MultiDict({"save": ""}))
    assert seen == [(form, form.save, "#preview")]


def test_field_selector_callback_gets_the_selector_as_target():
    """A field callback for a selector target receives the selector string."""
    seen = []

    class _Form(HtmxForm):
        content = StringField().triggers("#preview", lambda *args: seen.append(args))

    form = _Form(MultiDict({"content": "hello"}), headers=htmx_headers("content"))
    assert seen == [(form, form.content, "#preview")]


def test_listener_callback_gets_the_form_the_source_and_the_target():
    """A listener callback receives the form, the source field and the listener."""
    seen = []

    class _Form(HtmxForm):
        country = StringField()
        city = StringField().triggered_by("country", lambda *args: seen.append(args))

    form = _Form(MultiDict({"country": "FR"}), headers=htmx_headers("city"))
    assert seen == [(form, form.country, form.city)]


def test_wildcard_callback_gets_no_source():
    """A wildcard callback receives ``None`` as its source."""
    seen = []

    class _Form(HtmxForm):
        name = StringField()
        status = StringField().triggered_by(
            "*", lambda form, source, target: seen.append(source)
        )

    _Form(MultiDict({"name": "x"}), headers=htmx_headers("status"))
    assert seen == [None]


def test_wildcard_keeps_the_sources_declared_after_it():
    """A source declared after a wildcard still runs its own callback."""
    calls = []

    class _Form(HtmxForm):
        name = StringField()
        status = (
            StringField()
            .triggered_by("*", lambda form, source, target: calls.append(source))
            .triggered_by("name", lambda form, source, target: calls.append(source))
        )

    form = _Form(MultiDict({"name": "x"}), headers=htmx_headers("status"))
    assert calls == [None, form.name]


def test_listener_runs_the_callbacks_after_a_source_without_callback():
    """A source declared without callback does not stop the callbacks after it."""
    calls = []

    class _Form(HtmxForm):
        a = StringField()
        b = StringField()
        dst = (
            StringField()
            .triggered_by("a")
            .triggered_by("b", lambda form, source, target: calls.append(source.name))
        )

    _Form(MultiDict({"a": "x", "b": "y"}), headers=htmx_headers("dst"))
    assert calls == ["b"]


def test_listener_skips_a_source_that_no_longer_exists():
    """A source removed before dispatch is skipped, and the next sources still run."""
    calls = []

    class _Form(HtmxForm):
        class Meta:
            htmx_auto_mutate = False

        rows = FieldList(StringField(), min_entries=2)
        name = StringField()
        total = (
            StringField()
            .triggered_by("#rows-1", lambda form, source, target: calls.append("row"))
            .triggered_by("name", lambda form, source, target: calls.append("name"))
        )

    form = _Form(headers=htmx_headers("total"))
    form.rows.pop_entry()
    form.mutate()
    assert calls == ["name"]


def test_listener_in_a_prefixed_form_runs_its_callback():
    """The form ``prefix=`` does not prevent the source from being found."""
    calls = []

    class _Form(HtmxForm):
        country = StringField()
        city = StringField().triggered_by(
            "country", lambda form, source, target: calls.append(source)
        )

    form = _Form(
        MultiDict({"px-country": "FR"}), prefix="px", headers=htmx_headers("px-city")
    )
    assert calls == [form.country]


def test_subform_listener_dispatches_from_the_root_form():
    """A request from a listener in a list row runs the row callback."""

    class _Row(HtmxForm):
        a = StringField().triggers(
            "b", lambda form, source, target: setattr(target, "data", f"{source.data}*")
        )
        b = StringField()

    class _Form(HtmxForm):
        rows = FieldList(FormField(_Row), min_entries=1)

    form = _Form(
        MultiDict({"rows-0-a": "hello", "rows-0-b": ""}),
        headers=htmx_headers("rows-0-b"),
    )
    assert form.rows[0].form.b.data == "hello*"


def test_subform_button_targets_its_sibling():
    """A button in a sub-form targets the field of the same name in that sub-form."""

    class _Inner(HtmxForm):
        value = StringField()
        confirm = ButtonField("confirm").triggers(
            "value", lambda form, source, target: setattr(target, "data", "PICKED")
        )

    class _Form(HtmxForm):
        value = StringField()
        wrap = FormField(_Inner)

    form = _Form(MultiDict({"value": "", "wrap-value": "", "wrap-confirm": "confirm"}))
    assert (form.value.data, form.wrap.form.value.data) == ("", "PICKED")


def test_subform_button_reaches_a_root_field_by_id():
    """A button in a sub-form targets a root field with a ``#id`` selector."""

    class _Inner(HtmxForm):
        kick = ButtonField("kick").triggers(
            "#top_value", lambda form, source, target: setattr(target, "data", "outer")
        )

    class _Form(HtmxForm):
        wrap = FormField(_Inner)
        top_value = StringField()

    form = _Form(MultiDict({"top_value": "", "wrap-kick": "kick"}))
    assert form.top_value.data == "outer"


def test_dotted_target_reaches_a_subform_field():
    """A dotted target reaches a field of a sibling ``FormField``."""

    class _Address(HtmxForm):
        region = StringField()

    class _Form(HtmxForm):
        address = FormField(_Address)
        go = ButtonField("x").triggers(
            "address.region",
            lambda form, source, target: setattr(target, "data", "filled"),
        )

    form = _Form(MultiDict({"go": "x"}))
    assert form.address.region.data == "filled"


def test_id_selector_target_reaches_a_field_with_a_custom_id():
    """A ``#id`` target matches the field id, even when it differs from the name."""

    class _Form(HtmxForm):
        renamed = StringField(id="custom-id")
        go = ButtonField("x").triggers(
            "#custom-id", lambda form, source, target: setattr(target, "data", "filled")
        )

    form = _Form(MultiDict({"go": "x"}))
    assert form.renamed.data == "filled"


@pytest.mark.parametrize(
    "headers",
    [
        {"HX-Request": "true", "HX-Trigger": "city"},
        {"HX-Request": "true", "HX-Source": "input#city"},
    ],
    ids=["htmx2", "htmx4"],
)
def test_listener_dispatches_on_both_htmx_versions(headers):
    """A listener callback runs with htmx 2 and htmx 4 headers."""
    calls = []

    class _Form(HtmxForm):
        country = StringField()
        city = StringField().triggered_by(
            "country", lambda form, source, target: calls.append(target.name)
        )

    _Form(MultiDict({"country": "FR", "city": ""}), headers=headers)
    assert calls == ["city"]


def test_listener_with_a_non_ascii_id_dispatches_on_htmx4():
    """A percent-encoded non-ASCII id in ``HX-Source`` reaches its listener."""
    calls = []

    class _Form(HtmxForm):
        country = StringField()
        company = StringField(id="société").triggered_by(
            "country", lambda form, source, target: calls.append(target.name)
        )

    _Form(
        MultiDict({"country": "FR", "company": ""}),
        headers={"HX-Request": "true", "HX-Source": "input#soci%C3%A9t%C3%A9"},
    )
    assert calls == ["company"]


class _CsrfTagsForm(HtmxForm):
    class Meta:
        csrf = True
        csrf_class = SessionCSRF
        csrf_secret = b"secret"

    tags = FieldList(StringField())
    add_tag = ButtonField("+").triggers("tags", list_add)


def test_invalid_csrf_token_runs_no_callback():
    """A submit without a valid CSRF token runs no callback."""
    form = _CsrfTagsForm(
        MultiDict({"tags-0": "a", "add_tag": ""}), meta={"csrf_context": {}}
    )
    assert form.tags.data == ["a"]
    assert form.csrf_token.errors


def test_invalid_csrf_token_sends_no_partial():
    """An htmx request without a valid CSRF token gets no partial."""
    form = _CsrfTagsForm(
        MultiDict({"tags-0": "a", "add_tag": ""}),
        meta={"csrf_context": {}},
        headers={"HX-Request": "true", "HX-Source": "button#add_tag"},
    )
    assert form.partial() is None


def test_valid_csrf_token_runs_the_callbacks():
    """A submit with a valid CSRF token runs the callbacks."""
    session = {}
    token = _CsrfTagsForm(meta={"csrf_context": session}).csrf_token.current_token
    form = _CsrfTagsForm(
        MultiDict({"tags-0": "a", "add_tag": "", "csrf_token": token}),
        meta={"csrf_context": session},
    )
    assert form.tags.data == ["a", None]


def test_csrf_is_not_checked_without_formdata():
    """A form built without form data reports no CSRF error."""
    form = _CsrfTagsForm(meta={"csrf_context": {}})
    assert not form.csrf_token.errors


def test_mutated_after_a_mutation_click():
    """A click on a button with triggers sets mutated."""
    form = _TagsForm(MultiDict({"tags-0": "a", "add_tag": ""}))
    assert form.mutated


def test_not_mutated_after_a_plain_submit():
    """A submit from a button without triggers leaves mutated False."""

    class _Form(HtmxForm):
        tags = FieldList(StringField())
        save = SubmitField("Save")

    assert not _Form(MultiDict({"tags-0": "a", "save": "Save"})).mutated


def test_not_mutated_before_mutate_runs():
    """With htmx_auto_mutate off, mutated stays False until mutate runs."""

    class _Form(_TagsForm):
        class Meta:
            htmx_auto_mutate = False

    form = _Form(MultiDict({"tags-0": "a", "add_tag": ""}))
    assert not form.mutated
    form.mutate()
    assert form.mutated


def test_not_mutated_with_an_invalid_csrf_token():
    """A mutation click blocked by the CSRF check leaves mutated False."""
    form = _CsrfTagsForm(
        MultiDict({"tags-0": "a", "add_tag": ""}), meta={"csrf_context": {}}
    )
    assert not form.mutated
