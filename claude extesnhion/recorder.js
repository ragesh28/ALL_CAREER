/**
 * Claude in Chrome — Dedicated Workflow Step Recorder Sidebar Script
 * Real-time step recording, element picking, AI node selection, and loop control.
 * Matches Autofill V4 workflow creating popup format and syncs directly with content.js.
 */

const STORAGE_KEY_WORKFLOWS = 'browserWorkflows';
const RECORDING_KEY = 'recording_session';

function getNextDefaultWorkflowName(existingWorkflows) {
  const wfs = Array.isArray(existingWorkflows) ? existingWorkflows : [];
  let maxNum = 0;
  for (const wf of wfs) {
    const name = String(wf?.name || '').trim();
    const match = name.match(/^Workflow\s*(\d+)$/i);
    if (match) {
      const num = parseInt(match[1], 10);
      if (!isNaN(num) && num > maxNum) {
        maxNum = num;
      }
    }
  }
  let candidateNum = maxNum + 1;
  while (wfs.some(w => String(w?.name || '').trim().toLowerCase() === `workflow ${candidateNum}`.toLowerCase())) {
    candidateNum++;
  }
  return `Workflow ${candidateNum}`;
}

const INSTRUCTIONS = {
  click: 'Select any element. Dropdowns, checkboxes, choices, and uploads are detected automatically.',
  fill: 'Select the input where the workflow should type.',
  dropdown: 'Select the dropdown, then select the required option.',
  checkbox: 'Select the checkbox or its label.',
  multiple_choice: 'Select the required radio or multiple-choice option.',
  file_upload: 'Select Add File or the file input. Replay uses the workflow resume.',
  ai_step: 'Click the box, modal, or region containing the recruiter questions. AI will automatically answer everything in it.',
  loop: 'Select one repeated item, such as the first job card.',
  loop_end: 'Move over the page and select the success message that ends this loop item.',
  full_end: 'Move over the page and select the success message that ends the full workflow.',
};

const ACTION_COLORS = {
  open_url: '#22c55e',
  click: '#38bdf8',
  fill: '#a855f7',
  select_option: '#eab308',
  dropdown: '#eab308',
  check: '#ec4899',
  checkbox: '#ec4899',
  multiple_choice: '#06b6d4',
  attach_resume: '#f97316',
  file_upload: '#f97316',
  ai_fallback: '#14b8a6',
  ai_step: '#14b8a6',
  loop_start: '#eab308',
  loop: '#eab308',
  loop_end: '#eab308',
  stop: '#ef4444',
};

const ACTION_BADGES = {
  open_url: 'URL',
  click: 'CLK',
  fill: 'TYP',
  select_option: 'SEL',
  dropdown: 'DRP',
  check: 'CHK',
  checkbox: 'CHK',
  multiple_choice: 'RAD',
  attach_resume: 'FILE',
  file_upload: 'FILE',
  ai_fallback: 'AI',
  ai_step: 'AI',
  loop_start: 'LOOP',
  loop: 'LOOP',
  loop_end: 'LEND',
  stop: 'STOP',
};

let targetTabId = null;
let currentWorkflowId = null;
let currentWorkflow = null;
let workflows = [];
let manualLoopDepth = 0;
let isStopWorkingActive = false;

document.addEventListener('DOMContentLoaded', async () => {
  const params = new URLSearchParams(window.location.search);
  const tabIdParam = parseInt(params.get('tabId'), 10);
  currentWorkflowId = params.get('wf');

  if (tabIdParam) targetTabId = tabIdParam;

  await loadWorkflowData();
  await updateTargetTabHeader();
  setupUIEvents();
  setupCrossTabSync();
  renderStepsList();
  populateRecorderResumes();
});

