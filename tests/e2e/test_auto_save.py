"""End-to-end tests for the auto-save example."""

import re

from playwright.sync_api import expect


def test_auto_save_commits_on_typing_pause(page, open_example):
    """A typing pause saves the form and the button shows the save time."""
    open_example("Auto-save")

    page.locator("input#name").fill("Bob Brown")

    expect(page.locator("#save")).to_contain_text("Saved at")
    page.goto(page.url)
    expect(page.locator("input#name")).to_have_value("Bob Brown")


def test_auto_save_skips_commit_on_invalid_form(page, open_example):
    """Clearing a required field shows an error on the button and saves nothing."""
    open_example("Auto-save")

    page.locator("input#email").fill("")

    expect(page.locator("#save")).to_contain_text("Not saved")
    page.goto(page.url)
    expect(page.locator("input#email")).to_have_value("alice@example.org")


def test_auto_save_recovers_after_invalid(page, open_example):
    """A valid edit after an error saves the form again."""
    open_example("Auto-save")
    email = page.locator("input#email")
    save = page.locator("#save")
    email.fill("")
    expect(save).to_have_class(re.compile(r"auto-save-status-errors"))

    email.fill("bob@example.org")

    expect(save).to_have_class(re.compile(r"auto-save-status-saved"))
    page.goto(page.url)
    expect(email).to_have_value("bob@example.org")


def test_auto_save_explicit_submit_saves(page, open_example):
    """Clicking Save saves the form and shows the success message."""
    open_example("Auto-save")

    page.locator("input#name").fill("Carol")
    with page.expect_navigation():
        page.locator("#save").click()

    expect(page.get_by_role("status")).to_contain_text("Saved.")
    expect(page.locator("input#name")).to_have_value("Carol")
