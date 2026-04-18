from __future__ import annotations

import json

import pytest
from markupsafe import Markup
from wtforms import ButtonField
from wtforms import DataList
from wtforms import FieldList
from wtforms import FormField
from wtforms import RadioField
from wtforms import SelectChoice
from wtforms import SelectField
from wtforms import SelectMultipleField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import widgets

from wtforms_htmx import HtmxForm
from wtforms_htmx.mutations import list_add
from wtforms_htmx.mutations import list_remove

from .helpers import attr


def test_inline_validation_renders_the_form_wide_defaults():
    """A plain field validates inline with the form-wide defaults."""

    class _Form(HtmxForm):
        email = StringField()

    assert _Form().email() == (
        '<input hx-include="closest form" hx-post="" hx-swap="outerHTML"'
        ' hx-trigger="blur changed" id="email" name="email" type="text" value="">'
    )


def test_inline_validation_follows_the_meta_settings():
    """Meta settings change the trigger and the swap of inline validation."""

    class _Form(HtmxForm):
        class Meta:
            htmx_validation_trigger = "change"
            htmx_swap = "innerHTML"

        email = StringField()

    html = _Form().email()
    assert attr(html, "hx-trigger") == "change"
    assert attr(html, "hx-swap") == "innerHTML"


@pytest.mark.parametrize(
    "field",
    [
        RadioField(choices=["a", "b"]),
        SelectMultipleField(
            choices=["a", "b"],
            widget=widgets.ListWidget(prefix_label=False),
            option_widget=widgets.CheckboxInput(),
        ),
    ],
    ids=["radio", "checkbox"],
)
def test_inline_validation_of_an_option_list_fires_on_change(field):
    """A list of radio buttons or checkboxes validates on ``change``, not on blur."""

    class _Form(HtmxForm):
        class Meta:
            htmx_validation_trigger = "blur changed delay:1s"

    _Form.choice = field
    html = _Form().choice()
    assert html.startswith("<ul ")
    assert html.count("hx-trigger") == 1
    assert attr(html, "hx-trigger") == "change"


def test_inline_validation_skips_buttons_and_containers():
    """Buttons, ``FormField`` and ``FieldList`` containers get no inline validation."""

    class _Sub(HtmxForm):
        x = StringField()

    class _Form(HtmxForm):
        save = SubmitField()
        sub = FormField(_Sub)
        rows = FieldList(StringField(), min_entries=1)
        email = StringField()

    form = _Form()
    assert "hx-" not in form.save()
    assert form.sub().startswith('<table id="sub">')
    assert form.rows().startswith('<ul id="rows">')
    assert attr(form.sub.form.x(), "hx-trigger") == "blur changed"
    assert attr(form.email(), "hx-trigger") == "blur changed"


def test_inline_validation_reaches_the_rows_of_a_field_list():
    """Each row of a ``FieldList`` of plain fields validates inline, nested lists too."""

    class _Form(HtmxForm):
        rows = FieldList(StringField(), min_entries=1)
        grid = FieldList(FieldList(StringField(), min_entries=1), min_entries=1)

    form = _Form()
    assert attr(form.rows[0](), "hx-trigger") == "blur changed"
    assert attr(form.grid[0][0](), "hx-trigger") == "blur changed"


def test_inline_validation_off_leaves_fields_inert():
    """With inline validation off, a plain field renders without htmx attributes."""

    class _Form(HtmxForm):
        class Meta:
            htmx_inline_validation = False

        email = StringField()

    assert _Form().email() == '<input id="email" name="email" type="text" value="">'


def test_field_render_kw_wins_over_form_wide_attrs():
    """``render_kw`` on the field wins over the form-wide trigger."""

    class _Form(HtmxForm):
        email = StringField(render_kw={"hx-trigger": "input changed delay:200ms"})

    assert attr(_Form().email(), "hx-trigger") == "input changed delay:200ms"


