"""The Outlook renderer (roadmap v0.9.0), against a fake COM surface: no Windows needed."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from qa import outlook_render
from qa.fixtures import all_fixtures


class FakeAccessor:
    def __init__(self) -> None:
        self.props: dict[str, Any] = {}

    def SetProperty(self, name: str, value: Any) -> None:  # noqa: N802 - COM's spelling
        self.props[name] = value


class FakeMail:
    def __init__(self, fail_export: bool = False) -> None:
        self.attachments: list[tuple[str, FakeAccessor]] = []
        self.closed_with: int | None = None
        self.saved = self.sent = False
        self.HTMLBody = ""
        self.setup = SimpleNamespace()
        self.exported: str | None = None
        self.fail_export = fail_export
        self.Attachments = SimpleNamespace(Add=self._add)
        mail = self

        class Editor:
            PageSetup = mail.setup

            def ExportAsFixedFormat(self, path: str, fmt: int) -> None:  # noqa: N802
                if mail.fail_export:
                    raise RuntimeError("export refused")
                assert fmt == outlook_render.WD_EXPORT_PDF
                mail.exported = path
                Path(path).write_bytes(b"%PDF-1.4 fake")

        class Inspector:
            WordEditor = Editor()
            WindowState = 0

            def Display(self, modal: bool) -> None:  # noqa: N802
                assert modal is False

        self.GetInspector = Inspector()

    def _add(self, path: str, how: int) -> SimpleNamespace:
        assert how == outlook_render.OL_BY_VALUE and Path(path).is_file()
        accessor = FakeAccessor()
        self.attachments.append((Path(path).name, accessor))
        return SimpleNamespace(PropertyAccessor=accessor)

    def Save(self) -> None:  # noqa: N802
        self.saved = True

    def Send(self) -> None:  # noqa: N802
        self.sent = True

    def Close(self, how: int) -> None:  # noqa: N802
        self.closed_with = how


class FakeOutlook:
    Version = "16.0.0.0"

    def __init__(self, fail_export: bool = False, gone: int = 0) -> None:
        self.mails: list[FakeMail] = []
        self.fail_export = fail_export
        self.gone = gone

    def CreateItem(self, kind: int) -> FakeMail:  # noqa: N802
        if self.gone:
            self.gone -= 1
            raise OSError(-2147023174, "The RPC server is unavailable.")
        mail = FakeMail(self.fail_export)
        self.mails.append(mail)
        return mail


class TestOneEmail:
    def test_it_is_exported_and_discarded_never_saved_or_sent(self, tmp_path: Path):
        outlook = FakeOutlook()
        pdf = outlook_render.render_email(all_fixtures()["minimal"](), "minimal", tmp_path, outlook)
        (mail,) = outlook.mails
        assert pdf == (tmp_path / "minimal.pdf").resolve() and mail.exported == str(pdf)
        assert mail.closed_with == outlook_render.OL_DISCARD
        assert not mail.saved and not mail.sent

    def test_a_failed_export_still_discards_the_message(self, tmp_path: Path):
        outlook = FakeOutlook(fail_export=True)
        with pytest.raises(RuntimeError, match="export refused"):
            outlook_render.render_email(all_fixtures()["minimal"](), "minimal", tmp_path, outlook)
        assert outlook.mails[0].closed_with == outlook_render.OL_DISCARD

    def test_every_attached_image_carries_its_content_id_hidden(self, tmp_path: Path):
        email = all_fixtures()["image_matrix"]()
        outlook = FakeOutlook()
        outlook_render.render_email(email, "image_matrix", tmp_path, outlook)
        mail = outlook.mails[0]
        ids = [
            accessor.props[outlook_render.PR_ATTACH_CONTENT_ID] for _, accessor in mail.attachments
        ]
        assert ids == [asset.content_id for asset in email.assets()] and ids
        assert all(
            a.props[outlook_render.PR_ATTACHMENT_HIDDEN] is True for _, a in mail.attachments
        )
        assert mail.HTMLBody == email.render()

    def test_the_page_is_as_tall_as_word_allows(self, tmp_path: Path):
        outlook = FakeOutlook()
        outlook_render.render_email(all_fixtures()["minimal"](), "minimal", tmp_path, outlook)
        assert outlook.mails[0].setup.PageHeight == outlook_render.PAGE_HEIGHT_PT == 1584


class TestTheGallery:
    def test_an_outlook_that_quits_is_reached_again_once(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(outlook_render, "rasterise", lambda pdf: [pdf.with_suffix(".png")])
        fresh = FakeOutlook()
        run = outlook_render.render_gallery(
            ["minimal"], tmp_path, FakeOutlook(gone=1), reconnect=lambda: fresh
        )
        assert run["fixtures"] == {"minimal": ["minimal.png"]} and len(fresh.mails) == 1
        assert (tmp_path / "run.json").is_file()

    def test_any_other_failure_stops_the_run(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(outlook_render, "rasterise", lambda pdf: [])
        with pytest.raises(RuntimeError):
            outlook_render.render_gallery(["minimal"], tmp_path, FakeOutlook(fail_export=True))

    def test_an_unknown_fixture_is_named(self, tmp_path: Path):
        with pytest.raises(SystemExit, match="no such fixture: nope"):
            outlook_render.render_gallery(["nope"], tmp_path, FakeOutlook())
