# UX, gamification and accessibility for a Spanish-language reading platform for children aged 6-9 with dyslexia (El Salvador, Django web app)

Research date: 2026-10-14. 17 tool calls. Some primary pages could not be fetched; those claims are marked as secondary or moved to Gaps.

## Q1. Child UX for pre-readers and early readers (audio-first, icons, touch, gestures, feedback, errors, sessions)

### Takeaway
Treat 6-8 year olds as their own segment, distinct from 3-5 and 9-12. Every instruction should be audio + icon + short text. Use large, always-visible icon navigation with an on-screen Back/Home button. Stick to simple tap, drag and swipe. Feedback should be immediate and multimodal. Errors get gentle visual hints, never text-heavy messages.

### Cited Findings
- NN/g (3 studies: 2001, 2010, 2018; 125 children; guidelines grew from 130 to 156) says to segment ages into at least 3-5, 6-8 and 9-12. Kids notice when a site looks "for babies." — [NN/g, Children's websites usability issues](https://www.nngroup.com/articles/childrens-websites-usability-issues/)
- NN/g: the youngest children don't read and young children read tentatively. They skip long instruction blocks. Avoid scrolling for young kids. Use about 14 pt type for young children and 12 pt for older ones. — [NN/g](https://www.nngroup.com/articles/childrens-websites-usability-issues/)
- NN/g: children preferred touchscreens over a mouse until about age 9. Tap, swipe and drag work well, and kids expect characters and pictures to respond to taps. — [NN/g](https://www.nngroup.com/articles/childrens-websites-usability-issues/)
- NN/g: kids expect sound and animation. Slow or unresponsive designs frustrate them, and they often abandon a broken feature rather than recover. They struggle with error messages. — [NN/g](https://www.nngroup.com/articles/childrens-websites-usability-issues/)
- NN/g: redundant or multiple navigation paths confuse children. Young children often don't use the browser Back button, so provide an on-screen one. Put parent-facing links where kids are unlikely to click them, such as text-only footers. Real-life metaphors help pre-readers. — [NN/g](https://www.nngroup.com/articles/childrens-websites-usability-issues/)
- Google "Designing engaging apps" (Building for Kids): combine sound, visuals and text after each action. Don't rely on one mode of instruction. Use only essential sounds and visuals because of limited focus. — [Google for Developers, Building for kids](https://developers.google.com/building-for-kids/designing-engaging-apps)
- Google: use big touch targets because kids' motor skills are still developing and they hold devices in unexpected ways. Prefer draw, swipe and drag. Avoid multi-finger gestures, double-tap and pinch unless the audience is older or the gesture is essential. — [Google, Building for kids](https://developers.google.com/building-for-kids/designing-engaging-apps)
- Google: always show navigation, preferably as icons. Use familiar home and back arrows. Avoid text-only buttons. Put important content at the top, with hints when content scrolls. — [Google, Building for kids](https://developers.google.com/building-for-kids/designing-engaging-apps)
- Google: errors get positive audio and visual feedback and a quick return to the activity. For wrong answers, use visual hints such as arrows, highlights or pulses instead of text. — [Google, Building for kids](https://developers.google.com/building-for-kids/designing-engaging-apps)
- Google: include a parent-only section. Gate parental controls behind a challenge only an adult can answer. Support joint play between parent and child. — [Google, Building for kids](https://developers.google.com/building-for-kids/designing-engaging-apps)
- WCAG 2.2 SC 2.5.8 Target Size (Minimum), Level AA, requires a 24x24 CSS px target (or the spacing exception). The older AAA SC 2.5.5 requires 44x44. Apple recommends 44 pt and Material recommends 48 dp (secondary sources). — [DAISY KB, target size minimum](https://kb.daisy.org/publishing/docs/wcag/target-size-minimum.html); [Deque axe rule](https://dequeuniversity.com/rules/axe/4.8/target-size)
- WCAG 2.2 SC 2.2.1 Timing Adjustable (A): any time limit must be one the user can turn off, adjust up to 10x, or extend with a warning and 20 s (at least 10 extensions). — [W3C Understanding 2.2.1](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html)

### Inferences
- Use at least 48-64 CSS px targets with generous spacing for 6-9 year olds. The 24 px AA minimum is a floor meant for adults, and the platform guidance (44 pt / 48 dp) is still adult-oriented.
- Give every instruction screen an auto-played or tap-to-replay audio button (speaker icon) that reads the instruction in Spanish. Text stays short and visible underneath.
- Prefer tap-to-select / tap-to-place over drag-and-drop as the default. Offer drag as an alternative, not the only way. Google lists drag as a simple gesture, but on low-end tablets and for kids with motor difficulties, tap is more robust and is easier to make keyboard-accessible.
- Keep one primary navigation path: Home, Back, and an activity map. Drop secondary menus in the child view.
- Design sessions as short, finishable units (one story or exercise set) with a clear end screen and a "keep going" or "rest" choice. No specific minute value was found in the sources (see Gaps).

### Gaps
- Apple's kids-specific HIG page and Google's numeric target sizes for kids could not be fetched. 44 pt / 48 dp come from secondary sources.
- No authoritative source found for recommended session length (minutes) for ages 6-9 in reading apps.
- No direct study found comparing drag-and-drop vs tap error rates for 6-9 year olds on web.

## Q2. Gamification that supports learning vs. gamification that harms

### Takeaway
The evidence is mixed. Gamification helps young children when the elements fit their developmental stage and support Self-Determination Theory needs (competence, autonomy, relatedness). Mandatory badges and leaderboards, which bring competition, social comparison and lost autonomy, have been shown to lower intrinsic motivation and satisfaction. Struggling readers, who will tend to rank low, are the group most at risk.

### Cited Findings
- A 2025 meta-analysis of gamification in early childhood education found inconsistent effects across studies. Overall impact was significantly positive, especially when game elements were tailored to children's developmental characteristics. — [SciTePress 2025 meta-analysis](https://scitepress.org/publishedPapers/2025/140690/pdf/index.html)
- A systematic review of 16 studies (2017-2022) on gamified well-being apps for children and young people found SDT is the prevalent theoretical frame. Interactivity is essential, and offline connections are also needed. — [Seminar.net, OsloMet](https://journals.oslomet.no/seminar/article/view/5774)
- A small qualitative study (8 students) of a gamified online reading platform in Hong Kong found it helped students feel competent, autonomous and connected with family and friends. — [Zhu 2018, HKU](https://web.edu.hku.hk/f/staff/447/Zhu%202018%20Can%20Gamification%20Bring%20Long-term%20Effects%20for%20Elementary%20Students%E2%80%99%20Learning.pdf)
- Li & Chu (2021, BJET) is a mixed-methods study of gamification pedagogy on children's reading performance, reading mentality, behaviours and sustainability. — [summary](https://www.universityxp.com/research/2021/5/3/exploring-the-effects-of-gamification-pedagogy-on-childrens-reading-a-mixedmethod-study-on-academic-performance-readingrelated-mentality-and-behaviors-and-sustainability)
- Hanus & Fox (2015, Computers & Education 80:152-161), about 80 university students: a gamified course with mandatory badges and a leaderboard produced lower satisfaction and lower intrinsic motivation than an identical non-gamified course. The authors attributed this to social comparison/competition and to lack of autonomy. — [UCLA SMHP summary PDF](https://www.smhp.psych.ucla.edu/pdfdocs/gamil.pdf); [Emerald INTR review](https://www.emerald.com/insight/content/doi/10.1108/intr-12-2021-0897/full/html)
- Leaderboard literature hypothesis: high ranks may motivate while low ranks harm motivation. Excessive competition is a known side effect. — [Emerald INTR 2021-0897](https://www.emerald.com/insight/content/doi/10.1108/intr-12-2021-0897/full/html); [Mekler et al. 2017](https://glassmanlab.seas.harvard.edu/annotated_works/mekler17.pdf)
- Google kids guidance: reward task completion with visuals, animation and sound. — [Google, Building for kids](https://developers.google.com/building-for-kids/designing-engaging-apps)

### Inferences
- Patterns to adopt:
  - Mastery-based progression, where a child unlocks the next level by demonstrating a skill, not by time or points.
  - A personal progress map or narrative world compared only with the child's own past ("you read 3 more words than last week").
  - Avatar or companion customization unlocked by effort, which supports autonomy and relatedness.
  - Collectibles tied to content (stickers of story characters).
  - Choice of which story or activity to do next.
- Patterns to avoid or soften:
  - Class leaderboards: never show them to children.
  - Mandatory badges.
  - Timers and countdowns on reading tasks, which create anxiety and also conflict with WCAG 2.2.1 unless adjustable.
  - Loss-based streaks: if streaks are used, make them forgiving, for example weekly goals with "rest days" and no visible streak-loss shame.
  - Points economies disconnected from reading.
- A team or class cooperative goal ("our class read 200 pages together") can supply relatedness without individual ranking. This is an inference, not directly evidenced in the sources found.

### Gaps
- No meta-analysis was found specific to gamified literacy apps for children with dyslexia that tests SDT.
- No study found on leaderboard effects specifically for struggling/low-achieving young readers. The harm is inferred from the Hanus & Fox mechanism and the rank hypothesis.
- Evidence on streaks for young children was not found.
- Praise research (process/effort praise vs. ability praise, Mueller & Dweck 1998) is widely cited, but it was not fetched in this session. Verify before citing.

## Q3. Dyslexia accessibility guidelines and reading-mode features

### Takeaway
Use a clean sans-serif font at a large size (for young children, bigger than the BDA adult 12-14 pt baseline), extra letter and word spacing, 1.5 line spacing, bold (not italics or underline) for emphasis, no all-caps, and off-white backgrounds. Dyslexia-specific fonts (OpenDyslexic) show no readability benefit. Syllable coloring has mixed, small-sample evidence: it helps accuracy and beginning decoders more than speed, and it bothers some children, so make it an optional toggle. Text highlighting synchronized with audio helps.

### Cited Findings
- BDA Dyslexia Style Guide 2023 (via a secondary copy):
  - 12-14 pt, or about 1-1.2 em (16-19 px), with some readers wanting larger.
  - Letter spacing around 35% of average letter width, while excessive spacing can hurt.
  - Word spacing at least 3.5x letter spacing.
  - Line spacing 1.5.
  - Avoid underline and italics, use bold for emphasis, avoid all-caps.
  - Primary PDF not fetched. — [BU-hosted copy of BDA guide](https://www.bumc.bu.edu/jmedday/files/2025/05/Dyslexia-friendly-style-guide.docx); [JALT summary](https://jalt-publications.org/articles/29622-transforming-text-student-success-guide-creating-dyslexic-friendly-classroom)
- Rello & Baeza-Yates 2013 (ASSETS, "Good Fonts for Dyslexia", 48 participants with dyslexia, eye-tracking):
  - Helvetica and Courier gave shorter fixations.
  - OpenDyslexic did not improve readability, and participants preferred Arial/Helvetica.
  - Italics decreased readability.
  - Critique: spacing across fonts was not controlled. DOI 10.1145/2513383.2513447. — [BYU Editing Research summary](https://editingresearch.byu.edu/2020/05/28/which-fonts-are-best-for-dyslexia/)
- Rello & Baeza-Yates 2016 (ACM TACCESS) replicated the work with 97 native Spanish speakers (48 with dyslexia), which makes it especially relevant for Spanish text. — [summary](https://a11y-paradise.onrender.com/reviews/69cd7af2bbd7e71582e41407)
- Rello et al. 2017 ("How to present more readable text for people with dyslexia", UAIS, eye-tracking with 92 people) found that larger text and larger character spacing led both readers with and without dyslexia to read significantly faster. DOI 10.1007/s10209-015-0438-8. — [UPF repository](https://repositori.upf.edu/items/e0ca6f40-a0fa-490f-9d03-53d043270deb)
- Syllable coloring evidence:
  - French thesis (65 dyslexic children): no speed change, improved accuracy, and children preferred colored text.
  - German study (21 dyslexic 2nd-3rd graders): highly variable responses, and some children were bothered.
  - Some studies show benefit for first graders but not older children. — [Brügelmann 2025, peDOCS](https://www.pedocs.de/volltexte/2025/34472/pdf/Bruegelmann_2025_Red_and_blue.pdf); [DUMAS thesis](https://dumas.ccsd.cnrs.fr/dumas-03282114/document)
- A Brazilian dissertation (77 second graders, Portuguese) found that syllabic coloring boosted phonological recoding, with larger effects for weaker readers. This is relevant because Spanish and Portuguese are both syllable-transparent. — [USP thesis](https://teses.usp.br/teses/disponiveis/59/59141/tde-05032018-214619/es.php)
- In a small study (4 children with dyslexia), reading along was easier with audio synchronized with text highlighting. — [IAFOR ACSET2015](https://papers.iafor.org/wp-content/uploads/papers/acset2015/ACSET2015_20150.pdf)
- Coloured overlays were ineffective and potentially detrimental in a 3-participant study. Don't build on the overlay claims. — [PMC4999357](https://pmc.ncbi.nlm.nih.gov/articles/PMC4999357/)
- W3C COGA "Making Content Usable" has 8 objectives (clear purpose, findability, clear content, avoid/correct mistakes, help focus, not relying on memory, help and support, adaptation and personalization). Patterns relevant here:
  - Use Clear Words (4.4.1), Keep Text Succinct, Separate Each Instruction, Use White Spacing.
  - Provide Feedback, Make it Easy to Undo.
  - Limit Interruptions, Avoid Too Much Content.
  - Do Not Rely on Memorizing Information (4.7.5), Login That Does Not Rely on Memory (4.7.1).
  - Provide Reminders, Provide Human Help.
  - Let Users Control When Content Moves (4.9.1), Avoid Data Loss and Timeouts, Support Simplification (4.9.3).
  - Break Media into Chunks.
  - COGA is not child-specific. Its "Tal" persona is a student with dyslexia. — [W3C COGA Content Usable](https://www.w3.org/TR/coga-usable/)

### Inferences
- Reading-mode toolbar (per child, stored on the server so it follows the child across shared devices):
  - Font size slider with a default of about 22-28 px for ages 6-9.
  - Letter and word spacing presets.
  - Line spacing 1.5-2.
  - Background tint (cream, off-white) without making colored overlays a "treatment".
  - Focus line / reading ruler that dims other lines.
  - Optional syllable coloring, off by default and offered to beginners.
  - Per-word highlighting synced with TTS.
  - "Read this word to me" by tapping any word.
- Default font: a common sans such as Arial/Helvetica/Verdana-like (or an open equivalent with distinct b/d/p/q and a single-story "a" for young readers). Offer OpenDyslexic only as an optional preference.
- The COGA "no memory login" pattern maps directly to shared classroom devices: picture or class-roster login (tap your class, then tap your avatar, then an optional picture password) instead of typed passwords.
- Spanish has a transparent syllable structure, so programmatic syllabification for syllable coloring is feasible with rule-based code. Not sourced here; verify with a Spanish syllabification library.

### Gaps
- The BDA 2023 primary PDF was not retrieved. Values come from a secondary copy.
- No controlled study found on "reading ruler / focus line" effectiveness for children.
- No source found on recommended font size specifically for dyslexic 6-9 year olds. The "18 pt" Rello/Baeza-Yates Wikipedia paper ("Size matters (spacing not)") was not retrieved.

## Q4. Web technology feasibility (Web Speech API, privacy, offline, low-end devices)

### Takeaway
Speech synthesis is broadly available, but per-word `boundary` events are unreliable. They often don't fire on Chrome Android or with Google network voices, so word highlighting needs a fallback (chunking or timing estimates, or pre-generated audio with word timestamps). SpeechRecognition is not Baseline: Chrome/Safari are partial, Edge/Firefox unsupported per caniuse, and Chrome sends audio to a server. For minors in El Salvador under Decreto 144 (2024), voice-based reading assessment through browser speech recognition is a privacy and reliability risk. Treat it as optional, opt-in and not core.

### Cited Findings
- The `boundary` event fires at word or sentence boundaries and exposes `name` and `elapsedTime` (plus `charIndex`/`charLength` per the spec). MDN marks it "Limited availability", not Baseline. — [MDN boundary event](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisUtterance/boundary_event)
- Boundary events don't fire on Chrome/Firefox Android, and don't fire for Chrome's remote "Google" voices, while local OS voices (e.g., Microsoft) do. Reports vary by device. Workarounds: chunk text into smaller utterances, or estimate timing. Pause/resume hacks break on Android Chrome. — [codersblock](https://codersblock.com/blog/javascript-text-to-speech-and-its-many-quirks/); [PhET issue #60](https://github.com/phetsims/utterance-queue/issues/60); [W3C public-speech-api list](https://lists.w3.org/Archives/Public/public-speech-api/2021Jun/0000.html)
- SpeechRecognition support per caniuse (accessed 2026-10):
  - Chrome 25+: partial.
  - Edge: not supported.
  - Safari 14.1+ and iOS Safari 14.5+: partial.
  - Firefox: disabled by default.
  - Firefox Android: not supported.
  - Chrome Android and Samsung Internet: partial. — [caniuse speech-recognition](https://caniuse.com/speech-recognition)
- MDN: SpeechRecognition is not Baseline. "On some browsers, like Chrome... audio is sent to a web service for recognition processing, so it won't work offline." Newer APIs `processLocally`, `SpeechRecognition.available()` and `install()` support on-device recognition, with support undocumented on the page. `lang` defaults to the HTML `lang` attribute. — [MDN SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition)
- El Salvador Ley de Protección de Datos Personales (Decreto Legislativo 144):
  - Approved 12 Nov 2024 and in force from 23 Nov 2024.
  - Applies to the public and private sectors.
  - Principles include informed consent, transparency, data minimization, security and demonstrated accountability.
  - The Agencia de Ciberseguridad del Estado (ACE) issued mandatory data management policies, including designating a Data Protection Officer. — [ECIJA](https://www.ecija.com/actualidad-insights/ley-de-proteccion-de-datos-en-el-salvador/); [García & Bodán](https://garciabodan.com/en/el-salvador-strengthens-personal-data-protection/); [Central Law](https://central-law.com/en/?p=15542)
- UNICEF Guidance on AI and Children 3.0 (2025) has 10 requirements, including children's data and privacy, safety by design, transparency and accountability. It applies if any AI or voice analysis is added. — [UNICEF Innocenti](https://www.unicef.org/innocenti/reports/policy-guidance-ai-children)

### Inferences
- TTS strategy:
  - Prefer `voice.localService === true` voices with `lang` starting with "es" (es-MX, es-US or es-ES; no es-SV voice is expected).
  - Feature-detect boundary events at runtime. If none fire within about 1 s, fall back to sentence/word chunking (one utterance per word or phrase, which is slower but syncs exactly) or estimated timing.
  - For core reading texts, the most reliable option is server-pre-generated audio (or teacher-recorded audio) with stored word timestamps, cached offline. This avoids depending on device voice quality on cheap Android tablets.
- SpeechRecognition:
  - Don't make it required. Edge, a common Windows school browser, and Firefox lack it.
  - Audio leaves the device in Chrome, which for minors needs explicit parent/guardian informed consent under the consent principle of Decreto 144, plus a privacy notice and a DPO for public-sector use.
  - Recognition accuracy for 6-9 year-old Salvadoran speech, and for dyslexic misreadings, is unverified.
  - Teacher-scored oral reading (the teacher listens and taps errors) is the safer default.
  - If the app records audio for the teacher, keep it opt-in, short-retention, never shared with third parties, and stored server-side under school control.
- Offline / low connectivity: Django can serve a PWA (manifest + service worker) that caches the app shell, the current week's texts and audio, and queues results in IndexedDB for sync. This is standard web platform capability, not sourced in this session.
- Low-end tablets: avoid heavy animation libraries. Use CSS transforms and honor `prefers-reduced-motion`. Lazy-load audio and compress images. Inference.
- Shared devices: no persistent child login tokens on shared devices. Use the picture-login per session and auto-logout at the end of an activity, while respecting WCAG 2.2.1 for any timeout. Preferences live on the server.

### Gaps
- No source found evaluating Spanish voice quality across Android/Windows/iOS TTS engines.
- Browser support status for `processLocally`/on-device recognition in Chrome 2026 was not confirmed.
- Whether Decreto 144 has specific provisions for minors (age of consent, school data, voice/biometric data) was not confirmed. Read the Diario Oficial text and the ACE policies directly.
- No COPPA-equivalent child-specific statute found for El Salvador. LEPINA (child protection law) was not checked in this session.
- No benchmark found on PWA/Service Worker behavior on low-end Android tablets in Central American schools.

## Q5. Teacher and family features that improve outcomes

### Takeaway
The evidence-based model is data-based individualization (DBI): frequent progress monitoring (e.g., CBM oral reading fluency) graphed against an aim line, with explicit decision rules that trigger instructional change. Dashboards should show trend vs. goal and suggest the next action, not just raw scores. Family features should be a plain-language, parent-gated area that supports joint reading.

### Cited Findings
- DBI / data-based decision making is a recommended practice to intensify intervention for students who respond inadequately. Teachers use ongoing progress-monitoring data to judge response and decide when to adjust. — [Filderman & Toste 2018](https://education.ufl.edu/patterson/files/2021/01/FildermanToste2018.pdf)
- DBI is a continuous cycle. An illustrative Vanderbilt case graphs fluency data against an aim line with a rule of "4 data points below the line, then change instruction." This is an example, not a validated standard. — [Vanderbilt DBI case study](https://my.vanderbilt.edu/spedteacherresources/data-based-individualization-case-study-part-two/)
- Ardoin et al. (2013, Journal of School Psychology 51(1):1-18) systematically reviewed CBM-R decision rules (cited via REL Southeast). Decision rules developed for ORF should not be extrapolated to other measures such as letter-sound fluency without testing (Van Norman & Nelson 2019). — [IES REL Southeast Ask A REL](https://ies.ed.gov/ncee/edLabs/regions/southeast/aar/ee_08-2019.asp); [Penn State](https://pure.psu.edu/en/publications/assessing-the-consequential-validity-of-early-literacy-progress-m/)
- Google: provide a parent-only section explaining how the experience works, gated behind an adult challenge, and give parents and kids active roles in joint play. — [Google, Building for kids](https://developers.google.com/building-for-kids/designing-engaging-apps)
- COGA patterns: Provide Human Help, Provide Reminders, Use Clear Words. These apply to family communication. — [W3C COGA](https://www.w3.org/TR/coga-usable/)

### Inferences
- Teacher dashboard:
  - Per-child trend chart vs. aim line (words correct per minute, accuracy, or skill mastery).
  - A class heatmap of skills.
  - "Needs attention" alerts using a transparent, configurable rule such as N consecutive points below the aim line. The rule should be labeled as a heuristic.
  - A suggested next activity per child linked to the skill gap.
  - Printable worksheets matching the skill, for offline or no-device days.
  - Teacher-scored oral reading entry on a tablet.
- Family view (plain Spanish, short, audio option for low-literacy parents):
  - What the child practiced this week.
  - One concrete 10-minute home activity that needs no device (e.g., read a label together).
  - Effort-focused messages ("María practicó 4 días").
  - No rankings and no diagnostic labels.
  - Delivery via printable note or WhatsApp-shareable link. Inference based on local context, not sourced.
- Alerts should go to teachers, not to children, and be framed as "try this", not "failing".

### Gaps
- NCII's official ORF decision-rule guidance and progress-monitoring tools chart were not fetched.
- No study found measuring the effect of parent-facing dashboards or home-practice prompts on reading outcomes for dyslexic children in Latin America.
- No Spanish-language (Latin American) CBM-ORF norms were located in this session.

## Q6. Inclusion / social-emotional learning: reading self-esteem without labels

### Takeaway
Few direct sources were retrieved this session. The best-supported design levers are: compare only against the child's own past, never against peers; frame errors as "try again" with visual hints; give choice and autonomy; and keep diagnostic labels out of the child UI. These follow from the gamification and child-UX evidence above, but specific SEL-for-dyslexia studies were not located.

### Cited Findings
- Social comparison via leaderboards and forced badges lowered intrinsic motivation and satisfaction. — [Emerald INTR review of Hanus & Fox](https://www.emerald.com/insight/content/doi/10.1108/intr-12-2021-0897/full/html)
- Errors should get positive audio and visual feedback and a quick return to play. — [Google, Building for kids](https://developers.google.com/building-for-kids/designing-engaging-apps)
- A gamified reading platform helped children feel competent, autonomous and connected to family and friends. — [Zhu 2018](https://web.edu.hku.hk/f/staff/447/Zhu%202018%20Can%20Gamification%20Bring%20Long-term%20Effects%20for%20Elementary%20Students%E2%80%99%20Learning.pdf)
- Children like colored/supported text even when it doesn't change speed, so preference and comfort matter for engagement. — [DUMAS thesis](https://dumas.ccsd.cnrs.fr/dumas-03282114/document)

### Inferences
- Don't show "dislexia" or risk labels anywhere a child can see. Supports should be universal toggles available to every child (universal design), so using them carries no stigma.
- Celebrate effort and strategy: "You used the read-aloud button to check a word, great strategy." Avoid "you're smart."
- Give a "my growth" portfolio: recordings or reread texts the child can compare over time, with child consent and parental consent for audio.
- Let kids choose stories by interest, with culturally relevant Salvadoran and Central American content and characters.
- A companion character that "also makes mistakes" can model a growth mindset. This is a design hypothesis, not evidenced here.

### Gaps
- No peer-reviewed source retrieved on reading self-concept / self-esteem interventions for children with dyslexia, or on the effects of digital supports on self-concept.
- Mueller & Dweck (1998) and growth-mindset intervention evidence (including later mixed replication results) were not fetched. Verify before citing.
- UNESCO/UNICEF guidance on inclusive edtech for children with learning disabilities in Latin America was not retrieved.