def test_call_site_attrs_win_over_field_render_kw():
    """Attributes passed when rendering win over the field ``render_kw``."""

    class _Form(HtmxForm):
        email = StringField(render_kw={"hx-trigger": "field-level"})

    assert attr(_Form().email(**{"hx-trigger": "call-site"}), "hx-trigger") == (
        "call-site"
    )


class _TagsForm(HtmxForm):
    tags = FieldList(StringField())
    add_tag = ButtonField("+").triggers("tags", list_add)


def test_button_renders_the_request_attrs_of_its_target():
    """A button posts the form without validation and swaps its target."""
    assert _TagsForm().add_tag() == (
        '<button formnovalidate hx-include="closest form" hx-post=""'
        ' hx-swap="outerHTML" hx-target="#tags" hx-vals="{&#34;add_tag&#34;: &#34;&#34;}"'
        ' id="add_tag" name="add_tag" type="submit" value="">+</button>'
    )


def test_button_target_includes_the_form_prefix():
    """A button targets the full id of its target, form prefix included."""
    assert attr(_TagsForm(prefix="my").add_tag(), "hx-target") == "#my-tags"


def test_button_with_a_selector_target_renders_it_verbatim():
    """A button with a selector target puts the selector in ``hx-target`` as is."""

    class _Form(HtmxForm):
        save = ButtonField("Save").triggers("#preview", lambda form, s, t: None)

    assert attr(_Form().save(), "hx-target") == "#preview"


def test_button_htmx_swap_ignores_the_meta_setting():
    """``Meta.htmx_swap`` changes inline validation, not the button swap."""

    class _Form(HtmxForm):
        class Meta:
            htmx_swap = "innerHTML"

        email = StringField()
        items = StringField()
        save = SubmitField("Save").triggers("items")

    form = _Form()
    assert attr(form.email(), "hx-swap") == "innerHTML"
    assert attr(form.save(), "hx-swap") == "outerHTML"
    assert form.htmx_submit_attrs(form.save)["hx-swap"] == "outerHTML"


def test_button_dotted_target_points_at_the_subform_field():
    """A dotted target resolves to the id of the sub-form field."""

    class _Address(HtmxForm):
        region = StringField()

    class _Form(HtmxForm):
        address = FormField(_Address)
        go = ButtonField().triggers("address.region")

    form = _Form()
    assert attr(form.go(), "hx-target") == "#address-region"
    assert form.htmx_submit_attrs(form.go)["hx-target"] == "#address-region"


class _PickerForm(HtmxForm):
    picker = SelectField(
        choices=[SelectChoice("FR", "France"), SelectChoice("DE", "Germany")],
        option_widget=widgets.Button(),
        validate_choice=False,
    ).triggers("dest")
    dest = StringField()


def test_htmx_submit_attrs_returns_the_attrs_of_the_first_target():
    """``htmx_submit_attrs`` returns the request attributes of the first target."""
    form = _PickerForm()
    assert form.htmx_submit_attrs(form.picker) == {
        "formnovalidate": True,
        "hx-post": "",
        "hx-target": "#dest",
        "hx-swap": "outerHTML",
        "hx-include": "closest form",
    }


def test_htmx_submit_attrs_of_an_option_uses_its_parent_field():
    """An option of a choices field in a sub-form gets the attributes of its parent field."""

    class _Sub(HtmxForm):
        picker = SelectField(
            choices=[SelectChoice("FR", "France")],
            option_widget=widgets.Button(),
            validate_choice=False,
        ).triggers("dest")
        dest = StringField()

    class _Form(HtmxForm):
        sub = FormField(_Sub)

    form = _Form()
    option = next(iter(form.sub.form.picker))
    assert form.htmx_submit_attrs(option)["hx-target"] == "#sub-dest"


