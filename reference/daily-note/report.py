"""The daily-note reference report as a :class:`Report` (roadmap v0.6.0)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from inkfold.report import Renderable, Report

#: The source that builds the stand-in today.
SOURCE = Path("examples/daily-investment-note/daily-investment-note.py")


@dataclass(frozen=True)
class DailyNote(Report):
    """A daily investment note with one typed parameter: the as-of date."""

    as_of: date

    def build(self) -> Renderable:
        """Build the daily note, through the worked example it stands in for.

        The ``as_of`` parameter is the report's contract — the stand-in
        does not yet use it for data binding (that is v0.7.0). Today it
        builds the same email regardless, proving the wiring.
        """
        from qa.reference import example

        return example("daily-investment-note").build()
