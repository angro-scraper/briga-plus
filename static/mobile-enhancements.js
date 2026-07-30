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
            formData.append('audio', new Blob(chunks, { type: recorder.mimeType || 'audio/webm' }), 'glasovna-poruka.webm');
            formData.append('csrfmiddlewaretoken', csrfToken());
            const response = await fetch('/', { method: 'POST', body: formData });
            if (!response.ok) throw new Error();
            window.location.reload();
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

  const speechButton = document.querySelector('#read-health-mobile');
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
    speechButton.addEventListener('click', async () => {
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
    });
  }

  const pushButton = document.querySelector('#push-button-mobile');
  const pushStatus = document.querySelector('#push-status');
  const toUint8Array = value => { const padding = '='.repeat((4 - value.length % 4) % 4); const base64 = (value + padding).replace(/-/g, '+').replace(/_/g, '/'); return Uint8Array.from(atob(base64), character => character.charCodeAt(0)); };
  if (pushButton && pushStatus) pushButton.addEventListener('click', async () => {
    const key = pushButton.dataset.vapidKey || '';
    try {
      pushButton.disabled = true; pushButton.textContent = 'Proveravamo dozvolu…';
      const nativePush = window.Capacitor?.Plugins?.PushNotifications;
      if (nativePush) {
        const permission = await nativePush.requestPermissions();
        if (permission.receive !== 'granted') throw new Error('Dozvola za obaveštenja nije data. Uključite je u podešavanjima telefona.');
        pushStatus.textContent = 'Dozvola je odobrena. Nativna isporuka se aktivira čim Firebase/APNs budu povezani za Briga+.';
        pushButton.textContent = 'Dozvola odobrena';
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
