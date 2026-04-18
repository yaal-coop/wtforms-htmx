"""End-to-end tests for the markdown preview example."""

from playwright.sync_api import expect


def test_markdown_preview_typing_renders_preview(page, open_example):
    """Typing markdown renders it in the preview."""
    open_example("Markdown preview")

    page.locator("textarea#content").fill("# Hi\n\n**Hello** world")

    expect(page.locator("#preview h1")).to_have_text("Hi")
    expect(page.locator("#preview strong")).to_have_text("Hello")


def test_markdown_preview_clears_when_content_emptied(page, open_example):
    """Emptying the textarea empties the preview."""
    open_example("Markdown preview")
    expect(page.locator("#preview")).not_to_be_empty()

    page.locator("textarea#content").fill("")

    expect(page.locator("#preview")).to_be_empty()


def test_markdown_preview_keeps_the_preview_element(page, open_example):
    """The rendered markdown fills the preview pane without replacing it."""
    open_example("Markdown preview")

    page.locator("textarea#content").fill("plain text")

    expect(page.locator("#preview.md-preview")).to_have_text("plain text")


def test_markdown_preview_save_renders_preview(page, open_example):
    """Saving keeps the markdown and shows its preview after the reload."""
    open_example("Markdown preview")

    page.locator("textarea#content").fill("## section\n\nbody")
    with page.expect_navigation():
        page.get_by_role("button", name="Save").click()

    expect(page.locator("#preview h2")).to_have_text("section")
