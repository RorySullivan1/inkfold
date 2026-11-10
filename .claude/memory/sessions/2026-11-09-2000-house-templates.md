# 2026-11-09 20:00 · house-templates

**Goal:** Build roadmap v0.8.0: three house email templates as parameterised products

## What happened
- Owner decided (asked this session): the templates ship in the package as `inkfold.house`, and a
  firm supplies data by subclassing and writing `@data_input` loaders, not by a data file.
- `required_input(kind, what)` in `inkfold/inputs.py`: a template declares what it reads; a class
  still holding one is refused at construction naming every missing input, and the subclass's
  loader inherits `kind`, so a wrong type is named at load.
- `inkfold/house/`: `House`, `HouseEmail`, `DailyNote`, `WeeklyWrap`, `ResearchAnnouncement`, and
  the data shapes in `models.py`. Every figure drawn in markup; no extra needed.
  `ResearchAnnouncement.message()` attaches the paper as a SCREEN PDF via `build_message`.
- Fixtures `house_daily_note`, `house_weekly_wrap`, `house_announcement` with email goldens:
  32.9, 26.7 and 14.2 KB. Rules in `.claude/rules/house.md`, routed from CLAUDE.md.
- Full suite 5,480 passed, 487 skipped.

## Gotchas & dead ends
- mypy refuses an abstract `Sequence` as `type[T]`, so list inputs are wrapped (`Sectors`,
  `Markets`, `Calendar`).
- WeasyPrint cannot load here (no GTK on this Windows machine), so the 20 MB attachment test
  skips locally; CI's all-extras job runs it.
- The v0.8.0 branch was cut from the v0.7.0-shipped bookkeeping branch (PR #486).

## State at end
- v0.8.0 in a PR; card in-progress until it merges.

## Open threads
- The 2.1 content-model spike was approved to start before v0.8.0 lands; not started.
