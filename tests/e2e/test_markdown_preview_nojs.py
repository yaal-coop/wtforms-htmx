"""Progressive-enhancement tests for the markdown preview example."""

from playwright.sync_api import expect


def test_markdown_preview_save_renders_preview_nojs(page_nojs, open_example):
    """Saving keeps the markdown and shows its preview after the reload."""
    open_example("Markdown preview")

    page_nojs.locator("textarea#content").fill("## section\n\nbody")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.locator("#preview h2")).to_have_text("section")
