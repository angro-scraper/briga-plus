(() => {
  'use strict';

  const root = document.documentElement;
  const body = document.body;
  root.classList.add('briga-js');

  // Keep the page behind native dialogs still and restore focus after closing.
  document.querySelectorAll('dialog').forEach(dialog => {
    let trigger = null;
    dialog.addEventListener('close', () => {
      body.classList.toggle('dialog-open', Boolean(document.querySelector('dialog[open]')));
      trigger?.focus?.({ preventScroll: true });
      trigger = null;
    });
    dialog.addEventListener('cancel', () => {
      body.classList.remove('dialog-open');
    });

    const originalShow = dialog.showModal?.bind(dialog);
    if (originalShow) {
      dialog.showModal = () => {
        trigger = document.activeElement;
        originalShow();
        body.classList.add('dialog-open');
        const focusTarget = dialog.querySelector('.senior-back, .modal-close, input:not([type="hidden"]), select, textarea, button');
        window.setTimeout(() => focusTarget?.focus?.({ preventScroll: true }), 40);
      };
    }
  });

  // Serbian time-aware greeting on the senior picture home.
  const greeting = document.querySelector('.picture-greeting b');
  if (greeting) {
    const hour = new Date().getHours();
    const prefix = hour < 12 ? 'Dobro jutro' : hour < 18 ? 'Dobar dan' : 'Dobro veče';
    greeting.textContent = greeting.textContent.replace(/^Dobro jutro|^Dobar dan|^Dobro veče/, prefix);
  }

  // Add selected-state semantics to the persistent mobile home item.
  document.querySelectorAll('.picture-bottom-nav a:first-child, .family-mobile-home > nav a:first-child').forEach(item => {
    item.setAttribute('aria-current', 'page');
  });

  // Never let an in-page link disappear below the mobile navigation.
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', () => {
      const selector = link.getAttribute('href');
      if (!selector || selector === '#') return;
      let target = null;
      try {
        target = document.querySelector(selector);
      } catch (_) {
        return;
      }
      if (!target) return;
      target.style.scrollMarginBottom = '100px';
    });
  });
})();
