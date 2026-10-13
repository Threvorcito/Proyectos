# Admin tables and dialogs from SistemaBodega

## Objective
Replace the look of the admin panel tables and dialogs (`/panel/admin/gestion/...`) with the table and dialog design used in `D:\SistemaBodega`, which the user prefers.

## Scope / constraints
- Source of truth for the look: `D:\SistemaBodega` (read-only; never edit it).
- Target: admin panel templates and CSS in this repo only. Behavior, forms, permissions, copy and URLs stay the same.
- Keep the responsive work from `odd/tasks/responsive-layout.md` (stacked tables on phones, 44px targets, fluid gutters).
- Branch: `fix/security-and-data-hardening`, separate commits.

## Tasks
- [x] B1 Port Bodega table styles/markup to admin resource tables
  - Source: `SistemaBodega/static/css/styles.css` (`.card`, `.toolbar`, `.search-control`, `.table-wrap.table-scroll-area`, `.data-table`, `.badge-*`, `.table-actions`, `.empty-state.compact`, `.btn*`), markup from `templates/catalogos/area_list.html`.
  - New `static/css/admin-ui.css`, scoped under `.admin-ui` (on `.admin-content` of `admin_resource_landing.html`): navy palette tokens, card + muted search toolbar, uppercase 12px sticky table head with rounded ends, 14px cells, pill badges for type/status, pinned actions column, dashed empty state. Phones keep `table-stack` + `data-label`, rendered as bordered row cards; coarse pointers keep 44px targets. Table min-width 880 -> 760px (no sideways scroll at 1280).
  - Check: dashboard tests 122 OK; 1280 usuarios page renders, wrap 842 >= table 760.
- [ ] B2 Port Bodega dialog (modal) styles/markup/JS to admin create/edit/delete dialogs
- [ ] B3 Verify at 375 / 768 / 1280 / 1920; tests green

## Route log
| Task | Route | Evidence | Commit |
|------|-------|----------|--------|
| B1 | delegated writer | Bodega CSS/markup read, 1280 render | (this commit) |

## Next step
B2.
