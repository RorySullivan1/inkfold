"""
Send the email gallery to test inboxes, for the clients no session reaches (roadmap v0.9.0).

Gmail on the web and its apps, Apple Mail, new Outlook and each one's dark mode
can be judged only in a real inbox. **Nothing is sent without ``--send``**: without
it the run lists what it would send and to whom::

    python -m qa.send_gallery you@icloud.com --from you@gmail.com            # dry run
    python -m qa.send_gallery you@icloud.com --from you@gmail.com --send     # by Gmail SMTP
    python -m qa.send_gallery --save output/eml                              # .eml files, no send

``--via smtp``, the default, hands each message to smtp.gmail.com exactly as
``build_message`` assembles it, signed in with a Google app password asked for at
the prompt (or read from ``INKFOLD_SMTP_PASSWORD``) and never stored. ``--via
outlook`` sends through classic Outlook instead, which re-encodes the HTML through
its own editor, so the inboxes judge Outlook's rewrite rather than inkfold's email.
``--save DIR`` sends nothing: it writes each message as a ``.eml`` file, which new
Outlook opens by double-click, since new Outlook takes no automation. The questions
to answer per client are in ``qa/clients/MATRIX.md``.
"""

from __future__ import annotations

import argparse
import getpass
import os
import smtplib
import sys
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from inkfold.builder.email import Email
from inkfold.delivery import build_message, save_eml
from inkfold.outlook.desktop import create_draft, outlook_application

from .fixtures import all_fixtures

#: ``olFolderOutbox`` and ``olFolderInbox`` in ``GetDefaultFolder``.
OL_FOLDER_OUTBOX = 4
OL_FOLDER_INBOX = 6

#: Every subject opens with this, so a test inbox can filter the run into one folder.
SUBJECT_TAG = "[inkfold gallery]"

#: Gmail's submission server, over TLS from the first byte.
GMAIL_HOST = "smtp.gmail.com"
GMAIL_PORT = 465

#: Who a saved ``.eml`` is addressed to when no inbox is named: it is opened, not sent.
SAVED_ADDRESS = "gallery@example.com"

#: Where a run may find the app password instead of asking for it.
PASSWORD_ENV = "INKFOLD_SMTP_PASSWORD"


def subject_of(name: str, email: Email) -> str:
    """``[inkfold gallery] kitchen_sink: <the email's own subject>``."""
    return f"{SUBJECT_TAG} {name}: {email.metadata.email_subject}"


def _built(
    names: Sequence[str],
    to: Sequence[str],
    sender: str,
    fixtures: Mapping[str, Callable[[], Email]] | None,
) -> Iterator[tuple[str, Email, EmailMessage]]:
    """Each named fixture as ``(subject, email, message)``, after checking the names and inboxes."""
    gallery = fixtures if fixtures is not None else all_fixtures()
    unknown = sorted(set(names) - set(gallery))
    if unknown:
        raise SystemExit(f"no such fixture: {', '.join(unknown)}")
    if not to:
        raise SystemExit("name at least one test inbox to send to.")
    for name in names:
        email = gallery[name]()
        subject = subject_of(name, email)
        yield subject, email, build_message(email, subject=subject, sender=sender, to=list(to))


def save_gallery(
    names: Sequence[str],
    out_dir: Path,
    *,
    to: Sequence[str] = (SAVED_ADDRESS,),
    sender: str = SAVED_ADDRESS,
    fixtures: Mapping[str, Callable[[], Email]] | None = None,
) -> list[Path]:
    """
    Each named fixture as ``out_dir/NAME.eml``, the message a send would carry, sent to no one.

    Opening one in a mail client shows that client's render of the email with its
    attached images, which is how new Outlook, with no automation, is checked.
    """
    return [
        save_eml(message, out_dir / f"{name}.eml")
        for name, (_subject, _email, message) in zip(
            names, _built(names, to, sender, fixtures), strict=True
        )
    ]


def send_via_smtp(
    names: Sequence[str],
    to: Sequence[str],
    *,
    sender: str,
    password: str,
    host: str = GMAIL_HOST,
    port: int = GMAIL_PORT,
    connect: Callable[..., Any] = smtplib.SMTP_SSL,
    fixtures: Mapping[str, Callable[[], Email]] | None = None,
) -> list[str]:
    """
    Send each named fixture to every address in ``to`` through an SMTP server.

    Every message is built before the server is reached, so a fixture that fails to
    build sends nothing. A refused sign-in stops the run with what to do about it.
    """
    messages = list(_built(names, to, sender, fixtures))
    lines = []
    with connect(host, port, timeout=60) as server:
        try:
            server.login(sender, password)
        except smtplib.SMTPAuthenticationError as exc:
            raise SystemExit(
                f"{host} refused the sign-in for {sender}. Gmail takes an app password "
                "(https://myaccount.google.com/apppasswords, which needs 2-Step Verification), "
                "not the account's own password."
            ) from exc
        for subject, _email, message in messages:
            server.send_message(message)
            lines.append(f"sent: {subject} -> {', '.join(to)}")
    return lines


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
    Through classic Outlook: queue, or with ``send`` false only list, each named fixture.

    Returns one line per message. A dry run touches no Outlook. A send refuses to start
    while gallery messages already wait in the Outbox, so a second run cannot queue
    duplicates; :func:`flush` then pushes the queue out.
    """
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
    for subject, _email, message in _built(names, to, "gallery@localhost", fixtures):
        if send:
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


def _password(sender: str) -> str:
    """The app password: from the environment, or asked for without echoing it."""
    return os.environ.get(PASSWORD_ENV) or getpass.getpass(f"Google app password for {sender}: ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send the email gallery to test inboxes.")
    parser.add_argument("to", nargs="*", help="test inbox addresses")
    parser.add_argument("--fixtures", nargs="*", default=None, help="default: every email")
    parser.add_argument("--via", choices=("smtp", "outlook"), default="smtp")
    parser.add_argument("--from", dest="sender", default="", help="the Gmail account to send from")
    parser.add_argument("--account", default="", help="with --via outlook: the Outlook account")
    parser.add_argument("--send", action="store_true", help="really send; otherwise a dry run")
    parser.add_argument("--save", type=Path, help="write .eml files to this folder; send nothing")
    args = parser.parse_args(argv)
    names = args.fixtures or list(all_fixtures())
    if args.save is not None:
        paths = save_gallery(
            names,
            args.save,
            to=args.to or (SAVED_ADDRESS,),
            sender=args.sender or SAVED_ADDRESS,
        )
        for path in paths:
            print(f"saved: {path}")
        print(
            f"Saved {len(paths)} .eml file(s) to {args.save}; nothing was sent. For new Outlook, "
            "right-click one and choose Open with > Outlook (new): a double-click may open "
            "classic Outlook instead."
        )
        return 0
    if not args.to:
        parser.error("name at least one test inbox, or use --save DIR to write .eml files")
    if args.via == "smtp":
        if not args.sender:
            parser.error("--via smtp needs --from, the Gmail address to send from")
        if not args.send:
            for line in send_gallery(names, args.to, send=False):
                print(line)
            print(f"Dry run: {len(names)} email(s) from {args.sender}. Add --send to send.")
            return 0
        lines = send_via_smtp(names, args.to, sender=args.sender, password=_password(args.sender))
        for line in lines:
            print(line)
        print(f"Sent: {len(lines)} email(s) from {args.sender}; they are in its Gmail Sent folder.")
        return 0
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
