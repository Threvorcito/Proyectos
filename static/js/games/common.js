(function () {
  var positiveMessages = ['¡Muy bien!', '¡Lo encontraste!', '¡Excelente!', '¡Buen trabajo!', '¡Vamos por otra!'];
  var tryMessages = ['Casi. Prueba otra vez.', 'Observa nuevamente.', 'Escúchala una vez más.', 'Vamos a intentarlo de nuevo.'];

  function readData() {
    var node = document.getElementById('game-data');
    if (!node) return [];
    try { return JSON.parse(node.textContent); } catch (error) { return []; }
  }

  function speak(text) {
    if (!text) return;
    window.AppSpeech?.speak(text, {rate: 0.85});
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

  function pickOne(items) {
    return items[Math.floor(Math.random() * items.length)];
  }

  function randomDigit(excluded) {
    var digit = String(Math.floor(Math.random() * 10));
    while (excluded.indexOf(digit) !== -1) digit = String(Math.floor(Math.random() * 10));
    return digit;
  }

  function randomTwoDigitNumber() {
    var first = String(Math.floor(Math.random() * 9) + 1);
    var second = randomDigit([first]);
    return first + second;
  }

  function uniqueItems(items) {
    var seen = {};
    return items.filter(function (item) {
      if (seen[item]) return false;
      seen[item] = true;
      return true;
    });
  }

  function shuffledWithAnswer(options) {
    return shuffleItems(uniqueItems(options));
  }

  function getDistractorPool(challenge) {
    if (challenge.option_visuals) return [];
    if (challenge.category === 'Matematica' || challenge.category === 'Secuencia de numeros' || challenge.category === 'Conteo') return ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
    if (challenge.category === 'English' || challenge.category === 'Animals' || challenge.category === 'Colors' || challenge.category === 'Numbers' || challenge.category === 'School') return ['CAT', 'DOG', 'BOOK', 'BLUE', 'RED', 'SUN', 'TREE', 'FISH', '3', '4'];
    if (challenge.category === 'Ciencias Naturales' || challenge.category === 'Animales' || challenge.category === 'Plantas' || challenge.category === 'Ambiente') return ['RANA', 'PEZ', 'PERRO', 'AVE', 'ARBOL', 'FLOR', 'AGUA', 'SOL', 'ZAFACON'];
    if (challenge.category === 'Estudios Sociales' || challenge.category === 'Comunidad' || challenge.category === 'Familia' || challenge.category === 'Convivencia' || challenge.category === 'Ubicacion') return ['ESCUELA', 'CASA', 'PARQUE', 'FAMILIA', 'CALLE', 'TIENDA', 'DERECHA', 'IZQUIERDA', 'ARRIBA'];
    if (challenge.category === 'Educacion Artistica y Cultural' || challenge.category === 'Figuras' || challenge.category === 'Colores' || challenge.category === 'Patrones') return ['▲', '●', '■', 'ROJO', 'AZUL', 'VERDE', 'CIRCULO', 'CUADRADO', 'TRIANGULO'];
    return ['LUNA', 'MESA', 'PATO', 'CASA', 'SOL', 'FLOR', 'LIBRO', 'MAMA', 'MO', 'LECHE'];
  }

  function applyDifficultyToOptions(challenge, difficulty) {
    if (!challenge.options) return challenge;
    var targetCount = difficulty === 'hard' ? 5 : difficulty === 'medium' ? 4 : 3;
    var options = uniqueItems(challenge.options.slice());
    var pool = shuffleItems(getDistractorPool(challenge));
    pool.forEach(function (item) {
      if (options.length < targetCount && item !== challenge.answer && options.indexOf(item) === -1) options.push(item);
    });
    if (difficulty === 'easy') options = options.filter(function (item) { return item === challenge.answer || options.indexOf(item) < 3; });
    if (options.indexOf(challenge.answer) === -1) options.push(challenge.answer);
    challenge.options = shuffledWithAnswer(options.slice(0, Math.max(targetCount, Math.min(options.length, targetCount))));
    if (challenge.options.indexOf(challenge.answer) === -1) {
      challenge.options.pop();
      challenge.options.push(challenge.answer);
      challenge.options = shuffledWithAnswer(challenge.options);
    }
    return challenge;
  }

  function applyDifficultyTiming(challenge, difficulty) {
    if (!challenge.memory_seconds) return challenge;
    challenge.memory_seconds = difficulty === 'hard' ? 3 : difficulty === 'medium' ? 4 : 5;
    return challenge;
  }

  function randomizeQuizChallenge(challenge, difficulty) {
    var copy = Object.assign({}, challenge);
    difficulty = difficulty || 'easy';
    if (copy.option_visuals) copy.option_visuals = Object.assign({}, copy.option_visuals);

    if (copy.category === 'Matematica' && copy.prompt.indexOf('Memoriza esta secuencia') !== -1) {
      var digits = [];
      var sequenceLength = difficulty === 'hard' ? 6 : difficulty === 'medium' ? 5 : 4;
      while (digits.length < sequenceLength) digits.push(randomDigit(digits));
      var position = Math.floor(Math.random() * digits.length);
      var ordinal = position + 1 + '.º';
      copy.visual = digits.join(' ');
      copy.question = '¿Cual era el ' + ordinal + ' digito?';
      copy.answer = digits[position];
      copy.options = digits.concat([randomDigit(digits)]);
      copy.hint = 'Cuenta las posiciones desde la izquierda hasta el ' + ordinal + ' digito.';
      copy.memory_seconds = difficulty === 'hard' ? 3 : difficulty === 'medium' ? 4 : 5;
    }

    if (copy.category === 'Matematica' && copy.prompt.indexOf('Memoriza este numero') !== -1) {
      var number = randomTwoDigitNumber();
      var reversed = number.charAt(1) + number.charAt(0);
      copy.visual = number;
      copy.question = '¿Que numero viste?';
      copy.answer = number;
      var distractor = randomTwoDigitNumber();
      while (distractor === number || distractor === reversed) distractor = randomTwoDigitNumber();
      copy.options = [reversed, number, distractor];
      copy.hint = 'Observa el orden: primero va el ' + number.charAt(0) + ' y despues va el ' + number.charAt(1) + '.';
      copy.memory_seconds = difficulty === 'hard' ? 3 : difficulty === 'medium' ? 4 : 5;
    }

    if (copy.category === 'Matematica' && copy.prompt.indexOf('Cuenta los puntos') !== -1) {
      var total = Math.floor(Math.random() * 4) + 3;
      copy.visual = Array(total + 1).join('● ').trim();
      copy.question = '¿Cuantos puntos hay?';
      copy.answer = String(total);
      copy.options = difficulty === 'easy' ? [String(total - 1), String(total), String(total + 1)] : [String(total - 2), String(total - 1), String(total), String(total + 1)];
      copy.hint = 'Puedes contarlos uno por uno hasta llegar a ' + total + '.';
    }

    if (copy.category === 'Matematica' && copy.prompt.indexOf('Completa la serie') !== -1) {
      var start = Math.floor(Math.random() * 3) + 1;
      var step = pickOne([2, 3]);
      var next = start + (step * 3);
      copy.visual = start + ' - ' + (start + step) + ' - ' + (start + step + step) + ' - ?';
      copy.question = '¿Que numero sigue?';
      copy.answer = String(next);
      copy.options = difficulty === 'easy' ? [String(next - 1), String(next), String(next + 1)] : [String(next - 2), String(next - 1), String(next), String(next + 1)];
      copy.hint = 'La serie avanza de ' + step + ' en ' + step + '.';
    }

    if (copy.category === 'Lengua y Literatura' && copy.prompt.indexOf('Memoriza la palabra') !== -1) {
      var word = pickOne([
        {visual: 'LUNA', options: ['LUNA', 'LANA', 'LIMA'], hint: 'Empieza con LU.'},
        {visual: 'MESA', options: ['MESA', 'MASA', 'MISA'], hint: 'Tiene la vocal E despues de la M.'},
        {visual: 'PATO', options: ['PATO', 'PALO', 'DATO'], hint: 'Empieza con P y tiene T.'},
        {visual: 'CASA', options: ['CASA', 'CAMA', 'COSA'], hint: 'Empieza con CA.'}
      ]);
      copy.visual = word.visual;
      copy.question = '¿Que palabra viste?';
      copy.answer = word.visual;
      copy.options = word.options;
      copy.hint = word.hint;
      copy.memory_seconds = difficulty === 'hard' ? 3 : difficulty === 'medium' ? 4 : 5;
    }

    if (copy.category === 'English' && copy.prompt.indexOf('word') !== -1) {
      var english = pickOne([
        {visual: '🐱 CAT', answer: 'CAT', options: ['CAT', 'CAR', 'CAN'], hint: 'Cat means gato.'},
        {visual: '🐶 DOG', answer: 'DOG', options: ['DOG', 'BOG', 'DOT'], hint: 'Dog means perro.'},
        {visual: '📘 BOOK', answer: 'BOOK', options: ['BOOK', 'LOOK', 'BOAT'], hint: 'Book means libro.'},
        {visual: 'BLUE', answer: 'BLUE', options: ['BLUE', 'BULE', 'BLU'], hint: 'Blue means azul.'}
      ]);
      copy.visual = english.visual;
      copy.question = 'Which word did you see?';
      copy.answer = english.answer;
      copy.options = english.options;
      copy.hint = english.hint;
      copy.memory_seconds = difficulty === 'hard' ? 3 : difficulty === 'medium' ? 4 : 5;
    }

    if (copy.category === 'Ciencias Naturales' && copy.prompt.indexOf('animal') !== -1) {
      var animal = pickOne([
        {visual: '🐸 RANA', answer: 'RANA', options: ['RANA', 'RAMA', 'LANA'], hint: 'Salta y vive cerca del agua.'},
        {visual: '🐟 PEZ', answer: 'PEZ', options: ['PEZ', 'PERA', 'PAN'], hint: 'Vive en el agua.'},
        {visual: '🐶 PERRO', answer: 'PERRO', options: ['PERRO', 'PEZ', 'PATO'], hint: 'Es domestico y ladra.'}
      ]);
      copy.visual = animal.visual;
      copy.question = '¿Que animal viste?';
      copy.answer = animal.answer;
      copy.options = animal.options;
      copy.hint = animal.hint;
      copy.memory_seconds = difficulty === 'hard' ? 3 : difficulty === 'medium' ? 4 : 5;
    }

    if (copy.category === 'Educacion Artistica y Cultural' && copy.prompt.indexOf('Memoriza la figura') !== -1) {
      var figure = pickOne([
        {visual: '▲', answer: '▲', options: ['■', '▲', '●'], hint: 'Tiene tres lados.'},
        {visual: '■', answer: '■', options: ['●', '▲', '■'], hint: 'Tiene cuatro lados iguales.'},
        {visual: '●', answer: '●', options: ['▲', '●', '■'], hint: 'Es redonda.'}
      ]);
      copy.visual = figure.visual;
      copy.question = '¿Cual figura viste?';
      copy.answer = figure.answer;
      copy.options = figure.options;
      copy.hint = figure.hint;
      copy.memory_seconds = difficulty === 'hard' ? 3 : difficulty === 'medium' ? 4 : 5;
    }

    if (copy.category === 'Estudios Sociales' && copy.prompt.indexOf('Observa el lugar') !== -1) {
      var place = pickOne([
        {visual: '🏫 ESCUELA', answer: 'ESCUELA', options: ['ESCUELA', 'CASA', 'PARQUE'], hint: 'Es el lugar donde aprendes.'},
        {visual: '🏠 CASA', answer: 'CASA', options: ['CASA', 'CALLE', 'ESCUELA'], hint: 'Es donde vive una familia.'},
        {visual: '🏞️ PARQUE', answer: 'PARQUE', options: ['PARQUE', 'TIENDA', 'CASA'], hint: 'Es un lugar para jugar y cuidar.'}
      ]);
      copy.visual = place.visual;
      copy.question = '¿Que lugar viste?';
      copy.answer = place.answer;
      copy.options = place.options;
      copy.hint = place.hint;
      copy.memory_seconds = difficulty === 'hard' ? 3 : difficulty === 'medium' ? 4 : 5;
    }

    applyDifficultyTiming(copy, difficulty);
    return applyDifficultyToOptions(copy, difficulty);
  }

  function randomizeQuizChallenges(challenges, difficulty) {
    return shuffleItems(challenges.map(function (challenge) { return randomizeQuizChallenge(challenge, difficulty); }));
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
    this.results = [];
    this.resultsDialog = root.querySelector('[data-game-results-dialog]');
    this.resultsBody = root.querySelector('[data-game-results-body]');
    this.resultsOpen = root.querySelector('[data-game-results-open]');
    this.resultsClose = root.querySelector('[data-game-results-close]');
    var self = this;
    if (this.resultsOpen) this.resultsOpen.addEventListener('click', function () { self.openResults(); });
    if (this.resultsClose) this.resultsClose.addEventListener('click', function () { self.closeResults(); });
    if (this.resultsDialog) {
      this.resultsDialog.addEventListener('click', function (event) {
        if (event.target === self.resultsDialog) self.closeResults();
      });
    }
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
    if (wasCorrect) this.sayGood();
    else {
      this.feedback.className = 'games-page__feedback is-try';
      this.feedback.textContent = 'Seguimos con el siguiente reto.';
    }
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
    this.renderResults();
    this.saveAttempt(total);
  };

  GameState.prototype.renderResults = function () {
    if (!this.resultsBody || !this.results.length) return;
    this.resultsBody.innerHTML = '';
    this.resultsBody.appendChild(this.buildSubjectProgress());
    this.resultsBody.appendChild(this.buildRecommendations());
    var list = document.createElement('div');
    list.className = 'games-page__result-list';
    this.results.forEach(function (result, index) {
      var item = document.createElement('article');
      item.className = 'games-page__result-item ' + (result.correct ? 'is-good' : 'is-bad');
      item.innerHTML = '<strong>Reto ' + (index + 1) + ': ' + result.category + '</strong><span>' + (result.correct ? 'Acertaste' : 'Fallaste') + '</span><small>' + result.question + ' Respuesta: ' + result.answer + '</small>';
      list.appendChild(item);
    });
    this.resultsBody.appendChild(list);
    if (this.resultsOpen) this.resultsOpen.hidden = false;
    this.openResults();
  };

  GameState.prototype.getSubjectProgress = function () {
    var progress = {};
    this.results.forEach(function (result) {
      if (!progress[result.category]) progress[result.category] = {correct: 0, total: 0};
      progress[result.category].total += 1;
      if (result.correct) progress[result.category].correct += 1;
    });
    return progress;
  };

  GameState.prototype.buildSubjectProgress = function () {
    var progress = this.getSubjectProgress();
    var panel = document.createElement('section');
    panel.className = 'games-page__subject-progress';
    panel.innerHTML = '<h3>Progreso por materia</h3>';
    Object.keys(progress).sort().forEach(function (subject) {
      var item = progress[subject];
      var row = document.createElement('article');
      var percent = Math.round((item.correct / item.total) * 100);
      row.innerHTML = '<div><strong>' + subject + '</strong><span>' + item.correct + '/' + item.total + '</span></div><progress max="100" value="' + percent + '">' + percent + '%</progress>';
      panel.appendChild(row);
    });
    return panel;
  };

  GameState.prototype.buildRecommendations = function () {
    var progress = this.getSubjectProgress();
    var panel = document.createElement('section');
    panel.className = 'games-page__recommendations';
    panel.innerHTML = '<h3>Recomendaciones automaticas</h3>';
    var messages = [];
    Object.keys(progress).sort().forEach(function (subject) {
      var item = progress[subject];
      if (item.correct === item.total) messages.push('Excelente en ' + subject + ': subir un poco la dificultad o usar retos mas largos.');
      else if (item.correct / item.total < 0.6) messages.push('Reforzar ' + subject + ' con ejercicios cortos, apoyo visual y repeticion guiada.');
    });
    if (!messages.length) messages.push('Buen avance general: mantener sesiones breves y alternar materias para evitar cansancio.');
    messages.forEach(function (message) {
      var item = document.createElement('p');
      item.textContent = message;
      panel.appendChild(item);
    });
    return panel;
  };

  GameState.prototype.openResults = function () {
    if (!this.resultsDialog) return;
    if (typeof this.resultsDialog.showModal === 'function') this.resultsDialog.showModal();
    else this.resultsDialog.setAttribute('open', 'open');
  };

  GameState.prototype.closeResults = function () {
    if (!this.resultsDialog) return;
    if (typeof this.resultsDialog.close === 'function') this.resultsDialog.close();
    else this.resultsDialog.removeAttribute('open');
  };

  GameState.prototype.saveAttempt = function (total) {
    if (!this.saveUrl) return;
    fetch(this.saveUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
      body: JSON.stringify({
        correct_answers: this.correct,
        total_questions: total,
        completed: true,
        answers: this.results.map(function (result, index) {
          return {
            subject: result.category,
            question: result.question,
            correct_answer: result.answer,
            selected_answer: result.selectedAnswer || '',
            is_correct: result.correct,
            attempts_used: result.attemptsUsed || 1,
            order: index + 1
          };
        })
      })
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

  function initDyslexiaQuiz(root, challenges, selectedDifficulty) {
    var state = new GameState(root, challenges);
    var category = root.querySelector('[data-quiz-category]');
    var prompt = root.querySelector('[data-quiz-prompt]');
    var visual = root.querySelector('[data-quiz-visual]');
    var countdown = root.querySelector('[data-quiz-countdown]');
    var question = root.querySelector('[data-quiz-question]');
    var options = root.querySelector('[data-quiz-options]');
    var speakButton = root.querySelector('[data-quiz-speak]');
    var hintButton = root.querySelector('[data-quiz-hint]');
    var hintText = root.querySelector('[data-quiz-hint-text]');
    var difficulty = root.querySelector('[data-quiz-difficulty]');
    var selectedAnswer = '';
    if (difficulty) difficulty.value = selectedDifficulty || 'easy';

    function resetFeedback() {
      state.feedback.hidden = false;
      state.feedback.className = 'games-page__feedback';
      state.feedback.textContent = '';
    }

    function render() {
      state.updateProgress();
      resetFeedback();
      var challenge = state.current();
      selectedAnswer = '';
      state.board.classList.toggle('games-page__quiz--pattern-layout', challenge.visual_type === 'missing_grid');
      category.textContent = challenge.category;
      prompt.textContent = challenge.prompt;
      renderQuizVisual(challenge);
      question.textContent = challenge.question;
      hintText.textContent = challenge.hint;
      hintText.hidden = true;
      options.innerHTML = '';
      question.hidden = false;
      options.hidden = false;
      if (countdown) countdown.hidden = true;
      challenge.options.forEach(function (option) {
        var button = createQuizOption(challenge, option);
        button.addEventListener('click', function () {
          selectedAnswer = option;
          if (option === challenge.answer) {
            this.classList.add('is-correct');
            disableQuizOptions(options);
            state.results.push({category: challenge.category, question: challenge.question, answer: challenge.answer, selectedAnswer: selectedAnswer, correct: true, attemptsUsed: state.tries + 1});
            state.next(true, render);
          } else {
            state.tries += 1;
            this.classList.add('is-missed');
            this.disabled = true;
            state.sayTry();
            if (state.tries === 1) {
              state.feedback.textContent = 'Casi. Tienes una oportunidad mas.';
            } else {
              disableQuizOptions(options);
              hintText.hidden = false;
              options.querySelectorAll('button').forEach(function (button) {
                if ((button.getAttribute('aria-label') || button.textContent) === challenge.answer) button.classList.add('is-hint');
              });
              state.results.push({category: challenge.category, question: challenge.question, answer: challenge.answer, selectedAnswer: selectedAnswer, correct: false, attemptsUsed: state.tries});
              window.setTimeout(function () { state.next(false, render); }, 1100);
            }
          }
        });
        options.appendChild(button);
      });
      if (challenge.memory_seconds) showMemoryStep(challenge);
    }

    function renderQuizVisual(challenge) {
      visual.className = 'games-page__quiz-visual';
      visual.innerHTML = '';
      if (challenge.visual_type === 'missing_grid') {
        visual.classList.add('games-page__quiz-visual--pattern');
        if (challenge.visual_pattern) visual.classList.add('games-page__quiz-visual--' + challenge.visual_pattern);
        visual.innerHTML = '<div class="games-page__missing-pattern" aria-hidden="true">?</div>';
        return;
      }
      visual.textContent = challenge.visual;
    }

    function createQuizOption(challenge, option) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'games-page__option games-page__quiz-option';
      if (challenge.option_visuals && challenge.option_visuals[option]) {
        button.setAttribute('aria-label', option);
        var pattern = document.createElement('span');
        pattern.className = 'games-page__pattern-option games-page__pattern--' + challenge.option_visuals[option];
        button.appendChild(pattern);
      } else {
        button.textContent = option;
      }
      return button;
    }

    function disableQuizOptions(optionsNode) {
      optionsNode.querySelectorAll('button').forEach(function (button) { button.disabled = true; });
    }

    function showMemoryStep(challenge) {
      var seconds = challenge.memory_seconds;
      question.hidden = true;
      options.hidden = true;
      if (countdown) {
        countdown.hidden = false;
        countdown.textContent = 'Desaparece en ' + seconds + ' segundos';
      }
      var timer = window.setInterval(function () {
        seconds -= 1;
        if (countdown) countdown.textContent = 'Desaparece en ' + seconds + ' segundos';
        if (seconds <= 0) {
          window.clearInterval(timer);
          visual.textContent = '••••';
          question.hidden = false;
          options.hidden = false;
          if (countdown) countdown.hidden = true;
        }
      }, 1000);
    }

    speakButton.addEventListener('click', function () {
      var challenge = state.current();
      speak('Observa con calma. ' + challenge.prompt + '. Luego responde: ' + challenge.question);
    });
    hintButton.addEventListener('click', function () { hintText.hidden = false; });
    if (difficulty) {
      difficulty.addEventListener('change', function () {
        window.location.hash = 'dificultad-' + difficulty.value;
        window.location.reload();
      });
    }
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
    if (type === 'dyslexia_quiz') {
      var difficulty = window.location.hash.replace('#dificultad-', '') || 'easy';
      if (['easy', 'medium', 'hard'].indexOf(difficulty) === -1) difficulty = 'easy';
      initDyslexiaQuiz(root, randomizeQuizChallenges(challenges, difficulty), difficulty);
    }
  });
})();
