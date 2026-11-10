"""The house daily note, fed one close's sample data: the template's fixture (v0.8.0)."""

from __future__ import annotations

from dataclasses import dataclass

from inkfold.builder import Email
from inkfold.house import Book, Commentary, DailyNote, Holding, SectorMove, Sectors
from inkfold.report import Dated, data_input

from ._house import CLOSE, FRESH, HOUSE, SOURCE


@dataclass(frozen=True)
class SampleNote(DailyNote):
    """The daily note with its three inputs loaded from constants."""

    house = HOUSE

    @data_input(source=SOURCE, max_age=FRESH)
    def book(self) -> Dated[Book]:
        return Dated(
            Book(
                portfolio="Hermes Global Equity",
                benchmark="MSCI ACWI",
                portfolio_return=0.62,
                benchmark_return=0.41,
                contributors=(
                    Holding("NVIDIA", 6.1, 2.85),
                    Holding("Microsoft", 5.4, 1.62),
                    Holding("ASML Holding", 2.3, 3.10),
                ),
                detractors=(
                    Holding("Novo Nordisk", 1.9, -2.64),
                    Holding("Exxon Mobil", 2.0, -1.35),
                ),
            ),
            CLOSE,
        )

    @data_input(source=SOURCE, max_age=FRESH)
    def sectors(self) -> Dated[Sectors]:
        moves = [
            ("Info. Tech.", 42.6),
            ("Financials", 11.2),
            ("Industrials", 6.4),
            ("Energy", -3.1),
            ("Health Care", -4.8),
        ]
        return Dated(Sectors(tuple(SectorMove(name, bps) for name, bps in moves)), CLOSE)

    @data_input(source="Hermes Research desk", max_age=FRESH)
    def commentary(self) -> Dated[Commentary]:
        return Dated(
            Commentary(
                headline="+62 bps, 21 ahead; chips lead again",
                body=(
                    "<p><strong>Semiconductors carried the tape.</strong> Global equities "
                    "rose 0.41% as the lithography makers lifted the chip complex for a "
                    "third session.</p>"
                ),
                outlook=(
                    "<p><strong>We trim NVIDIA by 50 bps at the open</strong> and add to JPMorgan "
                    "ahead of next week's bank earnings.</p>"
                ),
            ),
            CLOSE,
        )


def build() -> Email:
    """The note for the fixture's close. Deterministic: same bytes every call."""
    email = SampleNote(as_of=CLOSE).build()
    assert isinstance(email, Email)
    return email
