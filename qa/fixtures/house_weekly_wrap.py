"""The house weekly wrap, fed one week's sample data: the template's fixture (v0.8.0)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from inkfold.builder import Email
from inkfold.house import (
    Calendar,
    CalendarEvent,
    Commentary,
    MarketMove,
    Markets,
    WeekBook,
    WeeklyWrap,
)
from inkfold.report import Dated, data_input

from ._house import CLOSE, FRESH, HOUSE, SOURCE


@dataclass(frozen=True)
class SampleWrap(WeeklyWrap):
    """The weekly wrap with its four inputs loaded from constants."""

    house = HOUSE

    @data_input(source=SOURCE, max_age=FRESH)
    def book(self) -> Dated[WeekBook]:
        return Dated(
            WeekBook(
                portfolio="Hermes Global Equity",
                benchmark="MSCI ACWI",
                week_return=1.84,
                benchmark_week_return=1.37,
                ytd_return=14.92,
                benchmark_ytd_return=12.05,
                daily_active_bps=(8.0, -3.0, 12.0, 9.0, 21.0),
            ),
            CLOSE,
        )

    @data_input(source="Market data vendor", max_age=FRESH)
    def markets(self) -> Dated[Markets]:
        moves = (
            MarketMove("S&P 500", 5234.18, 1.42),
            MarketMove("Euro Stoxx 50", 4918.09, 0.63),
            MarketMove("Nikkei 225", 39_598.0, -0.41),
            MarketMove("US 10-year yield, %", 4.28, -1.15),
            MarketMove("Brent, $/bbl", 82.14, -2.30),
        )
        return Dated(Markets(moves), CLOSE)

    @data_input(source="Hermes Research desk", max_age=FRESH)
    def commentary(self) -> Dated[Commentary]:
        return Dated(
            Commentary(
                headline="47 bps ahead on the week; 287 bps ahead this year",
                body=(
                    "<p><strong>A broad week for risk.</strong> Equities rose on four of five "
                    "sessions as softer inflation data pulled yields lower.</p>"
                ),
                outlook=(
                    "<p><strong>CPI on Wednesday is the swing factor.</strong> We keep the "
                    "overweight in duration-sensitive growth into the print.</p>"
                ),
            ),
            CLOSE,
        )

    @data_input(source="Hermes Research desk", max_age=FRESH)
    def calendar(self) -> Dated[Calendar]:
        monday = CLOSE + timedelta(days=3)
        events = (
            CalendarEvent(monday, "Japan Q3 GDP", "First estimate"),
            CalendarEvent(monday + timedelta(days=2), "US CPI, October", "Core expected at 0.2%"),
            CalendarEvent(monday + timedelta(days=3), "JPMorgan results"),
        )
        return Dated(Calendar(events), CLOSE)


def build() -> Email:
    """The wrap for the fixture's week. Deterministic: same bytes every call."""
    email = SampleWrap(as_of=CLOSE).build()
    assert isinstance(email, Email)
    return email
