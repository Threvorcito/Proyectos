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
  const nameInput = document.querySelector('[data-teacher-name]');
  const emailInput = document.querySelector('[data-teacher-email]');
  const usernameInput = document.querySelector('[data-teacher-username]');
  if (!usernameInput) return;

  const slugify = (value) => value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/@.*$/, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 28);

  const suggestUsername = () => {
    if (usernameInput.dataset.touched === 'true') return;
    const source = emailInput?.value || nameInput?.value || '';
    usernameInput.value = slugify(source);
  };

  usernameInput.addEventListener('input', () => {
    usernameInput.dataset.touched = usernameInput.value ? 'true' : 'false';
  });
  nameInput?.addEventListener('input', suggestUsername);
  emailInput?.addEventListener('input', suggestUsername);
})();
