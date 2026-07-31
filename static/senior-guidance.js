(() => {
  const greeting = document.querySelector('#voice-greeting');
  if (!greeting) return;

  const listenButtons = [...document.querySelectorAll('#voice-listen, #voice-listen-mobile')];
  const title = document.querySelector('#voice-greeting-title');
  const text = document.querySelector('#voice-greeting-text');
  const kicker = document.querySelector('#voice-greeting-kicker');
  const periodField = document.querySelector('#voice-checkin-period');
  const scheduleButtons = [...document.querySelectorAll('#voice-reminder-toggle, #voice-reminder-toggle-mobile')];
  const scheduleStatuses = [...document.querySelectorAll('#voice-reminder-status, #voice-reminder-status-mobile')];
  const userName = greeting.dataset.name || '';
  let speaking = false;
  let activeAudio;
  const setListenText = value => listenButtons.forEach(button => { button.textContent = value; });
  const setScheduleText = value => scheduleButtons.forEach(button => { button.textContent = value; });
  const setScheduleDisabled = value => scheduleButtons.forEach(button => { button.disabled = value; });
  const setScheduleStatus = value => scheduleStatuses.forEach(status => { status.textContent = value; });

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
    setListenText('🔊 Čuj Sophie');
  };
  const speak = async () => {
    if (speaking) {
      activeAudio?.pause();
      speechSynthesis.cancel();
      finishSpeech();
      return;
    }
    setListenText('Pripremamo Sophie glas…');
    const narration = `${prompt.title} ${prompt.message}`;
    try {
      const response = await fetch('/sophie-govor/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify({ text: narration }) });
      if (response.ok && response.headers.get('content-type')?.includes('audio/')) {
        activeAudio = new Audio(URL.createObjectURL(await response.blob()));
        speaking = true;
        setListenText('■ Zaustavi Sophie');
        activeAudio.onended = activeAudio.onerror = () => { URL.revokeObjectURL(activeAudio.src); finishSpeech(); };
        await activeAudio.play();
        return;
      }
    } catch (_) { /* Sophie instalirana na uređaju je bezbedna rezerva. */ }
    if (!('speechSynthesis' in window)) {
      setListenText('Sophie nije dostupna na ovom uređaju.');
      return;
    }
    const voice = await waitForSophie();
    if (!voice) {
      setListenText('Sophie srpski glas nije dostupan na ovom uređaju.');
      return;
    }
    const utterance = new SpeechSynthesisUtterance(narration);
    utterance.lang = 'sr-RS'; utterance.voice = voice; utterance.rate = .82; utterance.pitch = 1;
    utterance.onstart = () => { speaking = true; setListenText('■ Zaustavi Sophie'); };
    utterance.onend = utterance.onerror = finishSpeech;
    speechSynthesis.cancel(); speechSynthesis.speak(utterance);
  };
  listenButtons.forEach(button => button.addEventListener('click', speak));
  greeting.querySelector('form').addEventListener('submit', () => localStorage.setItem(todayKey, 'done'));

  const plugin = window.Capacitor?.Plugins?.LocalNotifications;
  const schedules = [
    { id: 301, hour: 9, minute: 0, title: 'Dobro jutro iz Briga+', body: 'Kako ste jutros? Otvorite aplikaciju i javite porodici da ste dobro.' },
    { id: 302, hour: 15, minute: 0, title: 'Briga+ je tu', body: 'Kako ste ovog popodneva? Jednim dodirom javite porodici da ste dobro.' },
    { id: 303, hour: 20, minute: 0, title: 'Dobro veče iz Briga+', body: 'Kako ste večeras? Otvorite Briga+ za kratku dnevnu potvrdu.' },
  ];
  const showScheduleState = enabled => {
    setScheduleStatus(enabled ? 'Glasovni podsetnici su uključeni u 09:00, 15:00 i 20:00.' : 'Podsetnik u aplikaciji je spreman.');
    setScheduleText(enabled ? 'Podsetnici su uključeni' : 'Uključi jutro, popodne i veče');
    setScheduleDisabled(enabled);
  };
  showScheduleState(localStorage.getItem('briga-voice-reminders') === '1');
  const enableSchedule = async () => {
    if (!plugin) {
      setScheduleStatus('Ova opcija radi u Briga+ Android ili iPhone aplikaciji. U pregledniku vas čeka poruka čim otvorite „Moj dan”.');
      return;
    }
    try {
      setScheduleDisabled(true);
      setScheduleText('Tražimo dozvolu…');
      let permission = await plugin.checkPermissions();
      if (permission.display !== 'granted') permission = await plugin.requestPermissions();
      if (permission.display !== 'granted') throw new Error('Dozvola za obaveštenja nije data.');
      await plugin.schedule({ notifications: schedules.map(item => ({ ...item, schedule: { on: { hour: item.hour, minute: item.minute }, repeats: true, allowWhileIdle: true }, extra: { brigaGreeting: true, period: item.id } })) });
      localStorage.setItem('briga-voice-reminders', '1');
      showScheduleState(true);
    } catch (error) {
      setScheduleStatus(error.message || 'Podsetnike nismo uspeli da uključimo. Pokušajte ponovo.');
      setScheduleDisabled(false);
      setScheduleText('Pokušaj ponovo');
    }
  };
  scheduleButtons.forEach(button => button.addEventListener('click', enableSchedule));
  plugin?.addListener?.('localNotificationActionPerformed', () => {
    greeting.scrollIntoView({ behavior: 'smooth', block: 'center' });
    window.setTimeout(speak, 300);
  });
})();
