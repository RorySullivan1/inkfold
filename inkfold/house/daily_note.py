"""The house daily note: the day's return, what drove it, and what the desk is doing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from inkfold.builder import CardGroup, DataTable, FullWidth, TextBlock
from inkfold.builder.enums import RowKind
from inkfold.builder.formats import number
from inkfold.builder.glance import BarList
from inkfold.builder.models import Card, Column, TableRow
from inkfold.builder.provenance import Dataset, format_date
from inkfold.inputs import required_input
from inkfold.report import Renderable

from ._base import HouseEmail
from .models import Book, Commentary, Holding, Sectors


@dataclass(frozen=True)
class DailyNote(HouseEmail):
    """
    One close, read on a phone: three figures, the attribution table, sectors, two paragraphs.

    Subclass it, set ``house``, and load ``book`` (a :class:`Book`), ``sectors``
    (:class:`Sectors`) and ``commentary`` (a :class:`Commentary`),
    each with ``@data_input``. Every section is one column, so nothing collapses
    at 375px, and nothing is a picture, so the note needs no extra and no image
    to download. Every exhibit's source line is its input's.
    """

    campaign: ClassVar[str] = "Daily Note"

    book = required_input(Book, "the day's return and its largest contributors and detractors")
    sectors = required_input(Sectors, "each sector's contribution to the day")
    commentary = required_input(Commentary, "the headline, the day in brief, and positioning")

    def build(self) -> Renderable:
        book, sectors, words = self.book, self.sectors, self.commentary.value
        day = format_date(self.as_of)
        return self.email(
            subject=f"{self.campaign} — {day}: {words.headline}",
            preheader=words.headline,
            date_range=f"Close of {day}",
            sections=[
                FullWidth(title="The Day in Brief", content=_headline(book), source=book),
                FullWidth(title="Markets", content=TextBlock(words.body)),
                FullWidth(title="What Drove Returns", content=_attribution(book)),
                FullWidth(title="By Sector", content=_sectors(sectors), source=sectors),
                FullWidth(title="Positioning", content=TextBlock(words.outlook)),
            ],
        )


def _headline(book: Dataset[Book]) -> CardGroup:
    """The portfolio, its benchmark and the gap between them."""
    b = book.value
    pct = lambda v: number(v, 2, sign=True) + "%"  # noqa: E731 - one format, read three times
    return CardGroup(
        [
            Card.from_number(b.portfolio, b.portfolio_return, pct, tone="auto"),
            Card.from_number(b.benchmark, b.benchmark_return, pct, tone="auto"),
            Card.from_number("Active", b.active_bps, lambda v: number(v, 0, sign=True) + " bps"),
        ]
    )


def _attribution(book: Dataset[Book]) -> DataTable:
    """Contributors, detractors, the rest of the book, and the total, in four columns."""
    b = book.value
    named = [*b.contributors, *b.detractors]
    total_bps = round(b.portfolio_return * 100, 1)
    rows = [TableRow(cells=["Top contributors"], kind=RowKind.SUBHEAD), *map(_row, b.contributors)]
    if b.detractors:
        rows += [TableRow(cells=["Top detractors"], kind=RowKind.SUBHEAD), *map(_row, b.detractors)]
    rest_weight = round(100 - sum(h.weight for h in named), 1)
    if rest_weight > 0:
        rest_bps = round(total_bps - sum(h.contribution_bps for h in named), 1)
        rows.append(
            TableRow(
                cells=["Other holdings", rest_weight, round(rest_bps / rest_weight, 2), rest_bps]
            )
        )
    rows.append(
        TableRow(cells=[b.portfolio, 100.0, b.portfolio_return, total_bps], kind=RowKind.TOTAL)
    )
    return DataTable(
        headers=[
            Column("Holding", width=3),
            Column("Weight", format=lambda v: number(v, 1), align_decimal=True, unit="%"),
            Column(
                "Return",
                format=lambda v: number(v, 2, sign=True),
                tone="auto",
                align_decimal=True,
                unit="%",
            ),
            Column(
                "Contrib.",
                format=lambda v: number(v, 1, sign=True),
                tone="auto",
                align_decimal=True,
                unit="bps",
            ),
        ],
        rows=rows,
        source=book,
        caption="Contribution to return",
    )


def _row(holding: Holding) -> TableRow:
    return TableRow(cells=[holding.name, holding.weight, holding.ret, holding.contribution_bps])


def _sectors(sectors: Dataset[Sectors]) -> BarList:
    """Each sector's contribution, largest gain first, drawn about zero."""
    moves = sorted(sectors.value.moves, key=lambda m: m.bps, reverse=True)
    return BarList(
        [(m.sector, m.bps) for m in moves],
        value_format=lambda v: number(v, 1, sign=True),
        diverging=True,
        subtitle="Contribution to return, bps",
    )
