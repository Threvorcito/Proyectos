(() => {
  const preferredLanguages = ['es-MX', 'es-ES', 'es-US'];
  const missingSpanishVoiceMessage = 'Este navegador no tiene una voz en español disponible. Para escuchar mejor, usa Chrome o Edge.';
  let voices = [];
  let speakToken = 0;
  let noticeTimeout = null;

  const normalizeLanguage = (language) => (language || '').toLowerCase();

  const loadVoices = () => {
    if (!('speechSynthesis' in window)) return [];
    voices = window.speechSynthesis.getVoices() || [];
    return voices;
  };

  const voiceScore = (voice) => {
    const language = normalizeLanguage(voice.lang);
    const exactIndex = preferredLanguages.findIndex((preferred) => normalizeLanguage(preferred) === language);
    if (exactIndex !== -1) return exactIndex;
    return language.startsWith('es-') || language === 'es' ? preferredLanguages.length : preferredLanguages.length + 1;
  };

  const selectSpanishVoice = () => {
    const availableVoices = voices.length ? voices : loadVoices();
    const spanishVoices = availableVoices.filter((voice) => voiceScore(voice) <= preferredLanguages.length);
    if (!spanishVoices.length) return null;
    return spanishVoices.sort((first, second) => voiceScore(first) - voiceScore(second))[0];
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

  const speak = (text, options = {}) => {
    if (!('speechSynthesis' in window) || !text) return;
    const currentToken = ++speakToken;
    window.speechSynthesis.cancel();
    const startSpeaking = (retried = false) => {
      if (currentToken !== speakToken) return;
      const voice = selectSpanishVoice();
      if (!voice && !voices.length && !retried) {
        window.setTimeout(() => startSpeaking(true), 250);
        return;
      }
      if (!voice) {
        showSpeechNotice(missingSpanishVoiceMessage);
        return;
      }
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = voice.lang || options.lang || 'es-MX';
      utterance.rate = options.rate || 0.85;
      utterance.voice = voice;
      window.speechSynthesis.speak(utterance);
    };
    window.setTimeout(() => startSpeaking(), 40);
  };

  loadVoices();
  if ('speechSynthesis' in window) {
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices);
  }
  window.AppSpeech = {speak, loadVoices};
})();

(() => {
  const buttons = document.querySelectorAll('[data-speak-text]');
  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      window.AppSpeech?.speak(button.dataset.speakText || '');
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