async function populateRecorderResumes() {
  const resumeSelect = document.getElementById('wf-resume-select');
  if (!resumeSelect) return;
  try {
    const resData = await chrome.storage.local.get(['resumes', 'defaultResume', 'uploadedFiles']);
    const list = Array.isArray(resData.resumes) ? resData.resumes : Array.isArray(resData.uploadedFiles) ? resData.uploadedFiles : [];
    const defId = resData.defaultResume || '';
    resumeSelect.innerHTML = '<option value="">Default Resume PDF</option>';
    list.forEach(r => {
      const opt = document.createElement('option');
      opt.value = r.id || r.name;
      opt.dataset.filename = r.name || 'resume.pdf';
      opt.textContent = `${r.name || 'Resume'} ${r.id === defId ? '(Default ⭐)' : ''}`;
      if (r.id === defId) opt.selected = true;
      resumeSelect.appendChild(opt);
    });
  } catch (_) {}
}

async function loadWorkflowData() {
  // Check active recording session in storage first
  try {
    const sessionData = await chrome.storage.session.get(RECORDING_KEY);
    const recSession = sessionData?.[RECORDING_KEY];
    if (recSession?.workflow) {
      currentWorkflow = recSession.workflow;
      currentWorkflowId = currentWorkflow.id;
      if (recSession.tabId) targetTabId = recSession.tabId;
      manualLoopDepth = (recSession.loopStack || []).length;
    }
  } catch (_) {}

  // Fallback to local storage workflows
  const data = await chrome.storage.local.get([STORAGE_KEY_WORKFLOWS]);
  workflows = Array.isArray(data[STORAGE_KEY_WORKFLOWS]) ? data[STORAGE_KEY_WORKFLOWS] : [];

  if (!currentWorkflow && currentWorkflowId) {
    currentWorkflow = workflows.find((w) => w.id === currentWorkflowId);
  }

  if (!currentWorkflow && workflows.length > 0) {
    currentWorkflow = workflows[0];
    currentWorkflowId = currentWorkflow.id;
  }

  if (!currentWorkflow) {
    const defaultName = getNextDefaultWorkflowName(workflows);
    currentWorkflow = {
      id: 'wf_' + Date.now(),
      name: defaultName,
      startUrl: 'https://www.naukri.com/',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      steps: [
        {
          id: 's1',
          type: 'open_url',
          name: 'Open Page',
          value: 'https://www.naukri.com/',
          waitMs: 400,
          color: '#22c55e',
          badge: 'URL',
          target: 'https://www.naukri.com/',
          disabled: false,
          stopAfter: false,
          finalSubmit: false,
        },
      ],
    };
    workflows.unshift(currentWorkflow);
    await saveWorkflows();
  }

  const nameEl = document.getElementById('wf-name-label');
  if (nameEl) nameEl.textContent = currentWorkflow.name || getNextDefaultWorkflowName(workflows);
}

async function saveWorkflows(msg = 'Workflow updated!') {
  if (currentWorkflow) {
    currentWorkflow.updatedAt = Date.now();
    if (!currentWorkflow.name || currentWorkflow.name.trim().toLowerCase() === 'recorded workflow') {
      currentWorkflow.name = getNextDefaultWorkflowName(workflows.filter(w => w.id !== currentWorkflow.id));
    }
    workflows = workflows.filter((w) => w.id !== currentWorkflow.id);
    workflows.unshift(currentWorkflow);
  }

  await chrome.storage.local.set({ [STORAGE_KEY_WORKFLOWS]: workflows });
  renderStepsList();
  showStatus(msg);
}

async function updateTargetTabHeader() {
  if (targetTabId) {
    try {
      const tab = await chrome.tabs.get(targetTabId);
      if (tab) {
        document.getElementById('conn-banner').className = 'status-banner';
        document.getElementById('conn-text').textContent = '🟢 Connected to ' + (tab.title || tab.url || 'target tab');
        return;
      }
    } catch (_) {}
  }

  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const target = tabs.find((t) => t.url && /^https?:/i.test(t.url));
    if (target?.id) {
      targetTabId = target.id;
      document.getElementById('conn-banner').className = 'status-banner';
      document.getElementById('conn-text').textContent = '🟢 Connected to ' + (target.title || 'target tab');
      return;
    }
  } catch (_) {}

  document.getElementById('conn-banner').className = 'status-banner disconnected';
  document.getElementById('conn-text').textContent = '🔴 Target website tab not found';
}

