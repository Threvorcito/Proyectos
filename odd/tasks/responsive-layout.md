# Responsive layout

## Objective
Make every page adapt cleanly to phone (360-430px), laptop (1280-1440px) and large desktop (1920px+), with consistent page margins and spacing.

## Evidence (2026-10-13, before)
- No horizontal page scroll at 375px on /, /panel/docente/, /juegos/, /cuentas/estudiantes/.
- Side gutters are Bootstrap's default 12px at every width: cramped on phones, and content ends at a hard 1320px container on desktops.
- Teacher dashboard table (`teacher-table`) is 605px wide at 375px (inner scroll, columns hidden off-screen).
- Pages mix several ad-hoc section paddings in `static/css/main.css`.

## Scope / constraints
- Branch: `fix/security-and-data-hardening` (continue; separate commits).
- Refinement, not redesign: keep identity, colors, fonts, copy and behavior.
- Main files: `static/css/main.css`, `templates/**`.

## Tasks
- [x] R1 Fluid gutter + container tokens (phone/laptop/desktop), section spacing scale, applied globally
  - Tokens on `:root` (`--page-gutter`, `--page-max`, `--page-max-narrow`, `--measure`, `--section-space-*`, `--touch-target`); `.container` uses them so navbar, sections and footer share one edge; top-level `py-4`/`py-5` containers map to the fluid rhythm; admin content/topbar and home bands consolidated onto the tokens.
  - Check: 375px home -> gutter 16px (navbar 16px), section padding 32px, scrollWidth 375.
- [x] R2 Data tables on phones (teacher/admin/report tables): stacked rows or labelled cards; touch targets >= 44px
  - 14 tables (teacher dashboard/students, student report, lesson plan list/report, profile, admin resources) get `table-stack` + `data-label` per cell; below 640px rows become labelled blocks. Coarse pointers get 44px buttons, nav links, dropdown items, form controls and close buttons; form text 16px.
  - Check: 375px teacher table 592px -> 341px (fits card), scrollWidth 375, no `.btn` under 44px. The running server caches templates, so labels were emulated in-page with identical markup.
- [x] R3 Per-page fixes found by the 375 / 768 / 1280 / 1920 sweep (heroes, grids, forms, modals, game/reading/activity screens)
  - Sweep (srcdoc iframes at 375, 812x375 landscape, 768, 1280, 1920; anonymous, student, teacher and admin sessions; ~30 URLs): horizontal overflow 0px everywhere except `/panel/docente/alumnos/` at 768 (16px, nowrap headers on the 7-column table).
  - Fixes: teacher-table headers wrap and cells tighten at 576-991px; kid choice cards on tablets move the action pill under the text (text column was ~120px); learning-compass tips use auto-fit instead of a fixed 3 columns.
  - Confirm: alumnos at 640/768/900 -> 0px overflow; student dashboard text column no longer squeezed at 768. Modals (create student, create plan, admin edit resource) fit at 375 and 812x375 (8px side margins).
  - Tests: `DB_ENGINE=sqlite python manage.py test` -> 206 OK.
  - Detector: 18 findings, all pre-existing colour/decoration choices (low-contrast, side-tab, border accent, icon tile) or a false positive (edge-to-edge table card); none introduced by this work, left out of scope.
  - Not covered: drawings key page (needs a selected student in session), real-device touch testing.

## Route log
| Task | Route | Evidence | Commit |
|------|-------|----------|--------|
| R1 | delegated writer | CSS reasoning + 375px measurement | af7c57c |
| R2 | delegated writer | scripted data-label insertion (header count asserted per row) + 375px measurement | 15384e4 |
| R3 | delegated writer | iframe sweep, one fix batch, one confirm round | (this commit) |

## Next step
Done. Optional: contrast follow-up for detector findings on home/admin/404.
