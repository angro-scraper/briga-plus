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

  const fillLocation = (form, position) => {
    const accuracy = accuracyOf(position);
    form.elements.latitude.value = position.coords.latitude.toFixed(6);
    form.elements.longitude.value = position.coords.longitude.toFixed(6);
    if (form.elements.accuracy && Number.isFinite(accuracy)) {
      form.elements.accuracy.value = String(Math.max(1, Math.round(accuracy)));
    }
    return accuracy;
  };

  const restoreButton = button => {
    if (!button) return;
    button.disabled = false;
    if (button.dataset.originalLabel) button.innerHTML = button.dataset.originalLabel;
  };

  const showCountdown = (form, button, status) => {
    if (button) button.disabled = true;
    const overlay = document.createElement('section');
    overlay.className = 'sos-countdown-overlay';
    overlay.setAttribute('role', 'alertdialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'sos-countdown-title');
    overlay.innerHTML = `
      <div class="sos-countdown-panel">
        <svg class="ui-icon" aria-hidden="true"><use href="/static/briga-ui-icons.svg#phone"></use></svg>
        <h2 id="sos-countdown-title">Šaljemo SOS</h2>
        <p class="sos-countdown-copy">GPS lokacija se učitava. Alarm se automatski šalje porodici.</p>
        <strong class="sos-countdown-number" aria-live="assertive">5</strong>
        <div class="sos-countdown-actions">
          <button class="sos-cancel" type="button">OTKAŽI</button>
          <button class="sos-call-now" type="button">POZOVI ODMAH</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    document.body.classList.add('sos-overlay-open');

    const number = overlay.querySelector('.sos-countdown-number');
    const copy = overlay.querySelector('.sos-countdown-copy');
    const cancel = overlay.querySelector('.sos-cancel');
    const callNow = overlay.querySelector('.sos-call-now');
    let remaining = 5;
    let cancelled = false;
    let finishing = false;

    const locationResult = bestAvailablePosition().then(
      position => ({ position }),
      error => ({ error }),
    );

    const close = () => {
      window.clearInterval(timer);
      overlay.remove();
      document.body.classList.remove('sos-overlay-open');
    };

    const finish = async () => {
      if (cancelled || finishing) return;
      finishing = true;
      window.clearInterval(timer);
      number.textContent = '✓';
      copy.textContent = 'Proveravamo najprecizniju dostupnu GPS lokaciju…';
      cancel.disabled = true;
      callNow.disabled = true;

      const result = await locationResult;
      if (cancelled) return;
      if (result.position) {
        const accuracy = fillLocation(form, result.position);
        copy.textContent = qualityMessage(accuracy);
        if (status) status.textContent = qualityMessage(accuracy);
      } else {
        copy.textContent = 'GPS nije dostupan. SOS se ipak odmah šalje porodici.';
        if (status) status.textContent = copy.textContent;
      }
      form.dataset.locationReady = 'true';
      window.setTimeout(() => {
        close();
        form.submit();
      }, 250);
    };

    const timer = window.setInterval(() => {
      remaining -= 1;
      number.textContent = String(Math.max(0, remaining));
      if (remaining <= 0) finish();
    }, 1000);

    cancel.addEventListener('click', () => {
      cancelled = true;
      close();
      restoreButton(button);
      if (status) status.textContent = 'SOS je otkazan.';
    });
    callNow.addEventListener('click', finish);
    cancel.focus();
  };

  document.querySelectorAll(SOS_FORMS).forEach(form => {
    form.addEventListener('submit', async event => {
      if (form.dataset.locationReady === 'true') return;
      event.preventDefault();
      const button = form.querySelector('button[type="submit"], button');
      const status = form.querySelector('[aria-live]');
      if (button && !button.dataset.originalLabel) button.dataset.originalLabel = button.innerHTML;

      if (form.dataset.sosOverlay === 'true') {
        showCountdown(form, button, status);
        return;
      }

      if (form.dataset.sendImmediately !== 'true') {
        const confirmation = form.dataset.confirmMessage || 'Da li želite da pošaljete SOS porodici?';
        if (!window.confirm(confirmation)) return;
      }

      if (button) {
        button.disabled = true;
        button.textContent = 'Učitavamo preciznu GPS lokaciju…';
      }
      if (status) status.textContent = 'Sačekajte trenutak — GPS traži najpreciznije dostupno očitavanje.';

      try {
        const position = await bestAvailablePosition();
        const accuracy = fillLocation(form, position);
        if (status) status.textContent = qualityMessage(accuracy);
      } catch (_) {
        if (status) status.textContent = 'GPS nije dostupan. SOS se ipak odmah šalje bez lokacije.';
      }

      form.dataset.locationReady = 'true';
      form.submit();
    });
  });
})();