function showStatus(text, error = false) {
  const el = document.getElementById('wf-status');
  if (el) {
    el.textContent = text;
    el.style.color = error ? '#fca5a5' : '#a7f3d0';
    el.style.borderLeftColor = error ? '#ef4444' : '#10b981';
  }
}

function sendToTargetTab(message) {
  if (!targetTabId) return;
  chrome.tabs.sendMessage(targetTabId, message).catch(() => {});
}

function setupUIEvents() {
  const stepNameInput = document.getElementById('wf-step-name');
  const modeSelect = document.getElementById('wf-mode');
  const waitCheckbox = document.getElementById('wf-wait-for-element');
  const aiEditor = document.getElementById('wf-ai-editor');
  const aiElementCountSelect = document.getElementById('wf-ai-element-count');
  const aiFullPageCheckbox = document.getElementById('wf-ai-full-page');
  const aiPromptToggle = document.getElementById('wf-ai-custom-prompt-toggle');
  const aiPromptBox = document.getElementById('wf-ai-prompt-box');
  const aiPromptInput = document.getElementById('wf-ai-prompt-input');
  const fillEditor = document.getElementById('wf-fill-editor');
  const fillValueInput = document.getElementById('wf-fill-value');
  const saveFillBtn = document.getElementById('wf-save-fill');
  const pickBtn = document.getElementById('wf-pick');
  const addStepBtn = document.getElementById('wf-add-step');
  const undoBtn = document.getElementById('wf-undo');
  const inspectBtn = document.getElementById('wf-inspect');
  const endLoopBtn = document.getElementById('wf-end-loop');
  const finishBtn = document.getElementById('wf-finish');
  const backStudioBtn = document.getElementById('btn-back-studio');
  const refreshConnBtn = document.getElementById('btn-refresh-conn');

  // Step name sync
  stepNameInput?.addEventListener('input', (e) => {
    sendToTargetTab({
      action: 'RECORDER_TAB_STEP_NAME_CHANGE',
      name: e.target.value.trim(),
    });
  });

  // Action type change
  modeSelect?.addEventListener('change', (e) => {
    const act = e.target.value;
    if (aiEditor) aiEditor.style.display = act === 'ai_step' ? 'grid' : 'none';
    if (fillEditor) fillEditor.style.display = act === 'fill' ? 'grid' : 'none';
    const loopEditor = document.getElementById('wf-loop-editor');
    if (loopEditor) loopEditor.style.display = act === 'loop' ? 'block' : 'none';
    const resumeEditor = document.getElementById('wf-resume-editor');
    if (resumeEditor) {
      resumeEditor.style.display = act === 'file_upload' ? 'block' : 'none';
      if (act === 'file_upload') populateRecorderResumes();
    }
    showStatus(INSTRUCTIONS[act] || 'Select an action, then click an element on the page.');

    sendToTargetTab({
      action: 'RECORDER_TAB_MODE_CHANGE',
      mode: act,
    });
  });

  // Wait toggle
  waitCheckbox?.addEventListener('change', (e) => {
    const checked = e.target.checked;
    showStatus(checked ? 'Move over the page and select the element that must appear before this action.' : 'Appearance wait removed.');
    sendToTargetTab({
      action: 'RECORDER_TAB_WAIT_TOGGLE',
      checked,
    });
  });

  // AI Options
  aiElementCountSelect?.addEventListener('change', (e) => {
    sendToTargetTab({
      action: 'RECORDER_TAB_AI_ELEMENT_COUNT_CHANGE',
      count: parseInt(e.target.value, 10) || 2,
    });
  });

  aiFullPageCheckbox?.addEventListener('change', (e) => {
    sendToTargetTab({
      action: 'RECORDER_TAB_AI_FULL_PAGE_TOGGLE',
      checked: e.target.checked,
    });
  });

  aiPromptToggle?.addEventListener('change', (e) => {
    if (aiPromptBox) aiPromptBox.style.display = e.target.checked ? 'block' : 'none';
  });

  aiPromptInput?.addEventListener('input', (e) => {
    sendToTargetTab({
      action: 'RECORDER_TAB_AI_PROMPT_CHANGE',
      prompt: e.target.value.trim(),
    });
  });

  // Save Fill Text
  saveFillBtn?.addEventListener('click', () => {
    const val = fillValueInput?.value.trim() || '';
    sendToTargetTab({
      action: 'RECORDER_TAB_SAVE_FILL',
      value: val,
    });
    showStatus(`Saved typing value: ${val}`);
  });

  // Pick Element on Page
  pickBtn?.addEventListener('click', async () => {
    if (!targetTabId) return alert('No target tab connected.');
    const act = modeSelect?.value || 'click';
    showStatus(`🔍 Click an element on the target website to record [${act}]...`);

    if (act === 'file_upload') {
      const resumeSelect = document.getElementById('wf-resume-select');
      const chosenResumeId = resumeSelect?.value || '';
      if (chosenResumeId && currentWorkflow) {
        currentWorkflow.resumeId = chosenResumeId;
        chrome.storage.local.set({ [STORAGE_KEY_WORKFLOWS]: workflows }).catch(() => {});
      }
    }

    try {
      await chrome.tabs.update(targetTabId, { active: true });
      sendToTargetTab({ action: 'ENTER_PICKER_MODE' });
    } catch (err) {
      showStatus('Pick error: ' + err.message, true);
    }
  });

  // Add Step manually
  addStepBtn?.addEventListener('click', async () => {
    const act = modeSelect?.value || 'click';
    const fillVal = fillValueInput?.value.trim() || '';
    const isAi = act === 'ai_step';

    const resumeSelect = document.getElementById('wf-resume-select');
    const chosenResumeId = resumeSelect?.value || '';
    const chosenResumeOption = resumeSelect?.selectedOptions?.[0];
    const chosenFileName = chosenResumeOption?.dataset?.filename || chosenResumeOption?.textContent?.replace('(Default ⭐)', '').trim() || 'resume.pdf';
    const name = stepNameInput?.value.trim() || (act === 'file_upload' ? `Upload resume: ${chosenFileName}` : `Step ${(currentWorkflow?.steps?.length || 0) + 1}`);

    const newStep = {
      id: 's_' + Date.now(),
      type: isAi ? 'ai_fallback' : act === 'file_upload' ? 'attach_resume' : act,
      name,
      value: act === 'file_upload' ? chosenFileName : (fillVal || (isAi ? 'AI screening auto-response' : '')),
      fileName: act === 'file_upload' ? chosenFileName : undefined,
      resumeId: act === 'file_upload' ? chosenResumeId : undefined,
      target: isAi ? 'Questionnaire container' : act === 'file_upload' ? 'input[type="file"]' : 'Element selector',
      waitMs: isAi ? 800 : 400,
      color: ACTION_COLORS[act] || '#38bdf8',
      badge: ACTION_BADGES[act] || 'ACT',
      disabled: false,
      stopAfter: false,
      finalSubmit: false,
    };

    if (act === 'file_upload' && chosenResumeId) {
      currentWorkflow.resumeId = chosenResumeId;
    }

    currentWorkflow.steps.push(newStep);
    if (stepNameInput) stepNameInput.value = '';
    await saveWorkflows(`Added step "${name}"!`);
  });

  // Undo Step
  undoBtn?.addEventListener('click', async () => {
    undoBtn.disabled = true;
    try {
      const result = await chrome.runtime.sendMessage({ action: 'WORKFLOW_RECORD_UNDO' });
      if (result?.success) {
        if (currentWorkflow?.steps?.length > 1) {
          currentWorkflow.steps.pop();
        }
        await saveWorkflows(result.undone ? `Removed "${String(result.removedStep)}".` : 'The starting page is protected.');
      } else {
        showStatus(result?.error || 'Could not undo step.', true);
      }
    } catch (e) {
      if (currentWorkflow?.steps?.length > 1) {
        currentWorkflow.steps.pop();
        await saveWorkflows('Undid last step.');
      }
    } finally {
      undoBtn.disabled = false;
    }
  });

  // Stop Working (toggle pause tracking / OFF condition)
  inspectBtn?.addEventListener('click', async () => {
    isStopWorkingActive = !isStopWorkingActive;
    inspectBtn.classList.toggle('inspecting', isStopWorkingActive);
    inspectBtn.textContent = isStopWorkingActive ? 'Resume working' : 'Stop working';
    showStatus(isStopWorkingActive
      ? 'Tracking paused (OFF condition). Clicks & uploads work normally on websites.'
      : 'Recording active. Tracking enabled.');

    sendToTargetTab({ action: 'RECORDER_TAB_STOP_WORKING' });
    chrome.runtime.sendMessage({ action: 'RECORDER_TAB_STOP_WORKING' }).catch(() => {});
  });

  // Continue to loop step 1 / End Loop
  endLoopBtn?.addEventListener('click', async () => {
    if (manualLoopDepth < 1) return;
    sendToTargetTab({ action: 'RECORDER_TAB_END_LOOP' });
    manualLoopDepth = Math.max(0, manualLoopDepth - 1);
    document.getElementById('wf-loop-state').textContent = manualLoopDepth > 0 ? `Inside loop ${manualLoopDepth}` : 'No active loop';
    endLoopBtn.disabled = manualLoopDepth === 0;
    if (manualLoopDepth === 0) {
      endLoopBtn.style.background = '';
      endLoopBtn.style.color = '';
    }
    showStatus('Loop closed! Added "Continue to loop step 1".');
  });

  // Finish and Save
  finishBtn?.addEventListener('click', async () => {
    if (currentWorkflow) {
      if (!currentWorkflow.name || currentWorkflow.name.trim().toLowerCase() === 'recorded workflow') {
        currentWorkflow.name = getNextDefaultWorkflowName(workflows.filter(w => w.id !== currentWorkflow.id));
      }
      currentWorkflow.updatedAt = Date.now();
    }
    await chrome.runtime.sendMessage({ action: 'WORKFLOW_RECORD_STOP' }).catch(() => {});
    sendToTargetTab({ action: 'RECORDER_TAB_FINISH' });
    await saveWorkflows('Workflow saved successfully!');
    // Return to Options / Studio page
    const studioUrl = chrome.runtime.getURL('options.html#workflows');
    chrome.tabs.create({ url: studioUrl });
    window.close();
  });

  // Exit / Cancel Recording
  document.getElementById('wf-exit-record')?.addEventListener('click', async () => {
    await chrome.runtime.sendMessage({ action: 'WORKFLOW_RECORD_STOP' }).catch(() => {});
    sendToTargetTab({ action: 'WORKFLOW_RECORD_STOP' });
    window.close();
  });

  // Back to Studio
  backStudioBtn?.addEventListener('click', () => {
    chrome.tabs.create({ url: chrome.runtime.getURL('options.html#workflows') });
  });

  // Refresh Connection
  refreshConnBtn?.addEventListener('click', async () => {
    await updateTargetTabHeader();
    showStatus('Refreshed connection to target tab.');
  });
}

