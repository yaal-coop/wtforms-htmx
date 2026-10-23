from __future__ import annotations

import pytest
from flask import Flask
from flask import request
from flask import Response
from markupsafe import Markup
from werkzeug.datastructures import MultiDict
from wtforms import ButtonField
from wtforms import DataList
from wtforms import FieldList
from wtforms import Form
from wtforms import FormField
from wtforms import PasswordField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import DataRequired
from wtforms.validators import Length
from wtforms.validators import Regexp

from wtforms_htmx import HtmxForm
from wtforms_htmx import HtmxResponse
from wtforms_htmx.mutations import list_add
from wtforms_htmx.mutations import list_remove
from wtforms_htmx.mutations import value_set
from wtforms_htmx.partial import _extract_outer_id
from wtforms_htmx.partial import _with_swap_oob

from .helpers import attr
from .helpers import htmx_headers
from .helpers import oob_ids


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ('<div id="x">hi</div>', "x"),
        ('<input id="email">', "email"),
        ('<input id="email"/>', "email"),
        ('  \n  <div id="x">hi</div>', "x"),
        ('<!-- c --><div id="x">hi</div>', "x"),
        ('<div id="outer"><span id="inner"></span></div>', "outer"),
        ('<div class="x">hi</div>', None),
        ('<div><span id="inner">hi</span></div>', None),
        ("", None),
        ("just text", None),
    ],
    ids=[
        "element",
        "void",
        "self-closing",
        "leading-space",
        "leading-comment",
        "inner-id",
        "no-id",
        "only-inner-id",
        "empty",
        "text",
    ],
)
def test_extract_outer_id(html, expected):
    """The id of the first opening tag is returned, or ``None`` when it has none."""
    assert _extract_outer_id(html) == expected


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        (
            '<output id="t" class="x" >1</output>',
            '<output id="t" class="x" hx-swap-oob="outerHTML">1</output>',
        ),
        ('<input id="e" />', '<input id="e" hx-swap-oob="outerHTML"/>'),
        (
            '<!-- c -->\n<div\n id="x">y</div>',
            '<!-- c -->\n<div\n id="x" hx-swap-oob="outerHTML">y</div>',
        ),
    ],
    ids=["element", "self-closing", "comment-and-newlines"],
)
def test_with_swap_oob_marks_the_outer_element(html, expected):
    """``hx-swap-oob="outerHTML"`` is added to the outer element of a fragment."""
    assert _with_swap_oob(html) == expected


@pytest.mark.parametrize(
    "html",
    [
        '<div id="x" hx-swap-oob="innerHTML">a</div>',
        '<div id="x" data-hx-swap-oob="true">a</div>',
        '<template><tr id="r" hx-swap-oob="true"></tr></template>',
        "just text",
    ],
    ids=["explicit", "data-prefixed", "template", "text"],
)
def test_with_swap_oob_keeps_the_fragment(html):
    """A fragment that sets its own swap, a ``<template>`` or plain text is left as is."""
    assert _with_swap_oob(html) == html


def test_with_swap_oob_requires_an_outer_id():
    """An outer element without an id raises ``ValueError``."""
    with pytest.raises(ValueError, match="needs an id"):
        _with_swap_oob('<div class="x">a</div>')


class _UserForm(HtmxForm):
    email = StringField(
        validators=[DataRequired(), Regexp(r".+@.+\..+", message="Invalid email")]
    )
    name = StringField(validators=[DataRequired()])
    tags = FieldList(StringField())
    add_tag = ButtonField("+").triggers("tags", list_add)
    color = StringField(datalist="colors")


@pytest.mark.parametrize(
    ("formdata", "headers"),
    [
        (MultiDict({"email": "bad"}), {}),
        (MultiDict({"email": "bad"}), {"HX-Request": "true"}),
        (MultiDict({"email": "bad"}), htmx_headers("unknown")),
        (MultiDict({"email": "bad"}), {**htmx_headers("email"), "HX-Boosted": "true"}),
        (MultiDict({"tags-0": "a"}), {"HX-Request": "true"}),
        (None, {"HX-Request": "true"}),
        (MultiDict(), htmx_headers("colors")),
    ],
    ids=[
        "not-htmx",
        "no-source",
        "unknown-source",
        "boosted",
        "no-click",
        "no-formdata",
        "external-datalist",
    ],
)
def test_partial_is_none_when_nothing_is_dispatched(formdata, headers):
    """``partial()`` returns ``None`` when the request asks for no fragment."""
    assert _UserForm(formdata, headers=headers).partial() is None


