// Admin dialogs ported from SistemaBodega: native <dialog> + showModal().
// Triggers: [data-dialog-open="<dialog id>"]; closers: [data-dialog-close].
// showModal() makes the rest of the page inert, so focus stays inside the
// dialog; focus returns to the trigger on close. Escape and backdrop clicks
// close the dialog unless its form is submitting.
(() => {
  const DIALOG = '[data-aui-dialog]';
  const CLOSE_MS = 180;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const returnFocus = new WeakMap();

  const firstFocusTarget = (dialog) =>
    dialog.querySelector('[autofocus]') ||
    dialog.querySelector('.dialog-body :is(input:not([type="hidden"]), select, textarea):not([disabled])') ||
    dialog.querySelector('.dialog-footer button:not([disabled])') ||
    dialog.querySelector('[data-dialog-close]');

  const isSubmitting = (dialog) => dialog.dataset.submitting === 'true';

  const openDialog = (dialog, trigger) => {
    if (!dialog || dialog.open || typeof dialog.showModal !== 'function') return;
    returnFocus.set(dialog, trigger || document.activeElement);
    dialog.dataset.closing = 'false';
    dialog.dataset.submitting = 'false';
    document.body.classList.add('aui-dialog-open');
    dialog.showModal();
    const target = firstFocusTarget(dialog);
    if (target) target.focus({ preventScroll: true });
  };

  // Runs right after dialog.close(); the "close" event is queued and can be
  // throttled in background tabs, so cleanup must not depend on it alone.
  const afterClose = (dialog) => {
    dialog.dataset.closing = 'false';
    if (!document.querySelector(`${DIALOG}[open]`)) document.body.classList.remove('aui-dialog-open');
    const trigger = returnFocus.get(dialog);
    returnFocus.delete(dialog);
    if (trigger && trigger.isConnected) trigger.focus({ preventScroll: true });
  };

  const finishClose = (dialog) => {
    if (dialog.open) dialog.close();
    afterClose(dialog);
  };

  const closeDialog = (dialog) => {
    if (!dialog || !dialog.open || dialog.dataset.closing === 'true' || isSubmitting(dialog)) return;
    if (reduceMotion.matches) {
      finishClose(dialog);
      return;
    }
    dialog.dataset.closing = 'true';
    window.setTimeout(() => finishClose(dialog), CLOSE_MS);
  };

  document.addEventListener('click', (event) => {
    const opener = event.target.closest('[data-dialog-open]');
    if (opener) {
      event.preventDefault();
      openDialog(document.getElementById(opener.dataset.dialogOpen), opener);
      return;
    }
    const closer = event.target.closest('[data-dialog-close]');
    if (closer) closeDialog(closer.closest(DIALOG));
  });

  document.querySelectorAll(DIALOG).forEach((dialog) => {
    // Backdrop click: the press and the release must both land outside the
    // panel, so selecting text in a field and releasing outside never closes.
    let pressedOnBackdrop = false;
    dialog.addEventListener('pointerdown', (event) => {
      pressedOnBackdrop = event.target === dialog;
    });
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog && pressedOnBackdrop) closeDialog(dialog);
      pressedOnBackdrop = false;
    });

    // Escape fires "cancel": run the animated close instead of the instant one.
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      closeDialog(dialog);
    });

    dialog.addEventListener('submit', () => {
      dialog.dataset.submitting = 'true';
    });

    // Closes that bypass closeDialog() (e.g. form method="dialog") still clean up.
    dialog.addEventListener('close', () => afterClose(dialog));
  });

  // Coming back through the history cache must not leave a dialog locked.
  window.addEventListener('pageshow', (event) => {
    if (!event.persisted) return;
    document.querySelectorAll(DIALOG).forEach((dialog) => {
      dialog.dataset.submitting = 'false';
    });
  });
})();
