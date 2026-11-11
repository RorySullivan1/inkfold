"""
The email gallery through classic Outlook's own renderer, on Windows (roadmap v0.9.0).

Each email goes into an unsaved message, its ``cid:`` images attached hidden by
Content-ID as a send would carry them. The message window opens minimised,
Outlook's Word editor exports what it rendered to PDF, and the message is
discarded: nothing is saved to the mailbox and nothing is sent::

    python -m qa.outlook_render                      # the whole email gallery
    python -m qa.outlook_render kitchen_sink --out output/outlook

Needs Windows, classic Outlook, and the ``[outlook-desktop]`` and ``[qa]`` extras.
``run.json`` records the Outlook build, as the screenshot runner records Chromium's.
"""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import re
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from inkfold.builder.document import Document
from inkfold.outlook.desktop import (
    OL_BY_VALUE,
    OL_MAIL_ITEM,
    PR_ATTACH_CONTENT_ID,
    PR_ATTACHMENT_HIDDEN,
    outlook_application,
)

from .fixtures import all_fixtures

DEFAULT_OUT_DIR = Path("output/outlook")

#: ``olDiscard`` in ``MailItem.Close``: the message is dropped, never saved.
OL_DISCARD = 1

#: ``olMinimized`` for ``Inspector.WindowState``.
OL_MINIMIZED = 1

#: ``olFolderInbox`` in ``Namespace.GetDefaultFolder``.
OL_FOLDER_INBOX = 6

#: COM objects held for the run, so an Outlook that automation started does not quit mid-gallery.
_HELD: list[Any] = []

#: ``wdExportFormatPDF`` in ``Document.ExportAsFixedFormat``.
WD_EXPORT_PDF = 17

#: Word's tallest page, 22 in, so an email breaks across as few sheets as it can.
PAGE_HEIGHT_PT = 1584

#: Page margins, in points: small, so the frame is not pushed about by a printer's.
MARGIN_PT = 18

#: Raster scale: a PDF point is 1/72 in and a CSS px 1/96, so 4/3 shows each px as one.
SCALE = 4 / 3


def render_email(email: Document, name: str, out_dir: Path, outlook: Any) -> Path:
    """
    ``email`` as Outlook renders it, exported to ``out_dir/name.pdf``.

    The message is closed with ``olDiscard`` whatever happens, so a failed
    export never leaves a draft behind.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = (out_dir / f"{name}.pdf").resolve()
    mail = outlook.CreateItem(OL_MAIL_ITEM)
    try:
        with tempfile.TemporaryDirectory(prefix="inkfold-outlook-") as folder:
            for index, asset in enumerate(email.assets()):
                path = Path(folder, str(index), asset.filename or f"{asset.content_id}.img")
                path.parent.mkdir()
                path.write_bytes(asset.data)
                attachment = mail.Attachments.Add(str(path), OL_BY_VALUE)
                accessor = attachment.PropertyAccessor
                accessor.SetProperty(PR_ATTACH_CONTENT_ID, asset.content_id)
                accessor.SetProperty(PR_ATTACHMENT_HIDDEN, True)
            mail.HTMLBody = email.render()
            # Outlook hands over its Word editor only once the window exists.
            inspector = mail.GetInspector
            inspector.Display(False)
            inspector.WindowState = OL_MINIMIZED
            editor = inspector.WordEditor
            setup = editor.PageSetup
            setup.PageHeight = PAGE_HEIGHT_PT
            for edge in ("TopMargin", "BottomMargin", "LeftMargin", "RightMargin"):
                setattr(setup, edge, MARGIN_PT)
            editor.ExportAsFixedFormat(str(pdf), WD_EXPORT_PDF)
    finally:
        mail.Close(OL_DISCARD)
    return pdf


def rasterise(pdf: Path) -> list[Path]:
    """Each page of ``pdf`` as ``<stem>-pN.png`` beside it, through pypdfium2 (``[qa]``)."""
    pdfium = importlib.import_module("pypdfium2")
    document = pdfium.PdfDocument(str(pdf))
    pages = []
    try:
        for index in range(len(document)):
            path = pdf.with_name(f"{pdf.stem}-p{index + 1}.png")
            document[index].render(scale=SCALE).to_pil().save(path)
            pages.append(path)
    finally:
        document.close()
    return pages


def render_gallery(
    names: list[str],
    out_dir: Path,
    outlook: Any,
    fixtures: Mapping[str, Any] | None = None,
    reconnect: Callable[[], Any] | None = None,
) -> dict[str, object]:
    """
    Render each named fixture; the record ``run.json`` holds, also written there.

    An Outlook that quits mid-run is reached again through ``reconnect`` and the
    email retried once; any other failure stops the run.
    """
    reconnect = reconnect or _connect
    version = str(outlook.Version)
    gallery = fixtures if fixtures is not None else all_fixtures()
    unknown = sorted(set(names) - set(gallery))
    if unknown:
        raise SystemExit(f"no such fixture: {', '.join(unknown)}")
    rendered: dict[str, list[str]] = {}
    for name in names:
        email = gallery[name]()
        try:
            pdf = render_email(email, name, out_dir, outlook)
        except Exception as exc:
            if _hresult(exc) not in _GONE:
                raise
            outlook = reconnect()
            pdf = render_email(email, name, out_dir, outlook)
        rendered[name] = [page.name for page in rasterise(pdf)]
    run: dict[str, object] = {
        "outlook": version,
        "windows": platform.version(),
        "fixtures": rendered,
    }
    (out_dir / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return run


#: The HRESULTs of an Outlook that has gone: the RPC server unavailable, or disconnected.
_GONE = frozenset({-2147023174, -2147417848})


def _hresult(exc: BaseException) -> int | None:
    """A COM error's HRESULT, its first argument, or ``None`` for any other exception."""
    code = exc.args[0] if exc.args else None
    return code if isinstance(code, int) else None


