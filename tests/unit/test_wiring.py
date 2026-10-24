from __future__ import annotations

import pytest
from wtforms import ButtonField
from wtforms import FieldList
from wtforms import Form
from wtforms import FormField
from wtforms import SelectChoice
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField

from wtforms_htmx import HtmxForm
from wtforms_htmx.meta import _clauses
from wtforms_htmx.meta import _from_clause
from wtforms_htmx.mutations import list_add
from wtforms_htmx.mutations import list_remove

from .helpers import attr
from .helpers import marker_clause
from .helpers import markers


class _SingleTargetForm(HtmxForm):
    src = StringField().triggers("dst")
    dst = StringField()


def test_target_listens_to_its_source_after_inline_validation():
    """A target keeps its inline validation and listens to the marked source."""
    form = _SingleTargetForm()
    assert attr(form.dst(), "hx-trigger") == (
        f"{marker_clause('input delay:200ms', 'dst')}, blur changed"
    )
    assert markers(form.src()) == ["dst"]


def test_target_id_includes_the_form_prefix():
    """The marker uses the full id of the listener, form prefix included."""
    form = _SingleTargetForm(prefix="px")
    assert marker_clause("input delay:200ms", "px-dst") in form.dst()
    assert markers(form.src()) == ["px-dst"]


def test_triggers_list_wires_each_target():
    """A list of targets makes each target listen to the source."""

    class _Form(HtmxForm):
        src = StringField().triggers(["a", "b"])
        a = StringField()
        b = StringField()

    form = _Form()
    assert marker_clause("input delay:200ms", "a") in form.a()
    assert marker_clause("input delay:200ms", "b") in form.b()
    assert markers(form.src()) == ["a", "b"]


def test_triggers_chain_keeps_the_event_of_each_target():
    """Chained ``.triggers()`` calls keep their own event per target."""

    class _Form(HtmxForm):
        src = StringField().triggers("slow", on="keyup").triggers("fast")
        slow = StringField()
        fast = StringField()

    form = _Form()
    assert marker_clause("keyup", "slow") in form.slow()
    assert marker_clause("input delay:200ms", "fast") in form.fast()
    assert markers(form.src()) == ["slow", "fast"]


def test_sources_with_the_same_event_share_one_clause():
    """Sources with the same event share one marker and one clause."""

    class _Form(HtmxForm):
        a = StringField().triggers("dst")
        b = StringField()
        dst = StringField().triggered_by("b")

    form = _Form()
    assert attr(form.dst(), "hx-trigger").count("from:body") == 1
    assert markers(form.a()) == ["dst"]
    assert markers(form.b()) == ["dst"]


def test_sources_with_different_events_get_separate_markers():
    """Sources with different events get one marker and one clause per event."""

    class _Form(HtmxForm):
        a = StringField()
        b = StringField()
        dst = StringField().triggered_by("a").triggered_by("b", on="keyup")

    form = _Form()
    assert attr(form.dst(), "hx-trigger") == (
        f"{marker_clause('input delay:200ms', 'dst')},"
        f" {marker_clause('keyup', 'dst--1')}, blur changed"
    )
    assert markers(form.a()) == ["dst"]
    assert markers(form.b()) == ["dst--1"]


def test_triggered_by_list_wires_each_source():
    """A list of sources marks each source for the listener."""

    class _Form(HtmxForm):
        a = StringField()
        b = StringField()
        dst = StringField().triggered_by(["a", "b"])

    form = _Form()
    assert marker_clause("input delay:200ms", "dst") in form.dst()
    assert markers(form.a()) == ["dst"]
    assert markers(form.b()) == ["dst"]


def test_triggers_and_triggered_by_render_the_same_html():
    """Declaring a link on the source or on the target renders the same HTML."""

    class _OnSource(HtmxForm):
        a = StringField().triggers("b")
        b = StringField()

    class _OnTarget(HtmxForm):
        a = StringField()
        b = StringField().triggered_by("a")

    on_source = _OnSource()
    on_target = _OnTarget()
    assert on_source.a() == on_target.a()
    assert on_source.b() == on_target.b()


@pytest.mark.parametrize("source", ["nope", "#preview"])
def test_triggered_by_ignores_a_source_that_is_not_a_field(source):
    """A source that matches no field wires nothing and warns."""

    class _Form(HtmxForm):
        dst = StringField().triggered_by(source)

    with pytest.warns(UserWarning, match="matches no field"):
        form = _Form()

    assert attr(form.dst(), "hx-trigger") == "blur changed"


