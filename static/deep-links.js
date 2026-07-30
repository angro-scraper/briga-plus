(() => {
  const openInviteInsideBriga = event => {
    try {
      const url = new URL(event?.url || '');
      if (url.hostname === 'briga-plus.onrender.com' && url.pathname.startsWith('/poziv/')) {
        window.location.assign(`${url.pathname}${url.search}${url.hash}`);
      }
    } catch (_) { /* Ne menjamo navigaciju za nepoznat link. */ }
  };

  // Dostupno samo u Capacitor omotu; web verzija ostaje nepromenjena.
  window.Capacitor?.Plugins?.App?.addListener?.('appUrlOpen', openInviteInsideBriga);
})();
