"""
Send the email gallery to test inboxes through classic Outlook, for the clients no session reaches.

Gmail on the web and its apps, Apple Mail, new Outlook and each one's dark mode
can be judged only in a real inbox (roadmap v0.9.0). This builds each fixture as
a MIME message, puts it in Outlook as a draft, and sends it from the profile's
account, or the one ``--account`` names. **Nothing is sent without ``--send``**:
without it the run lists what it would send and to whom::

    python -m qa.send_gallery you@gmail.com you@icloud.com                 # dry run
    python -m qa.send_gallery you@gmail.com --send --fixtures house_daily_note

Needs Windows, classic Outlook and the ``[outlook-desktop]`` extra. The questions
to answer per client are in ``qa/clients/MATRIX.md``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from inkfold.builder.email import Email
from inkfold.delivery import build_message
from inkfold.outlook.desktop import create_draft, outlook_application

from .fixtures import all_fixtures

#: Every subject opens with this, so a test inbox can filter the run into one folder.
SUBJECT_TAG = "[inkfold gallery]"


def subject_of(name: str, email: Email) -> str:
    """``[inkfold gallery] kitchen_sink: <the email's own subject>``."""
    return f"{SUBJECT_TAG} {name}: {email.metadata.email_subject}"


def send_gallery(
    names: Sequence[str],
    to: Sequence[str],
    *,
    send: bool,
    outlook: Any = None,
    account: str = "",
    fixtures: Mapping[str, Callable[[], Email]] | None = None,
) -> list[str]:
    """
    Send, or with ``send`` false only list, each named fixture to every address in ``to``.

    Returns one line per message, sent or not. A dry run touches no Outlook.
    """
    gallery = fixtures if fixtures is not None else all_fixtures()
    unknown = sorted(set(names) - set(gallery))
    if unknown:
        raise SystemExit(f"no such fixture: {', '.join(unknown)}")
    if not to:
        raise SystemExit("name at least one test inbox to send to.")
    lines = []
    sender_account = None
    if send:
        outlook = outlook if outlook is not None else outlook_application()
        sender_account = _account(outlook, account) if account else None
    for name in names:
        email = gallery[name]()
        subject = subject_of(name, email)
        if send:
            message = build_message(email, subject=subject, sender="gallery@localhost", to=list(to))
            mail = create_draft(message, display=False, outlook=outlook)
            if sender_account is not None:
                mail.SendUsingAccount = sender_account
            mail.Send()
        lines.append(f"{'sent' if send else 'would send'}: {subject} -> {', '.join(to)}")
    return lines


def _account(outlook: Any, address: str) -> Any:
    """The Outlook account whose address is ``address``, or a refusal naming the ones there are."""
    accounts = outlook.GetNamespace("MAPI").Accounts
    found = [accounts.Item(i) for i in range(1, accounts.Count + 1)]
    for candidate in found:
        if str(candidate.SmtpAddress).lower() == address.lower():
            return candidate
    names = ", ".join(str(a.SmtpAddress) for a in found)
    raise SystemExit(f"no Outlook account {address!r}; this profile has: {names}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send the email gallery to test inboxes.")
    parser.add_argument("to", nargs="+", help="test inbox addresses")
    parser.add_argument("--fixtures", nargs="*", default=None, help="default: every email")
    parser.add_argument("--account", default="", help="send from this Outlook account")
    parser.add_argument("--send", action="store_true", help="really send; otherwise a dry run")
    args = parser.parse_args(argv)
    names = args.fixtures or list(all_fixtures())
    for line in send_gallery(names, args.to, send=args.send, account=args.account):
        print(line)
    if not args.send:
        print(f"Dry run: {len(names)} email(s) to {len(args.to)} inbox(es). Add --send to send.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
