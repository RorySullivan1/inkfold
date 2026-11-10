"""
House templates: the firm's standard emails as reports you subclass and feed (roadmap v0.8.0).

Each template is a :class:`~inkfold.report.Report` that builds its whole issue
from an as-of date and its declared inputs. A firm subclasses one, sets
``house`` once, and loads each input with ``@data_input``; it never builds a
section. ``python -m inkfold.run my_note.py --as-of 2026-11-09`` runs it.
"""

from ._base import House, HouseEmail
from .announcement import ResearchAnnouncement
from .daily_note import DailyNote
from .models import (
    Author,
    Book,
    Calendar,
    CalendarEvent,
    Commentary,
    Holding,
    MarketMove,
    Markets,
    Paper,
    SectorMove,
    Sectors,
    WeekBook,
)
from .weekly_wrap import WeeklyWrap

__all__ = [
    "Author",
    "Book",
    "Calendar",
    "CalendarEvent",
    "Commentary",
    "DailyNote",
    "Holding",
    "House",
    "HouseEmail",
    "MarketMove",
    "Markets",
    "Paper",
    "ResearchAnnouncement",
    "SectorMove",
    "Sectors",
    "WeekBook",
    "WeeklyWrap",
]
