# The client rendering matrix (roadmap v0.9.0)

What each email in the gallery looks like in each mail client, and who checked it. A result
is **OK**, **cosmetic** (readable, but off), or **broken** (content lost or unreadable), with
the issue that carries each defect.

## How each column is checked

| Client | How | Who |
|---|---|---|
| Classic Outlook (Windows) | `python -m qa.outlook_render`: each email in an unsaved message, Outlook's own Word editor exported to PDF, the message discarded. Needs Windows, classic Outlook, `[outlook-desktop]` and `[qa]` | a session on the owner's machine |
| New Outlook (Windows) | `python -m qa.send_gallery --save output/eml`, then right-click each file and choose Open with > Outlook (new); nothing is sent | the owner |
| Gmail web | the same send, to a Gmail inbox, in a desktop browser | the owner |
| Gmail app (iOS or Android) | the same Gmail inbox, in the app | the owner |
| Apple Mail (macOS or iOS) | the same send, to an iCloud or other inbox opened in Apple Mail | the owner |
| Dark mode | each of the four above with the client's dark theme on | the owner |

Set up with the repository's `environment.yml` (`conda env create -f environment.yml`, then
`conda activate inkfold`), from the repository root. It sends through Gmail's SMTP server from the `--from` account, signed in with a Google app
password it asks for at the prompt and never stores. Sending through classic Outlook
(`--via outlook`) is still there, but Outlook rewrites the HTML on the way out, so the inboxes
would judge its rewrite rather than inkfold's email. `qa.send_gallery` sends nothing without `--send`; without it, it lists what it would send.
Every subject starts `[inkfold gallery]`, so a filter can gather the run into one folder.

### What to answer for each email in a human-checked client

1. Every section is there, in order.
2. Columns sit side by side on a desktop and stack on a phone; nothing runs off the screen.
3. All text is readable: nothing dark on dark or light on light.
4. Attached images show inline. A hosted image from `cdn.example.com` cannot load anywhere and
   is not a finding; a hosted image the email depends on is.
5. Tables: headers, rules and aligned figures; coloured cells and arrows show.
6. In dark mode: the masthead and dark bands keep light text, and no figure disappears.

Record OK, cosmetic or broken in the client's column, and file each new defect as an issue.

## Results

Classic Outlook: 16.0.0.20527 on Windows 11 (10.0.26100), 2026-11-10. New Outlook: the owner,
from the `.eml` files, 2026-11-11: questions 1 to 5 good in every email, question 6 (dark mode)
broken, #501.
After #501 and #503 the owner accepted new Outlook in both modes on first open, 2026-11-11.
Its per-message light/dark toggle is a client defect (below), not counted against the email.
Gmail on the web, the Gmail app and Apple Mail: the owner, light and dark, 2026-11-11, every email OK. Page images are in
`.claude/context/evidence/v0.9.0/outlook-classic/`, with `run.json`.

Two defects are common to most emails, so they are listed once rather than in every row:

- **#490, fixed**: every email with the default `Banner` had its masthead copy inset past the
  body, its rule short of the right padding, and an empty band below it; only `minimal_banner`
  was free of it. Re-rendered in classic Outlook after the fix, the copy and rule sit on the
  body's edge and the band ends with the date line (`evidence/v0.9.0/490/`).
- **#508, fixed**: under a masthead with no logo the department wrapped at every word, in
  browsers too: "Global Equity" in the three house emails, `rich_table` and `aligned_layout`.
  Each now sets it on one line, in classic Outlook and in Chromium at 1000 and 375px
  (`evidence/v0.9.0/508/`).
- **#500**: an image that does not load shows its alt text in the client's default font, which
  on kitchen_sink's masthead is dark on dark. Its masthead background, logo and footer mark are
  hosted; since the owner's review they are served from this repository
  (`qa/fixtures/hosted/`, via `raw.githubusercontent.com`), so they load in a real inbox once
  the branch is on `main`. `image_matrix` keeps `cdn.example.com` for an image that never loads.
- **#501, dark mode**: the prose turned dark on the grounds new Outlook darkened. The skeleton
  forced it back to the light theme's type; the forcing is gone, and `tests/test_dark_mode.py`
  holds prose to AA under a model of the client's dark mode. To re-check in new Outlook, with
  an eye on `toned_layout`'s gold fact box and `rich_table`'s heat-scaled cells: mid-tone
  grounds the model cannot judge.