def test_self_trigger_keeps_the_links_declared_after_it():
    """A field that triggers itself still listens to the sources declared after."""

    class _Form(HtmxForm):
        class Meta:
            htmx_inline_validation = False

        a = StringField()
        dst = StringField().triggers("dst", on="keyup").triggered_by("a")

    form = _Form()
    assert attr(form.dst(), "hx-trigger") == (
        f"{marker_clause('input delay:200ms', 'dst')}, keyup"
    )
    assert markers(form.a()) == ["dst"]


def test_unknown_target_name_warns_and_is_used_as_selector():
    """A target name that matches no field warns, then goes to htmx as a selector."""

    class _Form(HtmxForm):
        src = StringField().triggers("nope")

    with pytest.warns(
        UserWarning, match="'src' triggers 'nope', which matches no field"
    ):
        form = _Form()

    assert attr(form.src(), "hx-target") == "nope"


@pytest.mark.parametrize("keyword", ["this", "next", "previous", "body"])
def test_htmx_target_keyword_does_not_warn(keyword):
    """An htmx target keyword such as ``this`` is a selector, without warning."""

    class _Form(HtmxForm):
        src = StringField().triggers(keyword)

    assert attr(_Form().src(), "hx-target") == keyword


def test_unknown_id_selector_target_is_passed_to_htmx():
    """A ``#id`` that matches no field is passed to htmx as a selector."""

    class _Form(HtmxForm):
        src = StringField().triggers("#nope")

    assert attr(_Form().src(), "hx-target") == "#nope"


def test_buttons_send_their_own_request_instead_of_marking():
    """Submit and button fields carry their target, and the target does not listen."""

    class _Form(HtmxForm):
        save = SubmitField("Save").triggers("dest")
        clicky = ButtonField("Click").triggers("dest")
        dest = StringField()

    form = _Form()
    assert [attr(form.save(), "hx-target"), attr(form.clicky(), "hx-target")] == [
        "#dest",
        "#dest",
    ]
    assert markers(form.save()) == []
    assert markers(form.clicky()) == []
    assert attr(form.dest(), "hx-trigger") == "blur changed"


def test_select_with_default_widget_marks_itself_as_a_source():
    """A ``<select>`` source is marked for its target, like a text input."""

    class _Form(HtmxForm):
        picker = SelectField(choices=[SelectChoice("FR", "France")]).triggers("dest")
        dest = StringField()

    form = _Form()
    assert markers(form.picker()) == ["dest"]
    assert marker_clause("input delay:200ms", "dest") in form.dest()


class _WildcardForm(HtmxForm):
    a = StringField()
    b = StringField()
    dst = StringField().triggered_by("*", on="input delay:800ms")


def test_wildcard_listener_marks_every_field():
    """A wildcard listener puts its marker on every field and has one clause."""
    form = _WildcardForm()
    assert attr(form.dst(), "hx-trigger") == (
        "input delay:800ms from:body target:[data-wtforms-htmx-for~=dst], blur changed"
    )
    assert markers(form.a()) == ["dst"]
    assert markers(form.b()) == ["dst"]


def test_wildcard_listener_marks_subform_fields_and_new_rows():
    """A wildcard listener marks sub-form fields and ``FieldList`` rows added later."""

    class _Entry(HtmxForm):
        x = StringField()

    class _Form(HtmxForm):
        top = StringField()
        sub = FormField(_Entry)
        rows = FieldList(StringField(), min_entries=2)
        dst = StringField().triggered_by("*", on="input")

    form = _Form()
    form.rows.append_entry()
    assert markers(form.top()) == ["dst"]
    assert markers(form.sub.form.x()) == ["dst"]
    assert [markers(row()) for row in form.rows] == [["dst"], ["dst"], ["dst"]]


def test_wildcard_listener_in_a_subform_marks_the_root_fields():
    """A wildcard listener in a sub-form also marks the fields of the root form."""

    class _Inner(HtmxForm):
        x = StringField()
        dst = StringField().triggered_by("*", on="input")

    class _Form(HtmxForm):
        top = StringField()
        sub = FormField(_Inner)

    form = _Form()
    assert marker_clause("input", "sub-dst") in form.sub.form.dst()
    assert markers(form.top()) == ["sub-dst"]
    assert markers(form.sub.form.x()) == ["sub-dst"]


