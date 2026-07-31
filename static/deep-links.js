(() => {
  const openInviteInsideBriga = event => {
    try {
      const url = new URL(event?.url || '');
      if (url.hostname === 'briga-plus.onrender.com' && url.pathname.startsWith('/poziv/')) {
        const target = `${url.pathname}${url.search}${url.hash}`;
        if (`${window.location.pathname}${window.location.search}${window.location.hash}` !== target) {
          window.location.assign(target);
        }
      }
    } catch (_) { /* Ne menjamo navigaciju za nepoznat link. */ }
  };

  // Dostupno samo u Capacitor omotu; web verzija ostaje nepromenjena.
  const app = window.Capacitor?.Plugins?.App;
  app?.addListener?.('appUrlOpen', openInviteInsideBriga);
  app?.getLaunchUrl?.().then(openInviteInsideBriga).catch(() => {});
})();
