(function () {
  const root = document.documentElement;
  const settings = {
    fontSize: localStorage.getItem('lsl_fontSize') || 18,
    letterSpacing: localStorage.getItem('lsl_letterSpacing') || 0,
    wordSpacing: localStorage.getItem('lsl_wordSpacing') || 0,
    lineHeight: localStorage.getItem('lsl_lineHeight') || 1.6,
    highContrast: localStorage.getItem('lsl_highContrast') === 'true',
    reduceMotion: localStorage.getItem('lsl_reduceMotion') === 'true',
    readingGuide: localStorage.getItem('lsl_readingGuide') === 'true',
  };

  function apply() {
    document.body.style.fontSize = `${settings.fontSize}px`;
    document.body.style.letterSpacing = `${settings.letterSpacing}px`;
    document.body.style.wordSpacing = `${settings.wordSpacing}px`;
    document.body.style.lineHeight = settings.lineHeight;
    document.body.classList.toggle('high-contrast', settings.highContrast);
    document.body.classList.toggle('reduce-motion', settings.reduceMotion);
  }

  apply();
})();