#: How classic Outlook is started to show one file: double-clicking a .eml runs ``/eml``.
_SINGLE_FILE = re.compile(r"\s/(?:eml|f)\s", re.IGNORECASE)


def single_file_outlooks() -> list[tuple[int, str]]:
    """
    Every classic Outlook running as a one-file viewer, by process id and command line.

    Such an instance outlives its window and answers COM without a mail session, so a
    render attached to it hangs on its first call rather than failing.
    """
    client = importlib.import_module("win32com.client")
    query = "SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name = 'OUTLOOK.EXE'"
    found = []
    for process in client.GetObject("winmgmts:").ExecQuery(query):
        line = str(process.CommandLine or "")
        if _SINGLE_FILE.search(line + " "):
            found.append((int(process.ProcessId), line))
    return found


def _connect(
    attempts: int = 10,
    wait_s: float = 2.0,
    viewers: Callable[[], list[tuple[int, str]]] = single_file_outlooks,
) -> Any:
    """
    A live Outlook, proved by creating and discarding a message.

    An Outlook that automation started quits when its last client lets go, so a
    run begun just after another can reach one still shutting down and be told
    the RPC server is unavailable. Each retry takes a fresh handle. A classic
    Outlook running as a one-file viewer is refused first, by name, since every
    call to it hangs.
    """
    stuck = viewers()
    if stuck:
        pid, line = stuck[0]
        raise SystemExit(
            f"Classic Outlook is running as a one-file viewer (process {pid}: {line.strip()}). "
            "It has no mail session, so a render would hang. Close it (Task Manager, "
            "Microsoft Outlook) and run again."
        )
    for attempt in range(attempts):
        outlook = outlook_application()
        try:
            # A held folder keeps Outlook running between messages; taken before the probe closes.
            _HELD.append(outlook.GetNamespace("MAPI").GetDefaultFolder(OL_FOLDER_INBOX))
            outlook.CreateItem(OL_MAIL_ITEM).Close(OL_DISCARD)
            return outlook
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(wait_s)
    raise AssertionError("unreachable")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else None)
    parser.add_argument("fixtures", nargs="*", help="fixture names; default, the email gallery")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    names = args.fixtures or list(all_fixtures())
    run = render_gallery(names, args.out, _connect())
    fixtures = run["fixtures"]
    assert isinstance(fixtures, dict)
    for name, pages in fixtures.items():
        print(f"{name}: {len(pages)} page(s)")
    print(f"Outlook {run['outlook']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
