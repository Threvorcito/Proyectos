/* Child step player: sends "done" and answers, shows friendly feedback, never fetches in preview. */
(() => {
  // Preview stacks several steps on one page: each one gets its own player.
  const init = (root) => {
    const preview = root.dataset.preview === '1';
    const feedbackBox = root.querySelector('[data-task-feedback]');
    const feedbackText = root.querySelector('[data-task-feedback-text]');
    const nextLink = root.querySelector('[data-task-next]');
    let copy = {};
    try {
      copy = JSON.parse(document.getElementById('task-feedback-copy')?.textContent || '{}');
    } catch (error) {
      copy = {};
    }
    const csrfToken = () => document.cookie.split('; ').find((row) => row.startsWith('csrftoken='))?.split('=')[1] || '';

    const post = async (url, body) => {
      const response = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': decodeURIComponent(csrfToken())},
        body: JSON.stringify(body),
      });
      let data = {};
      try {
        data = await response.json();
      } catch (error) {
        data = {};
      }
      return {ok: response.ok, status: response.status, data};
    };

    const lock = (locked) => {
      root.querySelectorAll('[data-task-done], [data-task-choice]').forEach((button) => {
        button.disabled = locked;
      });
    };

    const isOmission = (outcome) => outcome.status === 'try_again' && outcome.hint?.kind === 'omission';

    const messageFor = (outcome) => {
      if (isOmission(outcome)) return copy.omission || '';
      if (outcome.status === 'try_again') return copy.try_again || '';
      if (outcome.status === 'modeled') return (copy.modeled || '').replace('{answer}', outcome.model_answer || '');
      return copy.correct || '';
    };

    const clearMarks = () => {
      root.querySelectorAll('.is-hint, .is-model').forEach((node) => node.classList.remove('is-hint', 'is-model'));
    };

    // Hint = audio + highlight: the question (or the tile row) lights up; a modeled answer marks the right option.
    const highlight = (outcome) => {
      clearMarks();
      // Ejemplo and dictado show one exercise or item at a time: only that one is lit.
      const scope = root.querySelector('.task-exercise:not([hidden]), [data-dictado-item]:not([hidden])') || root;
      if (outcome.status === 'try_again') {
        (scope.querySelector('.task-question') || scope.querySelector('[data-build-row]'))?.classList.add('is-hint');
      } else if (outcome.status === 'modeled') {
        scope.querySelectorAll('[data-task-choice]').forEach((button) => {
          if (button.textContent.trim() === outcome.model_answer) button.classList.add('is-model');
        });
      }
    };

    // A hint sound is an audio file when one is recorded (hint.audio), speech otherwise.
    let hintAudio = null;
    const playHint = (hint) => {
      hintAudio?.pause();
      hintAudio = null;
      if (!hint) return Promise.resolve();
      if (!hint.audio) return window.AppSpeech?.speakSequence ? window.AppSpeech.speakSequence([hint.say], {rate: 0.7}) : Promise.resolve();
      return new Promise((resolve) => {
        const audio = new Audio(hint.audio);
        hintAudio = audio;
        audio.addEventListener('ended', resolve);
        audio.addEventListener('error', () => {
          hintAudio = null;
          (window.AppSpeech?.speakSequence ? window.AppSpeech.speakSequence([hint.say], {rate: 0.7}) : Promise.resolve()).then(resolve);
        });
        audio.play().catch(() => audio.dispatchEvent(new Event('error')));
      });
    };

    // Network failure or 5xx: neutral note, never "Casi…" (the answer may well have been right) and no Lumi cheer/encourage.
    const showSaveFailed = () => {
      if (!feedbackBox) return;
      clearMarks();
      const text = copy.save_failed || '';
      feedbackBox.hidden = false;
      feedbackBox.classList.remove('is-good', 'is-try', 'is-model');
      if (feedbackText) feedbackText.textContent = text;
      if (nextLink) nextLink.hidden = true;
      window.AppSpeech?.speak(text);
    };

    const showFeedback = (outcome) => {
      if (!feedbackBox || !outcome) return;
      const good = outcome.status === 'correct' || outcome.status === 'done';
      const modeled = outcome.status === 'modeled';
      highlight(outcome);
      const text = messageFor(outcome);
      feedbackBox.hidden = false;
      feedbackBox.classList.toggle('is-good', good);
      feedbackBox.classList.toggle('is-try', !good && !modeled);
      feedbackBox.classList.toggle('is-model', modeled);
      if (feedbackText) feedbackText.textContent = text;
      if (nextLink) {
        nextLink.hidden = !outcome.step_done;
        if (outcome.step_done && outcome.next_url) nextLink.href = outcome.next_url;
      }
      if (isOmission(outcome) && window.AppSpeech?.speakSequence) {
        // The missing sound is its own utterance, said slowly: it is the hint (never the letter name).
        window.AppSpeech.speakSequence([text], {rate: 0.7}).then(() => playHint(outcome.hint));
      } else {
        window.AppSpeech?.speak(outcome.status === 'try_again' && outcome.hint?.say ? `${text} ${outcome.hint.say}` : text);
      }
      window.Mascot?.react(good ? 'cheer' : 'encourage', {say: text});
    };

    // Calls run one after another: a second one waits its turn instead of being dropped.
    let chain = Promise.resolve();
    const send = (url, body) => {
      if (preview) {
        // Preview never saves: show how the feedback looks and stop.
        showFeedback({status: 'correct', step_done: false});
        return Promise.resolve({status: 'correct', step_done: false});
      }
      const run = chain.then(() => transmit(url, body));
      chain = run.catch(() => {});
      return run;
    };

    const transmit = async (url, body) => {
      lock(true);
      try {
        const {ok, status, data} = await post(url, body);
        if (ok || (status === 409 && data.reason === 'closed')) {
          const outcome = ok ? data : {status: 'correct', step_done: Boolean(data.step_done), next_url: data.next_url};
          showFeedback(outcome);
          lock(Boolean(outcome.step_done));
          if (outcome.step_done && nextLink) nextLink.focus();
          return outcome;
        }
        lock(false);
        showSaveFailed();
        return null;
      } catch (error) {
        lock(false);
        showSaveFailed();
        return null;
      }
    };

    const api = {
      done: (itemIndex) => send(root.dataset.doneUrl, {item_index: itemIndex}),
      answer: (itemIndex, body = {}) => send(root.dataset.answerUrl, {item_index: itemIndex, ...body}),
      showFeedback,
      playHint,
    };
    root.taskPlayer = api; // preview stacks steps: code that needs this step's player reaches it via its root
    window.TaskPlayer = api;

    // Asking for help is logged for the teacher (never in preview, never on palabras: there tapping is the exercise).
    root.addEventListener('decode:help', (event) => {
      const helpUrl = root.dataset.helpUrl;
      if (preview || !helpUrl || root.dataset.stepType === 'palabras') return;
      const order = Number(root.dataset.stepOrder);
      post(helpUrl, {word: event.detail.word, step_order: Number.isInteger(order) ? order : null}).catch(() => {});
    });

    // Palabras: finishing the sounds of word i completes item i and stars its card.
    root.addEventListener('decode:done', (event) => {
      if (root.dataset.stepType !== 'palabras') return;
      const card = event.target.closest('[data-palabra]');
      if (!card) return;
      // The star is earned once the server has the word; on a failure the card stays open so the child can try again.
      api.done(Number(card.dataset.palabra)).then((outcome) => {
        if (!outcome) return;
        card.classList.add('is-done');
        card.querySelector('[data-palabra-star]')?.removeAttribute('hidden');
      });
    });

    // The reading practice (readings/partials/practice.html) announces the end of its 3-read cycle.
    root.addEventListener('reading-practice:done', () => api.done(0));

    // Ejemplo: the worked example one line at a time, then "¡Ahora yo!" opens the exercises, one per screen.
    let afterAnswer = () => {};
    const ejemplo = root.querySelector('[data-ejemplo]');
    if (ejemplo) {
      const lines = [...ejemplo.querySelectorAll('[data-ejemplo-line]')];
      const exercises = [...ejemplo.querySelectorAll('[data-exercise]')];
      const show = ejemplo.querySelector('[data-ejemplo-show]');
      const practice = ejemplo.querySelector('[data-ejemplo-practice]');
      const nextButton = ejemplo.querySelector('[data-ejemplo-next]');
      let lineIndex = 0;
      const isOpen = (node) => !node.classList.contains('is-done');

      const showLine = (index) => {
        lineIndex = index;
        lines.forEach((line, i) => { line.hidden = i !== index; });
        nextButton.textContent = index === lines.length - 1 ? '¡Ahora yo!' : 'Siguiente';
      };
      const showExercise = (exercise) => {
        exercises.forEach((node) => { node.hidden = node !== exercise; });
        exercise?.querySelector('.task-question')?.focus();
      };
      const startPractice = () => {
        show.hidden = true;
        practice.hidden = false;
        showExercise(exercises.find(isOpen) || exercises[exercises.length - 1]);
        window.Mascot?.react('hello');
      };

      exercises.forEach((node) => {
        // Exercises the server already closed start closed.
        if (!isOpen(node)) node.querySelectorAll('[data-task-choice]').forEach((button) => { button.disabled = true; });
      });
      if (ejemplo.hasAttribute('data-ejemplo-resume')) startPractice(); else showLine(0);

      nextButton.addEventListener('click', () => {
        if (lineIndex < lines.length - 1) {
          showLine(lineIndex + 1);
          lines[lineIndex].querySelector('.kid-listen')?.focus();
        } else {
          startPractice();
        }
      });

      afterAnswer = (outcome, itemIndex) => {
        const exercise = exercises.find((node) => Number(node.dataset.exercise) === itemIndex);
        if (!outcome || !exercise || (outcome.status !== 'correct' && outcome.status !== 'modeled')) return;
        // A closed exercise cannot be answered again; the child moves on when ready (no timers).
        exercise.classList.add('is-done');
        exercise.querySelectorAll('[data-task-choice]').forEach((button) => { button.disabled = true; });
        if (outcome.step_done) return;
        const continueButton = exercise.querySelector('[data-ejemplo-continue]');
        if (exercises.some(isOpen) && continueButton) {
          continueButton.hidden = false;
          continueButton.focus();
        }
      };

      ejemplo.addEventListener('click', (event) => {
        const button = event.target.closest('[data-ejemplo-continue]');
        if (!button) return;
        button.hidden = true;
        clearMarks();
        if (feedbackBox) feedbackBox.hidden = true;
        showExercise(exercises.find(isOpen));
      });
    }

    // Dictado: one item per screen. The child hears it (data-speak-text, never printed) and builds it with tiles;
    // once the server closes it (correct or modeled), "Siguiente" opens the next open item and says it aloud.
    const dictado = root.querySelector('[data-dictado]');
    if (dictado) {
      const items = [...dictado.querySelectorAll('[data-dictado-item]')];
      const isOpen = (node) => !node.classList.contains('is-done');

      root.addEventListener('build:answered', (event) => {
        const item = event.target.closest('[data-dictado-item]');
        const {outcome} = event.detail || {};
        if (!item || !outcome || (outcome.status !== 'correct' && outcome.status !== 'modeled')) return;
        item.classList.add('is-done');
        if (outcome.step_done) return;
        const nextButton = item.querySelector('[data-dictado-next]');
        if (items.some(isOpen) && nextButton) {
          nextButton.hidden = false;
          nextButton.focus();
        }
      });

      dictado.addEventListener('click', (event) => {
        const button = event.target.closest('[data-dictado-next]');
        if (!button) return;
        const next = items.find(isOpen);
        if (!next) return;
        button.hidden = true;
        clearMarks();
        if (feedbackBox) feedbackBox.hidden = true;
        items.forEach((node) => { node.hidden = node !== next; });
        // The tap is a user gesture, so the next word can be heard right away; its listen button replays it.
        const listen = next.querySelector('.task-dictado__listen');
        listen?.focus();
        listen?.click();
      });
    }

    root.addEventListener('click', (event) => {
      const doneButton = event.target.closest('[data-task-done]');
      if (doneButton) {
        api.done(Number(doneButton.dataset.taskDone));
        return;
      }
      const choice = event.target.closest('[data-task-choice]');
      if (choice) {
        const itemIndex = Number(choice.dataset.taskItem || 0);
        api.answer(itemIndex, {choice: Number(choice.dataset.taskChoice)}).then((outcome) => afterAnswer(outcome, itemIndex));
      }
    });
  };
  document.querySelectorAll('[data-task-step]').forEach(init);
})();
