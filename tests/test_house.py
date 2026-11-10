"""The house email templates (roadmap v0.8.0): reports a firm subclasses and feeds."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pytest

from inkfold.builder.exceptions import ValidationError
from inkfold.config import get_config
from inkfold.house import (
    Book,
    Calendar,
    CalendarEvent,
    DailyNote,
    Holding,
    House,
    Paper,
    ResearchAnnouncement,
    WeeklyWrap,
)
from inkfold.house.weekly_wrap import _short
from inkfold.report import Dated, data_input
from inkfold.run.__main__ import EXIT_OK, main
from qa.fixtures import all_fixtures
from qa.fixtures._house import CLOSE, HOUSE
from qa.fixtures.house_announcement import SampleAnnouncement
from qa.fixtures.house_daily_note import SampleNote
from qa.fixtures.house_weekly_wrap import SampleWrap

TEMPLATES = ("house_daily_note", "house_weekly_wrap", "house_announcement")


class TestATemplateIsFedNotBuilt:
    @pytest.mark.parametrize(
        ("template", "inputs"),
        [
            (DailyNote, "book.*sectors.*commentary"),
            (WeeklyWrap, "book.*markets.*commentary.*calendar"),
            (ResearchAnnouncement, "paper"),
        ],
    )
    def test_a_subclass_with_no_loaders_names_every_input(self, template, inputs):
        @dataclass(frozen=True)
        class Bare(template):
            house = HOUSE

        with pytest.raises(ValidationError, match=f"must load each input.*{inputs}"):
            Bare(as_of=CLOSE)

    def test_a_subclass_with_no_house_is_refused(self):
        @dataclass(frozen=True)
        class Homeless(SampleNote):
            house = None  # type: ignore[assignment]

        with pytest.raises(ValidationError, match="House"):
            Homeless(as_of=CLOSE)

    def test_a_loader_of_the_wrong_kind_is_named(self):
        @dataclass(frozen=True)
        class Wrong(SampleNote):
            @data_input(source="X", max_age=timedelta(days=1))
            def book(self) -> Dated[Book]:
                return Dated({"portfolio": "x"}, CLOSE)  # type: ignore[arg-type]

        with pytest.raises(
            ValidationError, match="'book' returned dict; the template reads a Book"
        ):
            Wrong(as_of=CLOSE).load()

    def test_stale_data_is_refused_before_the_email(self):
        from inkfold.report import StaleDataError

        with pytest.raises(StaleDataError):
            SampleWrap(as_of=CLOSE + timedelta(days=10)).load()

    def test_the_templates_ship_in_the_package(self):
        import inkfold.house

        assert Path(inkfold.house.__file__).resolve().parent.parent.name == "inkfold"


class TestEachTemplateInTheGallery:
    @pytest.mark.parametrize("name", TEMPLATES)
    def test_it_is_under_the_size_warning(self, name):
        html = all_fixtures()[name]().render()
        assert len(html.encode("utf-8")) < get_config().size_warn_kb * 1024

    def test_every_exhibit_of_the_daily_note_is_traced(self):
        where = [(p.where, p.dataset) for p in SampleNote(as_of=CLOSE).build().provenance()]
        assert where == [
            ("The Day in Brief", "book"),
            ("Contribution to return", "book"),
            ("By Sector", "sectors"),
        ]

    def test_every_exhibit_of_the_weekly_wrap_is_traced(self):
        where = [(p.where, p.dataset) for p in SampleWrap(as_of=CLOSE).build().provenance()]
        assert where == [
            ("The Week in Brief", "book"),
            ("Markets over the week", "markets"),
            ("The Week Ahead", "calendar"),
        ]

    def test_an_empty_calendar_leaves_the_week_ahead_out(self):
        @dataclass(frozen=True)
        class Quiet(SampleWrap):
            @data_input(source="Desk", max_age=timedelta(days=3))
            def calendar(self) -> Dated[Calendar]:
                return Dated(Calendar(()), CLOSE)

        assert "The Week Ahead" not in Quiet(as_of=CLOSE).build().text()

    def test_the_key_points_are_escaped(self):
        @dataclass(frozen=True)
        class Marked(SampleAnnouncement):
            @data_input(source="Publishing", max_age=timedelta(days=3))
            def paper(self) -> Dated[Paper]:
                paper = SampleAnnouncement(as_of=CLOSE).paper.value
                points = ("Rates < 5% <script>",)
                return Dated(
                    Paper(
                        paper.title,
                        paper.summary,
                        points,
                        paper.authors,
                        paper.document,
                        paper.filename,
                    ),
                    CLOSE,
                )

        html = Marked(as_of=CLOSE).build().render()
        assert "<script>" not in html and "Rates &lt; 5% &lt;script&gt;" in html


class TestTheAnnouncementsMessage:
    def test_it_carries_the_paper_as_a_screen_pdf_inside_the_budget(self):
        from inkfold.pdf import available

        if not available():
            pytest.skip('rendering the paper needs the "[pdf]" extra')
        message = SampleAnnouncement(as_of=CLOSE).message(
            sender="research@example.com", to="client@example.com"
        )
        parts = [p for p in message.walk() if p.get_content_type() == "application/pdf"]
        assert [p.get_filename() for p in parts] == ["momentum-after-the-rate-peak.pdf"]
        assert len(message.as_bytes()) < get_config().attachment_limit_kb * 1024


class TestTheData:
    def test_a_book_over_its_whole_weight_is_refused(self):
        with pytest.raises(ValidationError, match="over 100%"):
            Book("P", "B", 1.0, 1.0, (Holding("A", 80, 1.0),), (Holding("B", 30, 1.0),))

    def test_a_calendar_runs_in_date_order(self):
        with pytest.raises(ValidationError, match="date order"):
            Calendar(
                (CalendarEvent(date(2026, 11, 10), "b"), CalendarEvent(date(2026, 11, 9), "a"))
            )

    def test_a_paper_attaches_a_bare_pdf_name(self):
        paper = SampleAnnouncement(as_of=CLOSE).paper.value
        with pytest.raises(ValidationError, match="bare name ending .pdf"):
            Paper(paper.title, paper.summary, ("a",), paper.authors, paper.document, "x/y.pdf")

    def test_a_house_names_its_firm(self):
        with pytest.raises(ValidationError, match="firm_name"):
            House(firm_name=" ")

    def test_a_day_in_the_week_ahead_reads_in_english(self):
        assert _short(date(2026, 11, 9)) == "Mon 9 Nov"


class TestARunFromAFirmsOwnFile:
    def test_a_subclass_in_its_own_file_runs(self, tmp_path: Path):
        script = tmp_path / "our_note.py"
        script.write_text(
            textwrap.dedent("""\
                from dataclasses import dataclass
                from qa.fixtures.house_daily_note import SampleNote

                @dataclass(frozen=True)
                class OurNote(SampleNote):
                    pass
            """),
            encoding="utf-8",
        )
        code = main([str(script), "--as-of", "2026-11-09", "--out", str(tmp_path / "out")])
        assert code == EXIT_OK
        assert "Close of 9 November 2026" in (tmp_path / "out" / "our_note.txt").read_text(
            encoding="utf-8"
        )
