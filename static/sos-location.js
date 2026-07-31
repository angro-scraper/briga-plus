(() => {
  const SOS_FORMS = '#sos, #family-mobile-sos, #senior-sos, #picture-sos, #easy-sos';
  const TARGET_ACCURACY_METERS = 35;
  const MAX_WAIT_MS = 12000;

  const accuracyOf = position => {
    const value = Number(position?.coords?.accuracy);
    return Number.isFinite(value) && value > 0 ? value : Number.POSITIVE_INFINITY;
  };

  const bestAvailablePosition = () => new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Uređaj ne podržava GPS.'));
      return;
    }

    let best = null;
    let watchId = null;
    let settled = false;

    const finish = (position, error) => {
      if (settled) return;
      settled = true;
      if (watchId !== null) navigator.geolocation.clearWatch(watchId);
      window.clearTimeout(timeoutId);
      if (position) resolve(position);
      else reject(error || new Error('GPS lokacija nije dostupna.'));
    };

    const timeoutId = window.setTimeout(() => {
      finish(best, new Error('GPS nije uspeo da odredi lokaciju.'));
    }, MAX_WAIT_MS);

    watchId = navigator.geolocation.watchPosition(position => {
      if (!best || accuracyOf(position) < accuracyOf(best)) best = position;
      if (accuracyOf(best) <= TARGET_ACCURACY_METERS) finish(best);
    }, error => {
      // Odbijena dozvola se neće popraviti čekanjem; ostale greške ostavljaju
      // kratak prostor GPS-u da vrati bolje očitavanje.
      if (error?.code === 1) finish(best, error);
    }, {
      enableHighAccuracy: true,
      maximumAge: 0,
      timeout: MAX_WAIT_MS,
    });
  });

  const qualityMessage = accuracy => {
    if (!Number.isFinite(accuracy)) return 'GPS lokacija je učitana. Šaljemo SOS…';
    const rounded = Math.max(1, Math.round(accuracy));
    if (rounded <= 50) return `Precizna GPS lokacija je učitana (oko ${rounded} m). Šaljemo SOS…`;
    if (rounded <= 150) return `GPS lokacija je učitana, procenjena preciznost je oko ${rounded} m. Šaljemo SOS…`;
    return `Lokacija je približna (oko ${rounded} m). Za precizniji GPS uključite „Precizna lokacija” u podešavanjima telefona.`;
  };

  document.querySelectorAll(SOS_FORMS).forEach(form => {
    form.addEventListener('submit', async event => {
      if (form.dataset.locationReady === 'true') return;
      event.preventDefault();
      if (form.dataset.sendImmediately !== 'true') {
        const confirmation = form.dataset.confirmMessage || 'Da li želite da pošaljete SOS porodici?';
        if (!window.confirm(confirmation)) return;
      }

      const button = form.querySelector('button[type="submit"], button');
      const status = form.querySelector('[aria-live]');
      if (button) {
        button.disabled = true;
        button.dataset.originalLabel = button.innerHTML;
        button.textContent = 'Učitavamo preciznu GPS lokaciju…';
      }
      if (status) status.textContent = 'Sačekajte trenutak — GPS traži najpreciznije dostupno očitavanje.';

      try {
        const position = await bestAvailablePosition();
        const accuracy = accuracyOf(position);
        form.elements.latitude.value = position.coords.latitude.toFixed(6);
        form.elements.longitude.value = position.coords.longitude.toFixed(6);
        if (form.elements.accuracy && Number.isFinite(accuracy)) {
          form.elements.accuracy.value = String(Math.max(1, Math.round(accuracy)));
        }
        if (status) status.textContent = qualityMessage(accuracy);
      } catch (_) {
        if (status) status.textContent = 'GPS nije dostupan. SOS se ipak odmah šalje bez lokacije.';
      }

      form.dataset.locationReady = 'true';
      form.submit();
    });
  });
})();
