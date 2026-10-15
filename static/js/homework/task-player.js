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
    let busy = false;

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
      if (outcome.status === 'try_again') {
        (root.querySelector('.task-question') || root.querySelector('[data-build-row]'))?.classList.add('is-hint');
      } else if (outcome.status === 'modeled') {
        root.querySelectorAll('[data-task-choice]').forEach((button) => {
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

    const send = async (url, body) => {
      if (preview) {
        // Preview never saves: show how the feedback looks and stop.
        showFeedback({status: 'correct', step_done: false});
        return {status: 'correct', step_done: false};
      }
      if (busy) return null;
      busy = true;
      lock(true);
      try {
        const {ok, status, data} = await post(url, body);
        if (ok || (status === 409 && data.reason === 'closed')) {
          const outcome = ok ? data : {status: 'correct', step_done: true, next_url: data.next_url};
          showFeedback(outcome);
          lock(Boolean(outcome.step_done));
          if (outcome.step_done && nextLink) nextLink.focus();
          return outcome;
        }
        lock(false);
        showFeedback({status: 'try_again', step_done: false});
        return null;
      } catch (error) {
        lock(false);
        showFeedback({status: 'try_again', step_done: false});
        return null;
      } finally {
        busy = false;
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
      card.classList.add('is-done');
      card.querySelector('[data-palabra-star]')?.removeAttribute('hidden');
      api.done(Number(card.dataset.palabra));
    });

    // The reading practice (readings/partials/practice.html) announces the end of its 3-read cycle.
    root.addEventListener('reading-practice:done', () => api.done(0));

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
