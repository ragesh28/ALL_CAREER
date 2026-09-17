/**
 * Claude in Chrome — Workflow Recorder Script
 * Live step recording, element picking, and AI node insertion.
 */

const STORAGE_KEY_WORKFLOWS = 'browserWorkflows';

const INSTRUCTIONS = {
  click: 'Click any element on the website tab. Buttons, links, dropdowns and uploads are auto-detected.',
  fill: 'Select the typing area or enter text below to fill into the element on the website.',
  dropdown: 'Select the dropdown on the website, then select your desired option.',
  checkbox: 'Select the checkbox or its label on the website.',
  multiple_choice: 'Select the radio button or choice on the website.',
  file_upload: 'Upload resume step. Silently attaches candidate resume from Settings.',
  ai_step: 'AI will read the question or region on the page and autonomously answer from candidate profile.',
  loop: 'Select a repeated item on the website (e.g. first job card) to loop through.',
  loop_end: 'Select the element or success message that completes a single loop item.',
  full_end: 'Select the element that confirms the entire workflow is finished.',
};

const ACTION_COLORS = {
  open_url: '#22c55e',
  click: '#38bdf8',
  fill: '#a855f7',
  dropdown: '#eab308',
  checkbox: '#ec4899',
  multiple_choice: '#06b6d4',
  file_upload: '#f97316',
  ai_step: '#14b8a6',
  ai_fallback: '#14b8a6',
  loop: '#eab308',
  stop: '#ef4444',
};

const ACTION_BADGES = {
  open_url: 'URL',
  click: 'CLK',
  fill: 'TYP',
  dropdown: 'DRP',
  checkbox: 'CHK',
  multiple_choice: 'RAD',
  file_upload: 'RES',
  ai_step: 'AI',
  ai_fallback: 'AI',
  loop: 'LOOP',
  stop: 'STOP',
};

let targetTabId = null;
let currentWorkflowId = null;
let currentWorkflow = null;
let workflows = [];

document.addEventListener('DOMContentLoaded', async () => {
  const params = new URLSearchParams(window.location.search);
  const tabIdParam = parseInt(params.get('tabId'), 10);
  currentWorkflowId = params.get('wf');

  if (tabIdParam) targetTabId = tabIdParam;

  await loadWorkflowData();
  await updateTargetTabHeader();
  setupUIEvents();
  renderStepsList();
});

async function loadWorkflowData() {
  const data = await chrome.storage.local.get([STORAGE_KEY_WORKFLOWS]);
  workflows = Array.isArray(data[STORAGE_KEY_WORKFLOWS]) ? data[STORAGE_KEY_WORKFLOWS] : [];

  if (currentWorkflowId) {
    currentWorkflow = workflows.find(w => w.id === currentWorkflowId);
  }

  if (!currentWorkflow && workflows.length > 0) {
    currentWorkflow = workflows[workflows.length - 1];
    currentWorkflowId = currentWorkflow.id;
  }

  if (!currentWorkflow) {
    currentWorkflow = {
      id: 'wf_' + Date.now(),
      name: 'Recorded workflow',
      startUrl: 'https://www.naukri.com/',
      steps: [
        { id: 's1', type: 'open_url', name: 'Open Page', value: 'https://www.naukri.com/', waitMs: 400, color: '#22c55e', badge: 'URL', target: 'https://www.naukri.com/', disabled: false, stopAfter: false, finalSubmit: false }
      ],
    };
    workflows.push(currentWorkflow);
    await saveWorkflows();
  }

  document.getElementById('wf-name-label').textContent = currentWorkflow.name || 'Recorded workflow';
}

async function saveWorkflows(msg = 'Workflow updated!') {
  const idx = workflows.findIndex(w => w.id === currentWorkflow.id);
  if (idx >= 0) workflows[idx] = currentWorkflow;
  else workflows.push(currentWorkflow);

  await chrome.storage.local.set({ [STORAGE_KEY_WORKFLOWS]: workflows });
  renderStepsList();
  showStatus(msg);
}

