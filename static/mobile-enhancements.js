(() => {
  const csrfToken = () => document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';

  const voiceButton = document.querySelector('#voice-button-mobile');
  const voiceStatus = document.querySelector('#voice-status');
  if (voiceButton && voiceStatus) {
    let recorder;
    let chunks = [];
    let stream;
    voiceButton.addEventListener('click', async () => {
      if (recorder?.state === 'recording') { recorder.stop(); return; }
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        voiceStatus.textContent = 'Snimanje glasa nije podržano na ovom uređaju.';
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const supportedMime = ['audio/mp4', 'audio/webm;codecs=opus', 'audio/webm'].find(type => MediaRecorder.isTypeSupported?.(type));
        chunks = [];
        recorder = supportedMime ? new MediaRecorder(stream, { mimeType: supportedMime }) : new MediaRecorder(stream);
        recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
        recorder.onstart = () => { voiceButton.textContent = '■ Završi snimanje'; voiceStatus.textContent = 'Snimanje je u toku…'; };
        recorder.onerror = () => { voiceStatus.textContent = 'Snimanje nije uspelo. Pokušajte ponovo.'; };
        recorder.onstop = async () => {
          stream?.getTracks().forEach(track => track.stop());
          voiceButton.disabled = true;
          voiceStatus.textContent = 'Šaljemo glasovnu poruku…';
          try {
            const formData = new FormData();
            formData.append('action', 'voice_message');
            formData.append('return_modal', 'chat');
            formData.append('audio', new Blob(chunks, { type: recorder.mimeType || 'audio/webm' }), 'glasovna-poruka.webm');
            formData.append('csrfmiddlewaretoken', csrfToken());
            const response = await fetch('/', { method: 'POST', body: formData });
            if (!response.ok) throw new Error();
            window.location.assign('/?open=chat');
          } catch (_) {
            voiceButton.disabled = false;
            voiceButton.textContent = '● Snimi glasovnu poruku';
            voiceStatus.textContent = 'Poruka nije poslata. Proverite vezu i pokušajte ponovo.';
          }
        };
        recorder.start();
      } catch (_) {
        voiceStatus.textContent = 'Mikrofon nije dostupan. Proverite dozvolu za mikrofon u podešavanjima telefona.';
      }
    });
  }

  const speechButton = document.querySelector('#read-health-mobile, #read-health');
  const cleanSerbianText = value => value.replace(/(\d{2,3})\s*\/\s*(\d{2,3})/g, '$1 kroz $2').replace(/(\d),\s*(\d)/g, '$1 zarez $2').replace(/\s+/g, ' ').trim();
  const waitForSophie = () => new Promise(resolve => {
    const find = () => speechSynthesis.getVoices().find(voice => /sophie/i.test(voice.name) && (/^sr(?:-|_)/i.test(voice.lang) || /serbian|srpski/i.test(voice.name)));
    const immediate = find();
    if (immediate) return resolve(immediate);
    const finish = () => { speechSynthesis.removeEventListener('voiceschanged', changed); resolve(find()); };
    const changed = () => { if (find()) finish(); };
    speechSynthesis.addEventListener('voiceschanged', changed);
    setTimeout(finish, 5500);
  });
  if (speechButton) {
    let speaking = false;
    let activeAudio = null;
    speechButton.addEventListener('click', async event => {
      // Ovaj handler važi za oba panela i zaustavlja stariji lokalni handler
      // čuvanog lica, kako bi se uvek prvo koristio serverski Sophie glas.
      event.stopImmediatePropagation();
      if (speaking) {
        if (activeAudio) {
          activeAudio.pause();
          activeAudio.currentTime = 0;
          activeAudio.onended();
        } else {
          speechSynthesis.cancel();
        }
        return;
      }
      const entries = [...document.querySelectorAll('.health-list article')].map(item => cleanSerbianText(item.innerText));
      const narration = entries.length ? `Zdravstveni dnevnik. ${entries.join('. ')}. Kraj unosa.` : 'Zdravstveni dnevnik je trenutno prazan.';
      speechButton.textContent = 'Pripremamo Sophie glas…';
      try {
        const response = await fetch('/sophie-govor/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify({ text: narration }) });
        if (response.ok && response.headers.get('content-type')?.includes('audio/')) {
          const audio = new Audio(URL.createObjectURL(await response.blob()));
          activeAudio = audio;
          speaking = true; speechButton.textContent = '■ Zaustavi čitanje';
          audio.onended = audio.onerror = () => { speaking = false; activeAudio = null; speechButton.textContent = '🔊 Pročitaj poslednje unose — Sophie'; URL.revokeObjectURL(audio.src); };
          audio.play();
          return;
        }
      } catch (_) { /* Lokalna Sophie je bezbedna rezerva kada Azure nije podešen. */ }
      if (!('speechSynthesis' in window)) { speechButton.textContent = 'Sophie glas nije dostupan na ovom uređaju.'; return; }
      const sophie = await waitForSophie();
      if (!sophie) { speechButton.textContent = 'Sophie srpski glas nije dostupan. Ne prebacujemo na drugi glas.'; return; }
      const utterance = new SpeechSynthesisUtterance(narration);
      utterance.lang = 'sr-RS'; utterance.voice = sophie; utterance.rate = .82; utterance.pitch = 1; utterance.volume = 1;
      utterance.onstart = () => { speaking = true; speechButton.textContent = '■ Zaustavi čitanje'; };
      utterance.onend = utterance.onerror = () => { speaking = false; speechButton.textContent = '🔊 Pročitaj poslednje unose — Sophie'; };
      speechSynthesis.cancel(); speechSynthesis.speak(utterance);
    }, { capture: true });
  }

  const pushButton = document.querySelector('#push-button-mobile');
  const pushStatus = document.querySelector('#push-status');
  const toUint8Array = value => { const padding = '='.repeat((4 - value.length % 4) % 4); const base64 = (value + padding).replace(/-/g, '+').replace(/_/g, '/'); return Uint8Array.from(atob(base64), character => character.charCodeAt(0)); };
  const openNotificationTarget = event => {
    const notification = event?.notification || {};
    const kind = notification.data?.kind || notification.extra?.kind || '';
    const target = kind === 'sos'
      ? '/?open=sos-detail'
      : (notification.data?.url || notification.extra?.url || '/');
    try {
      const url = new URL(target, window.location.origin);
      if (url.origin === window.location.origin) window.location.assign(`${url.pathname}${url.search}${url.hash}`);
    } catch (_) { /* Nepoznata adresa se ne otvara iz bezbednosnih razloga. */ }
  };
  const nativePushPlugin = window.Capacitor?.Plugins?.PushNotifications;
  nativePushPlugin?.addListener?.('pushNotificationActionPerformed', openNotificationTarget);
  window.Capacitor?.Plugins?.LocalNotifications?.addListener?.('localNotificationActionPerformed', openNotificationTarget);
  let nativeRegistrationPromise = null;
  const saveNativeToken = async registration => {
    const platform = window.Capacitor.getPlatform?.() === 'ios' ? 'ios' : 'android';
    const userId = document.body.dataset.userId || 'anonymous';
    const cacheKey = `briga-native-push-${platform}-${userId}`;
    try {
      const cached = JSON.parse(localStorage.getItem(cacheKey) || 'null');
      if (cached?.token === registration.value && Date.now() - cached.savedAt < 24 * 60 * 60 * 1000) {
        return { delivery_configured: cached.deliveryConfigured, cached: true };
      }
    } catch (_) { /* Neispravan stari zapis se bezbedno zamenjuje. */ }
    const response = await fetch('/native-push-pretplata/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
      body: JSON.stringify({ token: registration.value, platform }),
    });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error('Telefon nije sačuvan uz nalog.');
    localStorage.setItem(cacheKey, JSON.stringify({
      token: registration.value,
      deliveryConfigured: Boolean(result.delivery_configured),
      savedAt: Date.now(),
    }));
    return result;
  };
  const registerNativePush = async ({ askPermission = false } = {}) => {
    if (!nativePushPlugin) return null;
    if (nativeRegistrationPromise) return nativeRegistrationPromise;
    nativeRegistrationPromise = (async () => {
      const permission = askPermission
        ? await nativePushPlugin.requestPermissions()
        : await nativePushPlugin.checkPermissions();
      if (permission.receive !== 'granted') {
        if (askPermission) throw new Error('Dozvola za obaveštenja nije data. Uključite je u podešavanjima telefona.');
        return null;
      }
      if (window.Capacitor.getPlatform?.() === 'android') {
        await nativePushPlugin.createChannel?.({
          id: 'briga_vazno',
          name: 'Briga+ važna obaveštenja',
          description: 'SOS, terapija, porodične poruke i važni podsetnici',
          importance: 5,
          visibility: 1,
          vibration: true,
        });
      }
      return new Promise(async (resolve, reject) => {
        let finished = false;
        let successHandle;
        let errorHandle;
        const finish = async (callback, value) => {
          if (finished) return;
          finished = true;
          window.clearTimeout(timeoutId);
          await successHandle?.remove?.();
          await errorHandle?.remove?.();
          callback(value);
        };
        successHandle = await nativePushPlugin.addListener('registration', async registration => {
          try { await finish(resolve, await saveNativeToken(registration)); }
          catch (error) { await finish(reject, error); }
        });
        errorHandle = await nativePushPlugin.addListener('registrationError', () => {
          finish(reject, new Error('Povezivanje telefona nije uspelo.'));
        });
        const timeoutId = window.setTimeout(() => {
          finish(reject, new Error('Povezivanje telefona traje predugo. Pokušajte ponovo.'));
        }, 8000);
        try { await nativePushPlugin.register(); }
        catch (error) { await finish(reject, error); }
      });
    })().finally(() => { nativeRegistrationPromise = null; });
    return nativeRegistrationPromise;
  };

  // Ako je korisnik ranije već dao dozvolu, token se pri svakom otvaranju
  // tiho obnavlja uz trenutno prijavljen nalog. Ne prikazujemo novi sistemski upit.
  if (nativePushPlugin) {
    registerNativePush().then(result => {
      if (!result || !pushStatus || !pushButton) return;
      pushStatus.textContent = result.delivery_configured
        ? 'SOS i važni podsetnici su uključeni na ovom telefonu.'
        : 'Telefon je povezan, ali serverska isporuka još nije podešena.';
      pushButton.textContent = 'Obaveštenja uključena';
      pushButton.disabled = true;
    }).catch(() => { /* Ručni pokušaj ostaje dostupan u prozoru Obaveštenja. */ });
  }

  if (pushButton && pushStatus) pushButton.addEventListener('click', async () => {
    const key = pushButton.dataset.vapidKey || '';
    try {
      pushButton.disabled = true; pushButton.textContent = 'Proveravamo dozvolu…';
      if (nativePushPlugin) {
        pushStatus.textContent = 'Povezujemo ovaj telefon sa vašim Briga+ nalogom…';
        const result = await registerNativePush({ askPermission: true });
        if (!result) throw new Error('Dozvola za obaveštenja nije data.');
        pushStatus.textContent = result.delivery_configured
          ? 'SOS i važni podsetnici su uključeni na ovom telefonu.'
          : 'Telefon je povezan. Serverski ključ za isporuku još treba završno podesiti.';
        pushButton.textContent = 'Obaveštenja uključena';
        pushButton.disabled = true;
        return;
      }
      if (!key) throw new Error('Push ključevi još nisu podešeni na serveru.');
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) throw new Error('Ovaj preglednik ne podržava push. U aplikaciji će se koristiti native obaveštenja.');
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') throw new Error('Dozvola za obaveštenja nije data.');
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: toUint8Array(key) });
      const response = await fetch('/push-pretplata/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(subscription) });
      const result = await response.json();
      if (!result.ok) throw new Error(result.error || 'Pretplata nije uspela.');
      pushStatus.textContent = 'Obaveštenja su uključena na ovom uređaju.'; pushButton.textContent = 'Obaveštenja uključena';
    } catch (error) {
      pushButton.disabled = false; pushButton.textContent = 'Uključi na ovom uređaju'; pushStatus.textContent = error.message || 'Uključivanje obaveštenja nije uspelo.';
    }
  });
})();
