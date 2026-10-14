/*
 * Child sign-in helpers (accounts/student_access_*.html).
 * - Student cards: a tap says the name aloud, then opens that card.
 * - Pair key: tap 2 of 9 drawings (order free); each tap says the word.
 */
(() => {
  const speak = (text) => window.AppSpeech?.speak(text);
  const canSpeak = () => 'speechSynthesis' in window && Boolean(window.AppSpeech);

  document.querySelectorAll('[data-kid-card]').forEach((card) => {
    card.addEventListener('click', (event) => {
      if (!canSpeak() || card.dataset.going) return;
      event.preventDefault();
      card.dataset.going = '1';
      card.classList.add('is-picked');
      speak(card.dataset.speakName || '');
      // Let the name be heard before the next page loads.
      window.setTimeout(() => card.form.submit(), 1100);
    });
  });

  const form = document.querySelector('[data-pair-key]');
  if (!form) return;
  const size = Number(form.dataset.pairSize) || 2;
  const boxes = Array.from(form.querySelectorAll('input[name="symbols"]'));
  const count = form.querySelector('[data-pair-count]');
  const dots = Array.from(form.querySelectorAll('.pair-key__dots i'));
  const submit = form.querySelector('[data-pair-submit]');

  const refresh = () => {
    const chosen = boxes.filter((box) => box.checked).length;
    count.textContent = String(chosen);
    dots.forEach((dot, index) => dot.classList.toggle('is-on', index < chosen));
    submit.disabled = chosen !== size;
  };

  boxes.forEach((box) => {
    box.addEventListener('change', () => {
      if (box.checked && boxes.filter((item) => item.checked).length > size) {
        box.checked = false;
        speak('Ya tienes dos. Toca uno para quitarlo.');
        return;
      }
      speak(box.dataset.word || '');
      refresh();
    });
  });

  form.addEventListener('submit', (event) => {
    if (boxes.filter((box) => box.checked).length !== size) event.preventDefault();
  });
  refresh();
})();
