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
- [ ] R2 Data tables on phones (teacher/admin/report tables): stacked rows or labelled cards; touch targets >= 44px
- [ ] R3 Per-page fixes found by the 375 / 768 / 1280 / 1920 sweep (heroes, grids, forms, modals, game/reading/activity screens)

## Route log
| Task | Route | Evidence | Commit |
|------|-------|----------|--------|
| R1 | delegated writer | CSS reasoning + 375px measurement | (this commit) |

## Next step
R2.