def test_wildcard_listener_in_each_row_marks_every_row_field():
    """Each row's wildcard listener puts its marker on the fields of every row."""

    class _Row(HtmxForm):
        x = StringField()
        dst = StringField().triggered_by("*", on="input")

    class _Form(HtmxForm):
        rows = FieldList(FormField(_Row), min_entries=2)

    form = _Form()
    assert markers(form.rows[0].form.x()) == ["rows-0-dst", "rows-1-dst"]


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        ("input delay:200ms", "input delay:200ms from:body target:#src"),
        ("change", "change from:body target:#src"),
        ("blur", "focusout from:body target:#src"),
        ("focus changed", "focusin changed from:body target:#src"),
        ("keyup[key=='Escape']", "keyup[key=='Escape'] from:body target:#src"),
    ],
)
def test_from_clause_listens_on_body(event, expected):
    """A clause listens on ``body`` and maps events that do not bubble."""
    assert _from_clause(event, "#src") == expected


def test_subform_button_targets_the_parent_list_by_id():
    """A button in a list row targets the parent ``FieldList`` with a ``#id`` selector."""

    class _Entry(HtmxForm):
        value = StringField()
        rm_tag = ButtonField("×").triggers("#tags", list_remove)

    class _Form(HtmxForm):
        tags = FieldList(FormField(_Entry), min_entries=2)

    form = _Form()
    assert [attr(entry.form.rm_tag(), "hx-target") for entry in form.tags] == [
        "#tags",
        "#tags",
    ]


class _PlainAddress(Form):
    street = StringField()
    city = StringField()


def test_plain_subform_renders_without_htmx_attrs():
    """A sub-form built on a plain WTForms ``Form`` renders its fields as WTForms does."""

    class _Form(HtmxForm):
        address = FormField(_PlainAddress)
        rows = FieldList(FormField(_PlainAddress), min_entries=1)

    form = _Form()
    assert form.address.form.city() == (
        '<input id="address-city" name="address-city" type="text" value="">'
    )
    assert form.rows[0].form.city() == (
        '<input id="rows-0-city" name="rows-0-city" type="text" value="">'
    )


def test_plain_subform_declared_first_keeps_later_links():
    """A plain sub-form declared before a link does not hide the link."""

    class _Form(HtmxForm):
        address = FormField(_PlainAddress)
        src = StringField()
        dst = StringField().triggered_by("src")

    assert markers(_Form().src()) == ["dst"]


def test_plain_subform_target_gives_its_source_no_marker():
    """A field of a plain sub-form cannot listen, so its source carries no marker for it."""

    class _Form(HtmxForm):
        address = FormField(_PlainAddress)
        src = StringField().triggers("#address-city")
        dst = StringField().triggered_by("src")

    assert markers(_Form().src()) == ["dst"]


@pytest.mark.parametrize(
    "source",
    [
        StringField().triggers(["#x", "#y"]),
        StringField().triggers("#x").triggers("#y"),
        ButtonField().triggers(["#x", "#y"]),
        ButtonField().triggers("#x").triggers("#y"),
    ],
    ids=["field-list", "field-chained", "button-list", "button-chained"],
)
def test_several_selector_targets_are_rejected(source):
    """A source may declare at most one selector target."""

    class _Form(HtmxForm):
        src = source

    with pytest.raises(ValueError, match="'src' declares several selector targets"):
        _Form()


def test_one_selector_target_with_field_targets_is_accepted():
    """One selector target can go along with field targets."""

    class _Form(HtmxForm):
        chips = StringField()
        genre = StringField().triggers(["#results", "chips"], on="change")

    form = _Form()
    assert attr(form.genre(), "hx-target") == "#results"
    assert "change" in attr(form.genre(), "hx-trigger")


def test_selector_source_that_listens_to_a_field_is_rejected():
    """A field with a selector target cannot listen to another field."""

    class _Form(HtmxForm):
        name = StringField()
        a = StringField().triggers("#x").triggered_by("b")
        b = StringField()

    with pytest.raises(ValueError, match="'a' has a selector target and listens"):
        _Form()


def test_selector_source_targeted_by_another_field_is_rejected():
    """A field with a selector target cannot be the target of another field."""

    class _Form(HtmxForm):
        name = StringField()
        a = StringField().triggers("#x")
        b = StringField().triggers("a")

    with pytest.raises(ValueError, match="'a' has a selector target and listens"):
        _Form()


def test_button_rejects_an_event():
    """A button fires on click, so ``on=`` on its declaration raises ``ValueError``."""

    class _Form(HtmxForm):
        tags = FieldList(StringField())
        add = ButtonField("+").triggers("tags", list_add, on="change")

    with pytest.raises(ValueError, match="'add' is a button"):
        _Form()


