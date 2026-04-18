"""Progressive-enhancement tests for the tag picker example."""

from playwright.sync_api import expect


def test_tag_picker_catalog_click_adds_chip_nojs(page_nojs, open_example):
    """Clicking a catalog tag adds it as a chip."""
    open_example("Tag picker")

    with page_nojs.expect_navigation():
        page_nojs.locator(".tags-catalog").get_by_role("button", name="rust").click()

    expect(page_nojs.locator("#tags .chip-label")).to_have_text(["python", "rust"])
    expect(
        page_nojs.locator(".tags-catalog").get_by_role("button", name="rust")
    ).to_have_count(0)


def test_tag_picker_chip_remove_nojs(page_nojs, open_example):
    """A chip's × removes the tag and puts it back in the catalog."""
    open_example("Tag picker")

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Remove python").click()

    expect(page_nojs.locator("#tags .chip")).to_have_count(0)
    expect(
        page_nojs.locator(".tags-catalog").get_by_role("button", name="python")
    ).to_be_visible()


def test_tag_picker_save_persists_nojs(page_nojs, open_example):
    """Saving keeps the chosen tags after the reload."""
    open_example("Tag picker")
    with page_nojs.expect_navigation():
        page_nojs.locator(".tags-catalog").get_by_role("button", name="rust").click()

    with page_nojs.expect_navigation():
        page_nojs.get_by_role("button", name="Save").click()

    expect(page_nojs.get_by_role("status")).to_contain_text(
        "Saved tags: ['python', 'rust']."
    )
    expect(page_nojs.locator("#tags .chip-label")).to_have_text(["python", "rust"])
