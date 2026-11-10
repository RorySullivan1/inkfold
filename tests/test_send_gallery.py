"""Sending the gallery to test inboxes (roadmap v0.9.0), against a fake Outlook."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from qa import send_gallery


class FakeMail:
    def __init__(self) -> None:
        self.sent = False
        self.SendUsingAccount: Any = None
        self.Attachments = SimpleNamespace(
            Add=lambda path, how: SimpleNamespace(
                PropertyAccessor=SimpleNamespace(SetProperty=lambda name, value: None)
            )
        )

    def Save(self) -> None:  # noqa: N802 - COM's spelling
        pass

    def Display(self, modal: bool) -> None:  # noqa: N802
        raise AssertionError("a gallery send never opens a window")

    def Send(self) -> None:  # noqa: N802
        self.sent = True
        self.outlook.outbox.append(SimpleNamespace(Subject=f"{send_gallery.SUBJECT_TAG} x"))


class FakeOutlook:
    """Mail goes to the Outbox on Send, and leaves it after ``drains`` polls of Send/Receive."""

    def __init__(self, accounts: tuple[str, ...] = ("desk@example.com",), drains: int = 1) -> None:
        self.mails: list[FakeMail] = []
        items = [SimpleNamespace(SmtpAddress=a) for a in accounts]
        self.accounts = SimpleNamespace(Count=len(items), Item=lambda i: items[i - 1])
        self.outbox: list[SimpleNamespace] = []
        self.drains = drains
        self.synced = 0
        outbox = SimpleNamespace(Items=self.outbox)
        store = SimpleNamespace(
            GetDefaultFolder=lambda fid: outbox if fid == send_gallery.OL_FOLDER_OUTBOX else None
        )
        self.namespace = SimpleNamespace(
            Accounts=self.accounts,
            Stores=[store],
            GetDefaultFolder=lambda fid: SimpleNamespace(),
            SendAndReceive=self._sync,
        )

    def _sync(self, show: bool) -> None:
        self.synced += 1

    def CreateItem(self, kind: int) -> FakeMail:  # noqa: N802
        mail = FakeMail()
        mail.outlook = self
        self.mails.append(mail)
        return mail

    def GetNamespace(self, name: str) -> SimpleNamespace:  # noqa: N802
        return self.namespace

    def poll(self) -> None:
        """One wait in flush: the Outbox empties once enough have passed."""
        self.drains -= 1
        if self.drains <= 0:
            self.outbox.clear()


class TestADryRun:
    def test_it_lists_every_message_and_reaches_no_outlook(self, monkeypatch):
        monkeypatch.setattr(send_gallery, "outlook_application", lambda: pytest.fail("no Outlook"))
        lines = send_gallery.send_gallery(["minimal"], ["a@example.com"], send=False)
        assert lines == ["would send: [inkfold gallery] minimal: Minimal -> a@example.com"]

    def test_it_needs_an_inbox(self):
        with pytest.raises(SystemExit, match="at least one test inbox"):
            send_gallery.send_gallery(["minimal"], [], send=False)


class TestASend:
    def test_each_fixture_is_sent_once_tagged_to_every_inbox(self):
        outlook = FakeOutlook()
        lines = send_gallery.send_gallery(
            ["minimal", "house_daily_note"], ["a@x.com", "b@y.com"], send=True, outlook=outlook
        )
        assert [m.sent for m in outlook.mails] == [True, True]
        assert all(line.startswith("queued: [inkfold gallery] ") for line in lines)
        assert lines[0].endswith("-> a@x.com, b@y.com")

    def test_a_named_account_sends_it(self):
        outlook = FakeOutlook(("desk@example.com", "test@example.com"))
        send_gallery.send_gallery(
            ["minimal"], ["a@x.com"], send=True, outlook=outlook, account="TEST@example.com"
        )
        assert outlook.mails[0].SendUsingAccount.SmtpAddress == "test@example.com"

    def test_an_unknown_account_is_refused_before_anything_is_sent(self):
        outlook = FakeOutlook()
        with pytest.raises(SystemExit, match="this profile has: desk@example.com"):
            send_gallery.send_gallery(
                ["minimal"], ["a@x.com"], send=True, outlook=outlook, account="no@x.com"
            )
        assert outlook.mails == []

    def test_a_queue_left_by_an_earlier_run_is_refused_so_nothing_is_sent_twice(self):
        outlook = FakeOutlook()
        outlook.outbox.append(SimpleNamespace(Subject="[inkfold gallery] minimal: Minimal"))
        outlook.outbox.append(SimpleNamespace(Subject="Someone else's mail"))
        with pytest.raises(SystemExit, match="1 gallery message.*already wait"):
            send_gallery.send_gallery(["minimal"], ["a@x.com"], send=True, outlook=outlook)
        assert outlook.mails == []


class TestFlushingTheOutbox:
    def test_it_runs_send_receive_and_waits_for_the_outbox_to_empty(self):
        outlook = FakeOutlook(drains=3)
        send_gallery.send_gallery(["minimal"], ["a@x.com"], send=True, outlook=outlook)
        assert send_gallery.queued(outlook) == 1
        left = send_gallery.flush(outlook, sleep=lambda s: outlook.poll(), clock=lambda: 0.0)
        assert left == 0 and outlook.synced == 1

    def test_it_reports_what_is_still_queued_when_time_runs_out(self):
        outlook = FakeOutlook(drains=99)
        send_gallery.send_gallery(["minimal"], ["a@x.com"], send=True, outlook=outlook)
        ticks = iter(range(0, 1000, 60))
        left = send_gallery.flush(
            outlook, timeout_s=120, sleep=lambda s: outlook.poll(), clock=lambda: next(ticks)
        )
        assert left == 1

    def test_mail_that_is_not_the_gallerys_is_never_counted(self):
        outlook = FakeOutlook()
        outlook.outbox.append(SimpleNamespace(Subject="Quarterly letter"))
        assert send_gallery.queued(outlook) == 0