def test_partial_is_none_for_a_field_without_htmx_behavior():
    """A request from a field that neither validates inline nor listens gets no fragment."""

    class _Form(HtmxForm):
        class Meta:
            htmx_inline_validation = False

        email = StringField()

    form = _Form(MultiDict({"email": "x"}), headers=htmx_headers("email"))
    assert form.partial() is None


def test_inline_validation_returns_the_field():
    """An inline validation request gets the field back, with its value."""
    form = _UserForm(
        MultiDict({"email": "alice@example.com", "name": "Alice"}),
        headers=htmx_headers("email", "email"),
    )
    assert form.partial() == HtmxResponse(
        '<input hx-include="closest form" hx-post="" hx-swap="outerHTML"'
        ' hx-trigger="blur changed" id="email" name="email" required type="text"'
        ' value="alice@example.com">',
        {},
    )


class _ErrorsForm(_UserForm):
    class Meta:
        @staticmethod
        def field_wrapper(field, render_kw):
            errors = "".join(f"<p>{error}</p>" for error in field.errors)
            return f'<div id="{field.id}-wrapper">{field.widget(field, **render_kw)}{errors}</div>'


def test_inline_validation_returns_only_the_field_errors():
    """An invalid field gets back its own fragment with its own errors."""
    form = _ErrorsForm(
        MultiDict({"email": "not-an-email", "name": ""}), headers=htmx_headers("email")
    )
    body = form.partial().body
    assert body.startswith('<div id="email-wrapper"><input ')
    assert body.endswith("<p>Invalid email</p></div>")
    assert body.count("<p>") == 1


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        (htmx_headers("email"), {"HX-Retarget": "#email-wrapper"}),
        (htmx_headers("email", "email-wrapper"), {}),
        (
            {"HX-Request": "true", "HX-Trigger": "email", "HX-Target": "email-wrapper"},
            {},
        ),
    ],
    ids=["no-target", "htmx4-target", "htmx2-target"],
)
def test_retarget_is_sent_when_the_fragment_is_not_the_target(headers, expected):
    """``HX-Retarget`` points at the fragment, unless htmx already targets it."""
    form = _ErrorsForm(MultiDict({"email": "alice@example.com"}), headers=headers)
    assert form.partial().headers == expected


@pytest.mark.parametrize(
    "headers",
    [
        {"HX-Request": "true", "HX-Trigger": "city-datalist"},
        {"HX-Request": "true", "HX-Source": "datalist#city-datalist"},
    ],
    ids=["htmx2", "htmx4"],
)
def test_datalist_refresh_returns_the_datalist(headers):
    """A datalist refresh gets the datalist alone, without retarget."""

    class _Form(HtmxForm):
        city = StringField(datalist=DataList(lambda form, field: ["Bordeaux"]))

    result = _Form(MultiDict({"city": "Bord"}), headers=headers).partial()
    assert result.body.startswith("<datalist ")
    assert result.body.endswith(
        ' id="city-datalist"><option value="Bordeaux"></datalist>'
    )
    assert result.headers == {}


class _EmailsForm(HtmxForm):
    emails = FieldList(StringField(validators=[Length(min=3)]), min_entries=1)
    add_email = ButtonField("+").triggers("emails", list_add)
    rm_email = ButtonField("-").triggers("emails", list_remove)


def test_inline_validation_of_a_list_row_returns_the_row():
    """A row of a ``FieldList`` validates inline and comes back alone."""
    form = _EmailsForm(MultiDict({"emails-0": "x"}), headers=htmx_headers("emails-0"))
    result = form.partial()
    assert result.body == str(form.emails[0]())
    assert form.emails[0].errors


