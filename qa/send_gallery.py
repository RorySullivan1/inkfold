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
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from inkfold.builder.email import Email
from inkfold.delivery import build_message
from inkfold.outlook.desktop import create_draft, outlook_application

from .fixtures import all_fixtures

#: ``olFolderOutbox`` and ``olFolderInbox`` in ``GetDefaultFolder``.
OL_FOLDER_OUTBOX = 4
OL_FOLDER_INBOX = 6

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

    Returns one line per message, queued or not. A dry run touches no Outlook. A send
    refuses to start while gallery messages already wait in the Outbox, so a second run
    cannot queue duplicates; :func:`flush` then pushes the queue out.
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
        waiting = queued(outlook)
        if waiting:
            raise SystemExit(
                f"{waiting} gallery message(s) already wait in classic Outlook's Outbox. Open "
                "classic Outlook to send them, or delete them there, then run again."
            )
    for name in names:
        email = gallery[name]()
        subject = subject_of(name, email)
        if send:
            message = build_message(email, subject=subject, sender="gallery@localhost", to=list(to))
            mail = create_draft(message, display=False, outlook=outlook)
            if sender_account is not None:
                mail.SendUsingAccount = sender_account
            mail.Send()
        lines.append(f"{'queued' if send else 'would send'}: {subject} -> {', '.join(to)}")
    return lines


def queued(outlook: Any) -> int:
    """How many gallery messages wait in the Outbox of any store in the Outlook profile."""
    count = 0
    for store in outlook.GetNamespace("MAPI").Stores:
        try:
            outbox = store.GetDefaultFolder(OL_FOLDER_OUTBOX)
        except Exception:  # a store with no Outbox, such as an archive
            continue
        count += sum(str(item.Subject).startswith(SUBJECT_TAG) for item in outbox.Items)
    return count


def flush(
    outlook: Any,
    timeout_s: float = 180.0,
    poll_s: float = 3.0,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> int:
    """
    Run Send/Receive and wait for the gallery to leave the Outbox; how many are left.

    An Outlook that automation started quits when the script lets go, with its Outbox
    unsent, so the run waits here, holding the Inbox to keep Outlook up meanwhile.
    """
    session = outlook.GetNamespace("MAPI")
    held = session.GetDefaultFolder(OL_FOLDER_INBOX)
    session.SendAndReceive(False)
    deadline = clock() + timeout_s
    left = queued(outlook)
    while left and clock() < deadline:
        sleep(poll_s)
        left = queued(outlook)
    del held
    return left


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
    outlook = outlook_application() if args.send else None
    for line in send_gallery(names, args.to, send=args.send, outlook=outlook, account=args.account):
        print(line)
    if not args.send:
        print(f"Dry run: {len(names)} email(s) to {len(args.to)} inbox(es). Add --send to send.")
        return 0
    print("Sending: waiting for classic Outlook's Outbox to empty...")
    left = flush(outlook)
    if left:
        print(
            f"{left} message(s) are still in classic Outlook's Outbox. Open classic Outlook "
            "(not new Outlook) and they will send; then check its Sent Items."
        )
        return 1
    print(f"Sent: all {len(names)} email(s) left the Outbox. Find them in Sent Items.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