@pytest.mark.parametrize(
    ("event", "source_trigger"),
    [
        ("change", "blur changed, change"),
        ("click", "blur changed, click"),
        ("blur", "blur changed"),
        ("focusout", "blur changed"),
    ],
)
def test_source_posts_a_non_typing_event(event, source_trigger):
    """For an event that is not typing, the source posts and the target does not listen."""

    class _Form(HtmxForm):
        src = StringField()
        dst = StringField().triggered_by("src", on=event)

    form = _Form()
    assert attr(form.src(), "hx-trigger") == source_trigger
    assert attr(form.dst(), "hx-trigger") == "blur changed"
    assert markers(form.src()) == []


@pytest.mark.parametrize("event", ["input delay:300ms", "keyup"])
def test_target_listens_to_a_typing_event(event):
    """For a typing event, the target listens to the source."""

    class _Form(HtmxForm):
        src = StringField()
        dst = StringField().triggered_by("src", on=event)

    form = _Form()
    assert marker_clause(event, "dst") in form.dst()
    assert markers(form.src()) == ["dst"]


def test_source_without_inline_validation_posts_its_event():
    """Without inline validation, the source posts on the declared event alone."""

    class _Form(HtmxForm):
        class Meta:
            htmx_inline_validation = False

        src = StringField()
        dst = StringField().triggered_by("src", on="blur")

    form = _Form()
    assert attr(form.src(), "hx-trigger") == "blur"
    assert attr(form.dst(), "hx-trigger") is None


def test_select_validates_on_change():
    """A select validates as soon as the user picks an option."""

    class _Form(HtmxForm):
        color = SelectField(choices=["red", "blue"])

    assert attr(_Form().color(), "hx-trigger") == "change"


def test_select_source_posts_once_on_change():
    """A select whose declaration is on change posts one request for both."""

    class _Form(HtmxForm):
        color = SelectField(choices=["red", "blue"])
        dst = StringField().triggered_by("color", on="change")

    assert attr(_Form().color(), "hx-trigger") == "change"


@pytest.mark.parametrize("event", ["change", "input delay:200ms"])
def test_field_that_sends_requests_replaces_its_request_in_flight(event):
    """A field that sends requests aborts the one in flight on a new event."""

    class _Form(HtmxForm):
        class Meta:
            htmx_inline_validation = False

        src = StringField()
        dst = StringField().triggered_by("src", on=event)
        other = StringField()

    form = _Form()
    sender = form.src if event == "change" else form.dst
    assert attr(sender(), "hx-sync") == "this:replace"
    assert attr(form.other(), "hx-sync") is None


def test_posting_source_sync_can_be_overridden():
    """A ``render_kw`` value replaces the default ``hx-sync``."""

    class _Form(HtmxForm):
        src = StringField(render_kw={"hx-sync": "this:queue last"})
        dst = StringField().triggered_by("src", on="change")

    assert attr(_Form().src(), "hx-sync") == "this:queue last"


def test_several_events_with_a_typing_one_are_all_listened_to():
    """A declaration with a typing event gets one listener clause per event."""

    class _Form(HtmxForm):
        src = StringField()
        dst = StringField().triggered_by("src", on="input delay:200ms, focus")

    form = _Form()
    assert attr(form.dst(), "hx-trigger") == (
        f"{marker_clause('input delay:200ms', 'dst')},"
        f" {marker_clause('focusin', 'dst--1')}, blur changed"
    )
    assert markers(form.src()) == ["dst", "dst--1"]


def test_several_non_typing_events_are_posted_by_the_source():
    """A declaration without a typing event is posted by the source on each event."""

    class _Form(HtmxForm):
        src = StringField()
        dst = StringField().triggered_by("src", on="change, focus")

    form = _Form()
    assert attr(form.src(), "hx-trigger") == "blur changed, change, focus"
    assert markers(form.src()) == []


@pytest.mark.parametrize(
    ("event", "clauses"),
    [
        ("change", ["change"]),
        ("input delay:200ms, focus", ["input delay:200ms", "focus"]),
        ("keyup[key=='a,b'], focus", ["keyup[key=='a,b']", "focus"]),
        ("change,", ["change"]),
    ],
)
def test_clauses_split_on_top_level_commas(event, clauses):
    """An hx-trigger value splits on the commas outside event filters."""
    assert _clauses(event) == clauses


def test_selector_and_field_targets_on_one_event_share_one_clause():
    """A source with a selector and a field target on one event sends one request."""

    class _Form(HtmxForm):
        class Meta:
            htmx_inline_validation = False

        genre = StringField().triggers(["#results", "chips"], on="change")
        chips = StringField()

    assert attr(_Form().genre(), "hx-trigger") == "change"