def test_list_row_added_by_a_button_validates_inline():
    """A row added in the same request is rendered with inline validation."""
    form = _EmailsForm(
        MultiDict({"emails-0": "abc", "add_email": ""}),
        headers=htmx_headers("add_email", "emails"),
    )
    assert attr(str(form.emails[1]()), "hx-trigger") == "blur changed"


def test_renumbered_list_row_keeps_its_inline_validation():
    """After a removal renumbers the rows, each row still validates itself only."""
    form = _EmailsForm(
        MultiDict({"emails-0": "a", "emails-1": "b", "rm_email": "0"}),
        headers=htmx_headers("rm_email", "emails"),
    )
    html = str(form.emails[0]())
    assert form.emails[0].id == "emails-0"
    assert attr(html, "hx-trigger") == "blur changed"
    assert "data-wtforms-htmx-for" not in html


def test_list_button_returns_the_list_alone():
    """A list button click gets the whole list back, without validated fields."""
    form = _UserForm(
        MultiDict({"email": "bad", "tags-0": "a", "add_tag": ""}),
        headers=htmx_headers("add_tag", "tags"),
    )
    attrs = 'hx-include="closest form" hx-post="" hx-swap="outerHTML" hx-trigger="blur changed"'
    assert form.partial() == HtmxResponse(
        '<ul id="tags"><li><label for="tags-0">Tags-0</label>'
        f' <input {attrs} id="tags-0" name="tags-0" type="text" value="a"></li>'
        '<li><label for="tags-1">Tags-1</label>'
        f' <input {attrs} id="tags-1" name="tags-1" type="text" value=""></li></ul>',
        {},
    )


def test_row_button_returns_the_parent_list():
    """A remove button in a row returns the parent list without that row."""

    class _Row(HtmxForm):
        value = StringField()
        rm = SubmitField("×").triggers("#rows", list_remove)

    class _Form(HtmxForm):
        rows = FieldList(FormField(_Row))

    form = _Form(
        MultiDict(
            {
                "rows-0-value": "a",
                "rows-1-value": "b",
                "rows-2-value": "c",
                "rows-1-rm": "1",
            }
        ),
        headers=htmx_headers("rows-1-rm", "rows"),
    )
    result = form.partial()
    assert result.headers == {}
    assert result.body.startswith('<ul id="rows">')
    assert 'value="a"' in result.body
    assert 'value="b"' not in result.body
    assert result.body.count('hx-target="#rows"') == 2


class _PreviewForm(HtmxForm):
    content = StringField().triggers(
        "#preview",
        lambda form, source, target: Markup(
            f'<div id="preview">{form.content.data}</div>'
        ),
    )
    side = StringField(default="sidekick")


def test_selector_callback_markup_is_the_body():
    """Markup returned by a selector callback is the response body."""
    form = _PreviewForm(
        MultiDict({"content": "hello"}), headers=htmx_headers("content", "preview")
    )
    assert form.partial() == HtmxResponse('<div id="preview">hello</div>', {})


def test_selector_callback_returning_none_swaps_nothing():
    """A selector callback that returns ``None`` sends ``HX-Reswap: none``."""

    class _Form(HtmxForm):
        content = StringField().triggers("#preview", lambda form, source, target: None)

    form = _Form(MultiDict({"content": "x"}), headers=htmx_headers("content"))
    assert form.partial() == HtmxResponse("", {"HX-Reswap": "none"})


def test_selector_without_callback_swaps_nothing():
    """A selector target without callback sends ``HX-Reswap: none``."""

    class _Form(HtmxForm):
        content = StringField().triggers("#preview")

    form = _Form(MultiDict({"content": "x"}), headers=htmx_headers("content"))
    assert form.partial() == HtmxResponse("", {"HX-Reswap": "none"})


def test_selector_callback_str_is_one_fragment():
    """A plain ``str`` from a callback is one fragment, not a list of characters."""

    class _Form(HtmxForm):
        content = StringField().triggers(
            "#preview", lambda form, source, target: "<div id='preview'>raw</div>"
        )

    form = _Form(MultiDict({"content": "x"}), headers=htmx_headers("content"))
    assert form.partial().body == "<div id='preview'>raw</div>"