def test_htmx_submit_attrs_is_empty_without_trigger():
    """A field without trigger declaration gets no submit attributes."""

    class _Form(HtmxForm):
        email = StringField()

    form = _Form()
    assert form.htmx_submit_attrs(form.email) == {}
    assert form.htmx_submit_params(form.email) == Markup("")


@pytest.mark.parametrize("selector", ["#results", "closest .toast"])
def test_htmx_submit_attrs_passes_a_selector_target_verbatim(selector):
    """A selector target reaches ``hx-target`` as written."""

    class _Form(HtmxForm):
        picker = SelectField(
            choices=[SelectChoice("1", "One")],
            option_widget=widgets.Button(),
            validate_choice=False,
        ).triggers(selector, lambda form, s, t: None)

    form = _Form()
    assert form.htmx_submit_attrs(form.picker)["hx-target"] == selector


def test_htmx_submit_params_formats_the_attrs():
    """``htmx_submit_params`` returns the attributes as HTML markup."""
    form = _PickerForm()
    assert form.htmx_submit_params(form.picker) == Markup(
        'formnovalidate hx-include="closest form" hx-post=""'
        ' hx-swap="outerHTML" hx-target="#dest"'
    )


def test_choices_field_with_button_options_renders_a_bare_container():
    """A choices field with button options gets no htmx attribute on its container."""
    assert _PickerForm().picker() == (
        '<select id="picker" name="picker"><option value="FR">France</option>'
        '<option value="DE">Germany</option></select>'
    )


def test_choice_option_renders_bare_with_its_render_kw():
    """An option renders without wrapper, with the field and call-site attributes."""

    class _Form(HtmxForm):
        class Meta:
            @staticmethod
            def field_wrapper(field, render_kw):
                return f"<div>{field.widget(field, **render_kw)}</div>"

        color = RadioField(
            choices=[SelectChoice("r", "Red")], render_kw={"class": "a", "lang": "en"}
        )

    form = _Form()
    option = next(iter(form.color))
    assert form.color().startswith("<div><ul ")
    assert option(**{"class": "b", "data-x": "1"}) == (
        '<input class="b" data-x="1" id="color-0" lang="en" name="color"'
        ' type="radio" value="r">'
    )


class _ButtonsForm(HtmxForm):
    items = FieldList(StringField(), min_entries=2)
    rm_item = ButtonField("Remove").triggers("items", list_remove)
    save = SubmitField("Save it").triggers("items", list_add)
    plain = ButtonField("Plain")


@pytest.mark.parametrize(
    ("field_name", "render_kw"),
    [
        ("rm_item", {"value": "1"}),
        ("rm_item", {"value": 3}),
        ("rm_item", {"value": 'a"b<c>&é'}),
        ("rm_item", {}),
        ("save", {"value": "zz"}),
        ("save", {}),
    ],
    ids=[
        "button-str",
        "button-int",
        "button-special",
        "button-default",
        "submit-str",
        "submit-default",
    ],
)
def test_button_hx_vals_repeats_the_rendered_value(field_name, render_kw):
    """The ``hx-vals`` pair is exactly what a plain submit posts."""
    html = _ButtonsForm()[field_name](**render_kw)
    assert json.loads(attr(html, "hx-vals")) == {field_name: attr(html, "value")}


def test_button_hx_vals_falls_back_to_the_field_data():
    """Without a call-site ``value=``, a button posts its own data."""
    html = _ButtonsForm(data={"rm_item": "7"}).rm_item()
    assert attr(html, "value") == "7"
    assert json.loads(attr(html, "hx-vals")) == {"rm_item": "7"}


def test_submit_input_hx_vals_defaults_to_the_label():
    """A ``SubmitField`` posts its label, so its ``hx-vals`` carries the label."""
    assert json.loads(attr(_ButtonsForm().save(), "hx-vals")) == {"save": "Save it"}


def test_button_without_request_gets_no_hx_vals():
    """A button that sends no htmx request gets no ``hx-vals``."""
    assert attr(_ButtonsForm().plain(), "hx-vals") is None


