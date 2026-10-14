/*
 * Repeated reading practice ("Practicar lectura").
 *
 * Step 1 plays a spoken model of the text while highlighting it. The Web Speech
 * API `boundary` event is unreliable (it never fires on Chrome for Android or
 * with remote voices), so the text is spoken one short chunk at a time: the
 * active chunk is always highlighted, and the active word is estimated from the
 * elapsed time and the character position inside the chunk. When real
 * boundary events arrive they take over. If speech never starts, the same
 * timer drives a silent, visual-only guide.
 *
 * Step 2 times three reads without showing any clock. Step 3 draws the child's
 * own speed as an inline SVG bar chart.
 */
(() => {
  const root = document.querySelector('[data-reading-practice]');
  const textSource = document.getElementById('reading-practice-text');
  if (!root || !textSource) return;

  const fullText = JSON.parse(textSource.textContent || '""');
  const saveUrl = root.dataset.saveUrl || '';
  const totalReads = Number(root.dataset.reads || 3);
  const minMs = Number(root.dataset.minMs || 2000);
  const maxMs = Number(root.dataset.maxMs || 900000);
  const WORD = /[\p{L}\p{N}]+/gu;
  const MAX_CHUNK_WORDS = 12;
  // Slightly slower than the rest of the app: this voice models fluent reading.
  const SPEECH_RATE = 0.85;
  const SPEECH_PITCH = 1.05;

  const $ = (selector) => root.querySelector(selector);
  const steps = {
    listen: $('[data-practice-step="listen"]'),
    read: $('[data-practice-step="read"]'),
    result: $('[data-practice-step="result"]'),
  };
  const announcer = $('[data-practice-announce]');
  const stepMarkers = root.querySelectorAll('[data-practice-marker]');
  const listenText = $('[data-practice-text]');
  const readText = $('[data-practice-read-text]');
  const ttsNote = $('[data-practice-tts-note]');
  const playButton = $('[data-practice-play]');
  const restartButton = $('[data-practice-restart]');
  const toReadButton = $('[data-practice-to-read]');
  const startButton = $('[data-practice-start]');
  const finishButton = $('[data-practice-finish]');
  const listenAgainButton = $('[data-practice-listen-again]');
  const readDots = root.querySelectorAll('[data-practice-dot]');
  const readLabel = $('[data-practice-read-label]');
  const readMessage = $('[data-practice-message]');
  const chart = $('[data-practice-chart]');
  const celebration = $('[data-practice-celebration]');
  const pointsNote = $('[data-practice-points]');
  const againButton = $('[data-practice-again]');

  const synth = 'speechSynthesis' in window ? window.speechSynthesis : null;

  /* ---------- text model: paragraphs -> chunks -> words ---------- */

  const splitIntoChunks = (paragraph) => {
    const sentences = paragraph.match(/[^.!?…;:]+[.!?…;:]*["'»”)\]]*\s*/g) || [paragraph];
    const chunks = [];
    sentences.forEach((sentence) => {
      const pieces = sentence.split(/(?<=,)\s+/);
      let buffer = '';
      pieces.forEach((piece) => {
        const candidate = buffer ? `${buffer} ${piece}` : piece;
        if ((candidate.match(WORD) || []).length > MAX_CHUNK_WORDS && buffer) {
          chunks.push(buffer);
          buffer = piece;
        } else {
          buffer = candidate;
        }
      });
      if (buffer) chunks.push(buffer);
    });
    // Very long clauses without commas: cut every MAX_CHUNK_WORDS words.
    return chunks.flatMap((chunk) => {
      const words = chunk.trim().split(/\s+/);
      if (words.length <= MAX_CHUNK_WORDS + 2) return [chunk.trim()];
      const parts = [];
      for (let index = 0; index < words.length; index += MAX_CHUNK_WORDS) {
        parts.push(words.slice(index, index + MAX_CHUNK_WORDS).join(' '));
      }
      return parts;
    }).filter((chunk) => (chunk.match(WORD) || []).length > 0);
  };

  const buildListenText = () => {
    const chunks = [];
    fullText.split(/\n+/).map((line) => line.trim()).filter(Boolean).forEach((paragraph) => {
      const paragraphEl = document.createElement('p');
      splitIntoChunks(paragraph).forEach((chunkText, chunkIndex) => {
        if (chunkIndex) paragraphEl.appendChild(document.createTextNode(' '));
        const chunkEl = document.createElement('span');
        chunkEl.className = 'practice-chunk';
        const words = [];
        let cursor = 0;
        chunkText.replace(WORD, (match, offset) => {
          if (offset > cursor) chunkEl.appendChild(document.createTextNode(chunkText.slice(cursor, offset)));
          const wordEl = document.createElement('span');
          wordEl.className = 'practice-word';
          wordEl.textContent = match;
          chunkEl.appendChild(wordEl);
          words.push({el: wordEl, start: offset});
          cursor = offset + match.length;
          return match;
        });
        if (cursor < chunkText.length) chunkEl.appendChild(document.createTextNode(chunkText.slice(cursor)));
        paragraphEl.appendChild(chunkEl);
        chunks.push({text: chunkText, el: chunkEl, words});
      });
      listenText.appendChild(paragraphEl);
    });
    return chunks;
  };

  const buildReadText = () => {
    fullText.split(/\n+/).map((line) => line.trim()).filter(Boolean).forEach((paragraph) => {
      const paragraphEl = document.createElement('p');
      paragraphEl.textContent = paragraph;
      readText.appendChild(paragraphEl);
    });
  };

  const chunks = buildListenText();
  buildReadText();
  const localWordCount = (fullText.match(WORD) || []).length;

  /* ---------- step navigation ---------- */

  const announce = (message) => {
    if (!announcer) return;
    announcer.textContent = '';
    window.setTimeout(() => { announcer.textContent = message; }, 60);
  };

  const showStep = (name, message) => {
    Object.entries(steps).forEach(([key, el]) => { el.hidden = key !== name; });
    stepMarkers.forEach((marker) => {
      const isCurrent = marker.dataset.practiceMarker === name;
      if (isCurrent) marker.setAttribute('aria-current', 'step');
      else marker.removeAttribute('aria-current');
    });
    const heading = steps[name].querySelector('h2');
    if (heading) heading.focus({preventScroll: false});
    announce(message);
  };

  /* ---------- step 1: spoken model with highlighting ---------- */

  let voice = null;
  let mode = 'idle'; // idle | playing | paused | done
  let silent = false;
  let chunkIndex = 0;
  let token = 0;
  let msPerChar = 1000 / 12; // calibrated after each spoken chunk
  let tickTimer = null;
  let watchTimers = [];

  // Same voice as every other child screen (ranked female Spanish voice or the child's choice).
  const pickVoice = () => {
    if (!synth) return null;
    if (window.AppSpeech?.pickVoice) return window.AppSpeech.pickVoice();
    return synth.getVoices().find((candidate) => (candidate.lang || '').toLowerCase().startsWith('es')) || null;
  };

  const clearTimers = () => {
    window.clearInterval(tickTimer);
    tickTimer = null;
    watchTimers.forEach((timer) => window.clearTimeout(timer));
    watchTimers = [];
  };

  const clearHighlight = () => {
    listenText.querySelectorAll('.is-active').forEach((el) => el.classList.remove('is-active'));
  };

  const highlightWord = (chunk, charIndex) => {
    let active = chunk.words[0];
    chunk.words.forEach((word) => { if (word.start <= charIndex) active = word; });
    chunk.words.forEach((word) => word.el.classList.toggle('is-active', word === active));
  };

  const highlightChunk = (chunk) => {
    clearHighlight();
    chunk.el.classList.add('is-active');
    highlightWord(chunk, 0);
    const box = chunk.el.getBoundingClientRect();
    if (box.top < 0 || box.bottom > window.innerHeight) {
      const reduce = document.body.classList.contains('reduce-motion') || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      chunk.el.scrollIntoView({block: 'center', behavior: reduce ? 'auto' : 'smooth'});
    }
  };

  const estimateMs = (chunk) => Math.max(900, chunk.text.length * msPerChar);

  const startEstimatedWords = (chunk, myToken) => {
    const started = performance.now();
    const total = estimateMs(chunk);
    window.clearInterval(tickTimer);
    tickTimer = window.setInterval(() => {
      if (myToken !== token) return;
      const progress = Math.min(1, (performance.now() - started) / total);
      highlightWord(chunk, Math.floor(progress * chunk.text.length));
    }, 90);
  };

  const setPlayLabel = (label, icon) => {
    playButton.querySelector('[data-label]').textContent = label;
    playButton.querySelectorAll('[data-icon]').forEach((el) => { el.hidden = el.dataset.icon !== icon; });
  };

  const finishListening = () => {
    clearTimers();
    clearHighlight();
    mode = 'done';
    setPlayLabel('Escuchar otra vez', 'play');
    toReadButton.classList.add('is-ready');
    toReadButton.focus();
    announce('¡Listo! Ahora lees tú.');
  };

  const showTtsNote = (message) => {
    ttsNote.textContent = message;
    ttsNote.hidden = false;
  };

  const goSilent = () => {
    if (silent) return;
    silent = true;
    showTtsNote('No se oye la voz en este equipo. Sigue con los ojos las palabras que se iluminan, o pide a un adulto que lea contigo.');
  };

  const playChunk = (index) => {
    clearTimers();
    if (index >= chunks.length) {
      finishListening();
      return;
    }
    chunkIndex = index;
    const myToken = ++token;
    const chunk = chunks[index];
    highlightChunk(chunk);
    const next = () => {
      if (myToken !== token) return;
      watchTimers.push(window.setTimeout(() => playChunk(index + 1), 250));
    };

    if (silent || !voice) {
      startEstimatedWords(chunk, myToken);
      watchTimers.push(window.setTimeout(next, estimateMs(chunk)));
      return;
    }

    let startedAt = 0;
    let usedBoundary = false;
    const utterance = new SpeechSynthesisUtterance(chunk.text);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.rate = SPEECH_RATE;
    utterance.pitch = SPEECH_PITCH;
    utterance.onstart = () => {
      if (myToken !== token) return;
      startedAt = performance.now();
      startEstimatedWords(chunk, myToken);
      // Some engines never fire `end`; move on after a generous wait.
      watchTimers.push(window.setTimeout(next, estimateMs(chunk) * 2.5 + 3000));
    };
    utterance.onboundary = (event) => {
      if (myToken !== token || (event.name && event.name !== 'word')) return;
      usedBoundary = true;
      window.clearInterval(tickTimer);
      highlightWord(chunk, event.charIndex || 0);
    };
    utterance.onend = () => {
      if (myToken !== token) return;
      if (startedAt && !usedBoundary) {
        const measured = (performance.now() - startedAt) / Math.max(1, chunk.text.length);
        if (measured > 20 && measured < 400) msPerChar = (msPerChar + measured) / 2;
      }
      next();
    };
    utterance.onerror = (event) => {
      if (myToken !== token || event.error === 'interrupted' || event.error === 'canceled') return;
      goSilent();
      playChunk(index);
    };
    // If speech never starts (no audio output, blocked engine), guide silently.
    watchTimers.push(window.setTimeout(() => {
      if (myToken !== token || startedAt) return;
      synth.cancel();
      goSilent();
      playChunk(index);
    }, 2500));
    synth.speak(utterance);
  };

  const stopSpeech = () => {
    token += 1;
    clearTimers();
    if (synth) synth.cancel();
  };

  const startListening = (fromIndex) => {
    stopSpeech();
    mode = 'playing';
    setPlayLabel('Pausa', 'pause');
    const begin = () => window.setTimeout(() => playChunk(fromIndex), 60);
    if (silent || !synth) {
      if (!synth) goSilent();
      begin();
      return;
    }
    voice = pickVoice();
    if (voice) {
      begin();
      return;
    }
    // Voices load asynchronously on first use.
    window.setTimeout(() => {
      voice = pickVoice();
      if (!voice) goSilent();
      if (mode === 'playing') begin();
    }, 400);
  };

  const pauseListening = () => {
    stopSpeech();
    mode = 'paused';
    setPlayLabel('Seguir', 'play');
  };

  playButton.addEventListener('click', () => {
    if (mode === 'playing') pauseListening();
    else if (mode === 'paused') startListening(chunkIndex);
    else startListening(0);
  });
  restartButton.addEventListener('click', () => startListening(0));

  /* ---------- step 2: three timed reads ---------- */

  const encouragements = [
    '¡Muy bien! Vamos otra vez.',
    '¡Genial! Ya casi terminas.',
    '¡Lo lograste!',
  ];
  let reads = [];
  let sessionId = null;
  let offline = !saveUrl;
  let readStartedAt = 0;
  let lastResult = null;

  const csrfToken = () => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  };

  const renderReadProgress = () => {
    readDots.forEach((dot, index) => {
      dot.classList.toggle('is-done', index < reads.length);
      dot.classList.toggle('is-current', index === reads.length);
    });
    const current = Math.min(reads.length + 1, totalReads);
    readLabel.textContent = `Lectura ${current} de ${totalReads}`;
  };

  const resetReadButtons = () => {
    readStartedAt = 0;
    startButton.hidden = false;
    startButton.disabled = false;
    finishButton.hidden = true;
    finishButton.disabled = false;
    listenAgainButton.hidden = false;
  };

  const goToRead = () => {
    stopSpeech();
    clearHighlight();
    if (mode === 'playing') mode = 'paused';
    setPlayLabel(mode === 'paused' ? 'Seguir' : 'Escuchar otra vez', 'play');
    resetReadButtons();
    renderReadProgress();
    readMessage.textContent = reads.length ? readMessage.textContent : 'Toca Empezar y lee en voz alta.';
    showStep('read', `Ahora lees tú. Lectura ${Math.min(reads.length + 1, totalReads)} de ${totalReads}.`);
  };

  const saveRead = async (attemptNumber, durationMs) => {
    if (offline) return null;
    try {
      const response = await fetch(saveUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken()},
        body: JSON.stringify({session_id: sessionId, attempt_number: attemptNumber, duration_ms: durationMs}),
      });
      const data = await response.json().catch(() => ({}));
      if (response.ok) return data;
      if (data.reason === 'duration') return {retry: true};
    } catch (error) {
      // Network problems should never stop the child; continue without saving.
    }
    offline = true;
    return null;
  };

  const askToRetry = (message) => {
    readMessage.textContent = message;
    resetReadButtons();
    startButton.focus();
    announce(message);
  };

  startButton.addEventListener('click', () => {
    readStartedAt = performance.now();
    startButton.hidden = true;
    listenAgainButton.hidden = true;
    finishButton.hidden = false;
    readMessage.textContent = 'Lee en voz alta. Al final, toca Terminé.';
    finishButton.focus();
  });

  finishButton.addEventListener('click', async () => {
    if (!readStartedAt) return;
    const durationMs = Math.round(performance.now() - readStartedAt);
    if (durationMs < minMs) {
      askToRetry('¡Uy, fue muy rápido! Lee todo el cuento y luego toca Terminé.');
      window.Mascot?.react('encourage', {say: 'Despacito se lee mejor. ¡Otra vez!'});
      return;
    }
    if (durationMs > maxMs) {
      askToRetry('Parece que hiciste una pausa larga. ¡Vamos otra vez!');
      return;
    }
    finishButton.disabled = true;
    const attemptNumber = reads.length + 1;
    const data = await saveRead(attemptNumber, durationMs);
    if (data && data.retry) {
      askToRetry('¡Uy, fue muy rápido! Lee todo el cuento y luego toca Terminé.');
      window.Mascot?.react('encourage', {say: 'Despacito se lee mejor. ¡Otra vez!'});
      return;
    }
    const wpm = data ? data.words_per_minute : Math.round((localWordCount * 60000) / durationMs);
    if (data) sessionId = data.session_id;
    reads.push(wpm);
    lastResult = data;
    if (reads.length >= totalReads) {
      showResult();
      return;
    }
    renderReadProgress();
    resetReadButtons();
    window.Mascot?.react('cheer', {say: '¡Muy bien leído!'});
    readMessage.textContent = encouragements[reads.length - 1] || encouragements[0];
    announce(`${readMessage.textContent} Lectura ${reads.length + 1} de ${totalReads}.`);
    startButton.focus();
  });

  listenAgainButton.addEventListener('click', () => {
    toReadButton.querySelector('[data-label]').textContent = reads.length ? 'Seguir leyendo' : '¡Ahora leo yo!';
    showStep('listen', 'Escucha otra vez.');
    startListening(0);
  });

  toReadButton.addEventListener('click', goToRead);

  /* ---------- step 3: personal growth chart ---------- */

  const SVG_NS = 'http://www.w3.org/2000/svg';
  const svgEl = (name, attrs, text) => {
    const el = document.createElementNS(SVG_NS, name);
    Object.entries(attrs || {}).forEach(([key, value]) => el.setAttribute(key, value));
    if (text !== undefined) el.textContent = text;
    return el;
  };

  const shortDate = (iso) => {
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? 'Antes' : `${date.getDate()}/${date.getMonth() + 1}`;
  };

  const drawChart = (history) => {
    const bars = history.map((item) => ({value: item.words_per_minute, label: 'Antes', sub: shortDate(item.date), past: true}))
      .concat(reads.map((value, index) => ({value, label: `Lectura ${index + 1}`, sub: 'hoy', past: false})));
    const barWidth = 64;
    const gap = 28;
    const groupGap = history.length ? 44 : 0;
    const top = 40;
    const plotHeight = 200;
    const bottom = 64;
    const width = bars.length * barWidth + (bars.length - 1) * gap + groupGap + 32;
    const height = top + plotHeight + bottom;
    const maxValue = Math.max(...bars.map((bar) => bar.value), 1);
    const descParts = bars.map((bar) => `${bar.label}${bar.past ? ` ${bar.sub}` : ''}: ${bar.value} palabras por minuto`);

    const svg = svgEl('svg', {viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-labelledby': 'practice-chart-title practice-chart-desc', class: 'practice-chart__svg'});
    svg.appendChild(svgEl('title', {id: 'practice-chart-title'}, 'Tus palabras por minuto'));
    svg.appendChild(svgEl('desc', {id: 'practice-chart-desc'}, `${descParts.join('. ')}.`));
    svg.appendChild(svgEl('line', {x1: 8, x2: width - 8, y1: top + plotHeight, y2: top + plotHeight, class: 'practice-chart__axis'}));

    let x = 16;
    bars.forEach((bar, index) => {
      if (index === history.length && history.length) x += groupGap;
      const barHeight = Math.max(6, Math.round((bar.value / maxValue) * plotHeight));
      const y = top + plotHeight - barHeight;
      const isLast = index === bars.length - 1;
      const rect = svgEl('rect', {
        x, y, width: barWidth, height: barHeight, rx: 10,
        class: `practice-chart__bar${bar.past ? ' practice-chart__bar--past' : ''}${isLast ? ' practice-chart__bar--last' : ''}`,
      });
      rect.style.setProperty('--bar-delay', `${index * 90}ms`);
      svg.appendChild(rect);
      svg.appendChild(svgEl('text', {x: x + barWidth / 2, y: y - 10, class: 'practice-chart__value', 'text-anchor': 'middle'}, String(bar.value)));
      svg.appendChild(svgEl('text', {x: x + barWidth / 2, y: top + plotHeight + 26, class: 'practice-chart__label', 'text-anchor': 'middle'}, bar.label));
      svg.appendChild(svgEl('text', {x: x + barWidth / 2, y: top + plotHeight + 48, class: 'practice-chart__sub', 'text-anchor': 'middle'}, bar.sub));
      x += barWidth + gap;
    });
    chart.replaceChildren(svg);
  };

  const showResult = () => {
    const history = (lastResult && lastResult.history) || [];
    drawChart(history);
    const first = reads[0];
    const last = reads[reads.length - 1];
    const improved = last > first;
    root.classList.toggle('is-celebrating', improved);
    celebration.querySelector('[data-label]').textContent = improved
      ? `¡Leíste más rápido la tercera vez! Pasaste de ${first} a ${last} palabras por minuto.`
      : '¡Buen trabajo! Cada vez que lees, tu lectura se hace más fuerte.';
    if (lastResult && lastResult.points_awarded) {
      const stars = lastResult.stars_awarded || 0;
      pointsNote.textContent = `Ganaste ${lastResult.points_awarded} puntos${stars ? ` y ${stars} estrella${stars > 1 ? 's' : ''}` : ''}.`;
    } else if (lastResult) {
      pointsNote.textContent = 'Hoy ya ganaste los puntos de este cuento. ¡Practicar siempre ayuda!';
    } else {
      pointsNote.textContent = '';
    }
    pointsNote.hidden = !pointsNote.textContent;
    showStep('result', `¡Mira cómo mejoraste! ${celebration.textContent}`);
    window.Mascot?.react('cheer', {say: improved ? '¡Leíste más rápido!' : '¡Tres lecturas! ¡Bravo!'});
  };

  againButton.addEventListener('click', () => {
    reads = [];
    sessionId = null;
    lastResult = null;
    offline = !saveUrl;
    mode = 'idle';
    root.classList.remove('is-celebrating');
    readMessage.textContent = '';
    toReadButton.classList.remove('is-ready');
    toReadButton.querySelector('[data-label]').textContent = '¡Ahora leo yo!';
    setPlayLabel('Escuchar', 'play');
    showStep('listen', 'Paso 1: escucha el cuento.');
  });

  /* ---------- public hooks for the mode switcher ---------- */

  window.ReadingPractice = {
    enter() {
      const current = Object.keys(steps).find((key) => !steps[key].hidden) || 'listen';
      const messages = {listen: 'Paso 1: escucha el cuento.', read: 'Paso 2: ahora lees tú.', result: 'Paso 3: mira cómo mejoraste.'};
      showStep(current, `Practicar lectura. ${messages[current]}`);
    },
    leave() {
      stopSpeech();
      clearHighlight();
      if (mode === 'playing') {
        mode = 'paused';
        setPlayLabel('Seguir', 'play');
      }
    },
  };
  if (!synth) showTtsNote('Este equipo no puede leer en voz alta. Pide a un adulto que lea contigo, o toca "¡Ahora leo yo!".');
  renderReadProgress();
})();

(() => {
  const switches = document.querySelectorAll('[data-reading-mode]');
  const panels = document.querySelectorAll('[data-reading-mode-panel]');
  if (!switches.length) return;
  switches.forEach((button) => {
    button.addEventListener('click', () => {
      const target = button.dataset.readingMode;
      document.querySelectorAll('.reading-modes [data-reading-mode]').forEach((item) => {
        item.setAttribute('aria-pressed', String(item.dataset.readingMode === target));
      });
      panels.forEach((panel) => { panel.hidden = panel.dataset.readingModePanel !== target; });
      if (target === 'practice') {
        window.speechSynthesis?.cancel();
        window.ReadingPractice?.enter();
      } else {
        window.ReadingPractice?.leave();
      }
    });
  });
})();