def test_selector_callback_list_puts_the_extras_out_of_band():
    """``[Markup, field]`` makes the Markup the body and the field out-of-band."""

    class _Form(_PreviewForm):
        content = StringField().triggers(
            "#preview",
            lambda form, source, target: [
                Markup('<div id="preview">primary</div>'),
                form.side,
            ],
        )

    form = _Form(MultiDict({"content": "x"}), headers=htmx_headers("content"))
    assert form.partial().body == (
        '<div id="preview">primary</div>' + _with_swap_oob(str(form.side()))
    )


def test_selector_callback_list_without_primary_swaps_only_the_extras():
    """``[None, field, Markup]`` sends only out-of-band extras and ``HX-Reswap: none``."""

    class _Form(_PreviewForm):
        content = StringField().triggers(
            "#preview",
            lambda form, source, target: [
                None,
                form.side,
                Markup('<output id="grand_total">42</output>'),
            ],
        )

    form = _Form(MultiDict({"content": "x"}), headers=htmx_headers("content"))
    result = form.partial()
    assert result.headers == {"HX-Reswap": "none"}
    assert result.body == (
        _with_swap_oob(str(form.side()))
        + '<output id="grand_total" hx-swap-oob="outerHTML">42</output>'
    )


def test_callback_text_without_element_is_not_retargeted():
    """A callback that returns plain text swaps it into the target, with no ``HX-Retarget``."""

    class _Form(_PreviewForm):
        content = StringField().triggers("#preview", lambda form, source, target: "hi")

    form = _Form(MultiDict({"content": "x"}), headers=htmx_headers("content"))
    result = form.partial()
    assert result.body == "hi"
    assert result.headers == {}


def test_out_of_band_extras_are_rendered_once():
    """Duplicate out-of-band extras from a callback are rendered once."""

    class _Form(_PreviewForm):
        content = StringField().triggers(
            "#preview",
            lambda form, source, target: [
                None,
                form.side,
                form.side,
                Markup('<p id="note">1</p>'),
                Markup('<p id="note">2</p>'),
                Markup("plain text"),
            ],
        )

    form = _Form(MultiDict({"content": "x"}), headers=htmx_headers("content"))
    body = form.partial().body
    assert body.count('id="side"') == 1
    assert body.count('id="note"') == 1
    assert body.endswith('<p id="note" hx-swap-oob="outerHTML">1</p>plain text')


class _ListenerForm(HtmxForm):
    src = StringField()
    dst = StringField(default="default-dst")
    other = StringField(default="default-other")
    side = StringField(default="side-content")


def test_listener_callback_markup_replaces_the_target_render():
    """Markup returned by a listener callback replaces the target render."""

    class _Form(_ListenerForm):
        dst = StringField().triggered_by(
            "src", lambda form, source, target: Markup('<span id="dst">custom</span>')
        )

    form = _Form(MultiDict({"src": "x"}), headers=htmx_headers("dst"))
    assert form.partial() == HtmxResponse(
        '<span id="dst">custom</span>', {"HX-Retarget": "#dst"}
    )


def test_listener_callback_field_replaces_the_target():
    """A field returned by a listener callback is rendered instead of the target."""

    def callback(form, source, target):
        form.other.data = "from-cb"
        return form.other

    class _Form(_ListenerForm):
        dst = StringField().triggered_by("src", callback)

    form = _Form(MultiDict({"src": "x"}), headers=htmx_headers("dst", "other"))
    body = form.partial().body
    assert body.startswith("<input ")
    assert body.endswith(' id="other" name="other" type="text" value="from-cb">')
    assert body.count("<input ") == 1


def test_listener_callback_field_list_puts_the_extras_out_of_band():
    """``[field, *extras]`` renders the field as the body and the extras out-of-band."""

    class _Form(_ListenerForm):
        dst = StringField().triggered_by(
            "src", lambda form, source, target: [form.other, form.side]
        )

    form = _Form(MultiDict({"src": "x"}), headers=htmx_headers("dst", "other"))
    body = form.partial().body
    assert 'id="dst"' not in body
    assert body.index('id="other"') < body.index('id="side"')
    assert oob_ids(body) == ["side"]
    assert body.count("hx-swap-oob") == 1


