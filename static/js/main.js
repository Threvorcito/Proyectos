(() => {
  const buttons = document.querySelectorAll('[data-speak-text]');
  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      if (!('speechSynthesis' in window)) return;
      const utterance = new SpeechSynthesisUtterance(button.dataset.speakText || '');
      utterance.lang = 'es-MX';
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    });
  });
})();
