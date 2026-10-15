// Prints only the student access card: on beforeprint, clone the visible card
// into a top-level sheet and let the print stylesheet hide everything else.
(function () {
  var root = document.documentElement;

  function visibleCard() {
    var cards = document.querySelectorAll('[data-access-card]');
    for (var i = 0; i < cards.length; i += 1) {
      if (cards[i].getClientRects().length) return cards[i];
    }
    return cards[0] || null;
  }

  function cleanup() {
    root.classList.remove('access-card-printing');
    var sheet = document.querySelector('.access-card-print');
    if (sheet) sheet.remove();
  }

  window.addEventListener('beforeprint', function () {
    cleanup();
    var card = visibleCard();
    if (!card) return;
    var sheet = document.createElement('div');
    sheet.className = 'access-card-print';
    sheet.setAttribute('aria-hidden', 'true');
    sheet.appendChild(card.cloneNode(true));
    document.body.appendChild(sheet);
    root.classList.add('access-card-printing');
  });
  window.addEventListener('afterprint', cleanup);

  document.addEventListener('click', function (event) {
    if (event.target.closest('[data-access-card-print]')) window.print();
  });
})();
