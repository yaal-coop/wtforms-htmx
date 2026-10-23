<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/_static/logo-dark.webp">
    <img src="docs/_static/logo.webp" alt="wtforms-htmx">
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

A small runnable gallery lives in `examples/`:

- `/inline-validation`: per-field validation on blur, with WTForms' native validators.
- `/datalist`: server-filtered `<datalist>` autocomplete refreshed as the user types.
- `/password`: live password-strength meter plus a confirmation field.
- `/title-slug`: title input deriving a slug until the user edits it.
- `/markdown-preview`: textarea rendered into a non-field preview `<div>`.
- `/auto-save`: form-level auto-commit on every typing pause.
- `/currency`: bidirectional EUR ⇆ JPY converter, typing or buttons.
- `/cycle-button`: one button rotating a hidden value through a fixed list.
- `/inline-edit`: a read-only label that flips into an editable input.
- `/tag-picker`: chip picker on a `SelectMultipleField` (add/remove buttons).
- `/dual-listbox`: two-column shuttle with per-column search and bulk moves.
- `/combobox`: text-entry picker backed by a server-filtered popup listbox.
- `/task-list`: draggable TODO list (add/remove/reorder) on `FieldList(FormField)`.
- `/address`: country-driven postal lookup with a conditional billing block.
- `/invoice`: nested per-row VAT totals recomputed via out-of-band swaps.
- `/faceted-search`: book search with filter chips and cascading facet autocomplete.
- `/pagination`: page navigation built from a `SelectField` of button options.
- `/attendance`: 2D attendance grid; add/remove rows and columns, cells cycle on click.

```sh
uv sync --group example
uv run python -m examples
```

Then open <http://127.0.0.1:5000/>.
