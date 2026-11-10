"""What every house template shares: the firm's settings, and the email they open."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from inkfold.builder import Email, EmailBuilder, Footer
from inkfold.builder.containers import Container
from inkfold.builder.enums import SizeTheme
from inkfold.builder.exceptions import ValidationError
from inkfold.report import Report


@dataclass(frozen=True)
class House:
    """
    The firm a house template speaks for: one object a subclass sets once.

    ``disclaimer`` is HTML and closes every issue, emitted raw as
    ``Footer.disclaimer`` is; escaping untrusted text in it is the caller's job.
    ``theme`` and ``density`` are the builder's own names, checked when the
    email is built.
    """

    firm_name: str
    department: str = ""
    theme: str = "classic"
    density: str = SizeTheme.STANDARD
    disclaimer: str = ""
    unsubscribe_url: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.firm_name, str) or not self.firm_name.strip():
            raise ValidationError(f"House.firm_name is non-blank text, got: {self.firm_name!r}")


@dataclass(frozen=True)
class HouseEmail(Report):
    """
    A house email: an as-of date in, one issue out, in the firm's own settings.

    A subclass sets ``house`` and loads each input its template declares; it
    never builds a section. ``campaign`` names the series in the masthead.
    """

    house: ClassVar[House]
    campaign: ClassVar[str] = ""

    as_of: date

    def _validate(self) -> None:
        if not isinstance(getattr(type(self), "house", None), House):
            raise ValidationError(
                f"{type(self).__name__} sets `house = House(firm_name=...)`, "
                "the firm it speaks for."
            )

    def email(
        self, subject: str, preheader: str, date_range: str, sections: Sequence[Container]
    ) -> Email:
        """The issue: the house's masthead and footer around ``sections``."""
        house = self.house
        metadata = {
            "email_subject": subject,
            "preheader_text": preheader,
            "firm_name": house.firm_name,
            "campaign_name": self.campaign,
            "department": house.department,
            "date_range": date_range,
            "current_year": str(self.as_of.year),
            "theme": house.theme,
            "size_theme": house.density,
        }
        if house.unsubscribe_url:
            metadata["unsubscribe_url"] = house.unsubscribe_url
        builder = (
            EmailBuilder()
            .metadata(metadata)
            .footer(Footer(border=True, disclaimer=house.disclaimer))
        )
        for section in sections:
            builder.section(section)
        return builder.build()