def test_button_explicit_hx_vals_wins():
    """An ``hx-vals`` passed when rendering is kept."""
    html = _ButtonsForm().rm_item(value="1", **{"hx-vals": '{"rm_item": "9"}'})
    assert json.loads(attr(html, "hx-vals")) == {"rm_item": "9"}


def test_button_option_hx_vals_repeats_the_choice_value():
    """Each option button posts the parent field name with its own choice value."""

    class _Form(HtmxForm):
        items = FieldList(StringField(), min_entries=1)
        pick = SelectField(
            choices=[SelectChoice("a", "A"), SelectChoice("b<&>", 'Lab"el')],
            option_widget=widgets.Button(),
        ).triggers("items", list_add)

    form = _Form()
    htmls = [
        opt(label=opt.choice.label, **form.htmx_submit_attrs(opt)) for opt in form.pick
    ]
    assert [(json.loads(attr(h, "hx-vals")), attr(h, "value")) for h in htmls] == [
        ({"pick": "a"}, "a"),
        ({"pick": "b<&>"}, "b<&>"),
    ]


def test_choices_container_listener_gets_no_hx_vals():
    """A listening choices container posts its value natively, without ``hx-vals``."""

    class _Form(HtmxForm):
        query = StringField()
        pick = SelectField(
            choices=[SelectChoice("a", "A")], option_widget=widgets.Button()
        ).triggered_by("query")

    html = _Form().pick()
    assert attr(html, "hx-post") == ""
    assert attr(html, "hx-vals") is None


class _PreviewForm(HtmxForm):
    content = StringField().triggers("#preview", on="input delay:300ms")


def test_selector_target_renders_on_the_source():
    """A field with a selector target sends its own request and swaps the selector."""
    assert _PreviewForm().content() == (
        '<input hx-include="closest form" hx-post="" hx-swap="outerHTML"'
        ' hx-target="#preview" hx-trigger="input delay:300ms" id="content"'
        ' name="content" type="text" value="">'
    )


def test_selector_source_field_render_kw_wins():
    """``render_kw`` on a selector source wins over the computed swap."""

    class _Form(HtmxForm):
        content = StringField(render_kw={"hx-swap": "innerHTML"}).triggers(
            "#preview", on="input delay:300ms"
        )

    html = _Form().content()
    assert attr(html, "hx-swap") == "innerHTML"
    assert attr(html, "hx-target") == "#preview"
    assert attr(html, "hx-trigger") == "input delay:300ms"


def test_selector_source_call_site_attrs_win():
    """Attributes passed when rendering a selector source win over the computed ones."""
    assert attr(_PreviewForm().content(**{"hx-swap": "afterend"}), "hx-swap") == (
        "afterend"
    )


def test_htmx_method_sets_the_verb_of_every_request():
    """``Meta.htmx_method`` sets the verb of every request the library emits."""

    class _Form(HtmxForm):
        class Meta:
            htmx_method = "get"

        email = StringField()
        content = StringField().triggers("#preview", on="input")
        tags = FieldList(StringField())
        add = ButtonField("+").triggers("tags", list_add)
        country = StringField(datalist=DataList(lambda form, field: []))

    form = _Form()
    htmls = [form.email(), form.content(), form.add(), form.country.datalist()]
    assert [attr(html, "hx-get") for html in htmls] == ["", "", "", ""]
    assert [attr(html, "hx-post") for html in htmls] == [None, None, None, None]
    assert form.htmx_submit_attrs(form.add)["hx-get"] == ""
    assert "hx-post" not in form.htmx_submit_attrs(form.add)


