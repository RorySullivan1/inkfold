"""The house weekly wrap: the week's return, the markets, the review, and the week ahead."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from inkfold.builder import CardGroup, DataTable, FullWidth, TextBlock
from inkfold.builder.containers import Container
from inkfold.builder.formats import number
from inkfold.builder.models import Card, Column, TableRow
from inkfold.builder.organising import Event, Timeline
from inkfold.builder.provenance import Dataset, format_date
from inkfold.inputs import required_input
from inkfold.report import Renderable

from ._base import HouseEmail
from .models import Calendar, Commentary, Markets, WeekBook

#: English day and month names, so a date in the week ahead reads the same under any locale.
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@dataclass(frozen=True)
class WeeklyWrap(HouseEmail):
    """
    One week, closed: four figures, the review, the markets, the outlook, the week ahead.

    Subclass it, set ``house``, and load ``book`` (a :class:`WeekBook`),
    ``markets`` (:class:`Markets`), ``commentary`` (a :class:`Commentary`) and
    ``calendar`` (a :class:`Calendar`), each with ``@data_input``. The active
    card draws the week's daily active returns under its figure when the book
    carries them. An empty calendar leaves the week ahead out.
    """

    campaign: ClassVar[str] = "Weekly Wrap"

    book = required_input(WeekBook, "the portfolio's week and year to date against its benchmark")
    markets = required_input(Markets, "the markets the wrap lists, each with its week")
    commentary = required_input(Commentary, "the headline, the week's review, and the outlook")
    calendar = required_input(Calendar, "the events of the week ahead")

    def build(self) -> Renderable:
        words = self.commentary.value
        day = format_date(self.as_of)
        sections: list[Container] = [
            FullWidth(title="The Week in Brief", content=_headline(self.book), source=self.book),
            FullWidth(title="Review", content=TextBlock(words.body)),
            FullWidth(title="Markets", content=_markets(self.markets)),
            FullWidth(title="Outlook", content=TextBlock(words.outlook)),
        ]
        if self.calendar.value.events:
            sections.append(
                FullWidth(
                    title="The Week Ahead",
                    content=_ahead(self.calendar.value),
                    source=self.calendar,
                )
            )
        return self.email(
            subject=f"{self.campaign} — week to {day}: {words.headline}",
            preheader=words.headline,
            date_range=f"Week to {day}",
            sections=sections,
        )


def _headline(book: Dataset[WeekBook]) -> CardGroup:
    """The week for the portfolio and its benchmark, the gap, and the gap this year."""
    b = book.value
    pct = lambda v: number(v, 2, sign=True) + "%"  # noqa: E731 - one format, read twice
    bps = lambda v: number(v, 0, sign=True) + " bps"  # noqa: E731 - one format, read twice
    week_active = round((b.week_return - b.benchmark_week_return) * 100, 1)
    ytd_active = round((b.ytd_return - b.benchmark_ytd_return) * 100, 1)
    trend = list(b.daily_active_bps) or None
    return CardGroup(
        [
            Card.from_number(b.portfolio, b.week_return, pct, tone="auto"),
            Card.from_number(b.benchmark, b.benchmark_week_return, pct, tone="auto"),
            Card.from_number("Active, week", week_active, bps, trend=trend),
            Card.from_number("Active, year to date", ytd_active, bps),
        ]
    )


def _markets(markets: Dataset[Markets]) -> DataTable:
    """Each market's close and its week, in the order the input lists them."""
    return DataTable(
        headers=[
            Column("Market", width=3),
            Column("Close", format=lambda v: number(v, 2), align_decimal=True),
            Column(
                "Week",
                format=lambda v: number(v, 2, sign=True),
                tone="auto",
                align_decimal=True,
                unit="%",
            ),
        ],
        rows=[
            TableRow(cells=[move.market, move.level, move.change_pct])
            for move in markets.value.moves
        ],
        source=markets,
        caption="Markets over the week",
    )


def _ahead(calendar: Calendar) -> Timeline:
    """The week ahead, one event a line, each under its day."""
    return Timeline([Event(_short(e.day), e.title, e.detail) for e in calendar.events])


def _short(day: date) -> str:
    """``Mon 16 Nov``: a day in the week ahead, independent of locale."""
    return f"{_DAYS[day.weekday()]} {day.day} {_MONTHS[day.month - 1]}"
