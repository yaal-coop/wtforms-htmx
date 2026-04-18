"""End-to-end tests for the title slug example."""

from playwright.sync_api import expect


def _posted(text):
    return lambda response: text in (response.request.post_data or "")


def test_title_slug_updates_on_keystroke(page, open_example):
    """Typing a title updates the slug."""
    open_example("Title slug")

    page.locator("input#title").fill("Cafe de Paris")

    expect(page.locator("input#slug")).to_have_value("cafe-de-paris")


def test_title_slug_follows_after_leaving_and_retyping(page, open_example):
    """The slug still follows the title after the title input lost focus."""
    open_example("Title slug")
    title = page.locator("input#title")
    slug = page.locator("input#slug")
    title.fill("Cafe")
    expect(slug).to_have_value("cafe")
    title.evaluate("el => el.setAttribute('data-pre-swap', '')")

    page.locator("h1").click()
    expect(page.locator("input#title[data-pre-swap]")).to_have_count(0)
    title.fill("Cafe de Paris")

    expect(slug).to_have_value("cafe-de-paris")


def test_title_slug_custom_slug_stops_following(page, open_example):
    """Once the slug is edited by hand, typing a title leaves it alone."""
    open_example("Title slug")
    slug = page.locator("input#slug")
    slug.fill("my-slug")
    slug.evaluate("el => el.setAttribute('data-pre-swap', '')")
    slug.blur()
    expect(page.locator("input#slug[data-pre-swap]")).to_have_count(0)
    # htmx binds the triggers of new content when it removes htmx-added.
    expect(page.locator(".htmx-added")).to_have_count(0)

    with page.expect_response(_posted("title=Cafe")):
        page.locator("input#title").fill("Cafe de Paris")

    expect(slug).to_have_value("my-slug")


def test_title_slug_save_keeps_the_slug(page, open_example):
    """Saving keeps the derived slug."""
    open_example("Title slug")
    page.locator("input#title").fill("Cafe de Paris")
    expect(page.locator("input#slug")).to_have_value("cafe-de-paris")

    with page.expect_navigation():
        page.get_by_role("button", name="Save").click()

    expect(page.get_by_role("status")).to_contain_text("Saved slug 'cafe-de-paris'.")
