/*
 * Tile builder (arma and contesta "build"): the child taps (or drags) tiles into the answer row and presses "Revisar".
 *
 * - Tap a tile in the pool: it goes to the row (into the 👀 hole when there is one). Tap a placed tile: it goes back.
 * - Drag also works (pointer events); tapping always works, with keyboard too. Tiles are touch-action: pan-y so a swipe
 *   can still scroll to "Revisar"; on touch a mostly horizontal drag moves a tile, a vertical swipe scrolls instead.
 * - The step's player (task-player.js) is reached through the step root, never through window.TaskPlayer:
 *   the teacher preview stacks several steps on one page.
 * - Outcome 'try_again' + hint.kind 'omission': a 👀 hole marks the missing place and its sound is played
 *   (the phoneme or syllable, never the letter name). 'modeled': the model answer replaces the row.
 * - Preview: nothing is sent; the target units rendered for the teacher drive a local check, so the feedback can be tried.
 */
(() => {
  const DRAG_PX = 8;
  const MAX_ATTEMPTS = 2;

  const init = (build) => {
    const stepRoot = build.closest('[data-task-step]');
    const row = build.querySelector('[data-build-row]');
    const pool = build.querySelector('[data-build-tiles]');
    const check = build.querySelector('[data-build-check]');
    if (!stepRoot || !row || !pool || !check) return;
    const preview = stepRoot.dataset.preview === '1';
    const joiner = build.dataset.buildUnit === 'word' ? ' ' : '';
    let attempts = 0;
    let busy = false;
    let locked = false;
    let hole = null;
    let justDragged = false;

    pool.querySelectorAll('[data-tile]').forEach((tile) => {
      tile.slotNode = tile.closest('[data-tile-slot]');
    });

    const placedTiles = () => [...row.querySelectorAll('[data-tile]')];
    const sync = () => {
      check.disabled = locked || busy || placedTiles().length === 0;
      row.classList.toggle('is-empty', placedTiles().length === 0 && !hole);
    };

    const removeHole = () => {
      hole?.remove();
      hole = null;
    };

    const speakSound = (hint) => stepRoot.taskPlayer?.playHint(hint);

    const labelPlaced = (tile, isPlaced) => {
      tile.classList.toggle('is-placed', isPlaced);
      if (isPlaced) tile.setAttribute('aria-label', `Quitar la ficha ${tile.dataset.tile}`);
      else tile.removeAttribute('aria-label');
    };

    const place = (tile, before = null) => {
      if (before) {
        row.insertBefore(tile, before);
      } else if (hole) {
        row.insertBefore(tile, hole);
      } else {
        row.append(tile);
      }
      removeHole();
      labelPlaced(tile, true);
      sync();
    };

    const unplace = (tile) => {
      tile.slotNode.append(tile);
      labelPlaced(tile, false);
      sync();
    };

    const resetRow = () => {
      placedTiles().forEach(unplace);
      removeHole();
      sync();
    };

    const showHole = (hint) => {
      const index = hint.hole_index;
      removeHole();
      hole = document.createElement('button');
      hole.type = 'button';
      hole.className = 'task-build__hole';
      hole.setAttribute('aria-label', 'Aquí falta una ficha. Toca para escuchar lo que falta.');
      hole.textContent = '👀';
      hole.addEventListener('click', () => speakSound(hint));
      const tiles = placedTiles();
      row.insertBefore(hole, tiles[index] || null);
      sync();
    };

    // Preview only: put the builder back to its first state so the teacher can try again.
    const resetButton = build.querySelector('[data-build-reset]');
    const allTiles = [...pool.querySelectorAll('[data-tile]')];
    resetButton?.addEventListener('click', () => {
      allTiles.forEach((tile) => {
        tile.disabled = false;
        unplace(tile);
      });
      removeHole();
      row.replaceChildren();
      row.classList.remove('is-model', 'is-good', 'is-hint');
      build.querySelectorAll('[data-build-before], [data-build-after]').forEach((node) => {
        node.hidden = false;
      });
      pool.hidden = false;
      attempts = 0;
      locked = false;
      resetButton.hidden = true;
      const feedbackBox = stepRoot.querySelector('[data-task-feedback]');
      if (feedbackBox) feedbackBox.hidden = true;
      sync();
    });

    const closeBuild = (modelAnswer) => {
      locked = true;
      if (resetButton) resetButton.hidden = false;
      if (modelAnswer) {
        // The model is the whole sentence: it replaces the row and the words around it.
        removeHole();
        build.querySelectorAll('[data-build-before], [data-build-after]').forEach((node) => {
          node.hidden = true;
        });
        const model = document.createElement('span');
        model.className = 'task-build__model';
        model.textContent = modelAnswer;
        row.replaceChildren(model);
        row.classList.add('is-model');
        pool.hidden = true;
      } else {
        row.classList.add('is-good');
        pool.querySelectorAll('button').forEach((node) => {
          node.disabled = true;
        });
      }
      sync();
    };

    const apply = (outcome) => {
      if (!outcome) {
        sync();
        return;
      }
      if (outcome.status === 'correct') {
        closeBuild('');
      } else if (outcome.status === 'modeled') {
        closeBuild(outcome.model_answer || '');
      } else if (outcome.hint?.kind === 'omission') {
        showHole(outcome.hint);
      } else {
        resetRow();
      }
      if (outcome.step_done) locked = true;
      sync();
    };

    /* ---------- preview: a local stand-in for the server check ----------
     * APPROXIMATE mirror of homework.writing.check_build for the teacher preview only (preview never writes
     * and has no assignment to evaluate against): case-insensitive, and "omission" means the answer is a
     * subsequence of the target. The real check is always the server's. */
    const previewUnits = () => {
      try {
        return JSON.parse(document.getElementById(build.dataset.buildUnits)?.textContent || '[]');
      } catch (error) {
        return [];
      }
    };

    const previewOutcome = (tiles) => {
      const units = previewUnits();
      const target = units.map((unit) => unit.text.toLowerCase());
      const answer = tiles.map((tile) => tile.toLowerCase());
      attempts += 1;
      if (target.length === answer.length && target.every((unit, i) => unit === answer[i])) {
        return {status: 'correct', step_done: false};
      }
      let matched = 0;
      let firstMissing = -1;
      target.forEach((unit, i) => {
        if (matched < answer.length && unit === answer[matched]) matched += 1;
        else if (firstMissing < 0) firstMissing = i;
      });
      if (attempts >= MAX_ATTEMPTS) {
        return {status: 'modeled', model_answer: build.dataset.buildModel || '', step_done: false};
      }
      if (matched === answer.length && firstMissing >= 0) {
        return {status: 'try_again', hint: {say: units[firstMissing].say, audio: units[firstMissing].audio || undefined, hole_index: firstMissing, kind: 'omission'}, step_done: false};
      }
      return {status: 'try_again', hint: {say: units.map((unit) => unit.text).join(joiner), hole_index: null, kind: 'try_again'}, step_done: false};
    };

    /* ---------- submit ---------- */
    const submit = async () => {
      if (busy || locked || !placedTiles().length) return;
      busy = true;
      sync();
      const tiles = placedTiles().map((tile) => tile.dataset.tile);
      const player = stepRoot.taskPlayer;
      let outcome = null;
      try {
        if (preview) {
          outcome = previewOutcome(tiles);
          player?.showFeedback(outcome);
        } else if (player) {
          outcome = await player.answer(0, {tiles});
        }
      } finally {
        busy = false;
      }
      apply(outcome);
    };

    check.addEventListener('click', submit);

    /* ---------- tap ---------- */
    build.addEventListener('click', (event) => {
      const tile = event.target.closest('[data-tile]');
      if (!tile || !build.contains(tile)) return;
      if (justDragged) {
        justDragged = false;
        return;
      }
      if (locked || busy) return;
      if (row.contains(tile)) unplace(tile);
      else place(tile);
      tile.focus();
    });

    /* ---------- drag (optional; tapping always works) ---------- */
    const insertionPoint = (x, y, dragged) =>
      placedTiles().find((tile) => {
        if (tile === dragged) return false;
        const box = tile.getBoundingClientRect();
        return y < box.top || (y <= box.bottom && x < box.left + box.width / 2);
      }) || null;

    build.addEventListener('pointerdown', (event) => {
      const tile = event.target.closest('[data-tile]');
      if (!tile || locked || busy || (event.pointerType === 'mouse' && event.button !== 0)) return;
      justDragged = false;
      const startX = event.clientX;
      const startY = event.clientY;
      const box = tile.getBoundingClientRect();
      let dragging = false;
      let ghost = null;

      const move = (moveEvent) => {
        if (!dragging && Math.hypot(moveEvent.clientX - startX, moveEvent.clientY - startY) < DRAG_PX) return;
        if (!dragging) {
          dragging = true;
          ghost = tile.cloneNode(true);
          ghost.removeAttribute('data-tile');
          ghost.classList.add('is-ghost');
          ghost.style.width = `${box.width}px`;
          document.body.append(ghost);
          tile.classList.add('is-dragging');
        }
        moveEvent.preventDefault();
        ghost.style.left = `${moveEvent.clientX - box.width / 2}px`;
        ghost.style.top = `${moveEvent.clientY - box.height / 2}px`;
      };

      const finish = (endEvent) => {
        document.removeEventListener('pointermove', move);
        document.removeEventListener('pointerup', finish);
        document.removeEventListener('pointercancel', finish);
        if (!dragging) return;
        ghost.remove();
        tile.classList.remove('is-dragging');
        justDragged = true;
        window.setTimeout(() => {
          justDragged = false;
        }, 100);
        if (endEvent.type === 'pointercancel') return;
        const over = document.elementFromPoint(endEvent.clientX, endEvent.clientY);
        if (!over) return;
        if (hole && (over === hole || hole.contains(over))) {
          place(tile);
        } else if (row.contains(over) || over === row || over.closest('.task-build__line')) {
          place(tile, insertionPoint(endEvent.clientX, endEvent.clientY, tile));
        } else if (pool.contains(over) && row.contains(tile)) {
          unplace(tile);
        }
        tile.focus();
      };

      document.addEventListener('pointermove', move, {passive: false});
      document.addEventListener('pointerup', finish);
      document.addEventListener('pointercancel', finish);
    });

    sync();
  };

  document.querySelectorAll('[data-build]').forEach(init);
})();
