"""An inbox where the user ticks some messages, then applies one action
to all of them: ``Mark read``, ``Mark unread`` or ``Archive``.
The ``Select`` buttons tick all, the read, the unread or no messages
in one click. The toolbar appears once a box is ticked. It counts the
selection and only offers the actions that change a ticked message.

.. screencast:: |examples|/bulk-actions
   :locator: .demo-area
   :autoplay:
   :muted:
   :loop:
   :trim-start:
   :poster:
   :interactions:
     const $ = (s) => document.querySelector(s);
     const wait = (ms) => new Promise(r => setTimeout(r, ms));
     const tick = (id) => $(`input[name="selection"][value="${id}"]`).click();
     await wait(700);
     // An unread message: only "Mark read" and "Archive" apply.
     tick("m1");
     await wait(1100);
     // Add a read message: "Mark unread" appears.
     tick("m2");
     await wait(1300);
     // Select the unread messages, then clear the selection.
     $('button[name="select"][value="unread"]').click();
     await wait(1300);
     $('button[name="clear"]').click();
     await wait(1300);

   Each tick refreshes the toolbar: the count and the actions that
   change a ticked message. Unread messages are in bold, with a dot.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field as dc_field

from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from wtforms import ButtonField
from wtforms import FormField
from wtforms import SelectChoice
from wtforms import SelectMultipleField
from wtforms import SubmitField
from wtforms.widgets import CheckboxInput

from wtforms_htmx.mutations import value_set

from . import bp
from ._code import Excerpt
from ._shared import _INITIAL_STATE
from ._shared import _STATE
from ._shared import ExampleForm
from ._shared import jinja_widget


@dataclass
class Message:
    id: str
    sender: str
    subject: str
    received: str
    read: bool = False
    archived: bool = False


@dataclass
class BulkActionsData:
    messages: list[Message] = dc_field(default_factory=list)

    def inbox(self):
        """Return the messages that are not archived."""
        return [message for message in self.messages if not message.archived]


_STATE["bulk_actions"] = BulkActionsData(
    messages=[
        Message("m1", "Alice Brown", "Quarterly report draft", "09:14"),
        Message("m2", "Bob Carter", "Lunch on Friday?", "08:02", read=True),
        Message("m3", "Carol Davis", "Invoice #2024-117", "Yesterday"),
        Message("m4", "Dave Evans", "Team offsite agenda", "Oct 21", read=True),
        Message("m5", "Eve Foster", "Re: design review", "Oct 20", read=True),
    ],
)
_INITIAL_STATE["bulk_actions"] = deepcopy(_STATE["bulk_actions"])

#: Values and labels of the ``select`` buttons.
SELECT_SHORTCUTS = [("all", "All"), ("read", "Read"), ("unread", "Unread")]


def _inbox_choices(form, _field):
    """One choice per message in the inbox."""
    return [SelectChoice(message.id, message.subject) for message in form.inbox()]


def select_matching(form, source, target):
    """Select the messages that match the clicked button: all, read or unread."""
    value = (source.raw_data or [""])[0]
    if value not in ("all", "read", "unread"):
        return

    target.data = [
        message.id
        for message in form.inbox()
        if value == "all" or message.read == (value == "read")
    ]


class ToolbarForm(ExampleForm):
    mark_read = SubmitField("Mark read")
    mark_unread = SubmitField("Mark unread")
    archive = SubmitField("Archive")


class BulkActionsForm(ExampleForm):
    """Inbox: tick messages, then apply one toolbar action to all of them."""

    class Meta:
        # Ticking a box refreshes the toolbar; nothing else to validate.
        htmx_inline_validation = False

    select_shortcuts = SELECT_SHORTCUTS

    selection = SelectMultipleField(
        choices=_inbox_choices,
        option_widget=CheckboxInput(),
        widget=jinja_widget("_bulk_actions_widgets.html", "inbox"),
        wrapper=False,
    )
    select = ButtonField("Select")
    clear = ButtonField("None")
    toolbar = FormField(
        ToolbarForm,
        widget=jinja_widget("_bulk_actions_widgets.html", "toolbar"),
    )

    # Every tick refreshes the toolbar.
    selection.triggers("toolbar", on="change")

    select.triggers("selection", select_matching).triggers("toolbar")
    clear.triggers("selection", value_set([])).triggers("toolbar")

    def inbox(self):
        """Return the messages listed in ``selection``, in the same order."""
        return _STATE["bulk_actions"].inbox()

    def selected_messages(self):
        """Return the inbox messages whose box is ticked."""
        selected = set(self.selection.data or [])
        return [message for message in self.inbox() if message.id in selected]

    def useful_actions(self):
        """Return the toolbar actions that change at least one ticked message."""
        messages = self.selected_messages()
        toolbar = self.toolbar
        return {
            toolbar.mark_read: any(not message.read for message in messages),
            toolbar.mark_unread: any(message.read for message in messages),
            toolbar.archive: bool(messages),
        }


@bp.route("/bulk-actions", methods=["GET", "POST"])
def bulk_actions():
    form = BulkActionsForm(request.form or None, headers=request.headers)
    if result := form.partial():
        return Response(result.body, headers=result.headers)

    toolbar = form.toolbar
    actions = (toolbar.mark_read, toolbar.mark_unread, toolbar.archive)
    if not any(form.submitter is action for action in actions):
        return render_template("bulk_actions.html", form=form)

    messages = form.selected_messages()
    if not messages:
        flash("Select at least one message.", "warning")
        return render_template("bulk_actions.html", form=form)

    if form.submitter is toolbar.archive:
        for message in messages:
            message.archived = True

        flash(f"{len(messages)} archived.", "success")
        return redirect(url_for("main.bulk_actions"))

    # Without JavaScript, every action is offered: skip the messages it
    # would not change and say so.
    read = form.submitter is toolbar.mark_read
    state = "read" if read else "unread"
    changed = [message for message in messages if message.read != read]
    for message in changed:
        message.read = read

    text = f"{len(changed)} marked as {state}"
    if skipped := len(messages) - len(changed):
        text += f", {skipped} already {state}"

    flash(f"{text}.", "success")
    return redirect(url_for("main.bulk_actions"))


#: Code shown under the demo.
CODE = [
    _inbox_choices,
    select_matching,
    ToolbarForm,
    BulkActionsForm,
    bulk_actions,
    Excerpt("templates/bulk_actions.html", "{% block content %}", "{% endblock %}"),
    Excerpt("templates/_bulk_actions_widgets.html", "macro toolbar", "endmacro"),
    Excerpt("static/bulk_actions.css", "/* CSS, not JavaScript", "}"),
]
