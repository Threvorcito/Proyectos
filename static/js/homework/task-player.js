/* Child step player: sends "done" and answers, shows friendly feedback, never fetches in preview. */
(() => {
  const root = document.querySelector('[data-task-step]');
  if (!root) return;

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

  const messageFor = (outcome) => {
    if (outcome.status === 'try_again') return copy.try_again || '';
    if (outcome.status === 'modeled') return (copy.modeled || '').replace('{answer}', outcome.model_answer || '');
    return copy.correct || '';
  };

  const clearMarks = () => {
    root.querySelectorAll('.is-hint, .is-model').forEach((node) => node.classList.remove('is-hint', 'is-model'));
  };

  // Hint = audio + highlight: the question lights up; a modeled answer marks the right option.
  const highlight = (outcome) => {
    clearMarks();
    if (outcome.status === 'try_again') {
      root.querySelector('.task-question')?.classList.add('is-hint');
    } else if (outcome.status === 'modeled') {
      root.querySelectorAll('[data-task-choice]').forEach((button) => {
        if (button.textContent.trim() === outcome.model_answer) button.classList.add('is-model');
      });
    }
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
    window.AppSpeech?.speak(outcome.status === 'try_again' && outcome.hint?.say ? `${text} ${outcome.hint.say}` : text);
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
  };
  window.TaskPlayer = api;

  // The reading practice (readings/partials/practice.html) announces the end of its 3-read cycle.
  root.addEventListener('reading-practice:done', () => api.done(0));

  root.addEventListener('click', (event) => {
    const doneButton = event.target.closest('[data-task-done]');
    if (doneButton) {
      api.done(Number(doneButton.dataset.taskDone));
      return;
    }
    const choice = event.target.closest('[data-task-choice]');
    if (choice) api.answer(0, {choice: Number(choice.dataset.taskChoice)});
  });
})();
