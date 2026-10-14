// Row action menus ported from SistemaBodega: <details class="action-menu">
// with a <summary> kebab and an .action-menu-panel of items. The native
// <details> gives focus, Enter/Space toggling and the expanded state; this
// script adds Bodega's behaviour: one menu open at a time, click outside
// closes, viewport-aware placement (flip upward, cap height), Escape closes
// and returns focus to the kebab, and a chosen item closes its menu.
(() => {
  const MENU = 'details.action-menu';
  const GAP = 6;
  const EDGE = 8;
  let lastMenu = null;

  const summaryOf = (menu) => menu.querySelector(':scope > summary');
  const panelOf = (menu) => menu.querySelector(':scope > .action-menu-panel');

  const clearPlacement = (menu) => {
    menu.classList.remove('dropdown-up', 'is-floating');
    const panel = panelOf(menu);
    if (!panel) return;
    ['top', 'left', '--action-menu-max-height'].forEach((prop) => panel.style.removeProperty(prop));
  };

  // Fixed placement escapes the overflow of table scroll containers.
  const positionMenu = (menu) => {
    const trigger = summaryOf(menu);
    const panel = panelOf(menu);
    if (!trigger || !panel || !menu.open) return;
    clearPlacement(menu);
    const t = trigger.getBoundingClientRect();
    const viewportW = document.documentElement.clientWidth;
    const viewportH = window.innerHeight;
    if (viewportH > 0 && (t.bottom < 0 || t.top > viewportH)) {
      menu.open = false;
      return;
    }
    menu.classList.add('is-floating');
    const width = panel.offsetWidth;
    const height = panel.scrollHeight;
    const spaceBelow = viewportH - t.bottom - GAP - EDGE;
    const spaceAbove = t.top - GAP - EDGE;
    const openUp = height > spaceBelow && spaceAbove > spaceBelow;
    const available = Math.max(0, openUp ? spaceAbove : spaceBelow);
    const shown = Math.min(height, available);
    // Align to the kebab's right edge (Bodega); when that would leave the
    // screen (stacked phone rows), open rightward from its left edge.
    const preferred = t.right - width >= EDGE ? t.right - width : t.left;
    const left = Math.min(preferred, viewportW - width - EDGE);
    if (openUp) menu.classList.add('dropdown-up');
    if (available < height) panel.style.setProperty('--action-menu-max-height', `${available}px`);
    panel.style.left = `${Math.max(EDGE, left)}px`;
    panel.style.top = `${openUp ? t.top - GAP - shown : t.bottom + GAP}px`;
  };

  const closeMenu = (menu, { focus = false } = {}) => {
    if (!menu.open) return;
    menu.open = false;
    clearPlacement(menu);
    if (focus) summaryOf(menu)?.focus({ preventScroll: true });
  };

  const openMenus = () => document.querySelectorAll(`${MENU}[open]`);

  // "toggle" does not bubble; listen in the capture phase.
  document.addEventListener('toggle', (event) => {
    const menu = event.target;
    if (!(menu instanceof HTMLDetailsElement) || !menu.matches(MENU)) return;
    if (!menu.open) {
      clearPlacement(menu);
      return;
    }
    openMenus().forEach((other) => { if (other !== menu) closeMenu(other); });
    positionMenu(menu);
  }, true);

  document.addEventListener('click', (event) => {
    openMenus().forEach((menu) => { if (!menu.contains(event.target)) closeMenu(menu); });

    const item = event.target.closest('.action-menu-panel :is(a, button)');
    const menu = item?.closest(MENU);
    if (!menu) return;
    lastMenu = menu;
    // Close after the click finishes so the item's own action (dialog
    // trigger, form submit, link) runs first. Buttons hand focus back to
    // the kebab; a dialog that opens takes focus from there.
    const isButton = item.tagName === 'BUTTON';
    window.setTimeout(() => {
      const keepFocus = isButton && (document.activeElement === item || document.activeElement === document.body);
      closeMenu(menu, { focus: keepFocus });
    }, 0);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    const menu = event.target.closest?.(MENU) || [...openMenus()].pop();
    if (!menu || !menu.open) return;
    event.preventDefault();
    closeMenu(menu, { focus: true });
  });

  const reposition = () => openMenus().forEach(positionMenu);
  window.addEventListener('resize', reposition);
  document.addEventListener('scroll', reposition, true);

  // Bootstrap modals return focus to their trigger, which is hidden inside
  // the closed menu; send it to the kebab instead.
  document.addEventListener('hidden.bs.modal', () => {
    const menu = lastMenu;
    if (!menu?.isConnected) return;
    window.setTimeout(() => {
      const active = document.activeElement;
      const lost = !active || active === document.body
        || (active.checkVisibility ? !active.checkVisibility() : active.offsetParent === null);
      if (lost) summaryOf(menu)?.focus({ preventScroll: true });
    }, 0);
  });
})();