def test_listener_callback_empty_list_keeps_the_target_render():
    """A callback that returns an empty list keeps the default target render."""

    class _Form(_ListenerForm):
        dst = StringField().triggered_by("src", lambda form, source, target: [])

    form = _Form(MultiDict({"src": "x", "dst": "Paris"}), headers=htmx_headers("dst"))
    body = form.partial().body
    assert body.endswith(' id="dst" name="dst" type="text" value="Paris">')


def test_listener_without_callback_renders_the_posted_value():
    """A listener without callback re-renders with the value the user typed."""

    class _Form(_ListenerForm):
        dst = StringField().triggered_by("src")

    form = _Form(MultiDict({"src": "x", "dst": "Paris"}), headers=htmx_headers("dst"))
    assert form.partial().body.endswith(' value="Paris">')


def test_button_callback_field_keeps_the_other_targets_out_of_band():
    """A field returned by a button callback replaces the first target only."""

    class _Form(_ListenerForm):
        btn = ButtonField("Go").triggers(
            ["dst", "other", "side"], lambda form, source, target: form.other
        )

    form = _Form(MultiDict({"btn": ""}), headers=htmx_headers("btn"))
    body = form.partial().body
    assert 'id="dst"' not in body
    assert body.count('id="other"') == 1
    assert body.count("hx-swap-oob") == 1
    assert body.index('id="other"') < body.index('id="side"')
    assert oob_ids(body) == ["side"]


def test_button_without_callback_renders_its_targets():
    """A button without callback renders its first target and the others out-of-band."""

    class _Form(_ListenerForm):
        refresh = ButtonField("r").triggers(["dst", "other"])

    form = _Form(
        MultiDict({"refresh": "", "dst": "x", "other": "y"}),
        headers=htmx_headers("refresh"),
    )
    body = form.partial().body
    assert body.index('id="dst"') < body.index('id="other"')
    assert oob_ids(body) == ["other"]
    assert body.count("hx-swap-oob") == 1


def test_nested_field_renders_with_its_own_form_meta():
    """A partial renders a sub-form field with the sub-form's meta, as the page does."""

    class _Inner(HtmxForm):
        value = StringField()
        fill = ButtonField("f").triggers("value", value_set("x"))

    class _Form(HtmxForm):
        class Meta:
            @staticmethod
            def field_wrapper(field, render_kw):
                return f'<div id="wrap-{field.id}">{field.widget(field, **render_kw)}</div>'

        top = StringField()
        inner = FormField(_Inner)

    form = _Form(MultiDict({"inner-fill": ""}), headers=htmx_headers("inner-fill"))
    body = form.partial().body
    assert "wrap-top" in str(form.top())
    assert "wrap-inner-value" not in body
    assert body == str(form.inner.form.value())


def test_button_selector_without_callback_swaps_nothing():
    """A button with a selector target and no callback sends ``HX-Reswap: none``."""

    class _Form(HtmxForm):
        ping = ButtonField("p").triggers("#out")

    form = _Form(MultiDict({"ping": ""}), headers=htmx_headers("ping"))
    assert form.partial() == HtmxResponse("", {"HX-Reswap": "none"})


def test_button_selector_callback_markup_is_the_body():
    """Markup returned by a button callback for a selector is the response body."""

    class _Form(HtmxForm):
        save = ButtonField("Save").triggers(
            "#preview",
            lambda form, source, target: Markup('<div id="preview">rendered</div>'),
        )

    form = _Form(MultiDict({"save": ""}), headers={"HX-Request": "true"})
    assert form.partial() == HtmxResponse(
        '<div id="preview">rendered</div>',
        {"HX-Retarget": "#preview"},
    )


