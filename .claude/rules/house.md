---
paths:
  - "inkfold/house/**"
  - "inkfold/inputs.py"
  - "inkfold/report.py"
  - "qa/fixtures/house_*.py"
  - "qa/fixtures/_house.py"
  - "tests/test_house.py"
---

# The house templates — reports a firm subclasses and feeds (roadmap v0.8.0)

`inkfold.house` ships three standard emails as `Report`s: `DailyNote`, `WeeklyWrap` and
`ResearchAnnouncement`. A firm subclasses one, sets `house = House(firm_name=...)` once, and
loads each input the template declares with `@data_input`. It never builds a section.

| Template | Inputs it reads | Sections |
|---|---|---|
| `DailyNote` | `book: Book`, `sectors: Sectors`, `commentary: Commentary` | three cards, markets, the attribution table, sectors as a `BarList`, positioning |
| `WeeklyWrap` | `book: WeekBook`, `markets: Markets`, `commentary`, `calendar: Calendar` | four cards (the week's active card carries a trend), review, markets table, outlook, the week ahead as a `Timeline` |
| `ResearchAnnouncement` | `paper: Paper` | summary, key points, authors, a callout naming the attachment; `message()` attaches the PDF |

## Decisions (the owner's, 2026-11-09)

- **The templates ship in the package**, not under `reference/` or `examples/`, so Gate 1's
  outside user runs one unchanged from `pip install inkfold`. They are public API under the
  deprecation policy.
- **A firm supplies data by writing loaders**, not by a data file. A file schema would overlap
  roadmap 3.1, which is where the schema belongs.

## How a template declares what it reads

- **`required_input(kind, what)`** (`inkfold/inputs.py`) declares an input without a loader. A
  class that still holds one cannot be constructed: `Report.__post_init__` names every missing
  input and what it is. A subclass's `@data_input` of the same name replaces it and inherits
  its `kind` in `Input.__set_name__`, so a loader returning the wrong type is named at load.
- **`kind` is a concrete class.** mypy refuses an abstract `Sequence` as `type[T]`, so lists
  are wrapped: `Sectors`, `Markets`, `Calendar`. Each wrapper is also where the list is checked.
- **The data shapes validate at construction** (`house/models.py`): every number finite, a
  `Book`'s named holdings at most 100%, a calendar in date order, a paper's file a bare `.pdf`.

## Why each template looks as it does

- **No pictures.** Every figure is drawn in markup (`CardGroup`, `BarList`, a card's `trend`,
  `Timeline`), so the templates need no extra, attach no image, and read with images blocked,
  Outlook desktop's default. The worked daily-note example draws matplotlib charts; the house
  one deliberately does not.
- **One column throughout**, as the example argues: nothing collapses at 375px.
- **Sizes at their fixtures**: daily note 32.9 KB, weekly wrap 26.7 KB, announcement 14.2 KB,
  all far under the 90 KB warning; `TestEachTemplateInTheGallery` holds each under it.
- **Commentary is an input too**, dated and checked for freshness like the figures, so a
  stale paragraph is refused with the data. Its prose is HTML, raw as a `TextBlock`'s is.
- **`current_year` is the report's `as_of` year**, never the clock, so the goldens hold.
- **Dates read in English whatever the locale**: `format_date`, and `_short` for the week ahead.
- **The announcement's PDF is rendered under `SCREEN`** by `message()`, through
  `pdf_attachment` and `build_message`, so the 20 MB budget is the message's own check. The
  email alone needs nothing; the PDF needs `[pdf]`, and its test skips naming it.

## The fixtures

`house_daily_note`, `house_weekly_wrap` and `house_announcement` join `all_fixtures()`, each a
subclass of its template with constants for loaders (`qa/fixtures/_house.py` holds the firm
and the close, a Friday). Each has an email golden. The announcement attaches the paged
gallery's `a4_research_note`.
