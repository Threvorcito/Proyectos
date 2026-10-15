(() => {
  /*
   * Shared voice for every child screen. The Web Speech API exposes no voice
   * gender, so pleasant female Spanish voices are ranked by name across
   * platforms (Edge/Windows, Chrome, Apple, Android), Latin American first.
   */
  const missingSpanishVoiceMessage = 'Este navegador no tiene una voz en español disponible. Para escuchar mejor, usa Chrome o Edge.';
  const VOICE_STORAGE_KEY = 'lsl_voice';
  const DEFAULT_RATE = 0.9;
  const DEFAULT_PITCH = 1.1;
  // Ranked female voice names (accent-free, lowercase). The order only breaks ties.
  const FEMALE_NAMES = [
    'dalia', 'paloma', 'salome', 'elena', 'larissa', 'renata', 'beatriz', 'candela', 'carlota', 'marina', 'nuria',
    'catalina', 'camila', 'paola', 'valentina', 'andrea', 'lorena', 'marta', 'sofia', 'tania', 'maria', 'margarita',
    'ramona', 'karla', 'yolanda', 'karina', 'belkys', 'teresa',
    'sabina', 'helena', 'laura',
    'paulina', 'monica', 'marisol', 'angelica', 'soledad', 'isabela',
    'elvira', 'abril', 'arabella', 'estrella', 'irene', 'laia', 'lia', 'triana', 'vera', 'ximena',
    'es-us-x-sfb', 'es-us-x-esc', 'es-us-x-esf', 'es-es-x-eea', 'es-es-x-eec', 'es-es-x-eef',
  ];
  const MALE_NAMES = [
    'raul', 'jorge', 'pablo', 'diego', 'juan', 'carlos', 'enrique', 'alvaro', 'gerardo', 'alonso', 'gonzalo', 'tomas',
    'cecilio', 'liberto', 'luciano', 'pelayo', 'yago', 'arnau', 'dario', 'elias', 'nil', 'saul', 'teo', 'lorenzo',
    'alex', 'sebastian', 'mateo', 'luis', 'rodrigo', 'andres', 'marcelo', 'mario', 'roberto', 'emilio', 'federico',
    'victor', 'manuel', 'javier', 'eddy', 'reed', 'rocko', 'grandpa', 'es-us-x-esd', 'es-es-x-eed',
  ];
  const REGION_RANK = {mx: 0, us: 1, 419: 2, co: 3, ar: 4, es: 6};
  const LATAM = ['cl', 'pe', 've', 'uy', 'ec', 'sv', 'gt', 'bo', 'py', 'cr', 'pa', 'do', 'hn', 'ni', 'pr', 'cu'];
  const REGION_LABELS = {
    mx: 'México', us: 'Estados Unidos', 419: 'Latinoamérica', co: 'Colombia', ar: 'Argentina', es: 'España',
    cl: 'Chile', pe: 'Perú', ve: 'Venezuela', uy: 'Uruguay', ec: 'Ecuador', sv: 'El Salvador', gt: 'Guatemala',
    bo: 'Bolivia', py: 'Paraguay', cr: 'Costa Rica', pa: 'Panamá', do: 'República Dominicana', hn: 'Honduras',
    ni: 'Nicaragua', pr: 'Puerto Rico', cu: 'Cuba', gq: 'Guinea Ecuatorial',
  };
  let voices = [];
  let speakToken = 0;
  let noticeTimeout = null;
  const listeners = [];

  const fold = (text) => (text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const langOf = (voice) => fold(voice.lang).replace('_', '-');
  const isSpanish = (voice) => {
    const lang = langOf(voice);
    return lang === 'es' || lang.startsWith('es-');
  };
  const regionOf = (voice) => langOf(voice).split('-')[1] || '';
  const nameMatchers = (names) => names.map((name) => new RegExp(`(^|[^a-z])${name.replace(/-/g, '\\-')}([^a-z]|$)`));
  const FEMALE_MATCHERS = nameMatchers(FEMALE_NAMES);
  const MALE_MATCHERS = nameMatchers(MALE_NAMES);

  // Lower is better: [gender tier, quality tier, region rank, name rank].
  const rankOf = (voice) => {
    const name = fold(voice.name);
    const femaleIndex = FEMALE_MATCHERS.findIndex((matcher) => matcher.test(name));
    // Every Google Spanish voice is female.
    const female = femaleIndex !== -1 || name.startsWith('google');
    const male = !female && MALE_MATCHERS.some((matcher) => matcher.test(name));
    const quality = /natural|online|neural|google|premium|enhanced|mejorada/.test(name) ? 0 : 1;
    const region = regionOf(voice);
    let regionRank = 8;
    if (region in REGION_RANK) regionRank = REGION_RANK[region];
    else if (LATAM.includes(region)) regionRank = 5;
    else if (!region) regionRank = 7;
    return [female ? 0 : (male ? 2 : 1), quality, regionRank, femaleIndex === -1 ? FEMALE_NAMES.length : femaleIndex];
  };
  const compareVoices = (first, second) => {
    const a = rankOf(first);
    const b = rankOf(second);
    for (let index = 0; index < a.length; index += 1) {
      if (a[index] !== b[index]) return a[index] - b[index];
    }
    return Number(second.localService) - Number(first.localService);
  };

  const loadVoices = () => {
    if (!('speechSynthesis' in window)) return [];
    voices = window.speechSynthesis.getVoices() || [];
    return voices;
  };

  const spanishVoices = () => (voices.length ? voices : loadVoices()).filter(isSpanish).sort(compareVoices);
  const voiceId = (voice) => voice.voiceURI || voice.name;
  const isRecommended = (voice) => rankOf(voice)[0] === 0;

  const readStoredVoice = () => {
    try {
      return window.localStorage.getItem(VOICE_STORAGE_KEY) || '';
    } catch (error) {
      return '';
    }
  };
  let chosenVoiceId = readStoredVoice();
  const setPreferredVoice = (id) => {
    chosenVoiceId = id || '';
    try {
      if (chosenVoiceId) window.localStorage.setItem(VOICE_STORAGE_KEY, chosenVoiceId);
      else window.localStorage.removeItem(VOICE_STORAGE_KEY);
    } catch (error) {
      // Storage blocked: the choice lasts for this page only.
    }
  };

  // The child's chosen voice when this browser has it, else the best ranked one.
  const pickVoice = () => {
    const ranked = spanishVoices();
    if (!ranked.length) return null;
    return (chosenVoiceId && ranked.find((voice) => voiceId(voice) === chosenVoiceId)) || ranked[0];
  };

  const friendlyLabel = (voice) => {
    let name = (voice.name || '').replace(/^(microsoft|google|apple)\s+/i, '');
    if (!/^espa/i.test(name)) name = name.split(/\s+(?:online|desktop|\(|-)/i)[0];
    const region = REGION_LABELS[regionOf(voice)];
    return region && !fold(name).includes(fold(region)) ? `${name} · ${region}` : name;
  };

  const showSpeechNotice = (message) => {
    let notice = document.querySelector('[data-speech-notice]');
    if (!notice) {
      notice = document.createElement('div');
      notice.className = 'alert alert-warning position-fixed bottom-0 start-50 translate-middle-x mb-4 shadow';
      notice.setAttribute('role', 'status');
      notice.setAttribute('data-speech-notice', '');
      notice.style.zIndex = '1080';
      document.body.appendChild(notice);
    }
    notice.textContent = message;
    notice.hidden = false;
    window.clearTimeout(noticeTimeout);
    noticeTimeout = window.setTimeout(() => {
      notice.hidden = true;
    }, 5000);
  };

  // options.onend({cancelled}) runs once: on utterance end or error, when a newer speak() replaced this
  // one (cancelled: true), or at once when speech is unavailable.
  // Some engines never fire `end`, and Chrome may collect an utterance that nobody references.
  let currentUtterance = null;
  const speak = (text, options = {}) => {
    let finished = false;
    let safety = 0;
    const finish = (cancelled) => {
      if (finished) return;
      finished = true;
      window.clearTimeout(safety);
      if (typeof options.onend === 'function') options.onend({cancelled});
    };
    if (!('speechSynthesis' in window) || !text) {
      finish(false);
      return;
    }
    const currentToken = ++speakToken;
    window.speechSynthesis.cancel();
    const startSpeaking = (retried = false) => {
      if (currentToken !== speakToken) {
        finish(true);
        return;
      }
      const voice = pickVoice();
      if (!voice && !voices.length && !retried) {
        window.setTimeout(() => startSpeaking(true), 250);
        return;
      }
      if (!voice) {
        showSpeechNotice(missingSpanishVoiceMessage);
        finish(false);
        return;
      }
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = voice.lang || options.lang || 'es-MX';
      utterance.rate = options.rate || DEFAULT_RATE;
      utterance.pitch = options.pitch || DEFAULT_PITCH;
      utterance.voice = voice;
      const ended = () => finish(currentToken !== speakToken);
      utterance.addEventListener('end', ended);
      utterance.addEventListener('error', ended);
      currentUtterance = utterance;
      safety = window.setTimeout(() => finish(false), Math.max(1500, 120 * text.length) / (options.rate || 1));
      window.speechSynthesis.speak(utterance);
    };
    window.setTimeout(() => startSpeaking(), 40);
  };

  // Speaks the items one after another; resolves when done, or early when something else spoke over it.
  const speakSequence = (items, options = {}) =>
    new Promise((resolve) => {
      const gapMs = options.gapMs ?? 250;
      const queue = items.filter(Boolean);
      const next = () => {
        if (!queue.length) {
          resolve();
          return;
        }
        speak(queue.shift(), {
          rate: options.rate,
          onend: ({cancelled}) => {
            if (cancelled) resolve();
            else window.setTimeout(next, queue.length ? gapMs : 0);
          },
        });
      };
      next();
    });

  const onVoicesChanged = (callback) => listeners.push(callback);

  loadVoices();
  if ('speechSynthesis' in window) {
    // Chrome loads voices asynchronously.
    window.speechSynthesis.addEventListener('voiceschanged', () => {
      loadVoices();
      listeners.forEach((callback) => callback());
    });
  }
  window.AppSpeech = {
    speak,
    speakSequence,
    loadVoices,
    pickVoice,
    spanishVoices,
    isRecommended,
    friendlyLabel,
    voiceId,
    setPreferredVoice,
    getPreferredVoice: () => chosenVoiceId,
    onVoicesChanged,
  };
})();

(() => {
  // "Voz" chooser in the reading settings panel.
  const select = document.querySelector('[data-voice-select]');
  const preview = document.querySelector('[data-voice-preview]');
  const speech = window.AppSpeech;
  if (!select || !speech) return;

  const render = () => {
    const ranked = speech.spanishVoices();
    select.textContent = '';
    if (!ranked.length) {
      select.append(new Option('No hay voces en español en este navegador', ''));
      select.disabled = true;
      if (preview) preview.disabled = true;
      return;
    }
    const current = speech.pickVoice();
    ranked.forEach((voice, index) => {
      const label = speech.friendlyLabel(voice);
      const option = new Option(index === 0 && speech.isRecommended(voice) ? `${label} (Recomendada)` : label, speech.voiceId(voice));
      option.selected = voice === current;
      select.append(option);
    });
    select.disabled = false;
    if (preview) preview.disabled = false;
  };

  select.addEventListener('change', () => speech.setPreferredVoice(select.value));
  preview?.addEventListener('click', () => speech.speak('¡Hola! Vamos a leer juntos.'));
  document.querySelector('[data-accessibility-reset]')?.addEventListener('click', () => {
    speech.setPreferredVoice('');
    render();
  });
  speech.onVoicesChanged(render);
  render();
})();

(() => {
  const buttons = document.querySelectorAll('[data-speak-text]');
  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      window.AppSpeech?.speak(button.dataset.speakText || '');
    });
  });

  // Audio cue buttons that read the visible instruction they sit next to,
  // so the spoken words never drift from the on-screen copy.
  const readVisibleText = (selector) => Array.from(document.querySelectorAll(selector))
    .map((node) => {
      const clone = node.cloneNode(true);
      clone.querySelectorAll('.kid-listen, [aria-hidden="true"], .visually-hidden').forEach((item) => item.remove());
      // A short pause after each heading or line, so the voice does not run them together.
      clone.querySelectorAll('h1, h2, h3, h4, p, li, .eyebrow, small').forEach((item) => {
        if (!/[.!?:]\s*$/.test(item.textContent)) item.append('. ');
        else item.append(' ');
      });
      return clone.textContent.replace(/\s+/g, ' ').trim();
    })
    .filter(Boolean)
    .join('. ');

  document.querySelectorAll('[data-speak-from]').forEach((button) => {
    button.addEventListener('click', () => {
      window.AppSpeech?.speak(readVisibleText(button.dataset.speakFrom));
    });
  });
})();

