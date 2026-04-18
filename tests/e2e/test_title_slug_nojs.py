"""Progressive-enhancement tests for the title slug example."""

from playwright.sync_api import expect


def test_title_slug_save_derives_the_slug_nojs(page_nojs, open_example):
    """Saving a title with an empty slug saves the slug derived from the title."""
    open_example("Title slug")

    page_nojs.locator("input#title").fill("Cafe de Paris")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.get_by_role("status")).to_contain_text(
        "Saved slug 'cafe-de-paris'."
    )


def test_title_slug_save_keeps_a_custom_slug_nojs(page_nojs, open_example):
    """Saving keeps a slug typed by hand."""
    open_example("Title slug")

    page_nojs.locator("input#title").fill("Cafe de Paris")
    page_nojs.locator("input#slug").fill("my-slug")
    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.get_by_role("status")).to_contain_text("Saved slug 'my-slug'.")
