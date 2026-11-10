"""Tests for ``python -m inkfold.run`` (v0.6.0)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from inkfold.run.__main__ import EXIT_BUILD_FAILED, EXIT_OK, main

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture()
def tmp_report(tmp_path: Path) -> Path:
    """A minimal report module in a temporary directory."""
    script = tmp_path / "stub_report.py"
    script.write_text(
        textwrap.dedent("""\
            from __future__ import annotations
            from dataclasses import dataclass
            from datetime import date
            from inkfold.report import Renderable, Report
            from inkfold.builder import EmailBuilder, FullWidth, TextBlock

            @dataclass(frozen=True)
            class Stub(Report):
                as_of: date
                client: str = "default"

                def build(self) -> Renderable:
                    return (
                        EmailBuilder()
                        .metadata({
                            "email_subject": "Test",
                            "firm_name": "Firm",
                            "campaign_name": "campaign",
                        })
                        .section(FullWidth(content=TextBlock("body")))
                        .build()
                    )
        """),
        encoding="utf-8",
    )
    return script


@pytest.fixture()
def out_dir(tmp_path: Path) -> Path:
    return tmp_path / "out"


class TestTheRunCli:
    def test_a_valid_report_exits_ok(self, tmp_report: Path, out_dir: Path):
        code = main([str(tmp_report), "--as-of", "2026-10-30", "--out", str(out_dir)])
        assert code == EXIT_OK
        assert (out_dir / "stub_report.html").exists()
        assert (out_dir / "stub_report.txt").exists()

    def test_a_named_class(self, tmp_report: Path, out_dir: Path):
        code = main([f"{tmp_report}:Stub", "--as-of", "2026-10-30", "--out", str(out_dir)])
        assert code == EXIT_OK

    def test_missing_required_param_exits_2(self, tmp_report: Path, out_dir: Path):
        code = main([str(tmp_report), "--out", str(out_dir)])
        assert code == EXIT_BUILD_FAILED

    def test_bad_date_exits_2(self, tmp_report: Path, out_dir: Path):
        code = main([str(tmp_report), "--as-of", "not-a-date", "--out", str(out_dir)])
        assert code == EXIT_BUILD_FAILED

    def test_no_args_exits_2(self):
        code = main([])
        assert code == EXIT_BUILD_FAILED

    def test_an_unknown_parameter_exits_2(self, tmp_report: Path, out_dir: Path, capsys):
        code = main(
            [str(tmp_report), "--as-of", "2026-10-30", "--clinet", "x", "--out", str(out_dir)]
        )
        assert code == EXIT_BUILD_FAILED
        assert "--clinet" in capsys.readouterr().err

    def test_a_missing_backend_exits_2_without_a_traceback(self, tmp_path: Path, capsys):
        script = tmp_path / "needs_backend.py"
        script.write_text(
            textwrap.dedent("""                from dataclasses import dataclass
                from inkfold.data.exceptions import BackendMissingError
                from inkfold.report import Renderable, Report

                @dataclass(frozen=True)
                class NeedsBackend(Report):
                    def build(self) -> Renderable:
                        raise BackendMissingError("install the extra")
            """),
            encoding="utf-8",
        )
        assert main([str(script), "--out", str(tmp_path / "out")]) == EXIT_BUILD_FAILED
        assert "BackendMissingError: install the extra" in capsys.readouterr().err

    def test_two_runs_write_identical_bytes(self, tmp_report: Path, tmp_path: Path):
        outputs = []
        for run in ("first", "second"):
            out = tmp_path / run
            assert main([str(tmp_report), "--as-of", "2026-10-30", "--out", str(out)]) == EXIT_OK
            outputs.append(
                [(out / f"stub_report.{suffix}").read_bytes() for suffix in ("html", "txt")]
            )
        assert outputs[0] == outputs[1]

    def test_missing_file_exits_2(self, out_dir: Path):
        code = main(["no_such_file.py", "--as-of", "2026-10-30", "--out", str(out_dir)])
        assert code == EXIT_BUILD_FAILED


class TestTheReferenceDailyNote:
    """The ported daily-note runs from the CLI, twice to the same bytes."""

    def test_it_runs_and_is_deterministic(self, tmp_path: Path, monkeypatch):
        pytest.importorskip("matplotlib", reason='the daily note plots with "inkfold[charts]"')
        monkeypatch.chdir(REPO)
        outputs = []
        for run in ("first", "second"):
            out = tmp_path / run
            code = main(
                ["reference/daily-note/report.py", "--as-of", "2026-10-09", "--out", str(out)]
            )
            assert code == EXIT_OK
            outputs.append([(out / f"report.{suffix}").read_bytes() for suffix in ("html", "txt")])
        assert outputs[0] == outputs[1]

    def test_a_close_past_its_data_is_stale(self, tmp_path: Path, monkeypatch, capsys):
        monkeypatch.chdir(REPO)
        code = main(
            ["reference/daily-note/report.py", "--as-of", "2026-10-30", "--out", str(tmp_path)]
        )
        assert code == EXIT_BUILD_FAILED
        assert "StaleDataError: input 'performance'" in capsys.readouterr().err
