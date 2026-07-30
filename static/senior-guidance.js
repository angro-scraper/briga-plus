(() => {
  const greeting = document.querySelector('#voice-greeting');
  if (!greeting) return;

  const listen = document.querySelector('#voice-listen');
  const title = document.querySelector('#voice-greeting-title');
  const text = document.querySelector('#voice-greeting-text');
  const kicker = document.querySelector('#voice-greeting-kicker');
  const periodField = document.querySelector('#voice-checkin-period');
  const scheduleButton = document.querySelector('#voice-reminder-toggle');
  const scheduleStatus = document.querySelector('#voice-reminder-status');
  const userName = greeting.dataset.name || '';
  let speaking = false;
  let activeAudio;

  const currentPeriod = () => {
    const hour = new Date().getHours();
    if (hour < 12) return { key: 'morning', label: 'Jutro', title: `Dobro jutro${userName ? `, ${userName}` : ''}.`, message: 'Kako ste jutros? Pritisnite veliko zeleno dugme i javite porodici da ste dobro.' };
    if (hour < 18) return { key: 'day', label: 'Popodne', title: `Dobar dan${userName ? `, ${userName}` : ''}.`, message: 'Kako ste ovog popodneva? Ako je sve u redu, pritisnite veliko zeleno dugme.' };
    return { key: 'evening', label: 'Veče', title: `Dobro veče${userName ? `, ${userName}` : ''}.`, message: 'Kako ste večeras? Jednim dodirom javite porodici da ste dobro.' };
  };

  const prompt = currentPeriod();
  const todayKey = `briga-greeting-${new Date().toISOString().slice(0, 10)}-${prompt.key}`;
  kicker.textContent = `${prompt.label.toUpperCase()} · NEŽNI DNEVNI PODSETNIK`;
  title.textContent = prompt.title;
  text.textContent = prompt.message;
  periodField.value = prompt.key === 'morning' ? 'morning' : prompt.key === 'evening' ? 'evening' : 'any';
  if (localStorage.getItem(todayKey) === 'done') {
    greeting.classList.add('is-complete');
    text.textContent = 'Hvala što ste se javili. Porodica zna da ste dobro.';
  }

  const csrfToken = () => document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
  const sophieVoice = () => speechSynthesis.getVoices().find(voice => /sophie/i.test(voice.name) && (/^sr(?:-|_)/i.test(voice.lang) || /serbian|srpski/i.test(voice.name)));
  const waitForSophie = () => new Promise(resolve => {
    const immediate = sophieVoice();
    if (immediate) return resolve(immediate);
    const finish = () => { speechSynthesis.removeEventListener('voiceschanged', changed); resolve(sophieVoice()); };
    const changed = () => { if (sophieVoice()) finish(); };
    speechSynthesis.addEventListener('voiceschanged', changed);
    window.setTimeout(finish, 4500);
  });
  const finishSpeech = () => {
    speaking = false;
    activeAudio = null;
    listen.textContent = '🔊 Čuj Sophie';
  };
  const speak = async () => {
    if (speaking) {
      activeAudio?.pause();
      speechSynthesis.cancel();
      finishSpeech();
      return;
    }
    listen.textContent = 'Pripremamo Sophie glas…';
    const narration = `${prompt.title} ${prompt.message}`;
    try {
      const response = await fetch('/sophie-govor/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify({ text: narration }) });
      if (response.ok && response.headers.get('content-type')?.includes('audio/')) {
        activeAudio = new Audio(URL.createObjectURL(await response.blob()));
        speaking = true;
        listen.textContent = '■ Zaustavi Sophie';
        activeAudio.onended = activeAudio.onerror = () => { URL.revokeObjectURL(activeAudio.src); finishSpeech(); };
        await activeAudio.play();
        return;
      }
    } catch (_) { /* Sophie instalirana na uređaju je bezbedna rezerva. */ }
    if (!('speechSynthesis' in window)) {
      listen.textContent = 'Sophie nije dostupna na ovom uređaju.';
      return;
    }
    const voice = await waitForSophie();
    if (!voice) {
      listen.textContent = 'Sophie srpski glas nije dostupan na ovom uređaju.';
      return;
    }
    const utterance = new SpeechSynthesisUtterance(narration);
    utterance.lang = 'sr-RS'; utterance.voice = voice; utterance.rate = .82; utterance.pitch = 1;
    utterance.onstart = () => { speaking = true; listen.textContent = '■ Zaustavi Sophie'; };
    utterance.onend = utterance.onerror = finishSpeech;
    speechSynthesis.cancel(); speechSynthesis.speak(utterance);
  };
  listen.addEventListener('click', speak);
  greeting.querySelector('form').addEventListener('submit', () => localStorage.setItem(todayKey, 'done'));

  const plugin = window.Capacitor?.Plugins?.LocalNotifications;
  const schedules = [
    { id: 301, hour: 9, minute: 0, title: 'Dobro jutro iz Briga+', body: 'Kako ste jutros? Otvorite aplikaciju i javite porodici da ste dobro.' },
    { id: 302, hour: 15, minute: 0, title: 'Briga+ je tu', body: 'Kako ste ovog popodneva? Jednim dodirom javite porodici da ste dobro.' },
    { id: 303, hour: 20, minute: 0, title: 'Dobro veče iz Briga+', body: 'Kako ste večeras? Otvorite Briga+ za kratku dnevnu potvrdu.' },
  ];
  const showScheduleState = enabled => {
    scheduleStatus.textContent = enabled ? 'Glasovni podsetnici su uključeni u 09:00, 15:00 i 20:00.' : 'Podsetnik u aplikaciji je spreman.';
    scheduleButton.textContent = enabled ? 'Podsetnici su uključeni' : 'Uključi jutro, popodne i veče';
    scheduleButton.disabled = enabled;
  };
  showScheduleState(localStorage.getItem('briga-voice-reminders') === '1');
  scheduleButton.addEventListener('click', async () => {
    if (!plugin) {
      scheduleStatus.textContent = 'Ova opcija radi u Briga+ Android ili iPhone aplikaciji. U pregledniku vas čeka poruka čim otvorite „Moj dan”.';
      return;
    }
    try {
      scheduleButton.disabled = true;
      scheduleButton.textContent = 'Tražimo dozvolu…';
      let permission = await plugin.checkPermissions();
      if (permission.display !== 'granted') permission = await plugin.requestPermissions();
      if (permission.display !== 'granted') throw new Error('Dozvola za obaveštenja nije data.');
      await plugin.schedule({ notifications: schedules.map(item => ({ ...item, schedule: { on: { hour: item.hour, minute: item.minute }, repeats: true, allowWhileIdle: true }, extra: { brigaGreeting: true, period: item.id } })) });
      localStorage.setItem('briga-voice-reminders', '1');
      showScheduleState(true);
    } catch (error) {
      scheduleStatus.textContent = error.message || 'Podsetnike nismo uspeli da uključimo. Pokušajte ponovo.';
      scheduleButton.disabled = false;
      scheduleButton.textContent = 'Pokušaj ponovo';
    }
  });
  plugin?.addListener?.('localNotificationActionPerformed', () => {
    greeting.scrollIntoView({ behavior: 'smooth', block: 'center' });
    window.setTimeout(speak, 300);
  });
})();