(() => {
  const alerts = document.querySelectorAll('[data-auto-dismiss-message]');
  alerts.forEach((alert) => {
    window.setTimeout(() => {
      const bootstrapAlert = window.bootstrap?.Alert.getOrCreateInstance(alert);
      if (bootstrapAlert) {
        bootstrapAlert.close();
        return;
      }
      alert.remove();
    }, 3500);
  });
})();

(() => {
  const dialogs = document.querySelectorAll('[data-permission-dialog]');
  dialogs.forEach((dialog) => {
    const selectAll = dialog.querySelector('[data-permission-select-all]');
    const checkboxes = dialog.querySelectorAll('[data-permission-checkbox]');
    if (!selectAll || !checkboxes.length) return;

    const syncSelectAll = () => {
      selectAll.checked = Array.from(checkboxes).every((checkbox) => checkbox.checked);
    };

    selectAll.addEventListener('change', () => {
      checkboxes.forEach((checkbox) => {
        checkbox.checked = selectAll.checked;
      });
    });
    checkboxes.forEach((checkbox) => checkbox.addEventListener('change', syncSelectAll));
    syncSelectAll();
  });
})();

(() => {
  const forms = document.querySelectorAll('[data-submit-once]');
  forms.forEach((form) => {
    form.addEventListener('submit', () => {
      const submitButton = form.querySelector('button[type="submit"]');
      if (!submitButton || submitButton.disabled) return;
      submitButton.disabled = true;
      submitButton.dataset.originalText = submitButton.textContent;
      submitButton.textContent = 'Guardando...';
    });
  });
})();
