(function () {
  const body = document.body;
  const controls = document.querySelector('[data-accessibility-controls]');

  if (!body || !controls) return;

  const defaults = {
    fontSize: Number(body.dataset.defaultFontSize || 16),
    letterSpacing: Number(body.dataset.defaultLetterSpacing || 0),
    wordSpacing: Number(body.dataset.defaultWordSpacing || 0),
    lineHeight: Number(body.dataset.defaultLineHeight || 1.6),
    highContrast: body.dataset.defaultHighContrast === 'true',
    reduceMotion: body.dataset.defaultReduceMotion === 'true',
    readingGuide: body.dataset.defaultReadingGuide === 'true',
  };

  const fields = {
    fontSize: controls.querySelector('[data-font-size]'),
    letterSpacing: controls.querySelector('[data-letter-spacing]'),
    wordSpacing: controls.querySelector('[data-word-spacing]'),
    lineHeight: controls.querySelector('[data-line-height]'),
    highContrast: controls.querySelector('[data-high-contrast]'),
    reduceMotion: controls.querySelector('[data-reduce-motion]'),
    readingGuide: controls.querySelector('[data-reading-guide]'),
  };

  const settings = {
    fontSize: Number(localStorage.getItem('lsl_fontSize') || defaults.fontSize),
    letterSpacing: Number(localStorage.getItem('lsl_letterSpacing') || defaults.letterSpacing),
    wordSpacing: Number(localStorage.getItem('lsl_wordSpacing') || defaults.wordSpacing),
    lineHeight: Number(localStorage.getItem('lsl_lineHeight') || defaults.lineHeight),
    highContrast: localStorage.getItem('lsl_highContrast') !== null ? localStorage.getItem('lsl_highContrast') === 'true' : defaults.highContrast,
    reduceMotion: localStorage.getItem('lsl_reduceMotion') !== null ? localStorage.getItem('lsl_reduceMotion') === 'true' : defaults.reduceMotion,
    readingGuide: localStorage.getItem('lsl_readingGuide') !== null ? localStorage.getItem('lsl_readingGuide') === 'true' : defaults.readingGuide,
  };

  function save() {
    localStorage.setItem('lsl_fontSize', settings.fontSize);
    localStorage.setItem('lsl_letterSpacing', settings.letterSpacing);
    localStorage.setItem('lsl_wordSpacing', settings.wordSpacing);
    localStorage.setItem('lsl_lineHeight', settings.lineHeight);
    localStorage.setItem('lsl_highContrast', settings.highContrast);
    localStorage.setItem('lsl_reduceMotion', settings.reduceMotion);
    localStorage.setItem('lsl_readingGuide', settings.readingGuide);
  }

  function syncControls() {
    fields.fontSize.value = settings.fontSize;
    fields.letterSpacing.value = settings.letterSpacing;
    fields.wordSpacing.value = settings.wordSpacing;
    fields.lineHeight.value = settings.lineHeight;
    fields.highContrast.checked = settings.highContrast;
    fields.reduceMotion.checked = settings.reduceMotion;
    fields.readingGuide.checked = settings.readingGuide;
  }

  function apply() {
    document.body.style.fontSize = `${settings.fontSize}px`;
    document.body.style.letterSpacing = `${settings.letterSpacing}px`;
    document.body.style.wordSpacing = `${settings.wordSpacing}px`;
    document.body.style.lineHeight = settings.lineHeight;
    document.body.classList.toggle('high-contrast', settings.highContrast);
    document.body.classList.toggle('reduce-motion', settings.reduceMotion);
    document.body.classList.toggle('reading-guide-enabled', settings.readingGuide);
  }

  function updateFromControls() {
    settings.fontSize = Number(fields.fontSize.value);
    settings.letterSpacing = Number(fields.letterSpacing.value);
    settings.wordSpacing = Number(fields.wordSpacing.value);
    settings.lineHeight = Number(fields.lineHeight.value);
    settings.highContrast = fields.highContrast.checked;
    settings.reduceMotion = fields.reduceMotion.checked;
    settings.readingGuide = fields.readingGuide.checked;
    apply();
    save();
  }

  Object.values(fields).forEach((field) => {
    field.addEventListener('input', updateFromControls);
    field.addEventListener('change', updateFromControls);
  });

  controls.querySelector('[data-accessibility-reset]')?.addEventListener('click', () => {
    Object.assign(settings, defaults);
    syncControls();
    apply();
    save();
  });

  document.addEventListener('mousemove', (event) => {
    if (!settings.readingGuide) return;
    document.documentElement.style.setProperty('--reading-guide-y', `${event.clientY}px`);
  });

  syncControls();
  apply();
})();
