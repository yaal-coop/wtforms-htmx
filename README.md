<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://wtforms-htmx.readthedocs.io/en/latest/_static/logo-dark.svg">
    <img src="https://wtforms-htmx.readthedocs.io/en/latest/_static/logo-light.svg" alt="wtforms-htmx">
  </picture>
</p>

# wtforms-htmx

Interactive [WTForms](https://wtforms.readthedocs.io/) forms declared in
Python and powered by [htmx](https://htmx.org/), with no JavaScript to
write, or even any htmx.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://wtforms-htmx.readthedocs.io/en/latest/_static/screencasts/title-slug-dark.webp">
    <img src="https://wtforms-htmx.readthedocs.io/en/latest/_static/screencasts/title-slug-light.webp" width="700" alt="Typing a title fills in its slug as you type.">
  </picture>
</p>

Here's (almost) everything wtforms-htmx adds on top of a regular form:

```python
class PostForm(HtmxForm):
    title = StringField().triggers("slug", slugify)
    slug = StringField()
```

## Features

- **Declare interactivity in Python.**
  Right on the field declaration, not scattered across `hx-*`
  attributes.
- **No extra endpoints.** Interactions are handled by the form's
  existing view. You don't write a route for each one.
- **Progressive enhancement.** The form works without JavaScript;
  htmx layers live updates and partial swaps on top. Same form, two
  render paths.
- **Opinionated defaults, fully overridable.** wtforms-htmx renders
  the right `hx-*` for you, but they're yours to override.
- **Common patterns in a few lines.** Inline validation and `FieldList`
  add/remove/reorder are built in. The examples show how to build
  autocomplete, comboboxes and dependent fields.

Full documentation: <https://wtforms-htmx.readthedocs.io/>

## Example app

A runnable gallery of examples lives in `examples/`. The
[documentation](https://wtforms-htmx.readthedocs.io/) shows most of them with a
screencast. To run it locally:

```sh
uv sync --group example
uv run python -m examples
```

Then open <http://127.0.0.1:5000/>.
