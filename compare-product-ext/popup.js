// ----------------------------------------------------------------
// State — persisted in chrome.storage.local between popup opens
// ----------------------------------------------------------------
const STATE_KEY = 'cart_compare_state';

let state = {
  a: null,  // { title, url, html }
  b: null
};

// ----------------------------------------------------------------
// DOM refs
// ----------------------------------------------------------------
const slotA    = document.getElementById('slotA');
const slotB    = document.getElementById('slotB');
const captureA = document.getElementById('captureA');
const captureB = document.getElementById('captureB');
const removeA  = document.getElementById('removeA');
const removeB  = document.getElementById('removeB');
const titleA   = document.getElementById('titleA');
const titleB   = document.getElementById('titleB');
const urlA     = document.getElementById('urlA');
const urlB     = document.getElementById('urlB');
const labelA   = document.getElementById('labelA');
const labelB   = document.getElementById('labelB');
const iconA    = document.getElementById('iconA');
const iconB    = document.getElementById('iconB');
const saveBtn  = document.getElementById('saveBtn');
const clearAll = document.getElementById('clearAll');
const toast    = document.getElementById('toast');

// ----------------------------------------------------------------
// Restore persisted state on popup open
// ----------------------------------------------------------------
chrome.storage.local.get(STATE_KEY, (data) => {
  if (data[STATE_KEY]) {
    state = data[STATE_KEY];
    render();
  }
});

// ----------------------------------------------------------------
// Render UI from state
// ----------------------------------------------------------------
function render() {
  renderSlot('a', slotA, titleA, urlA, captureA, labelA, iconA);
  renderSlot('b', slotB, titleB, urlB, captureB, labelB, iconB);
  saveBtn.disabled = !(state.a && state.b && queryIndex.value);
}

function renderSlot(key, slotEl, titleEl, urlEl, btnEl, labelEl, iconEl) {
  const data = state[key];
  if (data) {
    slotEl.classList.add('captured');
    titleEl.textContent = data.title || 'Untitled page';
    urlEl.textContent   = data.url;

    labelEl.textContent = 'Re-capture';
    iconEl.innerHTML = `
      <polyline points="23 4 23 10 17 10"/>
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
    `;
  } else {
    slotEl.classList.remove('captured');
    titleEl.textContent = '—';
    urlEl.textContent   = '—';
    labelEl.textContent = 'Capture this tab';
    iconEl.innerHTML = `
      <circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>
    `;
  }
}

// ----------------------------------------------------------------
// Capture — inject a content script to grab the page HTML
// ----------------------------------------------------------------
async function capture(slot) {
  const labelEl = slot === 'a' ? labelA : labelB;
  const iconEl  = slot === 'a' ? iconA  : iconB;

  // Show spinner
  labelEl.textContent = 'Capturing…';
  iconEl.innerHTML = `
    <path class="spin" d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
  `;
  iconEl.querySelector('path').style.animation = 'spin 0.7s linear infinite';

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab || !tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://')) {
      showToast('Navigate to a product page first.', 'error');
      render();
      return;
    }

    // Execute script inside the page to grab its full HTML
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => ({
        html:  document.documentElement.outerHTML,
        title: document.title,
        url:   location.href
      })
    });

    const { html, title, url } = results[0].result;

    state[slot] = { title, url, html };
    await chrome.storage.local.set({ [STATE_KEY]: state });

    render();
    showToast(`Product ${slot.toUpperCase()} captured!`, 'success');

  } catch (err) {
    console.error(err);
    showToast('Could not capture page. Try reloading it.', 'error');
    render();
  }
}

// ----------------------------------------------------------------
// Remove a slot
// ----------------------------------------------------------------
function removeSlot(slot) {
  state[slot] = null;
  chrome.storage.local.set({ [STATE_KEY]: state });
  render();
}

// ----------------------------------------------------------------
// Save both HTML files via chrome.downloads
// ----------------------------------------------------------------
async function saveBoth() {
  if (!state.a || !state.b || !queryIndex.value) return;

  saveBtn.disabled = true;
  saveBtn.innerHTML = `
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path style="animation:spin 0.7s linear infinite" d="M12 2a10 10 0 0 1 10 10"/>
    </svg>
    Saving…
  `;

  try {
    await downloadHTML(state.a.html, 'product_A.html');
    await downloadHTML(state.b.html, 'product_B.html');
    await downloadHTML(queryIndex.value, 'user_query.txt');

    showToast('All files saved ✓', 'success');
  } catch (err) {
    console.error(err);
    showToast('Download failed. Check permissions.', 'error');
  } finally {
    saveBtn.disabled = false;
    saveBtn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" width="15" height="15">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
      Save both pages
    `;
  }
}

// ----------------------------------------------------------------
// Helper — create a Blob and trigger download
// ----------------------------------------------------------------
function downloadHTML(content, filename) {
  return new Promise((resolve, reject) => {
    const blob = new Blob([content], { type: 'text/html' });
    const url  = URL.createObjectURL(blob);

    chrome.downloads.download(
      { url, filename, saveAs: false, conflictAction: 'overwrite' },
      (downloadId) => {
        URL.revokeObjectURL(url);
        if (chrome.runtime.lastError) {
          reject(chrome.runtime.lastError);
        } else {
          resolve(downloadId);
        }
      }
    );
  });
}

// ----------------------------------------------------------------
// Clear all
// ----------------------------------------------------------------
function clearState() {
  state = { a: null, b: null };
  chrome.storage.local.remove(STATE_KEY);
  render();
}

// ----------------------------------------------------------------
// Toast
// ----------------------------------------------------------------
let toastTimer;
function showToast(msg, type = '') {
  clearTimeout(toastTimer);
  toast.textContent = msg;
  toast.className = 'toast' + (type ? ` ${type}` : '');
  // force reflow so transition fires
  void toast.offsetWidth;
  toast.classList.add('show');
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
}

// ----------------------------------------------------------------
// Event listeners
// ----------------------------------------------------------------
captureA.addEventListener('click', () => capture('a'));
captureB.addEventListener('click', () => capture('b'));
removeA.addEventListener('click',  () => removeSlot('a'));
removeB.addEventListener('click',  () => removeSlot('b'));
saveBtn.addEventListener('click',  saveBoth);
clearAll.addEventListener('click', clearState);
