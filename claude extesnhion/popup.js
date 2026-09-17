/**
 * AI Auto Fill V4 — Main Extension Popup Script
 */

const STORAGE_KEYS = {
  USER_PROFILE: 'userProfile',
  CUSTOM_ANSWERS: 'customAnswers',
  RESUMES: 'resumes',
  DEFAULT_RESUME: 'defaultResume',
};

document.addEventListener('DOMContentLoaded', async () => {
  const isTabMode = new URLSearchParams(window.location.search).get('mode') === 'tab' || window.innerWidth > 500;
  if (isTabMode) {
    document.body.classList.add('tab-mode');
  }

  const profileNameEl = document.getElementById('profileName');
  const profileMetaEl = document.getElementById('profileMeta');
  const btnOpenAsTab = document.getElementById('btnOpenAsTab');
  const btnSettingsGear = document.getElementById('btnSettingsGear');
  const targetUrlInput = document.getElementById('targetUrl');
  const btnGoUrl = document.getElementById('btnGoUrl');
  const btnFillForm = document.getElementById('btnFillForm');
  const btnFillText = document.getElementById('btnFillText');
  const btnWorkflows = document.getElementById('btnWorkflows');
  const btnBatchUrls = document.getElementById('btnBatchUrls');
  const btnAnswers = document.getElementById('btnAnswers');
  const btnHistory = document.getElementById('btnHistory');
  const btnSettings = document.getElementById('btnSettings');
  const btnAiChat = document.getElementById('btnAiChat') || document.getElementById('btnFocusSplit');
  const statusBanner = document.getElementById('statusBanner');

  // If in Tab Mode, customize open button
  if (isTabMode && btnOpenAsTab) {
    btnOpenAsTab.textContent = '🗗 Close Tab';
    btnOpenAsTab.style.background = 'var(--btn-dock-bg)';
    btnOpenAsTab.style.color = 'var(--btn-dock-text)';
    btnOpenAsTab.style.borderColor = 'var(--btn-dock-border)';
  }

  // 1. Load Profile & Custom Answers
  try {
    const data = await chrome.storage.local.get([
      STORAGE_KEYS.USER_PROFILE,
      STORAGE_KEYS.CUSTOM_ANSWERS,
    ]);

    const profile = data[STORAGE_KEYS.USER_PROFILE] || {};
    const answers = data[STORAGE_KEYS.CUSTOM_ANSWERS] || [];

    const name = profile.fullName || profile.name || '';
    if (name) {
      profileNameEl.textContent = `👤 ${name}`;
    } else {
      profileNameEl.textContent = '👤 Not set';
    }

    const learnedCount = Array.isArray(answers) ? answers.length : 0;
    profileMetaEl.textContent = `📚 ${learnedCount} Learned Fields`;
  } catch (err) {
    profileNameEl.textContent = '👤 Not set';
    profileMetaEl.textContent = '📚 0 Learned Fields';
  }

  // 2. Open As Tab / Dock Action
  btnOpenAsTab?.addEventListener('click', () => {
    if (isTabMode) {
      window.close();
    } else {
      chrome.tabs.create({ url: chrome.runtime.getURL('popup.html?mode=tab') });
      window.close();
    }
  });

  // 3. Navigation Actions (Open Hub / Settings Pages)
  function openStudioTab(hash = '') {
    const url = chrome.runtime.getURL(`options.html${hash ? '#' + hash : ''}`);
    chrome.tabs.create({ url });
  }

  btnSettingsGear?.addEventListener('click', () => openStudioTab('settings'));
  btnSettings?.addEventListener('click', () => openStudioTab('settings'));
  btnWorkflows?.addEventListener('click', () => openStudioTab('workflows'));
  btnBatchUrls?.addEventListener('click', () => openStudioTab('workflows'));
  btnAnswers?.addEventListener('click', () => openStudioTab('customanswers'));
  btnHistory?.addEventListener('click', () => openStudioTab('prompts'));

  // 4. Open Claude AI Chat (Side Panel)
  btnAiChat?.addEventListener('click', async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab?.id) {
        if (chrome.sidePanel?.open) {
          try {
            await chrome.sidePanel.setOptions({
              tabId: tab.id,
              path: `sidepanel.html?tabId=${encodeURIComponent(tab.id)}`,
              enabled: true,
            });
            await chrome.sidePanel.open({ tabId: tab.id });
          } catch (e) {
            if (tab.windowId) {
              await chrome.sidePanel.open({ windowId: tab.windowId });
            }
          }
        }
        chrome.runtime.sendMessage({ type: 'open_side_panel', tabId: tab.id }).catch(() => {});
        if (!isTabMode) {
          window.close();
        } else {
          showStatus('Claude AI Chat opened in side panel', 'info');
        }
      } else {
        chrome.tabs.create({ url: chrome.runtime.getURL('sidepanel.html') });
        if (!isTabMode) window.close();
      }
    } catch (err) {
      chrome.tabs.create({ url: chrome.runtime.getURL('sidepanel.html') });
      if (!isTabMode) window.close();
    }
  });

  // 5. Go URL Action
  async function handleGoUrl() {
    let raw = (targetUrlInput?.value || '').trim();
    if (!raw) {
      showStatus('Please paste a job or form URL', 'error');
      return;
    }
    if (!raw.startsWith('http://') && !raw.startsWith('https://')) {
      raw = 'https://' + raw;
    }

    try {
      const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (activeTab?.id && !activeTab.url?.startsWith('chrome://')) {
        await chrome.tabs.update(activeTab.id, { url: raw });
      } else {
        await chrome.tabs.create({ url: raw, active: true });
      }
      showStatus('Navigating...', 'info');
    } catch (err) {
      showStatus('Failed to navigate: ' + err.message, 'error');
    }
  }

  btnGoUrl?.addEventListener('click', handleGoUrl);
  targetUrlInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleGoUrl();
  });

  // 6. Fill This Form Action
  btnFillForm?.addEventListener('click', async () => {
    btnFillForm.disabled = true;
    btnFillText.textContent = 'Filling...';
    showStatus('Scanning and filling form fields...', 'info');

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id) {
        showStatus('No active webpage found.', 'error');
        resetFillButton();
        return;
      }

      if (tab.url?.startsWith('chrome://') || tab.url?.startsWith('edge://') || tab.url?.startsWith('about:')) {
        showStatus('Cannot fill browser internal pages.', 'error');
        resetFillButton();
        return;
      }

      // Fetch latest profile & custom answers
      const storageData = await chrome.storage.local.get([
        STORAGE_KEYS.USER_PROFILE,
        STORAGE_KEYS.CUSTOM_ANSWERS,
      ]);

      const userProfile = storageData[STORAGE_KEYS.USER_PROFILE] || {};
      const customAnswers = storageData[STORAGE_KEYS.CUSTOM_ANSWERS] || [];

      // Execute autofill script in target tab
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: inPageAutoFillScript,
        args: [userProfile, customAnswers],
      });

      const res = results?.[0]?.result;
      if (res?.success) {
        showStatus(`✨ ${res.message}`, 'success');
      } else {
        showStatus(res?.error || 'No matching fields found to fill.', 'error');
      }
    } catch (err) {
      showStatus('Error filling page: ' + (err instanceof Error ? err.message : String(err)), 'error');
    } finally {
      resetFillButton();
    }
  });

  function resetFillButton() {
    btnFillForm.disabled = false;
    btnFillText.textContent = 'Fill This Form';
  }

  function showStatus(msg, type = 'info') {
    if (!statusBanner) return;
    statusBanner.textContent = msg;
    statusBanner.className = `status-banner ${type}`;
    statusBanner.style.display = 'block';

    if (type !== 'error') {
      setTimeout(() => {
        if (statusBanner) statusBanner.style.display = 'none';
      }, 3500);
    }
  }
});