def test_button_selector_and_field_targets_render_together():
    """A button with a selector then a field target renders both, the field out-of-band."""

    class _Form(HtmxForm):
        save = (
            ButtonField("Save")
            .triggers(
                "#preview",
                lambda form, source, target: Markup('<div id="preview">primary</div>'),
            )
            .triggers("side")
        )
        side = StringField(default="side-content")

    form = _Form(MultiDict({"save": ""}), headers={"HX-Request": "true"})
    assert form.partial().body == (
        '<div id="preview">primary</div>' + _with_swap_oob(str(form.side()))
    )


def test_rerendered_password_shows_its_new_value():
    """A password re-rendered by a mutation shows its new value, only in the fragment."""

    class _Form(HtmxForm):
        password = PasswordField()
        fill = ButtonField("f").triggers("password", value_set("secret"))

    form = _Form(MultiDict({"fill": ""}), headers=htmx_headers("fill"))
    assert form.partial().body.endswith(' type="password" value="secret">')
    assert form.password().endswith(' type="password" value="">')


def test_rerendered_password_does_not_reveal_other_passwords():
    """While a password is re-rendered, other password fields stay hidden."""
    seen = []

    class _Other(Form):
        password = PasswordField()

    class _Form(HtmxForm):
        class Meta:
            @staticmethod
            def field_wrapper(field, render_kw):
                seen.append(_Other(MultiDict({"password": "other"})).password())
                return field.widget(field, **render_kw)

        password = PasswordField()
        fill = ButtonField("f").triggers("password", value_set("secret"))

    form = _Form(MultiDict({"fill": ""}), headers=htmx_headers("fill"))
    assert form.partial().body.endswith(' value="secret">')
    assert seen == ['<input id="password" name="password" type="password" value="">']


def _signup_app():
    """Build a Flask app whose view adds its own htmx header to the partial response."""
    app = Flask(__name__)

    class _SignupForm(HtmxForm):
        class Meta:
            @staticmethod
            def field_wrapper(field, render_kw):
                return f'<div id="wrap-{field.id}">{field.widget(field, **render_kw)}</div>'

        email = StringField(validators=[Length(min=5)])

    @app.post("/signup")
    def signup():
        form = _SignupForm(request.form, headers=request.headers)
        result = form.partial()
        return Response(result.body, headers={**result.headers, "HX-Trigger": "done"})

    return app


@pytest.mark.parametrize(
    "source_headers",
    [{"HX-Trigger": "email"}, {"HX-Source": "input#email"}],
    ids=["htmx2", "htmx4"],
)
def test_partial_reads_werkzeug_request_headers(source_headers):
    """``partial()`` reads real request headers, and a view merges its own header in."""
    response = (
        _signup_app()
        .test_client()
        .post(
            "/signup",
            data={"email": "ab"},
            headers={"HX-Request": "true", "HX-Target": "stale", **source_headers},
        )
    )
    assert response.get_data(as_text=True).startswith('<div id="wrap-email"><input ')
    assert response.headers["HX-Retarget"] == "#wrap-email"
    assert response.headers["HX-Trigger"] == "done"


def test_wrapped_out_of_band_target_swaps_its_wrapper():
    """An out-of-band target rendered through a wrapper swaps the whole wrapper."""

    class _Form(HtmxForm):
        class Meta:
            @staticmethod
            def field_wrapper(field, render_kw):
                return Markup(
                    f'<div id="wrap-{field.id}">{field.widget(field, **render_kw)}</div>'
                )

        a = StringField()
        b = StringField()
        go = ButtonField("go", wrapper=False).triggers(["a", "b"], value_set("x"))

    form = _Form(MultiDict({"go": ""}), headers=htmx_headers("go"))
    body = form.partial().body
    assert '<div id="wrap-b" hx-swap-oob="outerHTML">' in body
    assert body.count("hx-swap-oob") == 1


def _set_hint(form, source, target):
    target.render_kw = {"placeholder": f"for {source.data}"}


class _AddressForm(HtmxForm):
    country = StringField()
    postal_code = StringField(validators=[DataRequired()])
    postal_code.triggered_by("country", _set_hint, on="change")


