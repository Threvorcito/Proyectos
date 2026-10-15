/*
 * Tap-a-word FAS overlay (Método FAS): the child taps a word, hears each letter's SOUND,
 * then the sounds blended into syllables, then the whole word.
 *
 * - [data-decodable]   : every word becomes a <button class="decode-word">.
 * - [data-decode-text] : text drawn by other scripts (reading practice); a tap on a word is read by position,
 *                        so those scripts keep their own markup.
 * - [data-decode-option]: a button that opens the overlay for the word in its attribute.
 * - Maps come from {% decode_map %}: script#decode-map-*. A word that is not in any map is just spoken.
 * Events (bubbling, from the tapped element): decode:help {word} when it opens, decode:done {word} when the blend ends.
 */
(() => {
  const overlay = document.querySelector('[data-decode-overlay]');
  if (!overlay) return;

  const SKIP = 'button, input, textarea, select, script, style, [data-no-decode], .decode-word, [contenteditable]';
  const WORD = /[\p{L}́̈]+/gu;
  const STEP_MS = 650; // minimum visual beat per step, so it reads without sound too
  const BLEND_RATE = 0.7;

  const lettersBox = overlay.querySelector('[data-decode-letters]');
  const wholeBox = overlay.querySelector('[data-decode-whole]');
  const blendButton = overlay.querySelector('[data-decode-blend]');
  const againButton = overlay.querySelector('[data-decode-again]');
  const closeButton = overlay.querySelector('[data-decode-close]');

  let token = 0;
  let current = null; // {word, entry, source, letterNodes}
  let activeAudio = null;

  const speech = () => window.AppSpeech;
  const normalize = (word) => word.normalize('NFC').toLowerCase();

  /* ---------- decode maps ---------- */
  const lookup = (word) => {
    for (const node of document.querySelectorAll('script[id^="decode-map-"]')) {
      if (!node.decodeMap) {
        try {
          node.decodeMap = JSON.parse(node.textContent || '{}');
        } catch (error) {
          node.decodeMap = {};
        }
      }
      if (node.decodeMap[word]) return node.decodeMap[word];
    }
    return null;
  };

  /* ---------- sound playback ---------- */
  const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

  const stopSound = () => {
    if (activeAudio) {
      activeAudio.pause();
      activeAudio = null;
    }
    window.speechSynthesis?.cancel();
  };

  const playFile = (url) =>
    new Promise((resolve) => {
      const audio = new Audio(url);
      activeAudio = audio;
      const finish = () => resolve();
      audio.addEventListener('ended', finish);
      audio.addEventListener('error', finish);
      audio.play().catch(finish);
      window.setTimeout(finish, 4000);
    });

  const say = (items, rate) =>
    speech()?.speakSequence ? speech().speakSequence(items, {rate, gapMs: 120}) : Promise.resolve();

  const playLetter = (letter) => {
    if (letter.audio) return playFile(letter.audio);
    if (!letter.say) return Promise.resolve(); // silent letter (h, u in "gue")
    return say([letter.say], BLEND_RATE);
  };

  /* ---------- overlay ---------- */
  const clearMarks = () => lettersBox.querySelectorAll('.is-sounding').forEach((n) => n.classList.remove('is-sounding'));

  const render = (word, entry) => {
    lettersBox.textContent = '';
    wholeBox.textContent = '';
    againButton.hidden = true;
    const nodes = [];
    if (entry) {
      entry.letters.forEach((letter, index) => {
        if (index) {
          const dot = document.createElement('span');
          dot.className = 'decode-sep';
          dot.setAttribute('aria-hidden', 'true');
          dot.textContent = '·';
          lettersBox.append(dot);
        }
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'decode-letter';
        button.textContent = letter.text;
        button.setAttribute('aria-label', `Letra ${letter.text}`);
        button.addEventListener('click', () => {
          token += 1;
          stopSound();
          clearMarks();
          button.classList.add('is-sounding');
          playLetter(letter).then(() => button.classList.remove('is-sounding'));
        });
        lettersBox.append(button);
        nodes.push(button);
      });
    } else {
      wholeBox.textContent = word;
    }
    return nodes;
  };

  // Letter index ranges per syllable, found by consuming letters until the syllable text is covered.
  const syllableRanges = (entry) => {
    const ranges = [];
    let cursor = 0;
    entry.syllables.forEach((syllable) => {
      let text = '';
      const start = cursor;
      while (cursor < entry.letters.length && text.length < syllable.text.length) {
        text += entry.letters[cursor].text;
        cursor += 1;
      }
      ranges.push([start, cursor]);
    });
    return ranges;
  };

  const mark = (nodes, from, to, on) => {
    for (let i = from; i < to; i += 1) nodes[i]?.classList.toggle('is-sounding', on);
  };

  const beat = (promise) => Promise.all([promise, wait(STEP_MS)]);

  const announce = (word) => {
    window.Mascot?.react('cheer', {say: `¡Muy bien! Ya sabes leer «${word}».`});
  };

  const blend = async () => {
    if (!current) return;
    const run = ++token;
    const {word, entry, source, letterNodes} = current;
    stopSound();
    clearMarks();
    const alive = () => run === token;
    blendButton.disabled = true;
    againButton.hidden = true;
    wholeBox.textContent = '';
    try {
      if (entry) {
        const ranges = syllableRanges(entry);
        for (let s = 0; s < entry.syllables.length; s += 1) {
          const syllable = entry.syllables[s];
          const [from, to] = ranges[s];
          mark(letterNodes, from, to, true);
          for (const index of syllable.blend) {
            if (!alive()) return;
            await beat(playLetter(entry.letters[index]));
          }
          if (!alive()) return;
          wholeBox.textContent = entry.syllables.slice(0, s + 1).map((item) => item.text).join(' · ');
          await beat(say([syllable.text], BLEND_RATE));
          mark(letterNodes, from, to, false);
        }
      }
      if (!alive()) return;
      wholeBox.textContent = word;
      await beat(say([word]));
      if (!alive()) return;
      announce(word);
      againButton.hidden = false;
      source.dispatchEvent(new CustomEvent('decode:done', {bubbles: true, detail: {word}}));
    } finally {
      if (alive()) {
        blendButton.disabled = false;
        clearMarks();
      }
    }
  };

  const open = (rawWord, source) => {
    const word = normalize(String(rawWord || '').trim());
    if (!word) return;
    token += 1;
    stopSound();
    const entry = lookup(word);
    current = {word, entry, source: source || document, letterNodes: []};
    current.letterNodes = render(word, entry);
    blendButton.disabled = false;
    if (typeof overlay.showModal === 'function') {
      if (!overlay.open) overlay.showModal();
    } else {
      overlay.setAttribute('open', '');
    }
    current.source.dispatchEvent(new CustomEvent('decode:help', {bubbles: true, detail: {word}}));
    window.Mascot?.react('encourage', {say: '¡Vamos a leerla juntos!'});
    if (!entry) {
      say([word]);
      againButton.hidden = false;
    }
  };

  const close = () => {
    token += 1;
    stopSound();
    clearMarks();
    if (overlay.open) overlay.close();
    else overlay.removeAttribute('open');
  };

  blendButton.addEventListener('click', blend);
  againButton.addEventListener('click', blend);
  closeButton.addEventListener('click', close);
  overlay.addEventListener('close', () => {
    token += 1;
    stopSound();
  });
  overlay.addEventListener('click', (event) => {
    if (event.target === overlay) close(); // the dim backdrop
  });

  /* ---------- making text tappable ---------- */
  const wrap = (root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.nodeValue.trim() && !node.parentElement.closest(SKIP)) nodes.push(node);
    }
    nodes.forEach((node) => {
      const text = node.nodeValue;
      const fragment = document.createDocumentFragment();
      let last = 0;
      for (const match of text.matchAll(WORD)) {
        if (match.index > last) fragment.append(text.slice(last, match.index));
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'decode-word';
        button.dataset.word = normalize(match[0]);
        button.textContent = match[0];
        fragment.append(button);
        last = match.index + match[0].length;
      }
      if (last < text.length) fragment.append(text.slice(last));
      node.replaceWith(fragment);
    });
  };

  const wordAt = (x, y) => {
    let node;
    let offset;
    if (document.caretPositionFromPoint) {
      const position = document.caretPositionFromPoint(x, y);
      node = position?.offsetNode;
      offset = position?.offset;
    } else if (document.caretRangeFromPoint) {
      const range = document.caretRangeFromPoint(x, y);
      node = range?.startContainer;
      offset = range?.startOffset;
    }
    if (!node || node.nodeType !== Node.TEXT_NODE) return '';
    for (const match of node.nodeValue.matchAll(WORD)) {
      if (offset >= match.index && offset <= match.index + match[0].length) return match[0];
    }
    return '';
  };

  document.addEventListener('click', (event) => {
    const button = event.target.closest('.decode-word');
    if (button) {
      open(button.dataset.word, button);
      return;
    }
    const option = event.target.closest('[data-decode-option]');
    if (option) {
      open(option.dataset.decodeOption, option);
      return;
    }
    const container = event.target.closest('[data-decode-text]');
    if (container && !event.target.closest('button, a, input, select, textarea')) {
      const word = wordAt(event.clientX, event.clientY);
      if (word) open(word, container);
    }
  });

  document.querySelectorAll('[data-decodable]').forEach(wrap);

  window.Decode = {open};
})();
