# Changelog

All notable changes to inkfold are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[semantic versioning](https://semver.org). The README's *Versions and deprecation* says how
long a deprecated public name survives.

## [Unreleased]

### Added

- **`Config.min_text_contrast`** (4.5, WCAG AA) and `inkfold.builder.filters.contrast_ratio`.
- **House email templates** (`inkfold.house`): `DailyNote`, `WeeklyWrap` and
  `ResearchAnnouncement`, reports a firm subclasses, sets `house = House(...)` on, and feeds by
  loading each declared input. Every figure is drawn in markup, so none needs an extra.
  `ResearchAnnouncement.message()` attaches its paper as a PDF rendered under `SCREEN`.
- **`required_input(kind, what)`** declares an input a template reads and its subclass loads; a
  report missing one is refused at construction, and a loader of the wrong type is named.
- **`inkfold.report.Report`**, a parameterised report: a frozen dataclass whose fields
  (an as-of date, a universe, a client) are validated at construction, and whose `build()`
  returns a `Renderable`, today a `Document`. A wrong type, a `bool` for an `int` or a
  `datetime` for a `date` raises `ValidationError` before `build()` runs.
- **`python -m inkfold.run report.py --as-of 2026-10-30`** builds a `Report` from the command
  line, writes its HTML and text parts to `output/` and runs the portability check, with
  `inkfold.check`'s exit codes. An unknown `--flag` is refused by name.
- The daily-note reference report is ported to a `Report` (`reference/daily-note/report.py`).
- **Declared data inputs** (`inkfold.report.data_input`): a loader returns its data `Dated`, and
  the report reads it as a `Dataset` with a name, a source and an as-of date. An input older
  than its `max_age` at the report's `as_of` raises `StaleDataError`, and one dated after it
  `FutureDataError`, both before anything renders; `python -m inkfold.run` loads every input
  before `build()` and exits 2 on either.
- **Provenance.** `DataTable`, `ChartBlock`, `FigureGrid` and every section take a `Dataset` (or
  several) as `source=`, printing the source line and its date from the data, and
  `Document.provenance()` lists each exhibit and section with the inputs it was drawn from.

### Changed

- **The masthead's muted type is lighter** (`text.on_dark_muted`: classic `#90A4AE` to `#BECAD0`,
  slate `#8FA0AE` to `#BEC8D0`), for the department, the date line and fine print on dark grounds.
  It read 4.24:1 on the classic navy, under WCAG AA; it is now 6.56:1.
- **A fill no theme type reads on is refused.** A section's `background_color`, with any
  `text_color` on it, and a solid `Callout`'s tone are refused when the section is added if their
  type reads under `Config.min_text_contrast`, naming the colour and both ratios (#503). It was
  accepted before; a mid-tone gold read at 3.4:1 in light mode and about 2.7:1 in dark mode.
- **An email no longer forces colours in dark mode.** It declared light only and also forced
  its frame and prose back to the light theme with `!important`, which left prose dark on the
  grounds Outlook.com and new Outlook darkened (#501). It now only declares
  `color-scheme: light only`: a client that honours it stays light, and one that darkens
  recolours everything together.
- **Outlook draws a hosted masthead photograph as the flat band.** A `Banner`'s
  `background_image_url` reaches classic Outlook's VML only when it is attached (`cid:`). A hosted
  one that did not load, and Outlook blocks remote pictures by default, left a broken-image
  placeholder over the masthead with its light title on white (#489). Every other client still
  draws the hosted photograph.
- **In classic Outlook the default masthead sits on the body's edge and ends with its copy.** Its
  title and subtitle began one `pad_x` further in than the body, its rule stopped short of the
  right padding, and 60 to 80px of empty band followed the date line (#490). The VML box now fits
  its copy with no inset, and the rule and date line pad from their own cells. Browsers render it
  pixel for pixel as before. `SpacingScale.masthead_vml_height` is no longer read; a scheme that sets it still
  builds.
- **A masthead's department keeps its line without a logo.** With no logo beside it, a
  `department` broke at every word in every client: "Global Equity" set on two lines in the
  house templates (#508). It now takes its own width when the row has room, in `Banner` and
  `MinimalBanner` alike. A desk name too long for the row still wraps, and now shares the row
  with the subtitle rather than setting one word a line beside it.
- **A wrapped figure floats in an email too.** `TextBlock(figure=...)` with a `wrap` side used to
  set the figure above the prose in an email; it now floats it, through a table's `align` and a
  CSS `float`, so the prose wraps beside it in Outlook and in browsers. On a phone it stacks above
  the prose as before.
- The `daily-investment-note` example is a `Report` with three declared inputs; its exhibits'
  source lines now carry their as-of date.

## [0.5.0] - 2026-11-09

The first public release, published to PyPI by trusted publishing from a version tag.

### Added

- **Four media from one section tree.** An `Email` checked against Gmail's 102 KB clipping
  limit and Outlook's Word engine; a `PagedDocument` with a cover, contents, running boxes and
  back matter; a folded `Brochure` imposed for the press with bleed and crop marks; and a `Deck`
  of slides with speaker notes.
- **The research apparatus**, numbered once in Python so every projection agrees: exhibit
  numbers, footnotes, contents, cross-references, lettered appendices, citations with a
  bibliography, and a glossary.
- **Exhibits for quantitative material**: `DataTable` with grouped heads, units, markers,
  decimal alignment and bars; charts, figure grids and legends; data at a glance without images
  (`BarList`, `Sparkline`, `HeroStat`); per-exhibit attribution and disclosure.
- **Three design axes**: colour themes, densities and typefaces, with per-object spacing.
- **Delivery**: MIME assembly with attachments and a 20 MB message budget, Gmail and Outlook
  send adapters that own no credentials, and a PDF exporter that makes no network requests.
- **Optional extras**, each behind its own install: `[pdf]`, `[data]`, `[charts]`, `[math]`,
  `[qr]` and `[outlook-desktop]`.
- **`python -m inkfold.check`**, the portability check, shipped with the package.
- **A release workflow**, `.github/workflows/release.yml`, which builds and checks both
  artefacts and publishes them on a version tag with no token stored anywhere.

### Changed

- **The project is named `inkfold`.** It was developed as `pyhermes`, a name Allegro's Hermes
  client holds on PyPI, then briefly renamed `octavo`, which PyPI prohibits. The import root
  was `svc` before that. Code written against any earlier name needs its imports changed to
  `inkfold`, and an environment variable set under an earlier prefix renamed to `INKFOLD_`.

### Deprecated

- `KpiStrip`. Use `CardGroup(cards, orientation="horizontal")`. Under the policy it may be
  removed from 0.7.0 onward, and no earlier than 2027-02-07.

[Unreleased]: https://github.com/RorySullivan1/inkfold/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/RorySullivan1/inkfold/releases/tag/v0.5.0