async function updateTargetTabHeader() {
  if (targetTabId) {
    try {
      const tab = await chrome.tabs.get(targetTabId);
      if (tab) {
        document.getElementById('tab-title-val').textContent = tab.title || tab.url || 'Active Website Tab';
        document.getElementById('conn-banner').className = 'status-banner';
        document.getElementById('conn-text').textContent = '🟢 Connected to website tab — ready to record';
        return;
      }
    } catch (e) {}
  }

  // Fallback: find active http tab
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const target = tabs.find(t => t.url && /^https?:/i.test(t.url));
    if (target?.id) {
      targetTabId = target.id;
      document.getElementById('tab-title-val').textContent = target.title || target.url;
      document.getElementById('conn-banner').className = 'status-banner';
      document.getElementById('conn-text').textContent = '🟢 Connected to ' + (target.title || 'website');
      return;
    }
  } catch (e) {}

  document.getElementById('tab-title-val').textContent = 'No target tab connected';
  document.getElementById('conn-banner').className = 'status-banner disconnected';
  document.getElementById('conn-text').textContent = '🔴 Target website tab not found';
}

function showStatus(text, color = '#a7f3d0') {
  const el = document.getElementById('status-box');
  if (el) {
    el.textContent = text;
    el.style.color = color;
  }
}

function setupUIEvents() {
  const actionSelect = document.getElementById('action-type-select');
  const aiBox = document.getElementById('ai-options-box');
  const fillBox = document.getElementById('fill-box');
  const promptChk = document.getElementById('ai-prompt-chk');
  const promptInput = document.getElementById('ai-custom-prompt');

  actionSelect?.addEventListener('change', (e) => {
    const act = e.target.value;
    aiBox.style.display = act === 'ai_step' ? 'grid' : 'none';
    fillBox.style.display = act === 'fill' ? 'grid' : 'none';
    showStatus(INSTRUCTIONS[act] || 'Select an action.');
  });

  promptChk?.addEventListener('change', (e) => {
    promptInput.style.display = e.target.checked ? 'block' : 'none';
  });

  // Pick element on page (injects picker overlay into target tab)
  document.getElementById('btn-pick-element')?.addEventListener('click', async () => {
    if (!targetTabId) return alert('No target tab connected.');
    const act = actionSelect.value;
    showStatus(`🔍 Picking element on target tab for [${act}]...`);

    try {
      await chrome.tabs.update(targetTabId, { active: true });
      const [res] = await chrome.scripting.executeScript({
        target: { tabId: targetTabId },
        func: (actionType) => {
          return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(56,189,248,0.08);z-index:2147483640;cursor:crosshair;pointer-events:all;border:4px solid #38bdf8;box-sizing:border-box;';
            const badge = document.createElement('div');
            badge.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);background:#1f2937;color:#fff;padding:8px 16px;border-radius:8px;border:1px solid #38bdf8;font:700 13px sans-serif;z-index:2147483647;box-shadow:0 10px 25px rgba(0,0,0,0.5);';
            badge.textContent = `🎯 Click any element on this page to record [${actionType}]`;
            document.body.appendChild(overlay);
            document.body.appendChild(badge);

            function cleanup() {
              overlay.remove();
              badge.remove();
              document.removeEventListener('click', clickHandler, true);
            }

            function clickHandler(e) {
              e.preventDefault();
              e.stopPropagation();
              cleanup();

              const target = e.target;
              let selector = target.tagName.toLowerCase();
              if (target.id && !target.id.includes('__') && !/\d{4,}/.test(target.id)) selector = '#' + CSS.escape(target.id);
              else if (target.className && typeof target.className === 'string') {
                const c = target.className.split(/\s+/).filter(x => x && !x.includes(':'))[0];
                if (c) selector = `${target.tagName.toLowerCase()}.${CSS.escape(c)}`;
              }

              const label = (target.textContent || target.getAttribute('aria-label') || target.getAttribute('placeholder') || target.tagName).trim().substring(0, 50);

              resolve({
                selector,
                label,
                tagName: target.tagName,
                type: target.type || '',
              });
            }

            document.addEventListener('click', clickHandler, true);
          });
        },
        args: [act],
      });

      if (res?.result) {
        const picked = res.result;
        const stepName = document.getElementById('step-name-input').value.trim() || `${act === 'click' ? 'Click' : 'Interact with'} ${picked.label || picked.selector}`;
        const fillVal = document.getElementById('fill-val-input').value.trim();

        currentWorkflow.steps.push({
          id: 's_' + Date.now(),
          type: act === 'ai_step' ? 'ai_fallback' : act,
          name: stepName,
          value: fillVal || picked.label || '',
          target: picked.selector,
          waitMs: 400,
          color: ACTION_COLORS[act] || '#38bdf8',
          badge: ACTION_BADGES[act] || 'ACT',
          disabled: false,
          stopAfter: false,
          finalSubmit: false,
        });

        document.getElementById('step-name-input').value = '';
        await saveWorkflows(`Recorded: "${stepName}" [${picked.selector}]`);
      }
    } catch (err) {
      showStatus('Pick error: ' + err.message, '#f87171');
    }
  });

  // Manual Add Step
  document.getElementById('btn-add-step-manual')?.addEventListener('click', async () => {
    const act = actionSelect.value;
    const name = document.getElementById('step-name-input').value.trim() || `Step ${currentWorkflow.steps.length + 1}`;
    const fillVal = document.getElementById('fill-val-input').value.trim();
    const isAi = act === 'ai_step';

    currentWorkflow.steps.push({
      id: 's_' + Date.now(),
      type: isAi ? 'ai_fallback' : act,
      name,
      value: fillVal || (isAi ? 'AI screening auto-response' : ''),
      target: isAi ? 'Questionnaire container' : 'Element selector',
      waitMs: isAi ? 800 : 400,
      color: ACTION_COLORS[act] || '#38bdf8',
      badge: ACTION_BADGES[act] || 'ACT',
      disabled: false,
      stopAfter: false,
      finalSubmit: false,
    });

    document.getElementById('step-name-input').value = '';
    await saveWorkflows(`Added step "${name}"!`);
  });

  // Undo step
  document.getElementById('btn-undo-step')?.addEventListener('click', async () => {
    if (currentWorkflow.steps.length <= 1) return showStatus('Workflow must have at least one step.');
    const popped = currentWorkflow.steps.pop();
    await saveWorkflows(`Undid: "${popped.name}"`);
  });

  // Finish & Save
  document.getElementById('btn-finish-wf')?.addEventListener('click', async () => {
    await saveWorkflows('Workflow saved successfully!');
    window.location.href = chrome.runtime.getURL('options.html');
  });

  // Back to Studio
  document.getElementById('btn-back-studio')?.addEventListener('click', () => {
    window.location.href = chrome.runtime.getURL('options.html');
  });

  // Refresh Connection
  document.getElementById('btn-refresh-conn')?.addEventListener('click', async () => {
    await updateTargetTabHeader();
    showStatus('Refreshed connection.');
  });
}

