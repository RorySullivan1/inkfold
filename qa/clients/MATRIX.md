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

Classic Outlook: 16.0.0.20527 on Windows 11 (10.0.26100), 2026-11-10. Page images are in
`.claude/context/evidence/v0.9.0/outlook-classic/`, with `run.json`.

Two defects are common to most emails, so they are listed once rather than in every row:

- **#490**: every email with the default `Banner` has its masthead copy inset past the body,
  and an empty band below it. Only `minimal_banner` is free of it.
- **#500**: an image that does not load shows its alt text in the client's default font, which
  on kitchen_sink's masthead is dark on dark. Its masthead background, logo and footer mark are
  hosted; since the owner's review they are served from this repository
  (`qa/fixtures/hosted/`, via `raw.githubusercontent.com`), so they load in a real inbox once
  the branch is on `main`. `image_matrix` keeps `cdn.example.com` for an image that never loads.
- **By design, though it can look wrong**: a table bar sits under its figure (`data-table.md`),
  and a sparkline's bars are a fixed 4 px each, so a three-point series is about 16 px wide.
- **Wrapped figures float in an email too** since the owner's review: the prose wraps beside
  a wrapped image, chart or equation on a desktop, and the figure stacks above it on a phone.

| Email | Classic Outlook | New Outlook | Gmail web | Gmail app | Apple Mail | Dark mode |
|---|---|---|---|---|---|---|
| minimal | OK | — | — | — | — | — |
| kitchen_sink | **broken** #489; cosmetic #492 #493 #494 #496 #500 | — | — | — | — | — |
| custom_banner | OK | — | — | — | — | — |
| custom_footer | OK | — | — | — | — | — |
| image_matrix | OK (its two hosted images point at a host that cannot load) | — | — | — | — | — |
| minimal_banner | cosmetic #494 | — | — | — | — | — |
| minimal_footer | OK | — | — | — | — | — |
| no_header | OK | — | — | — | — | — |
| slate_theme | OK | — | — | — | — | — |
| compact_size | **broken** #489; cosmetic #492 #493 #494 #496 | — | — | — | — | — |
| spacious_size | **broken** #489; cosmetic #491 #492 #493 #496 | — | — | — | — | — |
| modern_fonts | **broken** #489; cosmetic #491 #492 #493 #496 | — | — | — | — | — |
| rich_table | cosmetic #492 | — | — | — | — | — |
| aligned_layout | OK | — | — | — | — | — |
| composed_layout | OK | — | — | — | — | — |
| surfaced_layout | cosmetic #494 | — | — | — | — | — |
| research_note | cosmetic #491 #492 | — | — | — | — | — |
| placed_layout | OK | — | — | — | — | — |
| glance_layout | OK | — | — | — | — | — |
| labelled_layout | cosmetic #491 | — | — | — | — | — |
| organised_layout | cosmetic #494 | — | — | — | — | — |
| toned_layout | cosmetic #491 #494 | — | — | — | — | — |
| brief_layout | cosmetic #494 | — | — | — | — | — |
| product_brief_layout | cosmetic #491 #494 | — | — | — | — | — |
| house_daily_note | OK | — | — | — | — | — |
| house_weekly_wrap | cosmetic #494 | — | — | — | — | — |
| house_announcement | cosmetic #494 | — | — | — | — | — |

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
