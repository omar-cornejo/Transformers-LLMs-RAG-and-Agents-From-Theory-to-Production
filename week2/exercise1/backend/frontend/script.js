let conversationId = null;
console.debug('frontend script.js loaded', { href: typeof location !== 'undefined' ? location.href : null });
let isStreaming = false;
let attachedImage = null;
let attachedImagePreviewUrl = null;
let attachedImageLoadPromise = null;
let attachedImageToken = 0;

const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const modeSelect = document.getElementById('modeSelect');
const toggleContextBtn = document.getElementById('toggleContextBtn');
const contextPanel = document.getElementById('context-panel');
const newChatBtn = document.getElementById('newChatBtn');
const imageInput = document.getElementById('image-input');
const imagePreview = document.getElementById('image-preview');
const previewImg = document.getElementById('preview-img');
const removeImageBtn = document.getElementById('remove-image-btn');
const imageUploadLabel = document.getElementById('image-upload-label');

sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

toggleContextBtn.addEventListener('click', () => {
  contextPanel.classList.toggle('hidden');
});

newChatBtn.addEventListener('click', () => {
  conversationId = null;
  chatMessages.innerHTML = '';
  updateContextView(null, []);
  document.getElementById('prompt-tokens').textContent = '0';
  document.getElementById('completion-tokens').textContent = '0';
  document.getElementById('total-tokens').textContent = '0';
  document.getElementById('messages-json').textContent = '';
  document.getElementById('conversation-id-display').textContent = '-';
  clearAttachedImage();
});

modeSelect.addEventListener('change', () => {
  const isVision = modeSelect.value === 'vision';
  imageUploadLabel.classList.toggle('hidden', !isVision);
  if (!isVision) {
    clearAttachedImage();
  }
});

imageInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  clearAttachedImage();
  console.debug('imageInput.change', { fileName: file?.name, currentToken: attachedImageToken });
  
  if (!file) return;

  attachedImage = file;
  const selectionToken = ++attachedImageToken;
  attachedImageLoadPromise = new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (ev) => {
      if (selectionToken !== attachedImageToken) {
        resolve();
        return;
      }

      attachedImagePreviewUrl = ev.target.result;
      previewImg.src = attachedImagePreviewUrl;
      imagePreview.classList.remove('hidden');
      console.debug('image loaded into preview', { selectionToken, attachedImageToken, previewUrlLength: attachedImagePreviewUrl?.length });
      resolve();
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
});

removeImageBtn.addEventListener('click', () => {
  clearAttachedImage();
});

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text && !attachedImage) return;
  if (isStreaming) return;

  if (attachedImageLoadPromise) {
    console.debug('sendMessage awaiting image load', { attachedImageToken, attachedImagePreviewUrl });
    await attachedImageLoadPromise;
    console.debug('sendMessage resumed after image load', { attachedImageToken, attachedImagePreviewUrl });
  }

  const mode = modeSelect.value;

  if (!conversationId) {
    conversationId = crypto.randomUUID();
  }

  const imageUrl = attachedImagePreviewUrl;
  const displayText = text;
  console.debug('addMessage (user) about to be called', { displayTextLength: displayText?.length, imageUrl });
  addMessage(displayText, 'user', imageUrl);
  messageInput.value = '';

  const imageFile = attachedImage;
  clearAttachedImage();
  console.debug('after clearAttachedImage in sendMessage', { attachedImage, attachedImagePreviewUrl, imageInputValue: imageInput.value });

  imageInput.disabled = true;
  sendBtn.disabled = true;

  if (mode === 'baseline') {
    await sendBaseline(text);
  } else if (mode === 'stream') {
    await sendStream(text);
  } else {
    await sendVision(text, imageFile);
  }

  imageInput.disabled = false;
  sendBtn.disabled = false;
  messageInput.focus();
}

function clearAttachedImage() {
  attachedImageToken += 1;
  attachedImageLoadPromise = null;
  attachedImagePreviewUrl = null;
  attachedImage = null;
  imagePreview.classList.add('hidden');
  imageInput.value = '';
  previewImg.src = '';
}

async function sendBaseline(text) {
  const res = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id: conversationId, message: text }),
  });

  if (!res.ok) {
    addMessage('Error: ' + (await res.text()), 'assistant');
    return;
  }

  const data = await res.json();
  addMessage(data.reply, 'assistant');
  updateContextView(data.conversation_id, data.messages_sent, data.token_usage);
}

async function sendStream(text) {
  isStreaming = true;

  const msgDiv = document.createElement('div');
  msgDiv.className = 'message assistant';
  chatMessages.appendChild(msgDiv);

  const res = await fetch('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id: conversationId, message: text }),
  });

  if (!res.ok) {
    msgDiv.textContent = 'Error: ' + (await res.text());
    isStreaming = false;
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let fullReply = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'token') {
            fullReply += data.content;
            msgDiv.innerHTML = marked.parse(fullReply);
            chatMessages.scrollTop = chatMessages.scrollHeight;
          } else if (data.type === 'done') {
            conversationId = data.conversation_id;
            updateContextView(data.conversation_id, data.messages_sent, data.token_usage);
          }
        } catch (e) {
          console.error('SSE parse error', e);
        }
      }
    }
  }

  isStreaming = false;
}

async function sendVision(text, imageFile) {
  const formData = new FormData();
  formData.append('conversation_id', conversationId || '');
  formData.append('message', text);
  if (imageFile) {
    formData.append('image', imageFile);
  }

  const res = await fetch('/chat/vision', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    addMessage('Error: ' + (await res.text()), 'assistant');
    return;
  }

  const data = await res.json();
  addMessage(data.reply, 'assistant');
  updateContextView(data.conversation_id, data.messages_sent, data.token_usage);
}

function addMessage(content, role, imageUrl) {
  console.log('addMessage called', { role, imageUrl, hasContent: Boolean(content) });
  const div = document.createElement('div');
  div.className = `message ${role}`;

  if (role === 'assistant') {
    div.innerHTML = marked.parse(content);
  } else {
    if (imageUrl) {
      const img = document.createElement('img');
      img.src = imageUrl;
      img.alt = 'sent-image';
      img.className = 'message-image';
      div.appendChild(img);
    }
    if (content) {
      const span = document.createElement('span');
      span.textContent = content;
      div.appendChild(span);
    }
  }

  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateContextView(convId, messages, tokenUsage) {
  if (convId) {
    document.getElementById('conversation-id-display').textContent = convId;
  }
  if (messages) {
    document.getElementById('messages-json').textContent = JSON.stringify(messages, null, 2);
  }
  if (tokenUsage) {
    document.getElementById('prompt-tokens').textContent = tokenUsage.prompt_tokens ?? 0;
    document.getElementById('completion-tokens').textContent = tokenUsage.completion_tokens ?? 0;
    document.getElementById('total-tokens').textContent = tokenUsage.total_tokens ?? 0;
  }
}

// Initialize UI based on current mode selection (fixes vision button missing after reload)
function initUIFromMode() {
  if (!modeSelect) return;
  const isVision = modeSelect.value === 'vision';
  imageUploadLabel.classList.toggle('hidden', !isVision);
  if (!isVision) {
    clearAttachedImage();
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initUIFromMode);
} else {
  initUIFromMode();
}
