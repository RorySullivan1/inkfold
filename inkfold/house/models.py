"""The data the house templates read: each a frozen dataclass a loader returns ``Dated``."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from inkfold.builder.document import Document
from inkfold.builder.exceptions import ValidationError
from inkfold.builder.finite import require_finite


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} is non-blank text, got: {value!r}")
    return value


@dataclass(frozen=True)
class Holding:
    """One holding's day: its weight and return, both in percent."""

    name: str
    weight: float
    ret: float

    def __post_init__(self) -> None:
        _text(self.name, "Holding.name")
        require_finite(self.weight, f"{self.name}'s weight")
        require_finite(self.ret, f"{self.name}'s return")

    @property
    def contribution_bps(self) -> float:
        """Weight × return, in basis points, to one decimal."""
        return round(self.weight * self.ret, 1)


@dataclass(frozen=True)
class Book:
    """
    A portfolio's day against its benchmark, and what drove it.

    Returns are in percent. ``contributors`` and ``detractors`` are the holdings
    the note names; the rest of the book is shown as one residual row.
    """

    portfolio: str
    benchmark: str
    portfolio_return: float
    benchmark_return: float
    contributors: Sequence[Holding]
    detractors: Sequence[Holding] = ()

    def __post_init__(self) -> None:
        _text(self.portfolio, "Book.portfolio")
        _text(self.benchmark, "Book.benchmark")
        require_finite(self.portfolio_return, "Book.portfolio_return")
        require_finite(self.benchmark_return, "Book.benchmark_return")
        if not self.contributors:
            raise ValidationError("a Book names at least one contributor.")
        named = sum(h.weight for h in (*self.contributors, *self.detractors))
        if named > 100:
            raise ValidationError(f"the holdings a Book names weigh {named:g}%, over 100%.")

    @property
    def active_bps(self) -> float:
        """The portfolio's return over its benchmark's, in basis points."""
        return round((self.portfolio_return - self.benchmark_return) * 100, 1)


@dataclass(frozen=True)
class SectorMove:
    """One sector's contribution to the day, in basis points."""

    sector: str
    bps: float

    def __post_init__(self) -> None:
        _text(self.sector, "SectorMove.sector")
        require_finite(self.bps, f"{self.sector}'s bps")


@dataclass(frozen=True)
class Sectors:
    """The day's contribution by sector: one :class:`SectorMove` each."""

    moves: Sequence[SectorMove]

    def __post_init__(self) -> None:
        if not self.moves:
            raise ValidationError("Sectors holds at least one SectorMove.")


@dataclass(frozen=True)
class Commentary:
    """
    The author's words for one issue.

    ``headline`` is plain text, one line: it leads the subject and the inbox
    preview. ``body`` and ``outlook`` are HTML, each the caller's own paragraphs,
    emitted raw as a ``TextBlock`` is; escaping untrusted text in them is the
    caller's job.
    """

    headline: str
    body: str
    outlook: str

    def __post_init__(self) -> None:
        for name in ("headline", "body", "outlook"):
            _text(getattr(self, name), f"Commentary.{name}")
        if "\n" in self.headline:
            raise ValidationError("Commentary.headline is one line; it leads the subject.")


@dataclass(frozen=True)
class MarketMove:
    """One market's week: its closing level and its change over the week, in percent."""

    market: str
    level: float
    change_pct: float

    def __post_init__(self) -> None:
        _text(self.market, "MarketMove.market")
        require_finite(self.level, f"{self.market}'s level")
        require_finite(self.change_pct, f"{self.market}'s change")


@dataclass(frozen=True)
class Markets:
    """The markets a weekly wrap reports, in the order it lists them."""

    moves: Sequence[MarketMove]

    def __post_init__(self) -> None:
        if not self.moves:
            raise ValidationError("Markets holds at least one MarketMove.")


@dataclass(frozen=True)
class WeekBook:
    """A portfolio's week and year to date against its benchmark, in percent."""

    portfolio: str
    benchmark: str
    week_return: float
    benchmark_week_return: float
    ytd_return: float
    benchmark_ytd_return: float
    daily_active_bps: Sequence[float] = ()

    def __post_init__(self) -> None:
        _text(self.portfolio, "WeekBook.portfolio")
        _text(self.benchmark, "WeekBook.benchmark")
        for name in ("week_return", "benchmark_week_return", "ytd_return", "benchmark_ytd_return"):
            require_finite(getattr(self, name), f"WeekBook.{name}")
        for value in self.daily_active_bps:
            require_finite(value, "WeekBook.daily_active_bps")


@dataclass(frozen=True)
class CalendarEvent:
    """One event in the week ahead."""

    day: date
    title: str
    detail: str = ""

    def __post_init__(self) -> None:
        if type(self.day) is not date:
            raise ValidationError(f"CalendarEvent.day is a date, got {type(self.day).__name__}.")
        _text(self.title, "CalendarEvent.title")


@dataclass(frozen=True)
class Calendar:
    """The week ahead, in date order; empty when nothing is scheduled."""

    events: Sequence[CalendarEvent]

    def __post_init__(self) -> None:
        days = [event.day for event in self.events]
        if days != sorted(days):
            raise ValidationError("a Calendar's events run in date order.")


@dataclass(frozen=True)
class Author:
    """One of a paper's authors, as its author block prints them."""

    name: str
    job_title: str = ""
    email: str = ""

    def __post_init__(self) -> None:
        _text(self.name, "Author.name")


@dataclass(frozen=True)
class Paper:
    """
    A research report to announce, and the document to attach as its PDF.

    ``summary`` is HTML, the caller's own paragraphs; ``key_points`` are plain
    text. ``filename`` is the attachment's bare name, ending ``.pdf``.
    """

    title: str
    summary: str
    key_points: Sequence[str]
    authors: Sequence[Author]
    document: Document
    filename: str
    url: str = ""

    def __post_init__(self) -> None:
        _text(self.title, "Paper.title")
        _text(self.summary, "Paper.summary")
        if not self.key_points:
            raise ValidationError("a Paper names at least one key point.")
        for point in self.key_points:
            _text(point, "Paper.key_points")
        if not self.authors:
            raise ValidationError("a Paper names at least one author.")
        if not isinstance(self.document, Document):
            raise ValidationError(
                f"Paper.document is a Document, got {type(self.document).__name__}."
            )
        if not self.filename.lower().endswith(".pdf") or "/" in self.filename:
            raise ValidationError(
                f"Paper.filename is a bare name ending .pdf, got: {self.filename!r}"
            )
