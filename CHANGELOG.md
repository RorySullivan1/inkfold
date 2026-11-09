# Changelog

All notable changes to inkfold are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[semantic versioning](https://semver.org). The README's *Versions and deprecation* says how
long a deprecated public name survives.

## [Unreleased]

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
