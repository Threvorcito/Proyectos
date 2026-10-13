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
- [x] B2 Port Bodega dialog (modal) styles/markup/JS to admin create/edit/delete dialogs
  - Source: `SistemaBodega/templates/components/modal_form.html`, `catalogos/partials/catalogo_delete_dialog.html`, `static/js/app.js` (native `<dialog>` + `showModal`, `data-modal-open` / `data-dialog-close`, closing animation via data attribute, focus return), CSS `.dialog-root/.dialog-content/.dialog-header/.dialog-body/.dialog-footer/.dialog-close`, `.confirm-dialog-body`.
  - Bootstrap modals on `admin_resource_landing.html` (create, edit, teacher permissions, create-teacher permissions) became native `<dialog data-aui-dialog>` with Bodega header/body/footer; native `confirm()` on delete became a Bodega confirm dialog (same copy, same POST + CSRF). New `static/js/admin-ui.js`: open/close, Escape + backdrop close (blocked while submitting; backdrop needs press and release outside), initial focus on first field (Cancel on delete), focus returns to trigger, nested permissions dialog stacks over create. Cleanup runs after `dialog.close()` directly because the queued `close` event did not fire in the throttled preview pane.
  - Validation errors: unchanged server flow (invalid create/edit renders `admin_resource_form.html`); that page now uses the Bodega form card under `.admin-ui`.
  - Phones (<640px): dialogs take the screen with 8px margins, footer buttons share the row; coarse pointers get a 44px close button.
  - Check: dashboard tests 122 OK; scripted at 1280 on usuarios/profesores: create/edit/permissions/delete open, Escape/backdrop/close/Listo close, Escape ignored while submitting, focus back to trigger, scroll lock released.
- [x] B3 Verify at 375 / 768 / 1280 / 1920; tests green
  - Sweep (srcdoc iframes, admin session; usuarios, profesores, actividades, lecturas; create, edit and delete dialogs opened at each width): page overflow 0px at every width. Dialog panels inside the viewport everywhere (375: 13px margins, 772px tall with body scroll; 768+: centred), no sideways scroll inside dialog bodies. 375: stacked rows 318px in a 375 page, smallest button 44px (coarse pointer).
  - Fix batch: (1) actividades table 1119px wide at 1280 -> description clamps to two wrapped lines, title/description caps in `ch`; (2) action buttons broke mid-word ("E di ta r") -> actions column nowrap, sized to its buttons; (3) phone labels overlapped values because desktop cell padding outranked `table-stack` -> label column re-asserted in the phone rule.
  - Confirm: 1280 actividades 812/827 (15px inner scroll with pinned actions, page 0px), usuarios/profesores/lecturas no inner scroll; 1920 no inner scroll; 375 label column 143px, page 375. Screenshots at 1280 (edit dialog) and 375 (stacked rows).
  - Tests: `DB_ENGINE=sqlite python manage.py test` -> 206 OK.
  - Detector (`impeccable detect` on admin-ui.css + templates/dashboard): 0 findings (it warns it cannot resolve the `{% static %}` link, so colour rules from admin-ui.css were not cross-checked in templates).
  - Not covered: real-device touch, the admin sidebar is 940px tall on phones (pre-existing, outside this task).

## Route log
| Task | Route | Evidence | Commit |
|------|-------|----------|--------|
| B1 | delegated writer | Bodega CSS/markup read, 1280 render | e58e8c5 |
| B2 | delegated writer | Bodega dialog markup/JS read, scripted dialog checks | a3fc8d0 |
| B3 | delegated writer | 4-width iframe sweep, one fix batch, one confirm round | (this commit) |

## Next step
Done. Optional: hide "Ver más columnas" when the table does not overflow; phone admin sidebar height.
