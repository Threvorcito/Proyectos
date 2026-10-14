# Kid reading experience

## Objective
Make the student side more interactive and better suited to children aged 6-9 with dyslexia, following `reports/Mejoras interactivas para dislexia.md`: start with repeated reading with a model (top priority A1/A2), then a child-friendly visual pass (colors, sizes, audio-first cues) on every student-facing screen.

## Why
In Spanish, dyslexia shows mainly as slow, effortful reading. Repeated reading after listening to a model has the largest effect in the evidence (Lee & Yoon 2017). The user also asked that colors and everything else be adjusted to children.

## Scope / constraints
- Student-facing screens only for the visual pass; teacher/admin keep the SistemaBodega look.
- No speech recognition, no recording of children's voices (El Salvador Decreto 144). Timing is measured silently; no visible clock.
- No leaderboards, no "dyslexia fonts", no coloured overlays; compare the child only with themselves.
- Spanish UI copy, neutral and child-friendly. Artifacts in English.
- Branch: `fix/security-and-data-hardening` (continue).

## Tasks
- [x] K1 Repeated reading with model: listen with word highlighting → read 3 times (silent timing) → growth chart vs own attempts; separate "Escuchar el cuento" from "Practicar lectura"; points once per reading per day for a finished cycle; teacher report shows speed trend
- [ ] K2 Child-friendly visual pass on student screens: palette, contrast, big targets (48-64px), audio cue buttons, friendly feedback states

## Route log
| Task | Route | Evidence | Commit |
|------|-------|----------|--------|
| K1 | Delegated direct (writer) | Models + endpoint + reward service + teacher table + practice UI span 2+ non-trivial files. RED: ImportError on new models, then 3 failures; GREEN: readings/dashboard/progress 160 tests OK, full suite 225 OK; `makemigrations --check` clean. Browser: full cycle on /lecturas/2/ at 1280px and 375px (no horizontal scroll), highlight advanced word by word, too-fast read rejected kindly, 5 points first cycle, none on second same day, history bar shown. | see git log (feat(readings) x2) |

## Next step
K2.