function setupCrossTabSync() {
  // Listen to background & content script state broadcast
  chrome.runtime.onMessage.addListener((message) => {
    if (!message || typeof message.action !== 'string') return;

    if (message.action === 'RECORDER_STATE_UPDATE') {
      if (typeof message.stepCount === 'number') {
        const stepNum = document.getElementById('wf-step-number');
        if (stepNum) stepNum.textContent = `Step ${message.stepCount + 1}`;
      }
      if (typeof message.loopDepth === 'number') {
        manualLoopDepth = message.loopDepth;
        const loopLabel = document.getElementById('wf-loop-state');
        if (loopLabel) loopLabel.textContent = manualLoopDepth > 0 ? `Inside loop ${manualLoopDepth}` : 'No active loop';
        const endLoopBtn = document.getElementById('wf-end-loop');
        if (endLoopBtn) {
          endLoopBtn.disabled = manualLoopDepth === 0;
          if (manualLoopDepth > 0) {
            endLoopBtn.style.background = '#f59e0b';
            endLoopBtn.style.color = '#000';
            endLoopBtn.style.fontWeight = '700';
          } else {
            endLoopBtn.style.background = '';
            endLoopBtn.style.color = '';
            endLoopBtn.style.fontWeight = '';
          }
        }
      }
      if (message.status) {
        showStatus(message.status, message.error === true);
      }
      if (message.waitTarget !== undefined) {
        const waitTarget = document.getElementById('wf-wait-target');
        if (waitTarget) waitTarget.textContent = message.waitTarget;
      }
      if (message.paused !== undefined || message.skipNextCapture !== undefined) {
        isStopWorkingActive = Boolean(message.paused ?? message.skipNextCapture);
        const inspectBtn = document.getElementById('wf-inspect');
        if (inspectBtn) {
          inspectBtn.classList.toggle('inspecting', isStopWorkingActive);
          inspectBtn.textContent = isStopWorkingActive ? 'Resume working' : 'Stop working';
        }
      }
    }
  });

  // Real-time storage listener: updates steps list immediately when webpage clicks are recorded
  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName === 'session' && changes[RECORDING_KEY]?.newValue) {
      const rec = changes[RECORDING_KEY].newValue;
      if (rec.workflow?.steps) {
        currentWorkflow = rec.workflow;
        renderStepsList();
      }
    }
    if (areaName === 'local' && changes[STORAGE_KEY_WORKFLOWS]?.newValue) {
      const list = changes[STORAGE_KEY_WORKFLOWS].newValue;
      if (Array.isArray(list) && currentWorkflowId) {
        const updated = list.find((w) => w.id === currentWorkflowId);
        if (updated?.steps) {
          currentWorkflow = updated;
          renderStepsList();
        }
      }
    }
  });
}

function renderStepsList() {
  const container = document.getElementById('steps-container');
  const countEl = document.getElementById('steps-count');
  const stepNumEl = document.getElementById('wf-step-number');

  if (!container || !currentWorkflow) return;

  const steps = currentWorkflow.steps || [];
  if (countEl) countEl.textContent = steps.length;
  if (stepNumEl) stepNumEl.textContent = `Step ${steps.length + 1}`;

  container.innerHTML = steps.map((step, idx) => {
    const badgeColor = step.color || ACTION_COLORS[step.type] || '#38bdf8';
    const badgeText = step.badge || ACTION_BADGES[step.type] || 'ACT';
    return `
      <div class="step-item" style="border-left: 3px solid ${badgeColor};">
        <div style="display:flex;align-items:center;min-width:0;flex:1;">
          <span class="step-badge" style="background:${badgeColor};">${badgeText}</span>
          <span class="step-title">${idx + 1}. ${escapeHtml(step.name || 'Step ' + (idx + 1))}</span>
        </div>
        <button class="step-del btn-del-step" data-idx="${idx}" title="Delete step">✕</button>
      </div>
    `;
  }).join('');

  container.querySelectorAll('.btn-del-step').forEach((btn) => {
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
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
