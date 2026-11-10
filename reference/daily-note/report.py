"""The daily-note reference report as a :class:`Report` (roadmap v0.6.0, inputs v0.7.0)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qa.reference import example

#: The source that builds the stand-in today.
SOURCE = Path("examples/daily-investment-note/daily-investment-note.py")
_EXAMPLE = example("daily-investment-note")


@dataclass(frozen=True)
class DailyNote(_EXAMPLE.DailyNote):  # type: ignore[name-defined, misc]
    """The worked example's note: one parameter, its as-of date, and three dated inputs."""
