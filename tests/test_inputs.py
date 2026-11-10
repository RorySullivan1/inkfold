"""A report's declared data inputs and their freshness (roadmap v0.7.0)."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pytest

from inkfold.builder import EmailBuilder, FullWidth, TextBlock
from inkfold.builder.exceptions import ValidationError
from inkfold.report import (
    Dataset,
    Dated,
    FreshnessError,
    FutureDataError,
    Renderable,
    Report,
    StaleDataError,
    data_input,
)
from inkfold.run.__main__ import EXIT_BUILD_FAILED, main

CLOSE = date(2026, 10, 8)
CALLS: list[str] = []


def _email() -> Renderable:
    return (
        EmailBuilder()
        .metadata({"email_subject": "s", "firm_name": "f", "campaign_name": "c"})
        .section(FullWidth(content=TextBlock("<p>x</p>")))
        .build()
    )


@dataclass(frozen=True)
class Note(Report):
    """Two inputs, the second fresh for one day only."""

    as_of: date

    @data_input(source="House PMS", max_age=timedelta(days=3))
    def prices(self) -> Dated[list[float]]:
        CALLS.append("prices")
        return Dated([1.0, 2.0], CLOSE)

    @data_input(source="Risk system", max_age=timedelta(days=1))
    def risk(self) -> Dated[dict[str, float]]:
        return Dated({"beta": 1.1}, CLOSE)

    def build(self) -> Renderable:
        return _email()


class TestTheDeclaration:
    def test_the_class_lists_its_inputs_in_order(self):
        assert list(Note.inputs()) == ["prices", "risk"]

    def test_a_subclass_keeps_its_bases_inputs_first(self):
        @dataclass(frozen=True)
        class Wider(Note):
            @data_input(source="Desk", max_age=timedelta(days=1))
            def flows(self) -> Dated[int]:
                return Dated(1, CLOSE)

        assert list(Wider.inputs()) == ["prices", "risk", "flows"]

    def test_inputs_are_not_parameters(self):
        assert [f.name for f in Note.params()] == ["as_of"]

    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [
            ({"source": "", "max_age": timedelta(days=1)}, "source"),
            ({"source": "X", "max_age": 1}, "max_age"),
            ({"source": "X", "max_age": timedelta(days=-1)}, "max_age"),
        ],
    )
    def test_a_bad_declaration_raises(self, kwargs, match):
        with pytest.raises(ValidationError, match=match):
            data_input(**kwargs)

    def test_a_report_with_inputs_needs_an_as_of_date(self):
        @dataclass(frozen=True)
        class Undated(Report):
            client: str

            @data_input(source="X", max_age=timedelta(days=1))
            def prices(self) -> Dated[int]:
                return Dated(1, CLOSE)

        with pytest.raises(ValidationError, match="as_of: date"):
            Undated(client="acme")


class TestLoading:
    def test_an_input_reads_as_its_dataset(self):
        prices = Note(as_of=CLOSE).prices
        assert prices == Dataset("prices", "House PMS", CLOSE, [1.0, 2.0])
        assert prices.value == [1.0, 2.0]

    def test_an_input_loads_once_per_report(self):
        CALLS.clear()
        note = Note(as_of=CLOSE)
        note.load()
        assert note.prices is note.prices
        assert CALLS == ["prices"]

    def test_load_returns_every_input_in_order(self):
        assert [d.name for d in Note(as_of=CLOSE).load()] == ["prices", "risk"]

    def test_a_loaded_report_still_equals_a_fresh_one(self):
        loaded = Note(as_of=CLOSE)
        loaded.load()
        assert loaded == Note(as_of=CLOSE)

    def test_a_loader_must_return_dated(self):
        @dataclass(frozen=True)
        class Bare(Report):
            as_of: date

            @data_input(source="X", max_age=timedelta(days=1))
            def prices(self) -> Dated[int]:
                return 1  # type: ignore[return-value]

        with pytest.raises(ValidationError, match="Dated"):
            Bare(as_of=CLOSE).load()

    def test_a_loaders_own_error_is_not_swallowed(self):
        @dataclass(frozen=True)
        class Offline(Report):
            as_of: date

            @data_input(source="X", max_age=timedelta(days=1))
            def prices(self) -> Dated[int]:
                raise ConnectionError("feed down")

        with pytest.raises(ConnectionError, match="feed down"):
            Offline(as_of=CLOSE).load()


class TestFreshness:
    def test_data_exactly_max_age_old_passes(self):
        Note(as_of=CLOSE + timedelta(days=1)).load()

    def test_data_a_day_older_is_stale_and_named(self):
        with pytest.raises(StaleDataError, match="'risk'.*2 days.*max_age is 1 days"):
            Note(as_of=CLOSE + timedelta(days=2)).load()

    def test_data_dated_after_the_report_is_refused(self):
        with pytest.raises(FutureDataError, match="after the report's 7 October 2026"):
            Note(as_of=CLOSE - timedelta(days=1)).load()

    def test_both_are_freshness_errors_and_validation_errors(self):
        assert issubclass(StaleDataError, FreshnessError)
        assert issubclass(FutureDataError, FreshnessError)
        assert issubclass(FreshnessError, ValidationError)


class TestTheRunCommandLoadsFirst:
    @pytest.fixture()
    def script(self, tmp_path: Path) -> Path:
        path = tmp_path / "dated.py"
        path.write_text(
            textwrap.dedent("""\
                from dataclasses import dataclass
                from datetime import date, timedelta
                from inkfold.builder import EmailBuilder, FullWidth, TextBlock
                from inkfold.report import Dated, Renderable, Report, data_input

                BUILT = []

                @dataclass(frozen=True)
                class Dated_(Report):
                    as_of: date

                    @data_input(source="X", max_age=timedelta(days=1))
                    def prices(self) -> Dated[int]:
                        return Dated(1, date(2026, 10, 8))

                    @data_input(source="Y", max_age=timedelta(days=1))
                    def broken(self) -> Dated[int]:
                        if self.as_of == date(2026, 10, 9):
                            raise ConnectionError("feed down")
                        return Dated(1, date(2026, 10, 8))

                    def build(self) -> Renderable:
                        raise AssertionError("build ran before the inputs were checked")
            """),
            encoding="utf-8",
        )
        return path

    def test_a_stale_input_exits_2_before_build(self, script: Path, tmp_path: Path, capsys):
        code = main([str(script), "--as-of", "2026-10-30", "--out", str(tmp_path / "o")])
        assert code == EXIT_BUILD_FAILED
        assert "StaleDataError: input 'prices'" in capsys.readouterr().err

    def test_a_loader_that_raises_exits_2_naming_it(self, script: Path, tmp_path: Path, capsys):
        code = main([str(script), "--as-of", "2026-10-09", "--out", str(tmp_path / "o")])
        assert code == EXIT_BUILD_FAILED
        assert "ConnectionError" in capsys.readouterr().err
