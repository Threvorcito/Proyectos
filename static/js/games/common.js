(function () {
  var positiveMessages = ['¡Muy bien!', '¡Lo encontraste!', '¡Excelente!', '¡Buen trabajo!', '¡Vamos por otra!'];
  var tryMessages = ['Casi. Prueba otra vez.', 'Observa nuevamente.', 'Escúchala una vez más.', 'Vamos a intentarlo de nuevo.'];

  function readData() {
    var node = document.getElementById('game-data');
    if (!node) return [];
    try { return JSON.parse(node.textContent); } catch (error) { return []; }
  }

  function speak(text) {
    if (!('speechSynthesis' in window) || !text) return;
    window.speechSynthesis.cancel();
    var utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-MX';
    utterance.rate = 0.85;
    window.speechSynthesis.speak(utterance);
  }

  function getCsrfToken() {
    var match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  function createButton(className, text, handler) {
    var button = document.createElement('button');
    button.type = 'button';
    button.className = className;
    button.textContent = text;
    button.addEventListener('click', handler);
    return button;
  }

  function shuffleItems(items) {
    var copy = items.slice();
    for (var index = copy.length - 1; index > 0; index -= 1) {
      var swapIndex = Math.floor(Math.random() * (index + 1));
      var current = copy[index];
      copy[index] = copy[swapIndex];
      copy[swapIndex] = current;
    }
    return copy;
  }

  function buildBalancedCorrectPositions(totalChallenges, optionCount) {
    var positions = [];
    for (var index = 0; index < totalChallenges; index += 1) {
      positions.push(index % optionCount);
    }
    return shuffleItems(positions);
  }

  function placeCorrectOption(challenge, correctPosition) {
    var correctAnswer = challenge.word;
    var distractors = challenge.options.filter(function (option) { return option !== correctAnswer; });
    var orderedDistractors = shuffleItems(distractors);
    var orderedOptions = [];
    var distractorIndex = 0;
    for (var index = 0; index < challenge.options.length; index += 1) {
      if (index === correctPosition) orderedOptions.push(correctAnswer);
      else {
        orderedOptions.push(orderedDistractors[distractorIndex]);
        distractorIndex += 1;
      }
    }
    return orderedOptions;
  }

  function GameState(root, challenges) {
    this.root = root;
    this.challenges = challenges;
    this.index = 0;
    this.correct = 0;
    this.tries = 0;
    this.counter = root.querySelector('[data-game-counter]');
    this.progress = root.querySelector('[data-game-progress]');
    this.feedback = root.querySelector('[data-game-feedback]');
    this.finish = root.querySelector('[data-game-finish]');
    this.summary = root.querySelector('[data-game-summary]');
    this.stars = root.querySelector('[data-game-stars]');
    this.board = root.querySelector('.games-page__board');
    this.saveUrl = root.getAttribute('data-save-url');
  }

  GameState.prototype.current = function () { return this.challenges[this.index]; };

  GameState.prototype.updateProgress = function () {
    var total = this.challenges.length || 1;
    if (this.counter) this.counter.textContent = 'Reto ' + Math.min(this.index + 1, total) + ' de ' + total;
    if (this.progress) this.progress.style.width = Math.round((this.index / total) * 100) + '%';
  };

  GameState.prototype.sayGood = function () {
    this.feedback.className = 'games-page__feedback is-good';
    this.feedback.textContent = '✓ ' + positiveMessages[Math.floor(Math.random() * positiveMessages.length)];
  };

  GameState.prototype.sayTry = function () {
    this.feedback.className = 'games-page__feedback is-try';
    this.feedback.textContent = tryMessages[Math.floor(Math.random() * tryMessages.length)];
  };

  GameState.prototype.next = function (wasCorrect, render) {
    if (wasCorrect) this.correct += 1;
    this.sayGood();
    var self = this;
    window.setTimeout(function () {
      self.index += 1;
      self.tries = 0;
      if (self.index >= self.challenges.length) self.complete();
      else render();
    }, 750);
  };

  GameState.prototype.complete = function () {
    var total = this.challenges.length || 1;
    if (this.progress) this.progress.style.width = '100%';
    if (this.board) this.board.hidden = true;
    if (this.feedback) this.feedback.hidden = true;
    if (this.finish) this.finish.hidden = false;
    var starCount = this.correct === total ? 3 : this.correct >= Math.ceil(total * 0.6) ? 2 : 1;
    if (this.stars) this.stars.textContent = '⭐'.repeat(starCount);
    if (this.summary) this.summary.textContent = 'Retos completados: ' + total + ' | Aciertos: ' + this.correct;
    this.saveAttempt(total);
  };

  GameState.prototype.saveAttempt = function (total) {
    if (!this.saveUrl) return;
    fetch(this.saveUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
      body: JSON.stringify({correct_answers: this.correct, total_questions: total, completed: true})
    }).catch(function () {});
  };

  function initLetterHunter(root, challenges) {
    var state = new GameState(root, challenges);
    var target = root.querySelector('[data-target-letter]');
    var grid = root.querySelector('[data-letter-grid]');
    var speakButton = root.querySelector('[data-speak-target]');
    var checkButton = root.querySelector('[data-check-letters]');

    function render() {
      state.updateProgress();
      state.feedback.className = 'games-page__feedback';
      state.feedback.textContent = '';
      var challenge = state.current();
      target.textContent = challenge.target;
      grid.innerHTML = '';
      challenge.letters.forEach(function (letter) {
        var button = createButton('games-page__letter-tile', letter, function () {
          button.setAttribute('aria-pressed', button.getAttribute('aria-pressed') !== 'true');
        });
        button.setAttribute('aria-pressed', 'false');
        grid.appendChild(button);
      });
    }

    speakButton.addEventListener('click', function () { speak(state.current().speak); });
    checkButton.addEventListener('click', function () {
      var challenge = state.current();
      var buttons = Array.prototype.slice.call(grid.querySelectorAll('button'));
      var correct = buttons.every(function (button) {
        return (button.textContent === challenge.target) === (button.getAttribute('aria-pressed') === 'true');
      });
      if (correct) {
        buttons.forEach(function (button) { if (button.textContent === challenge.target) button.classList.add('is-correct'); });
        state.next(true, render);
      } else {
        state.tries += 1;
        state.sayTry();
        if (state.tries >= 2) buttons.forEach(function (button) { if (button.textContent === challenge.target) button.classList.add('is-hint'); });
      }
    });
    render();
  }

  function initBuildWord(root, challenges) {
    var state = new GameState(root, challenges);
    var image = root.querySelector('[data-build-image]');
    var prompt = root.querySelector('[data-build-prompt]');
    var answer = root.querySelector('[data-build-answer]');
    var options = root.querySelector('[data-build-options]');
    var selected = [];

    function renderAnswer() {
      answer.innerHTML = '';
      selected.forEach(function (part) { answer.appendChild(createButton('games-page__slot', part, function () {})); });
    }

    function render() {
      selected = [];
      state.updateProgress();
      state.feedback.className = 'games-page__feedback';
      state.feedback.textContent = '';
      var challenge = state.current();
      image.textContent = challenge.image;
      prompt.textContent = challenge.prompt;
      answer.innerHTML = '';
      options.innerHTML = '';
      challenge.choices.forEach(function (choice) {
        options.appendChild(createButton('games-page__option', choice, function () {
          selected.push(choice);
          renderAnswer();
        }));
      });
    }

    root.querySelector('[data-build-clear]').addEventListener('click', function () { selected = []; renderAnswer(); });
    root.querySelector('[data-build-check]').addEventListener('click', function () {
      var expected = state.current().answer.join('');
      if (selected.join('') === expected) state.next(true, render);
      else { state.tries += 1; state.sayTry(); }
    });
    render();
  }

  function initChoiceGame(root, challenges, selectors) {
    var state = new GameState(root, challenges);
    var options = root.querySelector(selectors.options);
    var speakButton = root.querySelector(selectors.speak);

    function render() {
      state.updateProgress();
      state.feedback.className = 'games-page__feedback';
      state.feedback.textContent = '';
      var challenge = state.current();
      options.innerHTML = '';
      challenge.options.forEach(function (option) {
        options.appendChild(createButton('games-page__option', option, function () {
          if (option === challenge.word) {
            this.classList.add('is-correct');
            state.next(true, render);
          } else {
            state.tries += 1;
            state.sayTry();
            if (state.tries >= 2) options.querySelectorAll('button').forEach(function (button) { if (button.textContent === challenge.word) button.classList.add('is-hint'); });
          }
        }));
      });
    }

    speakButton.addEventListener('click', function () { speak(state.current().word); });
    render();
  }

  function initListenFind(root, challenges) {
    var state = new GameState(root, challenges);
    var options = root.querySelector('[data-listen-options]');
    var speakButton = root.querySelector('[data-listen-word]');
    var correctPositions = buildBalancedCorrectPositions(challenges.length, 3);

    function render() {
      state.updateProgress();
      state.feedback.className = 'games-page__feedback';
      state.feedback.textContent = '';
      var challenge = state.current();
      var orderedOptions = placeCorrectOption(challenge, correctPositions[state.index]);
      options.innerHTML = '';
      orderedOptions.forEach(function (option) {
        options.appendChild(createButton('games-page__option', option, function () {
          if (option === challenge.word) {
            this.classList.add('is-correct');
            state.next(true, render);
          } else {
            state.tries += 1;
            state.sayTry();
            if (state.tries >= 2) options.querySelectorAll('button').forEach(function (button) { if (button.textContent === challenge.word) button.classList.add('is-hint'); });
          }
        }));
      });
    }

    speakButton.addEventListener('click', function () { speak(state.current().word); });
    render();
  }

  function initMemory(root, challenges) {
    var state = new GameState(root, challenges.slice(0, 5));
    var grid = root.querySelector('[data-memory-grid]');
    var open = [];
    var matches = 0;

    function shuffle(items) { return items.sort(function () { return Math.random() - 0.5; }); }

    function render() {
      state.updateProgress();
      grid.innerHTML = '';
      open = [];
      matches = 0;
      var cards = [];
      state.challenges.forEach(function (pair, index) {
        cards.push({pair: index, value: pair.image, word: pair.word});
        cards.push({pair: index, value: pair.word, word: pair.word});
      });
      shuffle(cards).forEach(function (card) {
        var button = createButton('games-page__memory-card', card.value, function () {
          if (button.classList.contains('is-visible') || button.classList.contains('is-matched') || open.length === 2) return;
          button.classList.add('is-visible');
          open.push({button: button, card: card});
          if (open.length === 2) checkPair();
        });
        button.dataset.pair = card.pair;
        grid.appendChild(button);
      });
    }

    function checkPair() {
      if (open[0].card.pair === open[1].card.pair) {
        open.forEach(function (item) { item.button.classList.add('is-matched'); });
        speak(open[0].card.word);
        matches += 1;
        state.correct = matches;
        state.index = matches;
        state.sayGood();
        state.updateProgress();
        open = [];
        if (matches === state.challenges.length) window.setTimeout(function () { state.complete(); }, 650);
      } else {
        state.sayTry();
        window.setTimeout(function () {
          open.forEach(function (item) { item.button.classList.remove('is-visible'); });
          open = [];
        }, 900);
      }
    }
    render();
  }

  function initReadingPath(root, challenges) {
    var state = new GameState(root, challenges);
    var station = root.querySelector('[data-path-station]');
    var prompt = root.querySelector('[data-path-prompt]');
    var target = root.querySelector('[data-path-target]');
    var options = root.querySelector('[data-path-options]');

    function render() {
      state.updateProgress();
      station.textContent = state.index + 1;
      var challenge = state.current();
      prompt.textContent = challenge.prompt;
      target.textContent = challenge.target;
      options.innerHTML = '';
      challenge.options.forEach(function (option) {
        options.appendChild(createButton('games-page__option', option, function () {
          if (option === challenge.target) state.next(true, render);
          else { state.tries += 1; state.sayTry(); }
        }));
      });
    }

    root.querySelector('[data-path-speak]').addEventListener('click', function () { speak(state.current().target); });
    render();
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = document.querySelector('[data-game-root]');
    if (!root) return;
    var challenges = readData();
    var type = root.getAttribute('data-game-type');
    var restart = root.querySelector('[data-game-restart]');
    if (restart) restart.addEventListener('click', function () { window.location.reload(); });

    if (type === 'letter_hunter') initLetterHunter(root, challenges);
    if (type === 'build_word') initBuildWord(root, challenges);
    if (type === 'listen_find') initListenFind(root, challenges);
    if (type === 'memory') initMemory(root, challenges);
    if (type === 'letter_detective') initChoiceGame(root, challenges, {options: '[data-detective-options]', speak: '[data-detective-speak]'});
    if (type === 'reading_path') initReadingPath(root, challenges);
  });
})();