function renderStepsList() {
  const container = document.getElementById('steps-container');
  const countEl = document.getElementById('steps-count');
  const stepNumLabel = document.getElementById('step-num-label');

  if (!container || !currentWorkflow) return;

  const steps = currentWorkflow.steps || [];
  countEl.textContent = steps.length;
  stepNumLabel.textContent = `Step ${steps.length + 1}`;

  container.innerHTML = steps.map((step, idx) => {
    const badgeColor = step.color || ACTION_COLORS[step.type] || '#38bdf8';
    const badgeText = step.badge || ACTION_BADGES[step.type] || 'ACT';
    return `
      <div class="step-item" style="border-left: 3px solid ${badgeColor};">
        <div style="display:flex;align-items:center;min-width:0;flex:1;">
          <span class="step-badge" style="background:${badgeColor};">${badgeText}</span>
          <span class="step-name">${idx + 1}. ${escapeHtml(step.name || 'Step ' + (idx + 1))}</span>
        </div>
        <button class="step-del btn-del-step" data-idx="${idx}" title="Delete Step">✕</button>
      </div>
    `;
  }).join('');

  container.querySelectorAll('.btn-del-step').forEach(btn => {
    btn.addEventListener('click', async () => {
      const idx = parseInt(btn.getAttribute('data-idx'), 10);
      if (currentWorkflow.steps.length <= 1) return alert('Workflow must have at least 1 step.');
      currentWorkflow.steps.splice(idx, 1);
      await saveWorkflows('Step deleted.');
    });
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