- **#503, the gold box**: the owner found `toned_layout`'s solid gold box hard to read in both
  modes. Its type read at 3.44:1 in light mode; a fill under 4.5:1 is now refused, and the box
  fills with a deep gold that takes white at 5.3:1 in either mode.
- **New Outlook's per-message light/dark toggle restores backgrounds but not text colours**
  (owner, 2026-11-11). After toggling, text keeps the other mode's colour: light text on a
  restored white page, or dark text on a navy band. It broke all five masthead variants tried
  (the current one, without its scrim, with one navy declaration, with `data-ogsc`/`data-ogsb`
  pinning rules, and a white masthead), light and dark alike, so it is the client's, not the
  email's. Judge dark mode by switching the app theme and opening the message afresh.
- **The masthead's muted line** (`on_dark_muted`) read 4.24:1 on the navy, under AA; it is now
  `#BECAD0`, 6.56:1. The dark-grey report that prompted it came from the toggle above.
- **By design, though it can look wrong**: a table bar sits under its figure (`data-table.md`),
  and a sparkline's bars are a fixed 4 px each, so a three-point series is about 16 px wide.
- **Wrapped figures float in an email too** since the owner's review: the prose wraps beside
  a wrapped image, chart or equation on a desktop, and the figure stacks above it on a phone.

| Email | Classic Outlook | New Outlook | Gmail web | Gmail app | Apple Mail | Dark mode |
|---|---|---|---|---|---|---|
| minimal | OK | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| kitchen_sink | #489 fixed; cosmetic #492 #493 #494 #496 #500 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| custom_banner | OK | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| custom_footer | OK | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| image_matrix | OK (its two hosted images point at a host that cannot load) | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| minimal_banner | cosmetic #494 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| minimal_footer | OK | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| no_header | OK | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| slate_theme | OK | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| compact_size | #489 fixed; cosmetic #492 #493 #494 #496 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| spacious_size | #489 fixed; cosmetic #491 #492 #493 #496 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| modern_fonts | #489 fixed; cosmetic #491 #492 #493 #496 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| rich_table | cosmetic #492 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| aligned_layout | OK | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| composed_layout | OK | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| surfaced_layout | cosmetic #494 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| research_note | cosmetic #491 #492 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| placed_layout | OK | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| glance_layout | OK | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| labelled_layout | cosmetic #491 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| organised_layout | cosmetic #494 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| toned_layout | cosmetic #491 #494 | OK; the gold box fixed, #503 | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| brief_layout | cosmetic #494 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| product_brief_layout | cosmetic #491 #494 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| house_daily_note | OK | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| house_weekly_wrap | cosmetic #494 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |
| house_announcement | cosmetic #494 | OK | OK | OK | OK | OK: new Outlook (first open), Gmail, Apple Mail |

`—` is not yet checked.

## The Outlook threads from memory, resolved here

| Thread | Result in classic Outlook | Evidence |
|---|---|---|
| `dir=rtl` on a reversed split | **Works**: the columns swap, the text inside reads left to right | `placed_layout-p1.jpg`, the first section and the label-value row |
| #319's VML trend arrow | **Works**: up, down and flat, each in its tone | `glance_layout-p1.jpg`, the KPI strip and the curve table |
| #399's connector | **Works**: a solid right-pointing arrow | `product_brief_layout-p1.jpg` |
| #325's square badge | **Works** | `labelled_layout-p1.jpg` |
| #325's status dot | **Fails**: a thin bar, #491 | `labelled_layout-p1.jpg`, the Status column |
| #331's empty rule cells (`font-size:0`) | **Works**: one continuous thin line | `organised_layout-p1.jpg`, the calendar |
| #337's legend swatch | **Fails**: a thin bar, #491 | `research_note-p2.jpg`, Exhibit 3 |

## Accessibility pass (email medium)

The gallery's markup was scanned, and each theme's text and ground pairs measured against WCAG AA.

- **Clean across all 27 emails**: a `lang` attribute, a `title`, alt text on every image, no
  empty or vague link text, no skipped heading level. Layout tables carry
  `role="presentation"` and data tables a header row, both already enforced by the lint.
- **#497**: six text-on-ground pairs fall below 4.5:1, among them the source lines (2.68:1 in
  classic) and the button labels (3.79:1 in classic). A palette decision, so it is the owner's.
- **#498**: no email has an `h1`, because the masthead title is not marked as a heading.
