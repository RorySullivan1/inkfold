# 2026-11-09 09:00 · inkfold-rename

**Goal:** Rename octavo to inkfold (roadmap v0.4.1) after PyPI refused octavo, through advance-roadmap-step

## What happened
- PR #479 (rename to octavo) merged, and the owner renamed the repository to octavo. Registering
  `octavo` on PyPI as a pending trusted publisher failed: "not allowed". No look-alike project
  exists and it is not a stdlib name, so it is on PyPI's prohibited list, which is not public.
- The owner chose a distinct coined name. `pyinky` was considered and advised against (ZURB's Inky
  is an email templating language; Pimoroni ships `inky` on PyPI). PyPI accepted `inkfold` as a
  pending publisher first; the owner then renamed the repository to RorySullivan1/inkfold.
- v0.4.1 repeated v0.4.0's scripted rename (2,394 replacements, 316 files), with hand edits to
  memory's State and Threads, the roadmap's stage and milestone text, and two history sentences.
- Review: no must-fix; took four optional findings (code forms never exempt, .meta/version exempt
  only while it holds a rename card, shipped only by the status header, README migration note,
  superseded records). Audit: PASS; v0.5.0's card now pins the publisher values. PR #480.

## Gotchas & dead ends
- A free name on PyPI's JSON API can still be refused: test a candidate on the pending-publisher
  form before renaming anything. A pending publisher reserves nothing until the first upload.
- The session's GitHub tools keep working through the repository's redirects (old names resolve).
- An exemption keyed on "the line names the new name" hides code forms; check code forms first.

## State at end
- PR #480 open; cursor v0.5.0 (the first release, by trusted publishing, as release.yml / pypi).

## Open threads
- On merge: flip v0.4.1 to shipped.
- v0.5.0 must match the pending publisher exactly; the first upload is what claims the name.