def test_source_change_refreshes_the_target_without_its_errors():
    """A change of the source re-renders the target out of band, with no error."""
    form = _AddressForm(
        MultiDict({"country": "de", "postal_code": ""}),
        headers=htmx_headers("country"),
    )
    body = form.partial().body
    assert body.index('id="country"') < body.index('id="postal_code"')
    assert oob_ids(body) == ["postal_code"]
    assert 'placeholder="for de"' in body
    assert not form.postal_code.errors


def test_target_blur_does_not_run_the_callback_of_its_source():
    """The target's own blur validates it, without the callback of its source."""
    form = _AddressForm(
        MultiDict({"country": "de", "postal_code": ""}),
        headers=htmx_headers("postal_code"),
    )
    body = form.partial().body
    assert "placeholder" not in body
    assert form.postal_code.errors


def test_only_the_callbacks_of_the_posting_source_run():
    """A target fed by two sources runs only the callback of the one that posted."""
    calls = []

    def record(form, source, target):
        calls.append(source.name)

    class _Form(HtmxForm):
        a = StringField()
        b = StringField()
        dst = StringField()
        dst.triggered_by("a", record, on="change")
        dst.triggered_by("b", record, on="change")

    _Form(MultiDict({"a": "x", "b": "y"}), headers=htmx_headers("b")).partial()
    assert calls == ["b"]


def test_source_change_clears_the_errors_of_a_sub_form_target():
    """A sub-form target re-renders without the errors of its fields."""

    class _Block(HtmxForm):
        line = StringField(validators=[DataRequired()])

    class _Form(HtmxForm):
        country = StringField()
        block = FormField(_Block)
        block.triggered_by("country", on="change")

    form = _Form(MultiDict({"country": "de"}), headers=htmx_headers("country"))
    form.partial()
    assert not form.block.line.errors


def test_source_change_with_a_selector_and_a_field_target():
    """A selector target is the main swap and a field target goes out of band."""

    def preview(form, source, target):
        return '<p id="preview">ok</p>'

    class _Form(HtmxForm):
        genre = StringField()
        chips = StringField()
        genre.triggers(["#preview", "chips"], preview, on="change")

    form = _Form(MultiDict({"genre": "x"}), headers=htmx_headers("genre"))
    body = form.partial().body
    assert body.startswith('<p id="preview">ok</p>')
    assert oob_ids(body) == ["chips"]


def test_source_without_inline_validation_renders_itself_and_its_target():
    """Without inline validation, the source is the main swap and the target goes out of band."""

    class _Form(_AddressForm):
        class Meta:
            htmx_inline_validation = False

    form = _Form(MultiDict({"country": "de"}), headers=htmx_headers("country"))
    body = form.partial().body
    assert body.index('id="country"') < body.index('id="postal_code"')
    assert oob_ids(body) == ["postal_code"]


def test_source_change_clears_the_errors_of_a_list_target():
    """A FieldList target re-renders without the errors of its rows."""

    class _Form(HtmxForm):
        country = StringField()
        lines = FieldList(StringField(validators=[DataRequired()]), min_entries=1)
        lines.triggered_by("country", on="change")

    form = _Form(
        MultiDict({"country": "de", "lines-0": ""}), headers=htmx_headers("country")
    )
    form.partial()
    assert not form.lines[0].errors


def test_source_blur_does_not_refresh_a_typing_target():
    """The source's own blur does not re-render a target that listens to its typing."""

    class _Form(HtmxForm):
        title = StringField()
        slug = StringField()
        slug.triggered_by("title", _set_hint)

    form = _Form(MultiDict({"title": "x"}), headers=htmx_headers("title"))
    body = form.partial().body
    assert 'id="slug"' not in body


def test_callback_can_validate_the_target_it_refreshes():
    """Errors set by the callback on its target show in the re-rendered target."""

    def revalidate(form, source, target):
        target.validate(form)

    class _Form(HtmxForm):
        country = StringField()
        postal_code = StringField(validators=[Regexp(r"^\d{4}$")])
        postal_code.triggered_by("country", revalidate, on="change")

    form = _Form(
        MultiDict({"country": "be", "postal_code": "75001"}),
        headers=htmx_headers("country"),
    )
    form.partial()
    assert form.postal_code.errors