class _WrappedForm(HtmxForm):
    class Meta:
        @staticmethod
        def field_wrapper(field, render_kw):
            return f'<div class="meta">{field.widget(field, **render_kw)}</div>'

    default = StringField()
    bare = StringField(wrapper=False)
    custom = StringField(
        wrapper=lambda field, render_kw: (
            f'<p class="own">{field.widget(field, **render_kw)}</p>'
        )
    )


def test_wrapper_kwarg_selects_the_wrapper():
    """``wrapper=`` picks the Meta wrapper, no wrapper, or a custom wrapper."""
    form = _WrappedForm()
    assert form.default().startswith('<div class="meta"><input ')
    assert form.bare().startswith("<input ")
    assert form.custom().startswith('<p class="own"><input ')


def test_callable_datalist_renders_its_refresh_attrs():
    """A datalist with callable choices refreshes its options on input."""

    class _Form(HtmxForm):
        city = StringField(datalist=DataList(lambda form, field: ["Paris"]))

    assert _Form().city.datalist() == (
        '<datalist hx-include="closest form" hx-post=""'
        ' hx-select="#city-datalist &gt; option" hx-swap="innerHTML"'
        ' hx-target="this"'
        ' hx-trigger="input delay:200ms from:body target:#city"'
        ' id="city-datalist"><option value="Paris"></datalist>'
    )


def test_datalist_render_kw_wins_over_the_refresh_attrs():
    """``render_kw`` on the datalist wins over the computed attributes."""

    class _Form(HtmxForm):
        city = StringField(
            datalist=DataList(lambda form, field: [], render_kw={"hx-trigger": "focus"})
        )

    assert attr(_Form().city.datalist(), "hx-trigger") == "focus"


def test_static_datalist_gets_no_htmx_attrs():
    """A datalist with static choices renders without htmx attributes."""

    class _Form(HtmxForm):
        color = StringField(datalist=DataList(["red"]))

    assert _Form().color.datalist() == (
        '<datalist id="color-datalist"><option value="red"></datalist>'
    )


class _Inner(HtmxForm):
    city = StringField()
    look_up = ButtonField("Look up").triggers("city")


def test_nested_form_inherits_the_endpoint_of_its_parent():
    """A sub-form posts to the endpoint set on the meta of its parent form."""

    class _Form(HtmxForm):
        address = FormField(_Inner)

    form = _Form(meta={"htmx_endpoint": "/merge"})
    assert attr(form.address.city(), "hx-post") == "/merge"
    assert attr(form.address.look_up(), "hx-post") == "/merge"


def test_nested_form_inherits_disabled_inline_validation():
    """A sub-form has no inline validation when its parent turns it off."""

    class _Form(HtmxForm):
        class Meta:
            htmx_inline_validation = False

        address = FormField(_Inner)

    assert attr(_Form().address.city(), "hx-trigger") is None


def test_nested_form_keeps_its_own_settings():
    """A setting the sub-form declares wins over the one of its parent."""

    class _OwnInner(HtmxForm):
        class Meta:
            htmx_endpoint = "/own"

        city = StringField()

    class _Form(HtmxForm):
        address = FormField(_OwnInner)

    assert (
        attr(_Form(meta={"htmx_endpoint": "/merge"}).address.city(), "hx-post")
        == "/own"
    )


def test_list_rows_inherit_the_settings_of_the_form():
    """The sub-forms of a FieldList inherit the settings of the form."""

    class _Form(HtmxForm):
        addresses = FieldList(FormField(_Inner), min_entries=1)

    form = _Form(meta={"htmx_endpoint": "/merge"})
    assert attr(form.addresses[0].city(), "hx-post") == "/merge"


def test_deeply_nested_form_inherits_the_settings():
    """A sub-form of a sub-form inherits the settings of the root form."""

    class _Middle(HtmxForm):
        inner = FormField(_Inner)

    class _Form(HtmxForm):
        middle = FormField(_Middle)

    form = _Form(meta={"htmx_endpoint": "/merge"})
    assert attr(form.middle.inner.city(), "hx-post") == "/merge"
