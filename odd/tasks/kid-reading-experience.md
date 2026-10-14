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
- [x] K2 Child-friendly visual pass on student screens: palette, contrast, big targets (48-64px), audio cue buttons, friendly feedback states
- [x] K3 Reading-buddy mascot (vanilla JS port of nilbuild/page-mascot, MIT; original SVG owl): greets on the student dashboard, cheers on correct answers and finished practice, encourages on mistakes; tap reaction on touch; reduced-motion aware

## Route log
| Task | Route | Evidence | Commit |
|------|-------|----------|--------|
| K1 | Delegated direct (writer) | Models + endpoint + reward service + teacher table + practice UI span 2+ non-trivial files. RED: ImportError on new models, then 3 failures; GREEN: readings/dashboard/progress 160 tests OK, full suite 225 OK; `makemigrations --check` clean. Browser: full cycle on /lecturas/2/ at 1280px and 375px (no horizontal scroll), highlight advanced word by word, too-fast read rejected kindly, 5 points first cycle, none on second same day, history bar shown. | see git log (feat(readings) x2) |
| K2 | Delegated direct (writer) | kid.css + base/navbar + ~18 student templates + main.js (2+ non-trivial files). No runnable RED for visual work: checked in the browser instead. Sweep at 375/768/1280 over home, login, student cards, dashboard, levels, level 1, activities + detail (wrong and right answers), 4 games, readings + practice result, progress, accessibility page, profile: no horizontal scroll, no contrast failures after the fix batch, interactive targets >= 48px. Teacher dashboard and admin usuarios load no kid.css (admin card 330-1504px at 1534x784, no page scroll). Full suite 225 OK; impeccable detect clean on changed files (fixed earlier home/404 contrast). | 028cc80, d149599 + this docs commit |
| K3 | Delegated direct (writer) | Partial + mascot.css + mascot.js + hooks in reading-practice.js, games/common.js and 6 child templates (2+ non-trivial files). RED: new `ReadingBuddyMascotTests` failed on the student dashboard; GREEN: both pass, full suite 227 OK. Browser at 375x812 and 1280x800 over dashboard, aprender, reading 2 (listen + full 3-read practice cycle), activity 1 (right and wrong), games index and Cazador de letras (wrong, 5 right, finish): no horizontal scroll, Lumi overlaps 0 interactive elements at 4 scroll positions per page; reactions observed via `data-expression` (hello greeting, encourage on too-fast read and wrong answers, cheer on reads/result/correct/finish). Docked fallback tucks when over content; reduced-motion switch sets `.is-still` (no animation, no tracking, expression swap only). Teacher dashboard and admin usuarios render no mascot. impeccable detect: []. | c6acd0b + this docs commit |

## Next step
Optional follow-ups from the report: A5 graded hints, A7 server-saved reading defaults.
