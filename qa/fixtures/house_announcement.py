"""The house research announcement, attaching the research-note fixture: its fixture (v0.8.0)."""

from __future__ import annotations

from dataclasses import dataclass

from inkfold.builder import Email
from inkfold.house import Author, Paper, ResearchAnnouncement
from inkfold.report import Dated, data_input

from . import a4_research_note
from ._house import CLOSE, FRESH, HOUSE


@dataclass(frozen=True)
class SampleAnnouncement(ResearchAnnouncement):
    """The announcement with its paper loaded from the paged gallery's research note."""

    house = HOUSE

    @data_input(source="Hermes Research publishing", max_age=FRESH)
    def paper(self) -> Dated[Paper]:
        return Dated(
            Paper(
                title="Momentum After the Rate Peak",
                summary=(
                    "<p>Momentum has historically weakened in the six months after a policy "
                    "rate peak. We test whether that holds across regions and what it means "
                    "for a factor book today.</p>"
                ),
                key_points=(
                    "Momentum's drawdown risk doubles after a rate peak, in every region tested.",
                    "Quality offsets most of it at a fraction of the turnover.",
                    "We cut the momentum tilt by a third and add to quality.",
                ),
                authors=(
                    Author("Ada Chen", "Head of Quant Research", "ada.chen@example.com"),
                    Author("Tomás Ruiz", "Quantitative Strategist"),
                ),
                document=a4_research_note.build(),
                filename="momentum-after-the-rate-peak.pdf",
                url="https://example.com/research/momentum-after-the-rate-peak",
            ),
            CLOSE,
        )


def build() -> Email:
    """The announcement for the fixture's paper. Deterministic: same bytes every call."""
    email = SampleAnnouncement(as_of=CLOSE).build()
    assert isinstance(email, Email)
    return email
