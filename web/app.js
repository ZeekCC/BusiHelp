(() => {
  'use strict';

  const messagesEl = document.getElementById('messages');
  const form = document.getElementById('composer');
  const input = document.getElementById('input');
  const sendBtn = document.getElementById('send');
  const newChatBtn = document.getElementById('new-chat');

  const GREETING = '你好，我是星选商城的客服小惠～ 下单、支付、物流、退换货、发票问题都可以问我。';
  const CAT_SVG = document.querySelector('.chat-header .avatar').innerHTML;

  let sessionId = null;
  let streaming = false;
  let controller = null;

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function createMessage(role, text = '') {
    const article = document.createElement('article');
    article.className = `msg ${role}`;

    if (role === 'assistant') {
      const avatar = document.createElement('div');
      avatar.className = 'avatar avatar-sm';
      avatar.setAttribute('aria-hidden', 'true');
      avatar.innerHTML = CAT_SVG;
      article.appendChild(avatar);
    }

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    const textEl = document.createElement('span');
    textEl.className = 'text';
    textEl.textContent = text;

    const caret = document.createElement('span');
    caret.className = 'caret';
    caret.style.display = 'none';

    bubble.append(textEl, caret);
    article.appendChild(bubble);
    messagesEl.appendChild(article);
    scrollToBottom();

    return { article, bubble, textEl, caret };
  }

  function appendMessage(role, text) {
    const node = createMessage(role, text);
    node.caret.remove();
    return node;
  }

  function endStream() {
    streaming = false;
    sendBtn.disabled = false;
    input.focus();
  }

  function attachTypewriter(node, dots) {
    let queue = '';
    let timer = null;
    let ended = false;
    let finished = false;

    function finish() {
      if (finished) return;
      finished = true;
      if (dots) {
        dots.remove();
        dots = null;
      }
      node.caret.remove();
      endStream();
    }

    function pump() {
      timer = null;
      if (!queue) {
        if (ended) finish();
        return;
      }
      const char = String.fromCodePoint(queue.codePointAt(0));
      queue = queue.slice(char.length);
      node.textEl.textContent += char;
      scrollToBottom();
      timer = setTimeout(pump, 14);
    }

    return {
      push(chunk) {
        if (finished || !chunk) return;
        if (dots) {
          dots.remove();
          dots = null;
        }
        node.caret.style.display = '';
        queue += chunk;
        if (timer === null) timer = setTimeout(pump, 0);
      },
      complete() {
        ended = true;
        if (!queue && timer === null) finish();
      },
      fail(message) {
        if (finished) return;
        finished = true;
        ended = true;
        queue = '';
        if (timer !== null) clearTimeout(timer);
        timer = null;
        if (dots) dots.remove();
        node.caret.remove();
        node.textEl.textContent = message;
        node.bubble.classList.add('error');
        endStream();
      },
    };
  }

  async function streamChat(message, typewriter) {
    controller = new AbortController();
    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
      signal: controller.signal,
    });

    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let failed = false;

    function dispatch(raw) {
      let eventName = 'message';
      const dataLines = [];
      for (const line of raw.split(/\r?\n/)) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim();
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
      }
      if (!dataLines.length) return;

      let payload;
      try {
        payload = JSON.parse(dataLines.join('\n'));
      } catch {
        payload = { content: dataLines.join('\n') };
      }

      if (eventName === 'meta') {
        sessionId = payload.session_id || sessionId;
      } else if (eventName === 'token') {
        typewriter.push(payload.content || '');
      } else if (eventName === 'done') {
        typewriter.complete();
      } else if (eventName === 'error') {
        failed = true;
        typewriter.fail(payload.message || '生成失败，请稍后重试');
      }
    }

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let boundary;
        while ((boundary = buffer.indexOf('\n\n')) !== -1) {
          dispatch(buffer.slice(0, boundary));
          buffer = buffer.slice(boundary + 2);
        }
      }
      buffer += decoder.decode();
      if (buffer.trim()) dispatch(buffer);
    } finally {
      reader.releaseLock();
    }

    if (!failed) typewriter.complete();
  }

  async function sendMessage(message) {
    streaming = true;
    sendBtn.disabled = true;
    appendMessage('user', message);

    const node = createMessage('assistant');
    const dots = document.createElement('span');
    dots.className = 'dots';
    dots.innerHTML = '<i></i><i></i><i></i>';
    node.bubble.appendChild(dots);

    const typewriter = attachTypewriter(node, dots);

    try {
      await streamChat(message, typewriter);
    } catch (error) {
      if (error && error.name === 'AbortError') {
        endStream();
        return;
      }
      typewriter.fail('网络异常，请稍后重试');
    } finally {
      controller = null;
    }
  }

  function resizeInput() {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message || streaming) return;
    input.value = '';
    resizeInput();
    sendMessage(message);
  });

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  input.addEventListener('input', resizeInput);

  newChatBtn.addEventListener('click', () => {
    if (controller) {
      controller.abort();
      controller = null;
    }
    streaming = false;
    sendBtn.disabled = false;
    sessionId = null;
    messagesEl.replaceChildren();
    appendMessage('assistant', GREETING);
    input.value = '';
    resizeInput();
    input.focus();
  });

  appendMessage('assistant', GREETING);
  input.focus();
})();
