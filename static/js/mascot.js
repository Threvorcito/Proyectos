/*
 * Reading buddy "Lumi" for the children's screens.
 * Mechanics adapted from nilbuild/page-mascot (MIT, © Kamran Ahmed); character art original.
 *
 * - Looks toward the pointer in 9 directions (8 sectors + a dead zone in the
 *   middle), only with a fine pointer and without reduced motion.
 * - Blinks now and then, gets sleepy when nobody plays with it.
 * - Tap: a short friendly reaction; the line is spoken only on that tap.
 * - Pages call window.Mascot?.react('cheer'|'encourage'|'hello'|'surprise', {say})
 *   to react to the child's progress; text shows in a polite live bubble.
 * - No animation loop: everything runs on events and short timers, which stop
 *   while the tab is hidden.
 */
(() => {
  const root = document.querySelector('[data-mascot]');
  if (!root) return;

  const buddy = root.querySelector('[data-mascot-buddy]');
  const bubble = root.querySelector('[data-mascot-bubble]');
  const hideButton = root.querySelector('[data-mascot-hide]');
  const showButton = root.querySelector('[data-mascot-show]');
  const body = document.body;

  const DIRECTIONS = ['e', 'se', 's', 'sw', 'w', 'nw', 'n', 'ne'];
  const REACTIONS = {
    cheer: {expression: 'cheer', animation: 'hop', duration: 1600},
    hello: {expression: 'hello', animation: 'wave', duration: 1500},
    encourage: {expression: 'encourage', animation: 'nod', duration: 2000},
    surprise: {expression: 'surprise', animation: 'pop', duration: 1100},
  };
  const TAP_LINES = [
    {kind: 'hello', text: '¡Hola! Soy Lumi.'},
    {kind: 'cheer', text: '¡Me encanta leer contigo!'},
    {kind: 'surprise', text: '¡Uy, cosquillas!'},
    {kind: 'encourage', text: '¡Tú puedes!'},
  ];
  const STORAGE_KEY = 'lsl_mascotHidden';
  const CONTENT = 'a[href], button, input, select, textarea, summary, [role="button"], [tabindex]:not([tabindex="-1"]), h1, h2, h3, p, li, label, img';
  const IDLE_MS = 30000;

  const finePointer = window.matchMedia('(pointer: fine)');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const narrow = window.matchMedia('(max-width: 767.98px)');

  let expressionTimer = null;
  let animationTimer = null;
  let bubbleTimer = null;
  let bubbleClearTimer = null;
  let blinkTimer = null;
  let idleTimer = null;
  let layoutTimer = null;
  let lastMove = 0;
  let lastTap = -1;
  let greetingSpoken = false;
  const greeting = root.dataset.mascotGreeting || '';

  const storage = {
    get() { try { return window.localStorage.getItem(STORAGE_KEY) === 'true'; } catch (error) { return false; } },
    set(value) { try { window.localStorage.setItem(STORAGE_KEY, String(value)); } catch (error) { /* private mode: keep it for this page only */ } },
  };

  const isStill = () => reducedMotion.matches || body.classList.contains('reduce-motion');
  const isHiddenByChild = () => root.classList.contains('is-hidden');
  const isAway = () => isHiddenByChild() || document.hidden || root.classList.contains('is-tucked');

  /* ---------- expressions and animation ---------- */

  const setExpression = (name) => {
    if (root.dataset.expression !== name) root.dataset.expression = name;
  };

  const playAnimation = (name) => {
    root.classList.remove('is-anim-hop', 'is-anim-wave', 'is-anim-nod', 'is-anim-pop');
    window.clearTimeout(animationTimer);
    if (isStill() || !name) return;
    void root.offsetWidth; // restart the keyframes when the same reaction repeats
    root.classList.add(`is-anim-${name}`);
    animationTimer = window.setTimeout(() => root.classList.remove(`is-anim-${name}`), 1000);
  };

  const say = (text) => {
    if (!text || isHiddenByChild()) return;
    window.clearTimeout(bubbleTimer);
    window.clearTimeout(bubbleClearTimer);
    bubble.textContent = text;
    bubble.classList.add('is-open');
    bubbleTimer = window.setTimeout(() => {
      bubble.classList.remove('is-open');
      bubbleClearTimer = window.setTimeout(() => { bubble.textContent = ''; }, 300);
    }, Math.min(6000, 2500 + text.length * 60));
  };

  /* ---------- idle: blink and sleepy ---------- */

  const scheduleBlink = () => {
    window.clearTimeout(blinkTimer);
    if (isStill() || document.hidden) return;
    blinkTimer = window.setTimeout(() => {
      if (!isAway() && root.dataset.expression !== 'cheer') {
        root.classList.add('is-blinking');
        window.setTimeout(() => root.classList.remove('is-blinking'), 140);
        // Now and then a double blink, like a real bird.
        if (Math.random() < 0.25) {
          window.setTimeout(() => root.classList.add('is-blinking'), 280);
          window.setTimeout(() => root.classList.remove('is-blinking'), 420);
        }
      }
      scheduleBlink();
    }, 3000 + Math.random() * 4000);
  };

  const scheduleIdle = () => {
    window.clearTimeout(idleTimer);
    if (document.hidden) return;
    idleTimer = window.setTimeout(() => {
      if (root.dataset.expression === 'neutral') setExpression('sleepy');
    }, IDLE_MS);
  };

  const wake = () => {
    if (root.dataset.expression === 'sleepy') setExpression('neutral');
    scheduleIdle();
  };

  /* ---------- look toward the pointer ---------- */

  const tracking = () => finePointer.matches && !isStill() && !isAway();

  const lookAt = (x, y) => {
    const box = buddy.getBoundingClientRect();
    const dx = x - (box.left + box.width / 2);
    const dy = y - (box.top + box.height * 0.45);
    let direction = 'c';
    // Dead zone over Lumi's own face so it settles instead of jittering.
    if (Math.hypot(dx, dy) > box.width * 0.5) {
      const sector = Math.round(Math.atan2(dy, dx) / (Math.PI / 4));
      direction = DIRECTIONS[(sector + 8) % 8];
    }
    if (root.dataset.look !== direction) root.dataset.look = direction;
  };

  document.addEventListener('pointermove', (event) => {
    if (event.pointerType !== 'mouse' && event.pointerType !== 'pen') return;
    if (event.timeStamp - lastMove < 60) return; // ~16 checks per second at most
    lastMove = event.timeStamp;
    wake();
    if (tracking()) lookAt(event.clientX, event.clientY);
  }, {passive: true});

  document.documentElement.addEventListener('pointerleave', () => { root.dataset.look = 'c'; });

  /* ---------- placement: side gutter, page slot, or tuck away ---------- */

  const sizeOf = () => buddy.getBoundingClientRect().width || (narrow.matches ? 72 : 104);

  const gutterFits = () => {
    const container = document.querySelector('.page-shell .container');
    if (!container) return false;
    const left = container.getBoundingClientRect().left + parseFloat(window.getComputedStyle(container).paddingLeft || '0');
    return left >= (narrow.matches ? 72 : 104) + 32;
  };

  // The last visible slot wins: pages put deeper slots next to the step the child is on.
  const visibleSlot = () => Array.from(document.querySelectorAll('[data-mascot-slot]'))
    .filter((slot) => !slot.closest('[hidden]') && slot.parentElement && slot.parentElement.getClientRects().length)
    .pop();

  const overlapsContent = () => {
    const box = root.getBoundingClientRect();
    if (!box.width) return false;
    const pad = 4;
    return Array.from(document.querySelectorAll(CONTENT)).some((element) => {
      if (root.contains(element) || element.closest('.accessibility-fab, .offcanvas, .navbar')) return false;
      const rect = element.getBoundingClientRect();
      if (!rect.width || !rect.height) return false;
      return rect.left < box.right - pad && rect.right > box.left + pad && rect.top < box.bottom - pad && rect.bottom > box.top + pad;
    });
  };

  const checkTuck = () => {
    if (!root.classList.contains('is-docked')) {
      root.classList.remove('is-tucked');
      return;
    }
    const tuck = overlapsContent();
    root.classList.toggle('is-tucked', tuck);
    if (tuck) root.dataset.look = 'c';
  };

  const place = () => {
    const slot = gutterFits() ? null : visibleSlot();
    if (slot) {
      if (root.parentElement !== slot) slot.appendChild(root);
      root.classList.add('is-inline');
      root.classList.remove('is-docked', 'is-tucked');
      body.classList.remove('has-mascot-dock');
    } else {
      if (root.parentElement !== body) body.appendChild(root);
      root.classList.add('is-docked');
      root.classList.remove('is-inline');
      body.classList.add('has-mascot-dock');
    }
    checkTuck();
  };

  const scheduleLayout = (delay = 120) => {
    if (layoutTimer) return;
    layoutTimer = window.setTimeout(() => {
      layoutTimer = null;
      place();
    }, delay);
  };

  window.addEventListener('scroll', () => scheduleLayout(), {passive: true});
  window.addEventListener('resize', () => scheduleLayout(), {passive: true});
  // Mode switches, game rounds and practice steps change what is on screen after a click.
  document.addEventListener('click', (event) => {
    if (root.contains(event.target)) return;
    scheduleLayout(60);
    window.setTimeout(() => scheduleLayout(0), 900);
  });

  /* ---------- hide / show (remembered) ---------- */

  const setHidden = (hidden, moveFocus) => {
    root.classList.toggle('is-hidden', hidden);
    showButton.hidden = !hidden;
    if (hidden) {
      bubble.classList.remove('is-open');
      bubble.textContent = '';
    }
    storage.set(hidden);
    if (moveFocus) (hidden ? showButton : buddy).focus();
  };

  hideButton.addEventListener('click', () => setHidden(true, true));
  showButton.addEventListener('click', () => {
    setHidden(false, true);
    react('hello', {say: '¡Aquí estoy!'});
  });

  /* ---------- reactions ---------- */

  function react(kind, options = {}) {
    const reaction = REACTIONS[kind] || REACTIONS.hello;
    place(); // the page may just have switched steps
    wake();
    window.clearTimeout(expressionTimer);
    setExpression(reaction.expression);
    playAnimation(reaction.animation);
    expressionTimer = window.setTimeout(() => setExpression('neutral'), reaction.duration);
    if (options.say) say(options.say);
  }

  const speakOnTap = (text) => {
    const synth = window.speechSynthesis;
    // Never cut off a story that is being read aloud.
    if (synth && (synth.speaking || synth.pending)) return;
    window.AppSpeech?.speak(text);
  };

  buddy.addEventListener('click', () => {
    if (greeting && !greetingSpoken) {
      greetingSpoken = true;
      react('hello', {say: greeting});
      speakOnTap(greeting);
      return;
    }
    let pick = Math.floor(Math.random() * TAP_LINES.length);
    if (pick === lastTap) pick = (pick + 1) % TAP_LINES.length;
    lastTap = pick;
    react(TAP_LINES[pick].kind, {say: TAP_LINES[pick].text});
    speakOnTap(TAP_LINES[pick].text);
  });

  /* ---------- lifecycle ---------- */

  const applyStill = () => {
    root.classList.toggle('is-still', isStill());
    if (isStill()) root.dataset.look = 'c';
    scheduleBlink();
  };

  reducedMotion.addEventListener?.('change', applyStill);
  // accessibility.js toggles body.reduce-motion from the "Reducir animaciones" switch.
  new MutationObserver(applyStill).observe(body, {attributes: true, attributeFilter: ['class']});

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      [blinkTimer, idleTimer, layoutTimer].forEach((timer) => window.clearTimeout(timer));
      layoutTimer = null;
      root.classList.remove('is-blinking');
    } else {
      scheduleBlink();
      scheduleIdle();
      scheduleLayout(0);
    }
  });

  setHidden(storage.get(), false);
  applyStill();
  place();
  scheduleIdle();

  window.Mascot = {react, say};

  // First words: a page cue (e.g. activity feedback) wins over the greeting. Never spoken aloud here.
  const cue = document.querySelector('[data-mascot-on-load]');
  const firstWords = () => {
    if (cue) react(cue.dataset.mascotOnLoad, {say: cue.dataset.mascotSay || ''});
    else if (greeting) react('hello', {say: greeting});
  };
  // Wait until Lumi is actually on screen (e.g. feedback below the fold on a phone).
  if ((cue || greeting) && 'IntersectionObserver' in window) {
    const watcher = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      watcher.disconnect();
      window.setTimeout(firstWords, 400);
    }, {threshold: 0.6});
    watcher.observe(buddy);
  } else {
    window.setTimeout(firstWords, 600);
  }
})();
