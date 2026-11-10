"""The house research announcement: a paper's summary in the email, the paper itself attached."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from email.message import EmailMessage
from typing import TYPE_CHECKING, Any, ClassVar

from inkfold.builder import AuthorBlock, Email, FullWidth, TextBlock
from inkfold.builder.components import Component
from inkfold.builder.composition import Stack
from inkfold.builder.containers import Container
from inkfold.builder.filters import escape_html
from inkfold.builder.provenance import format_date
from inkfold.builder.surfaces import Button, Callout
from inkfold.inputs import required_input
from inkfold.report import Renderable

from ._base import HouseEmail
from .models import Paper

if TYPE_CHECKING:
    from inkfold.pdf.profile import PdfProfile


@dataclass(frozen=True)
class ResearchAnnouncement(HouseEmail):
    """
    A new research report, announced: its summary and key points in the email, its PDF attached.

    Subclass it, set ``house``, and load ``paper`` (a :class:`Paper`) with
    ``@data_input``; the paper's as-of date is its publication date. ``build()``
    is the email; :meth:`message` is the email with the paper rendered to PDF
    under ``SCREEN`` and attached, inside the 20 MB message budget. Rendering
    the PDF needs the ``[pdf]`` extra; the email alone needs nothing.
    """

    campaign: ClassVar[str] = "New Research"

    paper = required_input(Paper, "the report to announce, with the document to attach")

    def build(self) -> Renderable:
        paper = self.paper.value
        sections: list[Container] = [
            FullWidth(title=paper.title, content=TextBlock(paper.summary), source=self.paper),
            FullWidth(title="Key Points", content=TextBlock(_points(paper.key_points))),
            FullWidth(title="Authors", content=_authors(paper)),
            FullWidth(content=_attached(paper)),
        ]
        return self.email(
            subject=f"{self.campaign}: {paper.title}",
            preheader=paper.key_points[0],
            date_range=f"Published {format_date(self.paper.as_of)}",
            sections=sections,
        )

    def message(
        self,
        *,
        sender: str,
        to: str | Sequence[str],
        profile: PdfProfile | None = None,
        **kwargs: Any,
    ) -> EmailMessage:
        """
        The email as a MIME message, the paper attached as a PDF rendered under ``profile``.

        ``profile`` defaults to ``SCREEN``; ``kwargs`` reach ``build_message``.

        Raises:
            MessageError: When the message is over the 20 MB budget.
            BackendMissingError: Without the ``[pdf]`` extra.
        """
        from inkfold.delivery import build_message
        from inkfold.pdf import SCREEN, pdf_attachment

        paper = self.paper.value
        email = self.build()
        assert isinstance(email, Email)
        attachment = pdf_attachment(paper.document, paper.filename, profile or SCREEN)
        return build_message(email, sender=sender, to=to, attachments=[attachment], **kwargs)


def _points(points: Sequence[str]) -> str:
    """The key points as a list, each escaped: they are plain text."""
    return "<ul>" + "".join(f"<li>{escape_html(point)}</li>" for point in points) + "</ul>"


def _authors(paper: Paper) -> Component:
    blocks = [AuthorBlock(a.name, job_title=a.job_title, email=a.email) for a in paper.authors]
    return blocks[0] if len(blocks) == 1 else Stack(blocks)


def _attached(paper: Paper) -> Component:
    """Where the full report is: attached, and online when the paper has a link."""
    note = TextBlock(
        f"<p>The full report is attached as <strong>{escape_html(paper.filename)}</strong>.</p>"
    )
    held: Component = Stack([note, Button("Read online", paper.url)]) if paper.url else note
    return Callout(held, label="The full report")
