"""A figure's source and as-of date, from a dataset into the document (roadmap v0.7.0)."""

from __future__ import annotations

import locale
from datetime import date
from pathlib import Path

import pytest

from inkfold.builder import (
    ChartBlock,
    DataTable,
    EmailBuilder,
    FullWidth,
    ImageBlock,
    TextBlock,
)
from inkfold.builder.exceptions import ValidationError
from inkfold.builder.exhibits import FigureGrid
from inkfold.builder.models import TableRow
from inkfold.builder.provenance import Dataset, Provenance, format_date, resolve_source
from inkfold.config import get_config

PNG = "https://example.com/chart.png"
SEP = get_config().exhibit_separator
PRICES = Dataset("prices", "House PMS", date(2026, 10, 8), [1.0])
RISK = Dataset("risk", "Risk system", date(2026, 10, 8), {})
FLOWS = Dataset("flows", "Desk", date(2026, 10, 7), 0)


class TestTheDataset:
    def test_a_datetime_is_refused(self):
        from datetime import datetime

        with pytest.raises(ValidationError, match="a datetime"):
            Dataset("prices", "House PMS", datetime(2026, 10, 8, 16, 0), [])  # type: ignore[arg-type]

    def test_a_blank_source_is_refused(self):
        with pytest.raises(ValidationError, match="source"):
            Dataset("prices", " ", date(2026, 10, 8), [])

    def test_its_value_is_not_compared(self):
        assert Dataset("p", "S", date(2026, 10, 8), [1]) == Dataset(
            "p", "S", date(2026, 10, 8), [2]
        )


class TestTheDate:
    def test_the_house_form(self):
        assert format_date(date(2026, 10, 8)) == "8 October 2026"

    def test_it_ignores_the_locale(self):
        before = locale.setlocale(locale.LC_TIME)
        try:
            for name in ("de_DE.UTF-8", "German_Germany.1252", "fr_FR.UTF-8"):
                try:
                    locale.setlocale(locale.LC_TIME, name)
                    break
                except locale.Error:
                    continue
            else:
                pytest.skip("no non-English locale is installed to set")
            assert format_date(date(2026, 3, 1)) == "1 March 2026"
        finally:
            locale.setlocale(locale.LC_TIME, before)


class TestResolvingASource:
    def test_text_passes_through(self):
        assert resolve_source("Bloomberg", "1 May", "X") == ("Bloomberg", "1 May", ())

    def test_one_dataset_prints_its_source_and_date(self):
        assert resolve_source(PRICES, None, "X") == ("House PMS", "8 October 2026", (PRICES,))

    def test_two_of_one_date_share_it(self):
        assert resolve_source([PRICES, RISK], None, "X")[:2] == (
            "House PMS; Risk system",
            "8 October 2026",
        )

    def test_one_source_twice_is_named_once(self):
        twin = Dataset("closes", "House PMS", date(2026, 10, 8), [])
        assert resolve_source([PRICES, twin], None, "X")[0] == "House PMS"

    def test_two_dates_date_each_source(self):
        assert resolve_source([PRICES, FLOWS], None, "X")[:2] == (
            "House PMS as of 8 October 2026; Desk as of 7 October 2026",
            "",
        )

    def test_a_holder_with_no_date_field_folds_it_in(self):
        assert resolve_source(PRICES, None, "X", dated=False)[:2] == (
            "House PMS as of 8 October 2026",
            "",
        )

    def test_a_typed_date_may_not_contradict_the_data(self):
        with pytest.raises(ValidationError, match="carries its own date"):
            resolve_source(PRICES, "9 October 2026", "DataTable")

    @pytest.mark.parametrize("bad", [[], [PRICES, "Bloomberg"], 3])
    def test_anything_else_is_refused(self, bad):
        with pytest.raises(ValidationError, match="plain text, or Datasets"):
            resolve_source(bad, None, "DataTable")


def _table(source) -> DataTable:
    return DataTable(
        ["Name", "Price"],
        [TableRow(cells=["A", 1.0])],
        source=source,
        caption="Prices",
        label="Exhibit",
    )


def _document(*sections):
    builder = EmailBuilder().metadata(
        {"email_subject": "s", "firm_name": "f", "campaign_name": "c"}
    )
    for section in sections:
        builder.section(section)
    return builder.build()


class TestTheDocumentListsItsProvenance:
    def test_every_holder_in_reading_order_with_the_sections_line_last(self):
        grid = FigureGrid(
            [
                ChartBlock(PNG, alt_text="a"),
                ImageBlock(PNG, alt_text="b"),
            ],
            caption="Flows",
            source=FLOWS,
        )
        document = _document(
            FullWidth(title="Holdings", content=_table([PRICES, RISK]), source=PRICES),
            FullWidth(title="Flows", content=grid),
            FullWidth(title="Prose", content=TextBlock("<p>words</p>")),
        )
        assert document.provenance() == [
            Provenance(f"Exhibit 1{SEP}Prices", "prices", "House PMS", date(2026, 10, 8)),
            Provenance(f"Exhibit 1{SEP}Prices", "risk", "Risk system", date(2026, 10, 8)),
            Provenance("Holdings", "prices", "House PMS", date(2026, 10, 8)),
            Provenance(f"Exhibit 2{SEP}Flows", "flows", "Desk", date(2026, 10, 7)),
        ]

    def test_a_document_with_no_datasets_lists_nothing(self):
        assert _document(FullWidth(content=_table("Bloomberg"))).provenance() == []

    def test_the_source_line_reaches_both_projections(self):
        document = _document(
            FullWidth(title="Holdings", content=TextBlock("<p>x</p>"), source=PRICES)
        )
        assert "House PMS as of 8 October 2026" in document.render()
        assert "House PMS as of 8 October 2026" in document.text()

    def test_a_slide_keeps_text_only_sources(self):
        from inkfold.deck import Slide

        with pytest.raises(ValidationError, match="plain text"):
            Slide([FullWidth(content=TextBlock("<p>x</p>"))], title="Title", source=PRICES)


class TestTheDailyNote:
    """The reference report's every exhibit is traced to its input (the v0.7.0 card)."""

    def test_its_provenance(self, monkeypatch):
        pytest.importorskip("matplotlib", reason='the daily note plots with "inkfold[charts]"')
        monkeypatch.chdir(Path(__file__).resolve().parent.parent)
        from qa.reference import example

        note = example("daily-investment-note")
        document = note.DailyNote(as_of=date(2026, 10, 9)).build()
        close = date(2026, 10, 8)
        source = "Hermes Research; illustrative sample data"
        assert document.provenance() == [
            Provenance("Cumulative total return, last 20 sessions", "performance", source, close),
            Provenance("Contribution to return, 8 October 2026", "book", source, close),
            Provenance("Contribution to return by sector, bps", "sectors", source, close),
        ]
