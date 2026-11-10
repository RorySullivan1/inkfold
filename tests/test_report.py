"""Tests for the Report base class and the Renderable type alias (v0.6.0)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pytest

from inkfold.builder.document import Document
from inkfold.builder.exceptions import ValidationError
from inkfold.report import Renderable, Report

# -- helpers ------------------------------------------------------------------


def _minimal_email():
    """The smallest valid Email, for build() tests."""
    from inkfold.builder import EmailBuilder, FullWidth, TextBlock

    return (
        EmailBuilder()
        .metadata(
            {
                "email_subject": "Test",
                "firm_name": "Firm",
                "campaign_name": "campaign",
            }
        )
        .section(FullWidth(content=TextBlock("body")))
        .build()
    )


@dataclass(frozen=True)
class StubReport(Report):
    """A report with one required and one optional parameter."""

    as_of: date
    client: str = "default-client"

    def build(self) -> Renderable:
        return _minimal_email()


@dataclass(frozen=True)
class FullReport(Report):
    """A report with one parameter of each kind a report may take."""

    as_of: date
    universe: tuple[str, ...] = ("AAPL",)
    lookback: int = 20
    weight: float = 1.0
    hedged: bool = False
    client: str | None = None

    def build(self) -> Renderable:
        return _minimal_email()


@dataclass(frozen=True)
class BareReport(Report):
    """A report that never overrides build()."""

    label: str = "bare"


# -- the Renderable alias ----------------------------------------------------


class TestTheRenderableAlias:
    def test_renderable_is_document_today(self):
        """The alias is Document; widening it is a conscious act."""
        assert Renderable is Document


# -- construction and validation ----------------------------------------------


class TestConstructionValidation:
    def test_a_valid_report_constructs(self):
        r = StubReport(as_of=date(2026, 10, 30))
        assert r.as_of == date(2026, 10, 30)
        assert r.client == "default-client"

    def test_a_required_field_that_is_none_raises(self):
        with pytest.raises(ValidationError, match="as_of"):
            StubReport(as_of=None)  # type: ignore[arg-type]

    def test_a_wrong_type_raises(self):
        with pytest.raises(ValidationError, match="as_of"):
            StubReport(as_of="2026-10-30")  # type: ignore[arg-type]

    def test_an_optional_field_accepts_its_default(self):
        r = StubReport(as_of=date(2026, 10, 30))
        assert r.client == "default-client"

    def test_an_optional_field_accepts_a_value(self):
        r = StubReport(as_of=date(2026, 10, 30), client="acme")
        assert r.client == "acme"

    def test_frozen(self):
        r = StubReport(as_of=date(2026, 10, 30))
        with pytest.raises(AttributeError):
            r.as_of = date(2026, 1, 1)  # type: ignore[misc]

    def test_a_datetime_is_not_a_date(self):
        with pytest.raises(ValidationError, match="as_of"):
            StubReport(as_of=datetime(2026, 10, 30, 9, 0))

    def test_a_bool_is_not_an_int(self):
        with pytest.raises(ValidationError, match="lookback"):
            FullReport(as_of=date(2026, 10, 30), lookback=True)

    def test_an_int_is_a_float(self):
        assert FullReport(as_of=date(2026, 10, 30), weight=2).weight == 2

    def test_a_tuple_parameter_checks_each_item(self):
        r = FullReport(as_of=date(2026, 10, 30), universe=("AAPL", "MSFT"))
        assert r.universe == ("AAPL", "MSFT")
        with pytest.raises(ValidationError, match="universe"):
            FullReport(as_of=date(2026, 10, 30), universe=("AAPL", 7))  # type: ignore[arg-type]

    def test_a_list_is_not_a_tuple(self):
        with pytest.raises(ValidationError, match="universe"):
            FullReport(as_of=date(2026, 10, 30), universe=["AAPL"])  # type: ignore[arg-type]

    def test_an_optional_parameter_takes_none(self):
        assert FullReport(as_of=date(2026, 10, 30), client=None).client is None

    def test_an_annotation_a_report_cannot_take_raises(self):
        @dataclass(frozen=True)
        class Odd(Report):
            weights: dict[str, float]

            def build(self) -> Renderable:
                return _minimal_email()

        with pytest.raises(ValidationError, match="weights"):
            Odd(weights={"a": 1.0})


# -- build() -----------------------------------------------------------------


class TestBuild:
    def test_build_returns_a_document(self):
        r = StubReport(as_of=date(2026, 10, 30))
        result = r.build()
        assert isinstance(result, Document)

    def test_unimplemented_build_raises(self):
        r = BareReport()
        with pytest.raises(NotImplementedError, match="BareReport"):
            r.build()


# -- determinism --------------------------------------------------------------


class TestDeterminism:
    def test_same_params_same_bytes(self):
        a = StubReport(as_of=date(2026, 10, 30))
        b = StubReport(as_of=date(2026, 10, 30))
        assert a.build().render() == b.build().render()


# -- from_cli -----------------------------------------------------------------


class TestFromCli:
    def test_coerces_date_from_iso(self):
        r = StubReport.from_cli({"as_of": "2026-10-30"})
        assert r.as_of == date(2026, 10, 30)  # type: ignore[union-attr]

    def test_coerces_str(self):
        r = StubReport.from_cli({"as_of": "2026-10-30", "client": "acme"})
        assert r.client == "acme"  # type: ignore[union-attr]

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError, match="--as-of"):
            StubReport.from_cli({})

    def test_an_unknown_parameter_raises(self):
        with pytest.raises(ValidationError, match="--clinet"):
            StubReport.from_cli({"as_of": "2026-10-30", "clinet": "acme"})

    def test_every_kind_parses(self):
        r = FullReport.from_cli(
            {
                "as_of": "2026-10-30",
                "universe": "AAPL, MSFT,NVDA",
                "lookback": "60",
                "weight": "0.5",
                "hedged": "yes",
                "client": "acme",
            }
        )
        assert r == FullReport(
            as_of=date(2026, 10, 30),
            universe=("AAPL", "MSFT", "NVDA"),
            lookback=60,
            weight=0.5,
            hedged=True,
            client="acme",
        )

    def test_a_bool_that_is_neither_raises(self):
        with pytest.raises(ValidationError, match="hedged"):
            FullReport.from_cli({"as_of": "2026-10-30", "hedged": "maybe"})

    def test_bad_date_raises(self):
        with pytest.raises(ValidationError, match="Cannot parse"):
            StubReport.from_cli({"as_of": "not-a-date"})


# -- params -------------------------------------------------------------------


class TestParams:
    def test_lists_declared_fields(self):
        names = [f.name for f in StubReport.params()]
        assert "as_of" in names
        assert "client" in names