/**
 * In-Page Autofill Execution Function
 * Injected into the active page tab to fill all standard and contenteditable fields.
 */
function inPageAutoFillScript(profile, customAnswers) {
  try {
    let filledCount = 0;

    // Helper to trigger realistic typing and framework change events
    function setInputValue(el, val) {
      if (!el || val === undefined || val === null || val === '') return false;

      el.focus();

      if (el.isContentEditable || el.getAttribute('contenteditable') === 'true') {
        el.textContent = String(val);
        el.innerText = String(val);
        try {
          const range = document.createRange();
          const sel = window.getSelection();
          range.selectNodeContents(el);
          range.collapse(false);
          sel?.removeAllRanges();
          sel?.addRange(range);
        } catch (e) {}
        el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: String(val) }));
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'End' }));
        return true;
      }

      if (el.tagName === 'SELECT') {
        const targetVal = String(val).toLowerCase();
        let matched = false;
        for (let i = 0; i < el.options.length; i++) {
          const opt = el.options[i];
          if (opt.value.toLowerCase().includes(targetVal) || opt.text.toLowerCase().includes(targetVal)) {
            el.selectedIndex = i;
            matched = true;
            break;
          }
        }
        if (!matched && el.options.length > 1) el.selectedIndex = 1;
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
      }

      // Input / Textarea
      const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
      if (setter) {
        setter.call(el, String(val));
      } else {
        el.value = String(val);
      }

      el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: String(val) }));
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      el.dispatchEvent(new Event('blur', { bubbles: true }));
      return true;
    }

    // Candidate Profile Field Dictionary
    const p = profile || {};
    const fullName = p.fullName || p.name || '';
    const nameParts = fullName.trim().split(/\s+/);
    const firstName = nameParts[0] || '';
    const lastName = nameParts.length > 1 ? nameParts.slice(1).join(' ') : '';
    const email = p.email || '';
    const phone = p.phone || p.mobile || '';
    const city = p.city || '';
    const state = p.state || '';
    const country = p.country || 'India';
    const address = p.address || '';
    const pincode = p.pincode || p.zipCode || '';
    const degree = p.degree || '';
    const gradYear = p.graduationYear || '';
    const university = p.university || '';
    const experience = p.experienceYears || '';
    const skills = p.skills || '';
    const linkedin = p.linkedin || '';
    const github = p.github || '';
    const curSalary = p.currentSalary || '';
    const expSalary = p.expectedSalary || '';
    const noticePeriod = p.noticePeriod || '';

    // Collect all fillable elements
    const elements = Array.from(document.querySelectorAll(
      'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"]):not([type="file"]), textarea, select, [contenteditable="true"]'
    ));

    for (const el of elements) {
      if (el.disabled || el.readOnly) continue;

      // Extract descriptive text & attributes
      const id = (el.id || '').toLowerCase();
      const name = (el.name || '').toLowerCase();
      const placeholder = (el.placeholder || el.getAttribute('data-placeholder') || '').toLowerCase();
      const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
      const parentText = (el.closest('label, .form-group, .field, div')?.innerText || '').toLowerCase().substring(0, 150);
      const combined = `${id} ${name} ${placeholder} ${ariaLabel} ${parentText}`;

      let fillVal = '';

      // Check custom answers first
      if (Array.isArray(customAnswers) && customAnswers.length > 0) {
        for (const qa of customAnswers) {
          if (!qa.question || !qa.answer) continue;
          const pattern = qa.question.toLowerCase().trim();
          if (combined.includes(pattern)) {
            fillVal = qa.answer;
            break;
          }
        }
      }

      // Check profile attributes
      if (!fillVal) {
        if (combined.includes('first name') || combined.includes('firstname') || combined.includes('fname')) {
          fillVal = firstName || fullName;
        } else if (combined.includes('last name') || combined.includes('lastname') || combined.includes('lname') || combined.includes('surname')) {
          fillVal = lastName;
        } else if (combined.includes('full name') || combined.includes('fullname') || combined.includes('candidate name') || combined.includes('name')) {
          fillVal = fullName;
        } else if (combined.includes('email') || el.type === 'email') {
          fillVal = email;
        } else if (combined.includes('phone') || combined.includes('mobile') || combined.includes('contact') || el.type === 'tel') {
          fillVal = phone;
        } else if (combined.includes('linkedin')) {
          fillVal = linkedin;
        } else if (combined.includes('github') || combined.includes('portfolio') || combined.includes('website')) {
          fillVal = github;
        } else if (combined.includes('current salary') || combined.includes('current ctc') || combined.includes('cur ctc')) {
          fillVal = curSalary || '0';
        } else if (combined.includes('expected salary') || combined.includes('expected ctc') || combined.includes('exp ctc')) {
          fillVal = expSalary || '0';
        } else if (combined.includes('notice') || combined.includes('notice period')) {
          fillVal = noticePeriod || 'Immediate';
        } else if (combined.includes('city') || combined.includes('location')) {
          fillVal = city;
        } else if (combined.includes('state')) {
          fillVal = state;
        } else if (combined.includes('country')) {
          fillVal = country;
        } else if (combined.includes('pin') || combined.includes('zip') || combined.includes('postal')) {
          fillVal = pincode;
        } else if (combined.includes('address')) {
          fillVal = address;
        } else if (combined.includes('degree') || combined.includes('qualification') || combined.includes('education')) {
          fillVal = degree;
        } else if (combined.includes('year of pass') || combined.includes('graduation year') || combined.includes('passout')) {
          fillVal = gradYear;
        } else if (combined.includes('college') || combined.includes('university') || combined.includes('institute')) {
          fillVal = university;
        } else if (combined.includes('experience') || combined.includes('years of exp') || combined.includes('total exp')) {
          fillVal = experience;
        } else if (combined.includes('skill') || combined.includes('key skills')) {
          fillVal = skills;
        }
      }

      if (fillVal) {
        const ok = setInputValue(el, fillVal);
        if (ok) filledCount++;
      }
    }

    return {
      success: true,
      message: filledCount > 0 ? `Filled ${filledCount} form field(s) with your profile!` : 'Page scanned, no empty matching fields found.',
      filledCount,
    };
  } catch (e) {
    return { success: false, error: e.message };
  }
}
