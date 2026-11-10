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


class FakeOutlook:
    def __init__(self, accounts: tuple[str, ...] = ("desk@example.com",)) -> None:
        self.mails: list[FakeMail] = []
        items = [SimpleNamespace(SmtpAddress=a) for a in accounts]
        self.accounts = SimpleNamespace(Count=len(items), Item=lambda i: items[i - 1])

    def CreateItem(self, kind: int) -> FakeMail:  # noqa: N802
        mail = FakeMail()
        self.mails.append(mail)
        return mail

    def GetNamespace(self, name: str) -> SimpleNamespace:  # noqa: N802
        return SimpleNamespace(Accounts=self.accounts)


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
        assert all(line.startswith("sent: [inkfold gallery] ") for line in lines)
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
