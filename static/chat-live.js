(() => {
  const form = document.querySelector('[data-live-chat-form]');
  const list = document.querySelector('[data-chat-messages]');
  const status = document.querySelector('[data-chat-status]');
  const chatDialog = document.querySelector('#chat');
  if (!form || !list || !chatDialog) return;

  const input = form.querySelector('[name="body"]');
  const button = form.querySelector('button[type="submit"]');
  const scroll = chatDialog.querySelector('.chat-scroll');
  const endpoint = '/chat/poruke/';
  let sending = false;
  let polling = false;

  const scrollToLatest = () => requestAnimationFrame(() => {
    if (scroll) scroll.scrollTop = scroll.scrollHeight;
  });

  const lastMessageId = () => Math.max(0, ...[...list.querySelectorAll('[data-message-id]')]
    .map(item => Number(item.dataset.messageId) || 0));

  const completePending = message => {
    const pending = [...list.querySelectorAll('.message.sending')]
      .find(item => item.querySelector('p')?.textContent === message.body);
    if (!pending) return false;
    pending.dataset.messageId = String(message.id);
    pending.querySelector('b').textContent = message.sender;
    pending.querySelector('time').textContent = message.created_at;
    pending.classList.remove('sending');
    return true;
  };

  const appendMessage = (message, { pending = false } = {}) => {
    if (!pending && list.querySelector(`[data-message-id="${message.id}"]`)) return;
    if (!pending && message.mine && completePending(message)) return;
    list.querySelector('.empty')?.remove();
    const article = document.createElement('article');
    article.className = `message${message.mine ? ' mine' : ''}${pending ? ' sending' : ''}`;
    if (!pending) article.dataset.messageId = String(message.id);
    const sender = document.createElement('b');
    const body = document.createElement('p');
    const time = document.createElement('time');
    sender.textContent = message.sender;
    body.textContent = message.body;
    time.textContent = pending ? 'Šaljemo…' : message.created_at;
    article.append(sender, body, time);
    list.append(article);
    scrollToLatest();
    return article;
  };

  const poll = async () => {
    if (polling || document.hidden || !chatDialog.open) return;
    polling = true;
    try {
      const response = await fetch(`${endpoint}?since=${lastMessageId()}`, {
        headers: { Accept: 'application/json' }, cache: 'no-store',
      });
      if (!response.ok) return;
      const payload = await response.json();
      payload.messages?.forEach(message => appendMessage(message));
    } catch (_) {
      // Sledeći kratak ciklus ponovo pokušava; chat ostaje potpuno upotrebljiv.
    } finally {
      polling = false;
    }
  };

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const body = input.value.trim();
    if (!body || sending) return;
    sending = true;
    input.value = '';
    button.disabled = true;
    status.textContent = 'Šaljemo poruku…';
    const optimistic = appendMessage({ body, sender: 'Vi', mine: true }, { pending: true });
    const data = new FormData(form);
    data.set('body', body);
    try {
      const response = await fetch(endpoint, {
        method: 'POST', body: data, headers: { Accept: 'application/json' },
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'Poruka nije poslata.');
      optimistic.dataset.messageId = String(payload.message.id);
      optimistic.querySelector('b').textContent = payload.message.sender;
      optimistic.querySelector('time').textContent = payload.message.created_at;
      optimistic.classList.remove('sending');
      status.textContent = 'Poslato ✓';
      window.setTimeout(() => { if (status.textContent === 'Poslato ✓') status.textContent = ''; }, 1600);
    } catch (error) {
      optimistic.remove();
      input.value = body;
      status.textContent = error.message || 'Veza je prekinuta. Pokušajte ponovo.';
      input.focus();
    } finally {
      sending = false;
      button.disabled = false;
    }
  });

  chatDialog.addEventListener('toggle', () => {
    if (chatDialog.open) { scrollToLatest(); poll(); }
  });
  window.setInterval(poll, 2500);
  window.addEventListener('focus', poll);
  scrollToLatest();
})();
