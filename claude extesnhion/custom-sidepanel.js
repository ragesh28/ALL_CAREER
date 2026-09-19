/**
 * Custom Sidepanel for Claude in Chrome (BYOK Mode)
 * Full Autonomous Browser Control & Agentic Execution Loop
 * Supports OmniRoute, Google Gemini, and Anthropic Claude
 * Features: Target Tab Locking (Background Execution) & New Tab Auto-Navigation
 */

const STORAGE_KEY = 'byok_config';
const CHAT_HISTORY_KEY = 'byok_chat_history';

const DEFAULT_CONFIG = {
  activeProvider: 'omniroute',
  gemini: {
    apiKey: '',
    model: 'gemini-2.0-flash',
  },
  omniroute: {
    apiKey: 'sk-f46d845e6a300177-0a895e-fbfbd25b',
    baseUrl: 'http://127.0.0.1:20128/v1',
    model: 'antigravity/gemini-3.6-flash-high',
    fetchedModels: [],
  },
  anthropic: {
    apiKey: '',
    model: 'claude-3-7-sonnet-20250219',
  },
};

const GEMINI_MODELS = [
  { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash' },
  { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' },
  { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro' },
  { id: 'gemini-2.0-pro-exp-02-05', name: 'Gemini 2.0 Pro Exp' },
];

const OMNIROUTE_PRESET_MODELS = [
  { id: 'antigravity/gemini-3.6-flash-high', name: 'Gemini 3.6 Flash High' },
  { id: 'auto/claude-sonnet', name: 'Claude Sonnet (Auto Routing)' },
  { id: 'auto/claude-opus', name: 'Claude Opus (Auto Routing)' },
  { id: 'auto/best-coding', name: 'Best Coding Model' },
  { id: 'auto/best-chat', name: 'Best Chat Model' },
  { id: 'auto/fast', name: 'Fastest Model' },
  { id: 'auto/smart', name: 'Smartest Model' },
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
  { id: 'gpt-4o', name: 'GPT-4o' },
];

const ANTHROPIC_MODELS = [
  { id: 'claude-3-7-sonnet-20250219', name: 'Claude 3.7 Sonnet' },
  { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet' },
  { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku' },
];

let config = { ...DEFAULT_CONFIG };
let chatMessages = [];
let isGenerating = false;
let isAgentRunning = false;
let currentTab = null;
let lockedTabId = null; // Follows active tab by default, or locked if manually requested
let isManuallyLocked = false; // When false (default), AI dynamically targets whichever tab the user is viewing!

// Extension Autonomy and Permissions
let aiDecisionMode = 'autonomous'; // 'autonomous' | 'ask_human'
let allowMultiTabControl = true;
let allowSettingsAccess = true;

// Universal safeFetch: Proxies via background service worker to bypass CSP/CORS restrictions
async function safeFetch(url, options = {}) {
  try {
    const proxyRes = await chrome.runtime.sendMessage({
      action: 'BYOK_PROXY_FETCH',
      url,
      options,
    });
    if (proxyRes) {
      if (proxyRes.error) throw new Error(proxyRes.error);
      return {
        ok: proxyRes.ok,
        status: proxyRes.status,
        statusText: proxyRes.statusText,
        text: async () => proxyRes.text,
        json: async () => JSON.parse(proxyRes.text),
      };
    }
  } catch (msgErr) {
    // Fallback
  }

  const directRes = await fetch(url, options);
  return {
    ok: directRes.ok,
    status: directRes.status,
    statusText: directRes.statusText,
    text: async () => directRes.text(),
    json: async () => directRes.json(),
  };
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const queryTabId = parseInt(urlParams.get('tabId'), 10);
  const queryMode = urlParams.get('mode');
  const queryWf = urlParams.get('wf');

  if (queryTabId && (queryMode === 'record' || queryMode === 'run')) {
    lockedTabId = queryTabId;
    isManuallyLocked = true;
  }

  await loadConfig();
  await loadAutonomySettings();
  await loadChatHistory();
  await updateActiveTabInfo();

  const recData = await chrome.storage.local.get(['workflowRecordingActive', 'currentRecordingWorkflowId']);
  if (queryMode === 'record') {
    activeSidepanelView = 'recorder';
    await loadSidepanelWorkflows();
  } else {
    activeSidepanelView = 'chat';
  }

  if (queryMode === 'record') {
    chatMessages.push({
      role: 'assistant',
      content: `🔴 **Workflow Recording Active** on locked tab.\n\nInstruct me what actions to perform (e.g. *"Click apply and answer questions"* or *"Upload resume"*), or interact directly with the web page!`,
      timestamp: Date.now(),
    });
  } else if (queryMode === 'run') {
    chatMessages.push({
      role: 'assistant',
      content: `⚡ **Running Workflow** on locked tab.\n\nI am connected to the target page and ready to execute all workflow steps autonomously.`,
      timestamp: Date.now(),
    });
  }

  renderApp();
  setupEventListeners();

  if (config.activeProvider === 'omniroute') {
    fetchOmniRouteModels(true).catch(() => {});
  }

  // Listen for tab switches - follow user active tab!
  chrome.tabs.onActivated?.addListener(async (activeInfo) => {
    try {
      const tab = await chrome.tabs.get(activeInfo.tabId);
      if (tab) {
        currentTab = tab;
        if (!isManuallyLocked || !isAgentRunning) {
          lockedTabId = tab.id;
        }
      }
    } catch (e) {}
    renderTabInfo();
  });

  chrome.tabs.onUpdated?.addListener(async (tabId, changeInfo) => {
    if ((tabId === lockedTabId || tabId === currentTab?.id) && changeInfo.status === 'complete') {
      await updateActiveTabInfo();
      renderTabInfo();
    }
  });

  // Listen for workflow recording updates
  chrome.storage.onChanged?.addListener(async (changes, area) => {
    if (area === 'local') {
      if (changes.workflowRecordingActive) {
        if (changes.workflowRecordingActive.newValue) {
          activeSidepanelView = 'recorder';
          await loadSidepanelWorkflows();
          renderApp();
          setupEventListeners();
        }
      }
      if (changes.browserWorkflows && activeSidepanelView === 'recorder') {
        await loadSidepanelWorkflows();
        renderApp();
        setupEventListeners();
      }
    }
  });

  chrome.runtime.onMessage?.addListener((msg) => {
    if (msg.action === 'WORKFLOW_RECORD_START') {
      activeSidepanelView = 'recorder';
      loadSidepanelWorkflows().then(() => {
        renderApp();
        setupEventListeners();
      });
    }
    if (msg.action === 'WORKFLOW_RECORD_STOP') {
      const statusEl = document.getElementById('side-rec-status');
      if (statusEl) statusEl.textContent = '⏹ Workflow recording stopped.';
    }
  });
});

async function loadConfig() {
  const data = await chrome.storage.local.get(STORAGE_KEY);
  if (data[STORAGE_KEY]) {
    config = {
      ...DEFAULT_CONFIG,
      ...data[STORAGE_KEY],
      gemini: { ...DEFAULT_CONFIG.gemini, ...(data[STORAGE_KEY].gemini || {}) },
      omniroute: { ...DEFAULT_CONFIG.omniroute, ...(data[STORAGE_KEY].omniroute || {}) },
      anthropic: { ...DEFAULT_CONFIG.anthropic, ...(data[STORAGE_KEY].anthropic || {}) },
    };
  }
}

async function loadAutonomySettings() {
  try {
    const data = await chrome.storage.local.get(['aiDecisionMode', 'allowMultiTabControl', 'allowSettingsAccess']);
    if (data.aiDecisionMode) aiDecisionMode = data.aiDecisionMode;
    if (typeof data.allowMultiTabControl === 'boolean') allowMultiTabControl = data.allowMultiTabControl;
    if (typeof data.allowSettingsAccess === 'boolean') allowSettingsAccess = data.allowSettingsAccess;
  } catch (e) {}
}

async function saveConfig() {
  await chrome.storage.local.set({ [STORAGE_KEY]: config });
}

async function loadChatHistory() {
  const data = await chrome.storage.local.get(CHAT_HISTORY_KEY);
  if (Array.isArray(data[CHAT_HISTORY_KEY])) {
    chatMessages = data[CHAT_HISTORY_KEY];
  } else {
    chatMessages = [
      {
        role: 'assistant',
        content: '👋 **Claude in Chrome Autonomous Agent**\n\nI can **inspect pages, upload resumes silently, auto-fill forms, create workflows, and manage tabs** step-by-step.\n\nTry: *"open indeed"*, *"Upload my resume"*, or *"Search for AI ML jobs and apply"*.',
        timestamp: Date.now(),
      },
    ];
  }
}

async function saveChatHistory() {
  await chrome.storage.local.set({ [CHAT_HISTORY_KEY]: chatMessages.slice(-50) });
}

async function updateActiveTabInfo() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.id) {
      currentTab = tab;
      if (!isManuallyLocked || !isAgentRunning) {
        lockedTabId = tab.id;
      }
    }
  } catch (err) {
    currentTab = null;
  }
}

async function getTargetTab() {
  if (!isManuallyLocked || !isAgentRunning) {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab?.id) {
        currentTab = tab;
        lockedTabId = tab.id;
        return tab;
      }
    } catch (e) {}
  }

  if (lockedTabId) {
    try {
      const tab = await chrome.tabs.get(lockedTabId);
      if (tab) return tab;
    } catch (e) {}
  }

  await updateActiveTabInfo();
  return currentTab;
}

// ─── DOM Inspection & Accessibility Tree ───────────────────────────────────

async function getActivePageContext(tabId = null) {
  const target = tabId ? await chrome.tabs.get(tabId).catch(() => null) : await getTargetTab();
  if (!target?.id) return null;

  const url = target.url || '';
  const isNewTab = url.startsWith('chrome://newtab') || url.startsWith('edge://newtab') || url.startsWith('about:blank') || url === '';
  const isInternal = url.startsWith('chrome://') || url.startsWith('edge://') || url.startsWith('about:') || url.startsWith('chrome-extension://');

  if (isInternal) {
    const isStudio = url.includes(chrome.runtime.id);
    return {
      title: target.title || (isNewTab ? 'New Tab' : isStudio ? 'Claude Automation Studio & Hub' : 'Internal Browser Page'),
      url: target.url || '',
      isRestricted: !isStudio,
      isNewTab,
      text: isNewTab
        ? 'Blank / New Tab page. Tell the agent which website or search URL to navigate to.'
        : isStudio
          ? 'Claude in Chrome Automation Studio & Hub. All saved workflows, candidate profile, and settings are directly accessible to you in extension storage.'
          : 'Internal browser page. Navigate to an external website to begin.',
      accessibilityTree: isNewTab
        ? '[Blank New Tab Page - Ready to navigate to target website URL]'
        : isStudio
          ? '[Claude in Chrome Automation Studio - Note: You have direct programmatic access to view, edit inputs of, and run all saved workflows via extension storage]'
          : '[Internal browser page]',
    };
  }

  try {
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: target.id },
      func: () => {
        let tree = '';
        try {
          if (typeof window.__generateAccessibilityTree === 'function') {
            const treeObj = window.__generateAccessibilityTree('interactive', 10, 22000);
            tree = treeObj?.pageContent || '';
          }
        } catch (e) {}

        const bodyText = (document.body.innerText || '').substring(0, 8000);
        return {
          title: document.title,
          url: location.href,
          isRestricted: false,
          isNewTab: false,
          accessibilityTree: tree,
          text: bodyText,
        };
      },
    });
    return result?.result || null;
  } catch (err) {
    return {
      title: target?.title || '',
      url: target?.url || '',
      isRestricted: false,
      isNewTab: false,
      text: '',
      accessibilityTree: '',
    };
  }
}

// ─── Browser Action Execution Engine ────────────────────────────────────────

async function executeActionInTab(actionData, targetTabId) {
  const {
    action, tabIndex, url, workflowName, workflowId, stepIndex, stepName,
    value, name, target, waitMs, startUrl, variables, steps, question, answer
  } = actionData;

  // 1. Tab Management Actions
  if (action === 'list_tabs') {
    if (!allowMultiTabControl) return { success: false, error: 'Multi-Tab control is disabled in Settings.' };
    const tabs = await chrome.tabs.query({ currentWindow: true });
    const list = tabs.map((t, i) => `[Tab ${i + 1}] "${t.title}" (${t.url}) ${t.id === targetTabId ? '👈 [CURRENT ACTIVE TAB USER IS LOOKING AT]' : ''}`).join('\n');
    return { success: true, message: `Open tabs in this window (${tabs.length}):\n${list}` };
  }

  if (action === 'switch_tab') {
    if (!allowMultiTabControl) return { success: false, error: 'Multi-Tab control is disabled in Settings.' };
    const tabs = await chrome.tabs.query({ currentWindow: true });
    let target = null;
    if (typeof tabIndex === 'number') {
      const idx = tabIndex >= 1 && tabIndex <= tabs.length ? tabIndex - 1 : tabIndex;
      target = tabs[idx];
    } else if (url || actionData.title || actionData.query) {
      const q = (url || actionData.title || actionData.query).toLowerCase();
      target = tabs.find(t => (t.url && t.url.toLowerCase().includes(q)) || (t.title && t.title.toLowerCase().includes(q)));
    } else {
      target = tabs.find(t => t.id !== targetTabId);
    }
    if (target?.id) {
      lockedTabId = target.id;
      currentTab = target;
      await chrome.tabs.update(target.id, { active: true });
      if (target.windowId) await chrome.windows.update(target.windowId, { focused: true });
      renderTabInfo();
      return { success: true, message: `Switched active tab to: "${target.title}" (${target.url})` };
    }
    return { success: false, error: 'Could not find tab to switch to.' };
  }

  if (action === 'inspect_tab') {
    if (!allowMultiTabControl) return { success: false, error: 'Multi-Tab control is disabled in Settings.' };
    const tabs = await chrome.tabs.query({ currentWindow: true });
    let target = null;
    if (typeof tabIndex === 'number') {
      const idx = tabIndex >= 1 && tabIndex <= tabs.length ? tabIndex - 1 : tabIndex;
      target = tabs[idx];
    } else if (url || actionData.title || actionData.query) {
      const q = (url || actionData.title || actionData.query).toLowerCase();
      target = tabs.find(t => (t.url && t.url.toLowerCase().includes(q)) || (t.title && t.title.toLowerCase().includes(q)));
    } else {
      target = tabs.find(t => t.id !== targetTabId);
    }
    if (target?.id) {
      const page = await getActivePageContext(target.id);
      return {
        success: true,
        message: `Inspected tab "${target.title}" (${target.url}):\n${page?.text ? page.text.substring(0, 2000) : '[No text content detected]'}`
      };
    }
    return { success: false, error: 'Could not find other tab to inspect.' };
  }

  if (action === 'new_tab') {
    if (!allowMultiTabControl) return { success: false, error: 'Multi-Tab control is disabled in Settings.' };
    const newTab = await chrome.tabs.create({ url: url || 'https://www.google.com', active: true });
    lockedTabId = newTab.id;
    currentTab = newTab;
    renderTabInfo();
    return { success: true, message: `Opened new tab and locked AI control: ${url || 'New Tab'}` };
  }

  if (action === 'close_tab') {
    if (!allowMultiTabControl) return { success: false, error: 'Multi-Tab control is disabled in Settings.' };
    if (targetTabId) {
      await chrome.tabs.remove(targetTabId);
      lockedTabId = null;
      await updateActiveTabInfo();
      renderTabInfo();
      return { success: true, message: 'Closed target tab.' };
    }
    return { success: false, error: 'No target tab to close.' };
  }

  // 2. Direct Navigation (Works from New Tab or ANY tab via chrome.tabs.update!)
  if (action === 'navigate') {
    if (!url) return { success: false, error: 'No URL provided.' };
    let targetUrl = url.trim();

    // Auto-expand common shortcuts (e.g. "indeed" or "inded" -> "https://www.indeed.com")
    const lower = targetUrl.toLowerCase();
    if (lower === 'indeed' || lower.includes('inded')) targetUrl = 'https://www.indeed.com';
    else if (lower === 'naukri') targetUrl = 'https://www.naukri.com';
    else if (lower === 'linkedin') targetUrl = 'https://www.linkedin.com/jobs';
    else if (lower === 'google') targetUrl = 'https://www.google.com';
    else if (!targetUrl.startsWith('http://') && !targetUrl.startsWith('https://')) {
      if (!targetUrl.includes('.')) {
        targetUrl = `https://www.google.com/search?q=${encodeURIComponent(targetUrl)}`;
      } else {
        targetUrl = 'https://' + targetUrl;
      }
    }

    try {
      await chrome.tabs.update(targetTabId, { url: targetUrl });
      // Wait for page to load
      await new Promise((resolve) => {
        const listener = (tid, changeInfo) => {
          if (tid === targetTabId && changeInfo.status === 'complete') {
            chrome.tabs.onUpdated.removeListener(listener);
            resolve();
          }
        };
        chrome.tabs.onUpdated.addListener(listener);
        setTimeout(resolve, 3200);
      });
      renderTabInfo();
      return { success: true, message: `Navigated tab to ${targetUrl}` };
    } catch (e) {
      return { success: false, error: 'Navigation failed: ' + e.message };
    }
  }

  // 3. Workflow Management Actions (Full Read, Write, Edit Inputs & Run)
  if (action === 'list_workflows') {
    try {
      const storageData = await chrome.storage.local.get(['browserWorkflows']);
      const wfs = Array.isArray(storageData.browserWorkflows) ? storageData.browserWorkflows : [];
      if (wfs.length === 0) {
        return { success: true, message: 'No workflows currently saved in extension storage.' };
      }
      const summary = wfs.map((w, i) => {
        const stepsStr = (w.steps || []).map((s, si) => `    • Step ${si + 1} [${s.type}]: "${s.name || s.type}" (Input value: "${s.value || ''}", Target: "${s.target || ''}")`).join('\n');
        return `[Workflow ${i + 1}] "${w.name}" (ID: "${w.id}")\n  Start URL: ${w.startUrl || 'N/A'}\n  Variables: ${JSON.stringify(w.variables || {})}\n  Steps (${(w.steps || []).length} nodes):\n${stepsStr}`;
      }).join('\n\n');
      return { success: true, message: `Found ${wfs.length} saved workflow(s):\n\n${summary}` };
    } catch (e) {
      return { success: false, error: 'Failed to list workflows: ' + e.message };
    }
  }

  if (action === 'get_workflow') {
    try {
      const storageData = await chrome.storage.local.get(['browserWorkflows']);
      const wfs = Array.isArray(storageData.browserWorkflows) ? storageData.browserWorkflows : [];
      const query = (workflowName || workflowId || '').toLowerCase();
      const wf = wfs.find(w => w.id === workflowId || (w.name && w.name.toLowerCase().includes(query))) || wfs[0];
      if (!wf) return { success: false, error: `Workflow "${workflowName || workflowId}" not found.` };
      return { success: true, message: `Workflow Details:\n${JSON.stringify(wf, null, 2)}` };
    } catch (e) {
      return { success: false, error: e.message };
    }
  }

  if (action === 'update_workflow_input' || action === 'update_workflow_step' || action === 'update_workflow') {
    if (!allowSettingsAccess) return { success: false, error: 'Settings/workflow access is disabled in Settings.' };
    try {
      const storageData = await chrome.storage.local.get(['browserWorkflows']);
      const wfs = Array.isArray(storageData.browserWorkflows) ? storageData.browserWorkflows : [];
      if (wfs.length === 0) return { success: false, error: 'No workflows found in storage to update.' };

      const query = (workflowName || workflowId || '').toLowerCase();
      let wf = null;
      if (query) {
        wf = wfs.find(w => w.id === workflowId || (w.name && w.name.toLowerCase().includes(query)));
      }
      if (!wf && typeof actionData.workflowIndex === 'number' && wfs[actionData.workflowIndex]) {
        wf = wfs[actionData.workflowIndex];
      }
      if (!wf) wf = wfs[0];

      // Update top-level properties if provided
      if (startUrl) wf.startUrl = startUrl;
      if (actionData.newWorkflowName) wf.name = actionData.newWorkflowName;
      if (variables && typeof variables === 'object') wf.variables = { ...(wf.variables || {}), ...variables };

      // Identify target step
      let step = null;
      let targetStepIdx = -1;
      if (typeof stepIndex === 'number') {
        targetStepIdx = stepIndex >= 1 && stepIndex <= (wf.steps || []).length ? stepIndex - 1 : stepIndex;
        step = wf.steps?.[targetStepIdx];
      } else if (stepName) {
        const sQuery = stepName.toLowerCase();
        targetStepIdx = (wf.steps || []).findIndex(s => (s.name && s.name.toLowerCase().includes(sQuery)) || s.id === stepName);
        if (targetStepIdx >= 0) step = wf.steps[targetStepIdx];
      } else if (actionData.stepId) {
        targetStepIdx = (wf.steps || []).findIndex(s => s.id === actionData.stepId);
        if (targetStepIdx >= 0) step = wf.steps[targetStepIdx];
      } else if (typeof value === 'string' && (wf.steps || []).length > 0) {
        targetStepIdx = (wf.steps || []).findIndex(s => s.type === 'fill' || s.type === 'open_url');
        if (targetStepIdx < 0) targetStepIdx = 0;
        step = wf.steps[targetStepIdx];
      }

      if (step) {
        if (typeof value !== 'undefined') step.value = value;
        if (name) step.name = name;
        if (target) step.target = target;
        if (waitMs) step.waitMs = parseInt(waitMs, 10) || 400;
      }

      await chrome.storage.local.set({ browserWorkflows: wfs });
      return {
        success: true,
        message: `Successfully updated workflow "${wf.name}"${step ? ` (Step ${targetStepIdx + 1} "${step.name}": input value set to "${step.value}")` : ''}. Changes saved to storage!`
      };
    } catch (e) {
      return { success: false, error: 'Failed to update workflow input: ' + e.message };
    }
  }

  if (action === 'run_workflow') {
    try {
      const storageData = await chrome.storage.local.get(['browserWorkflows']);
      const wfs = Array.isArray(storageData.browserWorkflows) ? storageData.browserWorkflows : [];
      const query = (workflowName || workflowId || '').toLowerCase();
      const wf = wfs.find(w => w.id === workflowId || (w.name && w.name.toLowerCase().includes(query))) || wfs[0];
      if (!wf) return { success: false, error: `Workflow "${workflowName || workflowId}" not found.` };
      const res = await chrome.runtime.sendMessage({
        action: 'WORKFLOW_RUN',
        workflowId: wf.id,
        workflow: wf,
      });
      return { success: true, message: `Started running workflow "${wf.name}" on active target tab!` };
    } catch (e) {
      return { success: false, error: 'Failed to run workflow: ' + e.message };
    }
  }

  if (action === 'delete_workflow') {
    if (!allowSettingsAccess) return { success: false, error: 'Settings access is disabled in Settings.' };
    try {
      const storageData = await chrome.storage.local.get(['browserWorkflows']);
      let wfs = Array.isArray(storageData.browserWorkflows) ? storageData.browserWorkflows : [];
      const query = (workflowName || workflowId || '').toLowerCase();
      const initialLen = wfs.length;
      wfs = wfs.filter(w => w.id !== workflowId && (!w.name || !w.name.toLowerCase().includes(query)));
      if (wfs.length === initialLen) return { success: false, error: `Workflow "${workflowName || workflowId}" not found.` };
      await chrome.storage.local.set({ browserWorkflows: wfs });
      return { success: true, message: `Deleted workflow "${workflowName || workflowId}". ${wfs.length} workflows remain.` };
    } catch (e) {
      return { success: false, error: e.message };
    }
  }

  if (action === 'create_workflow') {
    if (!allowSettingsAccess) return { success: false, error: 'Settings access is disabled in Settings.' };
    try {
      const storageData = await chrome.storage.local.get(['browserWorkflows']);
      const wfs = storageData.browserWorkflows || [];
      const newWf = {
        id: 'wf_' + Date.now(),
        name: workflowName || 'Custom Recorded Workflow',
        startUrl: currentTab?.url || 'https://www.naukri.com/',
        steps: Array.isArray(steps) ? steps : [
          { id: 's1', type: 'open_url', title: 'Open Page', target: currentTab?.url || '', value: currentTab?.url || '', icon: 'URL', color: '#10b981' }
        ],
      };
      wfs.push(newWf);
      await chrome.storage.local.set({ browserWorkflows: wfs });
      return { success: true, message: `Created new workflow "${newWf.name}" with ${newWf.steps.length} steps.` };
    } catch (e) {
      return { success: false, error: 'Failed to create workflow: ' + e.message };
    }
  }

  if (action === 'save_custom_answer') {
    if (!allowSettingsAccess) return { success: false, error: 'Settings access is disabled in Settings.' };
    try {
      const storageData = await chrome.storage.local.get(['customAnswers']);
      const answers = storageData.customAnswers || [];
      answers.push({ id: 'qa_' + Date.now(), question, answer, matchType: 'contains' });
      await chrome.storage.local.set({ customAnswers: answers });
      return { success: true, message: `Saved custom answer: "${question}" ➔ "${answer}"` };
    } catch (e) {
      return { success: false, error: e.message };
    }
  }

  if (action === 'ask_human') {
    return { success: true, message: `[Paused for Human Input]: ${question}` };
  }

  // Resume payload fetching for silent upload
  let resumePayload = null;
  if (action === 'upload_resume') {
    try {
      const storageData = await chrome.storage.local.get(['resumes', 'defaultResume']);
      const allResumes = storageData.resumes || [];
      const defId = storageData.defaultResume;
      const targetResume = allResumes.find(r => r.id === defId) || allResumes[0];
      if (targetResume && targetResume.data) {
        resumePayload = {
          name: targetResume.name || 'Resume.pdf',
          type: targetResume.type || 'application/pdf',
          data: targetResume.data,
        };
      }
    } catch (e) {}
  }

  // Profile fetching for autofill
  let userProfile = null;
  if (action === 'autofill_page') {
    try {
      const storageData = await chrome.storage.local.get(['userProfile']);
      userProfile = storageData.userProfile || null;
    } catch (e) {}
  }

  if (!targetTabId) {
    return { success: false, error: 'No active browser tab found.' };
  }

  try {
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: targetTabId },
      func: (data) => {
        const { action, ref_id, text, press_enter, key, direction, value, resumePayload, userProfile } = data;

        function highlightElement(el) {
          if (!el || !el.style) return;
          const origOutline = el.style.outline;
          const origBoxShadow = el.style.boxShadow;
          const origTransition = el.style.transition;
          el.style.transition = 'outline 0.2s ease, box-shadow 0.2s ease';
          el.style.outline = '3px solid #d97757';
          el.style.boxShadow = '0 0 14px rgba(217, 119, 87, 0.9)';
          setTimeout(() => {
            try {
              el.style.outline = origOutline;
              el.style.boxShadow = origBoxShadow;
              el.style.transition = origTransition;
            } catch (e) {}
          }, 1200);
        }

        function findElement(refId, textHint = '') {
          if (refId) {
            const maps = [window.__claudeElementMap, window.__autofillElementMap, window.__elementMap];
            for (const m of maps) {
              if (m && m[refId]) {
                const el = typeof m[refId].deref === 'function' ? m[refId].deref() : m[refId];
                if (el && document.contains(el)) return el;
              }
            }
          }

          if (textHint && textHint.length >= 2) {
            const needle = textHint.toLowerCase();
            const all = document.querySelectorAll('button, a, input, textarea, select, [contenteditable="true"], [role="textbox"], [role="button"], [class*="btn"], span, div');
            for (const el of all) {
              const txt = (el.textContent || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('data-placeholder') || '').toLowerCase().trim();
              if (txt === needle || (txt.includes(needle) && txt.length < 60)) {
                return el;
              }
            }
          }

          // Fallback for typing action if specific ref not found: active contenteditable or focused input
          if (action === 'type') {
            const active = document.activeElement;
            if (active && (active.isContentEditable || active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement)) {
              return active;
            }
            const editable = document.querySelector('div[contenteditable="true"]:not([aria-hidden="true"]), .chatbot_InputContainer div[contenteditable="true"], .textArea[contenteditable="true"]');
            if (editable) return editable;
          }

          return null;
        }

        // 1. CLICK
        if (action === 'click') {
          let hint = '';
          const quoteMatch = (data.thought || '').match(/['"]([^'"]+)['"]/);
          if (quoteMatch) hint = quoteMatch[1];

          const el = findElement(ref_id, hint);
          if (!el) return { success: false, error: `Element [${ref_id}] not found.` };

          highlightElement(el);
          try {
            el.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'center' });
          } catch (e) {}
          el.focus?.();

          const opts = { bubbles: true, cancelable: true, composed: true, view: window };
          el.dispatchEvent(new PointerEvent('pointerenter', opts));
          el.dispatchEvent(new MouseEvent('mouseenter', opts));
          el.dispatchEvent(new PointerEvent('pointerdown', opts));
          el.dispatchEvent(new MouseEvent('mousedown', opts));
          el.dispatchEvent(new PointerEvent('pointerup', opts));
          el.dispatchEvent(new MouseEvent('mouseup', opts));
          el.click();

          const label = el.getAttribute('aria-label') || el.innerText || el.value || el.tagName.toLowerCase();
          return { success: true, message: `Clicked "${label.substring(0, 30)}" [${ref_id}]` };
        }

        // 2. TYPE
        if (action === 'type') {
          const el = findElement(ref_id);
          if (!el) return { success: false, error: `Element [${ref_id}] not found.` };

          highlightElement(el);
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          el.focus?.();

          if (el.isContentEditable) {
            // Contenteditable divs (e.g. Naukri chatbot, rich text editors):
            // Must use execCommand('insertText') so the framework's input listeners fire.
            // Direct textContent assignment is invisible to React/chatbot SDKs.
            const sel = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(el);
            sel.removeAllRanges();
            sel.addRange(range);
            document.execCommand('delete', false);

            // Simulate realistic keyboard events per-character for anti-bot detection
            for (let i = 0; i < text.length; i++) {
              const ch = text[i];
              const keyOpts = { key: ch, code: 'Key' + ch.toUpperCase(), bubbles: true, cancelable: true, composed: true };
              el.dispatchEvent(new KeyboardEvent('keydown', keyOpts));
              el.dispatchEvent(new InputEvent('beforeinput', { inputType: 'insertText', data: ch, bubbles: true, cancelable: true, composed: true }));
              document.execCommand('insertText', false, ch);
              el.dispatchEvent(new InputEvent('input', { inputType: 'insertText', data: ch, bubbles: true, composed: true }));
              el.dispatchEvent(new KeyboardEvent('keyup', keyOpts));
            }
          } else if ('value' in el) {
            // Standard inputs / textareas: use native value setter for React compatibility
            const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
            if (setter) setter.call(el, text); else el.value = text;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
          }

          if (press_enter) {
            const keyOpts = { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true };
            el.dispatchEvent(new KeyboardEvent('keydown', keyOpts));
            el.dispatchEvent(new KeyboardEvent('keypress', keyOpts));
            el.dispatchEvent(new KeyboardEvent('keyup', keyOpts));
            if (el.form) {
              el.form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
            }
          }

          return { success: true, message: `Typed "${text}" into [${ref_id}]${press_enter ? ' and submitted Enter' : ''}` };
        }

        // 3. SCROLL
        if (action === 'scroll') {
          const amt = direction === 'up' ? -600 : 600;
          window.scrollBy({ top: amt, behavior: 'smooth' });
          return { success: true, message: `Scrolled page ${direction || 'down'}` };
        }

        // 4. SELECT OPTION
        if (action === 'select_option') {
          const el = findElement(ref_id);
          if (!el || el.tagName !== 'SELECT') return { success: false, error: `Select dropdown [${ref_id}] not found.` };
          highlightElement(el);
          let found = false;
          for (let i = 0; i < el.options.length; i++) {
            if (el.options[i].value === value || el.options[i].text.toLowerCase().includes(String(value).toLowerCase())) {
              el.selectedIndex = i;
              found = true;
              break;
            }
          }
          el.dispatchEvent(new Event('change', { bubbles: true }));
          return { success: found, message: found ? `Selected option "${value}" in [${ref_id}]` : `Option "${value}" not found.` };
        }

        // 5. PRESS KEY
        if (action === 'press_key') {
          const active = document.activeElement || document.body;
          const k = key || 'Enter';
          const keyOpts = { key: k, code: k, bubbles: true, cancelable: true };
          active.dispatchEvent(new KeyboardEvent('keydown', keyOpts));
          active.dispatchEvent(new KeyboardEvent('keyup', keyOpts));
          return { success: true, message: `Pressed key "${k}"` };
        }

        // 6. UPLOAD RESUME
        if (action === 'upload_resume') {
          if (!resumePayload || !resumePayload.data) {
            return { success: false, error: 'No default resume found in Settings vault.' };
          }
          try {
            const binary = atob(resumePayload.data);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            const file = new File([bytes], resumePayload.name || 'Resume.pdf', { type: resumePayload.type || 'application/pdf' });
            const dt = new DataTransfer();
            dt.items.add(file);

            let input = findElement(ref_id);
            if (!input || input.type !== 'file') input = document.querySelector('input[type="file"]');
            if (input && input.type === 'file') {
              input.files = dt.files;
              input.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
              input.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
              return { success: true, message: `Attached resume "${resumePayload.name}" silently.` };
            }

            const dropZone = findElement(ref_id) || document.querySelector('[class*="dropzone"], [class*="upload"], [class*="file"]');
            if (dropZone) {
              dropZone.dispatchEvent(new DragEvent('dragenter', { bubbles: true, cancelable: true, dataTransfer: dt }));
              dropZone.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt }));
              dropZone.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
              return { success: true, message: `Simulated file drop for "${resumePayload.name}".` };
            }

            return { success: false, error: 'Could not locate file upload element on page.' };
          } catch (e) {
            return { success: false, error: 'Resume upload error: ' + e.message };
          }
        }

        // 7. AUTOFILL PAGE
        if (action === 'autofill_page') {
          if (!userProfile) return { success: false, error: 'No profile found in Settings.' };
          let filled = 0;
          const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea');
          inputs.forEach(inp => {
            const label = (inp.name || inp.id || inp.placeholder || '').toLowerCase();
            let val = '';
            if (label.includes('name') || label.includes('full')) val = userProfile.fullName;
            else if (label.includes('email')) val = userProfile.email;
            else if (label.includes('phone') || label.includes('mobile')) val = userProfile.phone;
            else if (label.includes('city')) val = userProfile.city;
            else if (label.includes('skills')) val = userProfile.skills;

            if (val && !inp.value) {
              inp.value = val;
              inp.dispatchEvent(new Event('input', { bubbles: true }));
              inp.dispatchEvent(new Event('change', { bubbles: true }));
              filled++;
            }
          });
          return { success: true, message: `Auto-filled ${filled} input fields with your profile.` };
        }

        return { success: false, error: `Unknown action: ${action}` };
      },
      args: [{ ...actionData, resumePayload, userProfile }],
    });

    return result?.result || { success: false, error: 'Action produced no output.' };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

// ─── API Providers Calling ──────────────────────────────────────────────────

async function callGemini(apiKey, model, systemPrompt, messages) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`;

  const contents = messages.map(m => ({
    role: m.role === 'assistant' ? 'model' : 'user',
    parts: [{ text: m.content }],
  }));

  const payload = {
    contents,
    systemInstruction: { parts: [{ text: systemPrompt }] },
    generationConfig: { temperature: 0.2, maxOutputTokens: 2048 },
  };

  const response = await safeFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) throw new Error(`Gemini API Error (${response.status}): ${await response.text()}`);
  const data = await response.json();
  const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) throw new Error('Gemini returned an empty response.');
  return text;
}

async function callOmniRoute(apiKey, baseUrl, model, systemPrompt, messages) {
  let activeBaseUrl = baseUrl.trim() || 'http://127.0.0.1:20128/v1';
  let endpoint = `${activeBaseUrl.replace(/\/+$/, '')}/chat/completions`;

  const formattedMessages = [
    { role: 'system', content: systemPrompt },
    ...messages.map(m => ({ role: m.role, content: m.content })),
  ];

  const headers = { 'Content-Type': 'application/json' };
  if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

  const body = JSON.stringify({
    model: model || 'antigravity/gemini-3.6-flash-high',
    messages: formattedMessages,
    temperature: 0.2,
    max_tokens: 2048,
    stream: false,
  });

  let response;
  try {
    response = await safeFetch(endpoint, { method: 'POST', headers, body });
  } catch (err) {
    if (activeBaseUrl.includes('localhost')) {
      endpoint = `${activeBaseUrl.replace('localhost', '127.0.0.1').replace(/\/+$/, '')}/chat/completions`;
      response = await safeFetch(endpoint, { method: 'POST', headers, body });
    } else if (activeBaseUrl.includes('127.0.0.1')) {
      endpoint = `${activeBaseUrl.replace('127.0.0.1', 'localhost').replace(/\/+$/, '')}/chat/completions`;
      response = await safeFetch(endpoint, { method: 'POST', headers, body });
    } else {
      throw err;
    }
  }

  if (!response.ok) throw new Error(`OmniRoute Error (${response.status}): ${await response.text()}`);
  const rawText = await response.text();
  try {
    const data = JSON.parse(rawText);
    return data.choices?.[0]?.message?.content || rawText;
  } catch (e) {
    return rawText;
  }
}

async function fetchOmniRouteModels(silent = false) {
  let baseUrl = (config.omniroute.baseUrl || 'http://127.0.0.1:20128/v1').trim();
  let endpoint = `${baseUrl.replace(/\/+$/, '')}/models`;

  const headers = {};
  if (config.omniroute.apiKey) headers['Authorization'] = `Bearer ${config.omniroute.apiKey}`;

  try {
    let res = await safeFetch(endpoint, { headers });
    if (!res.ok && baseUrl.includes('localhost')) {
      res = await safeFetch(`${baseUrl.replace('localhost', '127.0.0.1').replace(/\/+$/, '')}/models`, { headers });
    } else if (!res.ok && baseUrl.includes('127.0.0.1')) {
      res = await safeFetch(`${baseUrl.replace('127.0.0.1', 'localhost').replace(/\/+$/, '')}/models`, { headers });
    }

    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();
    const models = Array.isArray(data.data) ? data.data.map(m => m.id) : [];
    if (models.length > 0) {
      config.omniroute.fetchedModels = models;
      await saveConfig();
      renderModelSelector();
      return models;
    }
  } catch (err) {
    if (!silent) throw new Error(`Could not fetch models: ${err.message}. Is OmniRoute running on port 20128?`);
  }
  return [];
}

async function callAnthropic(apiKey, model, systemPrompt, messages) {
  const url = 'https://api.anthropic.com/v1/messages';
  const formattedMessages = messages.map(m => ({
    role: m.role === 'assistant' ? 'assistant' : 'user',
    content: m.content,
  }));

  const response = await safeFetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'dangerously-allow-browser': 'true',
    },
    body: JSON.stringify({
      model,
      system: systemPrompt,
      messages: formattedMessages,
      max_tokens: 2048,
      temperature: 0.2,
    }),
  });

  if (!response.ok) throw new Error(`Anthropic API Error (${response.status}): ${await response.text()}`);
  const data = await response.json();
  const text = data.content?.[0]?.text;
  if (!text) throw new Error('Anthropic API returned an empty response.');
  return text;
}

// ─── Dynamic System Prompt Builder ──────────────────────────────────────────

async function buildAgentSystemPrompt() {
  const autonomyClause = aiDecisionMode === 'autonomous'
    ? `\n\n### CRITICAL AUTONOMY MODE ACTIVE:\n- You MUST make your own intelligent decisions and deductions from candidate profile.\n- NEVER stop to ask human. Complete all fields and actions autonomously.`
    : `\n\n### ASK HUMAN MODE ACTIVE:\n- If you encounter a crucial mandatory field that is completely missing from candidate profile, invoke action {"action": "ask_human", "question": "..."}.`;

  const tabClause = allowMultiTabControl
    ? `\n- Tab Management: {"thought": "...", "action": "switch_tab", "tabIndex": 1} or {"action": "new_tab", "url": "..."} or {"action": "close_tab"}`
    : `\n- Tab Management: Disabled by user. Stay on current tab.`;

  // Fetch all saved workflows and profile directly from extension storage
  let workflowsSummary = 'No saved workflows currently in storage.';
  let candidateProfileSummary = '';
  let customAnswersSummary = '';

  try {
    const storage = await chrome.storage.local.get(['browserWorkflows', 'userProfile', 'customAnswers']);
    const wfs = Array.isArray(storage.browserWorkflows) ? storage.browserWorkflows : [];
    if (wfs.length > 0) {
      workflowsSummary = wfs.map((w, i) => {
        const stepsStr = (w.steps || []).map((s, si) => {
          const val = s.value ? ` [input/value: "${s.value}"]` : '';
          const tgt = s.target ? ` [target: "${s.target}"]` : '';
          return `    • Step ${si + 1} (${(s.type || 'action').toUpperCase()}): "${s.name || s.type}"${val}${tgt}`;
        }).join('\n');
        return `  ${i + 1}. Workflow Name: "${w.name}" (ID: "${w.id}")
     Start URL: ${w.startUrl || 'https://www.naukri.com/'}
     Variables: ${JSON.stringify(w.variables || { role: '', location: '' })}
     Steps (${(w.steps || []).length} nodes):
${stepsStr}`;
      }).join('\n\n');
    }

    if (storage.userProfile) {
      candidateProfileSummary = `\n\n### CANDIDATE PROFILE:\n- Name: ${storage.userProfile.fullName || ''}\n- Email: ${storage.userProfile.email || ''}\n- Phone: ${storage.userProfile.phone || ''}\n- Skills: ${storage.userProfile.skills || ''}\n- Experience: ${storage.userProfile.experienceYears || ''} years\n- City: ${storage.userProfile.city || ''}, ${storage.userProfile.country || ''}`;
    }

    if (Array.isArray(storage.customAnswers) && storage.customAnswers.length > 0) {
      customAnswersSummary = `\n\n### SAVED Q&A RULES:\n${storage.customAnswers.map(a => `- "${a.question}" ➔ "${a.answer}"`).join('\n')}`;
    }
  } catch (e) {}

  // Fetch all open tabs in current window
  let openTabsSummary = '';
  try {
    const allTabs = await chrome.tabs.query({ currentWindow: true });
    openTabsSummary = allTabs.map((t, i) => `  [Tab ${i + 1}] "${t.title}" (${t.url}) ${t.id === (currentTab?.id || lockedTabId) ? '👈 [CURRENT ACTIVE TAB USER IS LOOKING AT]' : ''}`).join('\n');
  } catch (e) {}

  return `You are Claude in Chrome, an elite autonomous AI browser agent and automation orchestrator with direct browser execution and extension storage access.
You inspect interactive accessibility trees, click buttons, upload resumes silently, auto-fill forms, navigate to URLs, and have FULL PROGRAMMATIC ACCESS to read and modify all saved workflows.

### 🌐 ACTIVE BROWSER TAB (USER FOCUS):
- Currently Active Tab: "${currentTab?.title || 'Active Tab'}" (${currentTab?.url || ''})
- All Open Tabs in Window:
${openTabsSummary || '  (None)'}

### 🌐 TAB TARGETING & SWITCHING RULES:
1. BY DEFAULT, ALWAYS PERFORM ACTIONS ON THE USER'S CURRENT ACTIVE TAB ("${currentTab?.title || 'Active Tab'}"):
   - When the user asks to click, type, fill, apply, search, or summarize, ALWAYS act on this active tab!
   - You are directly connected to what the user is currently seeing.
2. WHEN THE USER ASKS "SEE OTHER TAB", "CHECK ANOTHER TAB", OR ASKS ABOUT OTHER WEBSITES:
   - Use action "list_tabs" to see all open tabs:
     \`\`\`json
     {"thought": "Listing all open tabs", "action": "list_tabs"}
     \`\`\`
   - Use action "switch_tab" to switch to the other tab:
     \`\`\`json
     {"thought": "Switching to the other tab", "action": "switch_tab"}
     \`\`\`
   - Use action "inspect_tab" to inspect what is on another tab without leaving:
     \`\`\`json
     {"thought": "Reading content of other tab", "action": "inspect_tab", "query": "indeed"}
     \`\`\`

### ⚡ WORKFLOWS CURRENTLY AVAILABLE IN EXTENSION (DIRECT ACCESS):
${workflowsSummary}
${candidateProfileSummary}
${customAnswersSummary}

### ⚡ WORKFLOW ACCESS & INPUT MODIFICATION RULES:
You have DIRECT, FULL READ AND WRITE ACCESS to all saved workflows stored in the extension.
- When the user asks "what workflows do we have?" or asks about existing workflows: Answer clearly with the exact workflow names, start URLs, and steps listed above. NEVER say you cannot read workflows because of internal extension pages!
- When the user asks "can you change the input or not?": Answer affirmatively YES, you have full access to change any input values (URLs, search terms, text inputs, form values, and variables), and you can update them immediately upon request.
- To update an input value in any workflow:
  \`\`\`json
  {"thought": "Updating input value of Step 1 in workflow t1", "action": "update_workflow_input", "workflowName": "t1", "stepIndex": 1, "value": "https://www.naukri.com/new-jobs"}
  \`\`\`
- To run a workflow:
  \`\`\`json
  {"thought": "Launching workflow t1", "action": "run_workflow", "workflowName": "t1"}
  \`\`\`
- To list or refresh workflows:
  \`\`\`json
  {"thought": "Listing all workflows", "action": "list_workflows"}
  \`\`\`

### STARTING ON A BLANK / NEW TAB:
If the user says "open indeed" or "search for jobs" and the current tab is a New Tab or blank page, your first action MUST be:
\`\`\`json
{"thought": "Navigating to Indeed job search", "action": "navigate", "url": "https://www.indeed.com"}
\`\`\`

### AVAILABLE BROWSER & WORKFLOW ACTIONS:
1. List workflows: \`\`\`json\n{"thought": "Listing workflows", "action": "list_workflows"}\n\`\`\`
2. Update workflow input: \`\`\`json\n{"thought": "Changing input value", "action": "update_workflow_input", "workflowName": "...", "stepIndex": 1, "value": "new value"}\n\`\`\`
3. Run workflow: \`\`\`json\n{"thought": "Executing workflow", "action": "run_workflow", "workflowName": "..."}\n\`\`\`
4. Create workflow: \`\`\`json\n{"thought": "Saving workflow", "action": "create_workflow", "workflowName": "Apply Job", "steps": [...]}\n\`\`\`
5. Delete workflow: \`\`\`json\n{"thought": "Deleting workflow", "action": "delete_workflow", "workflowName": "..."}\n\`\`\`
6. Navigate to website: \`\`\`json\n{"thought": "Opening website", "action": "navigate", "url": "https://www.naukri.com"}\n\`\`\`
7. Click element: \`\`\`json\n{"thought": "Clicking button", "action": "click", "ref_id": "ref_10"}\n\`\`\`
8. Type text: \`\`\`json\n{"thought": "Entering text", "action": "type", "ref_id": "ref_5", "text": "AI Engineer", "press_enter": true}\n\`\`\`
9. Upload resume: \`\`\`json\n{"thought": "Uploading resume", "action": "upload_resume", "ref_id": "ref_12"}\n\`\`\`
10. Select dropdown: \`\`\`json\n{"thought": "Selecting dropdown", "action": "select_option", "ref_id": "ref_8", "value": "Remote"}\n\`\`\`
11. AutoFill page: \`\`\`json\n{"thought": "Autofilling form fields with profile", "action": "autofill_page"}\n\`\`\`
12. Save custom answer: \`\`\`json\n{"thought": "Saving Q&A rule", "action": "save_custom_answer", "question": "...", "answer": "..."}\n\`\`\`
13. Scroll: \`\`\`json\n{"thought": "Scrolling down", "action": "scroll", "direction": "down"}\n\`\`\`
${tabClause}
14. Finish and report: \`\`\`json\n{"thought": "Task completed", "action": "done", "message": "..."}\n\`\`\`
${autonomyClause}

IMPORTANT RULES:
- Perform ONE action per step.
- When asked informational questions about workflows, profile, or capabilities, you can immediately answer using action "done" with your complete, helpful explanation!`;
}

function parseActionFromResponse(text) {
  if (!text) return null;

  const codeBlockMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (codeBlockMatch) {
    try {
      const parsed = JSON.parse(codeBlockMatch[1].trim());
      if (parsed.action) return parsed;
    } catch (e) {}
  }

  const jsonMatch = text.match(/\{[\s\S]*"action"\s*:\s*["'][^"']+["'][\s\S]*\}/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[0].trim());
      if (parsed.action) return parsed;
    } catch (e) {}
  }

  return { action: 'done', message: text };
}

async function callActiveModelRaw(systemPrompt, messages) {
  const provider = config.activeProvider;
  if (provider === 'gemini') {
    if (!config.gemini.apiKey) throw new Error('Please configure your Google Gemini API Key in Settings (⚙️).');
    return await callGemini(config.gemini.apiKey, config.gemini.model, systemPrompt, messages);
  } else if (provider === 'omniroute') {
    return await callOmniRoute(config.omniroute.apiKey, config.omniroute.baseUrl, config.omniroute.model, systemPrompt, messages);
  } else {
    if (!config.anthropic.apiKey) throw new Error('Please configure your Anthropic API Key in Settings (⚙️).');
    return await callAnthropic(config.anthropic.apiKey, config.anthropic.model, systemPrompt, messages);
  }
}

async function runAutonomousAgent(userGoal) {
  isAgentRunning = true;
  updateAgentControlsUI(true);

  // Lock target tab for this run session
  const targetTab = await getTargetTab();
  lockedTabId = targetTab?.id || currentTab?.id;
  renderTabInfo();

  const MAX_STEPS = 15;
  let currentStep = 0;
  const historyMessages = [];
  const activePrompt = await buildAgentSystemPrompt();

  try {
    while (currentStep < MAX_STEPS && isAgentRunning) {
      currentStep++;

      // 1. Read locked target tab context (even if user switches tabs!)
      const page = await getActivePageContext(lockedTabId);

      const stepPrompt = `[USER GOAL]: ${userGoal}
[STEP]: ${currentStep} of ${MAX_STEPS}
[CURRENT WEBPAGE]
URL: ${page?.url || 'unknown'}
Title: ${page?.title || 'unknown'}
${page?.isNewTab ? '[NOTE: Tab is currently a Blank / New Tab. To start, navigate to the target site using action "navigate"]' : ''}

--- ACCESSIBILITY INTERACTIVE ELEMENTS TREE ---
${page?.accessibilityTree ? page.accessibilityTree.substring(0, 15000) : '[No interactive elements detected]'}

--- PAGE TEXT SUMMARY ---
${page?.text ? page.text.substring(0, 3000) : ''}

Decide your next action. Respond with your thought and JSON action block.`;

      addLiveStepToChat(currentStep, `🔍 Planning Step ${currentStep} on "${page?.title || 'Tab'}"...`);

      historyMessages.push({ role: 'user', content: stepPrompt });
      const modelOutput = await callActiveModelRaw(activePrompt, historyMessages);
      historyMessages.push({ role: 'assistant', content: modelOutput });

      const actionData = parseActionFromResponse(modelOutput);

      if (!actionData || actionData.action === 'done') {
        const finalMsg = actionData?.message || modelOutput;
        updateLastStepInChat(`✅ **Goal Finished:**\n\n${finalMsg}`);
        break;
      }

      const thoughtText = actionData.thought || `Executing ${actionData.action} on ${actionData.ref_id || 'page'}`;
      updateLastStepInChat(`⚡ **Step ${currentStep}:** ${thoughtText}`);

      // 2. Execute Action specifically on the locked target tab!
      const execResult = await executeActionInTab(actionData, lockedTabId);

      if (actionData.action === 'ask_human') {
        updateLastStepInChat(`❓ **Question from AI:**\n${actionData.question || 'Please provide clarification'}`);
        break;
      }

      if (execResult.success) {
        historyMessages.push({ role: 'user', content: `[ACTION RESULT]: Success. ${execResult.message}` });
      } else {
        historyMessages.push({ role: 'user', content: `[ACTION RESULT]: Failed: ${execResult.error}. Try an alternate element or action.` });
        updateLastStepInChat(`⚡ **Step ${currentStep}:** ${thoughtText}\n⚠️ *Notice: ${execResult.error}*`);
      }

      await new Promise(r => setTimeout(r, actionData.action === 'navigate' ? 2400 : 1200));
    }

    if (currentStep >= MAX_STEPS && isAgentRunning) {
      addLiveStepToChat(currentStep, 'ℹ️ Reached maximum steps limit. Give additional instructions to continue.');
    }
  } catch (err) {
    addLiveStepToChat(currentStep, `❌ **Agent Stopped:** ${err.message}`);
  } finally {
    isAgentRunning = false;
    updateAgentControlsUI(false);
    await saveChatHistory();
  }
}

// ─── UI Rendering ────────────────────────────────────────────────────────────

function getAvailableModelsForCurrentProvider() {
  const p = config.activeProvider;
  if (p === 'gemini') return GEMINI_MODELS;
  if (p === 'anthropic') return ANTHROPIC_MODELS;

  const customList = (config.omniroute.fetchedModels || []).map(id => ({ id, name: id }));
  if (customList.length > 0) return customList;
  return OMNIROUTE_PRESET_MODELS;
}

let activeSidepanelView = 'chat'; // 'chat' | 'recorder'
let currentSidepanelWorkflow = null;

async function loadSidepanelWorkflows() {
  try {
    const data = await chrome.storage.local.get(['browserWorkflows', 'currentRecordingWorkflowId']);
    const wfs = Array.isArray(data.browserWorkflows) ? data.browserWorkflows : [];
    if (data.currentRecordingWorkflowId) {
      currentSidepanelWorkflow = wfs.find(w => w.id === data.currentRecordingWorkflowId);
    }
    if (!currentSidepanelWorkflow && wfs.length > 0) {
      currentSidepanelWorkflow = wfs[wfs.length - 1];
    }
    if (!currentSidepanelWorkflow) {
      currentSidepanelWorkflow = {
        id: 'wf_' + Date.now(),
        name: 'Recorded workflow',
        startUrl: currentTab?.url || 'https://www.naukri.com/',
        steps: [
          { id: 's1', type: 'open_url', name: 'Open page', value: currentTab?.url || 'https://www.naukri.com/', waitMs: 400, color: '#22c55e', badge: 'URL', target: currentTab?.url || '' }
        ],
      };
    }
  } catch (e) {}
}

async function saveSidepanelWorkflow(msg = 'Workflow updated!') {
  try {
    const data = await chrome.storage.local.get(['browserWorkflows']);
    const wfs = Array.isArray(data.browserWorkflows) ? data.browserWorkflows : [];
    const idx = wfs.findIndex(w => w.id === currentSidepanelWorkflow.id);
    if (idx >= 0) wfs[idx] = currentSidepanelWorkflow;
    else wfs.push(currentSidepanelWorkflow);
    await chrome.storage.local.set({ browserWorkflows: wfs });
    renderApp();
    const statusEl = document.getElementById('side-rec-status');
    if (statusEl) statusEl.textContent = msg;
  } catch (e) {}
}

function renderSidepanelStepsList() {
  const steps = currentSidepanelWorkflow?.steps || [];
  if (steps.length === 0) return '<div style="font-size:11px;color:var(--text-muted);text-align:center;padding:10px;">No steps recorded yet.</div>';

  return steps.map((step, idx) => {
    const badgeColor = step.color || (step.type === 'open_url' ? '#22c55e' : step.type === 'click' ? '#38bdf8' : step.type === 'ai_fallback' ? '#14b8a6' : '#a855f7');
    const badgeText = step.badge || (step.type ? String(step.type).toUpperCase().substring(0, 3) : 'ACT');
    return `
      <div class="rec-step-pill" style="border-left: 3px solid ${badgeColor};">
        <div style="display:flex;align-items:center;gap:6px;min-width:0;flex:1;">
          <span style="background:${badgeColor};color:#fff;font-size:9px;font-weight:800;padding:1px 5px;border-radius:3px;">${badgeText}</span>
          <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#fff;">${idx + 1}. ${escapeHtml(step.name || 'Step ' + (idx + 1))}</span>
        </div>
        <button class="subtle-button btn-del-side-step" data-idx="${idx}" title="Delete step" style="color:var(--accent-red);padding:2px 4px;font-size:11px;">✕</button>
      </div>
    `;
  }).join('');
}

function renderSidepanelRecorderView() {
  const steps = currentSidepanelWorkflow?.steps || [];
  let openLoopCount = 0;
  for (const s of steps) {
    if (s.type === 'loop_start') openLoopCount++;
    else if (s.type === 'loop_end') openLoopCount = Math.max(0, openLoopCount - 1);
  }
  const hasOpenLoop = openLoopCount > 0;

  return `
    <div class="sidepanel-recorder-view">
      <div class="rec-card">
        <div class="rec-status-banner" id="side-rec-status">
          ${hasOpenLoop ? '🔄 Inside Loop (Recording loop actions). Click "Continue to loop step 1" when done.' : '🟢 Connected to target tab. Pick an element or add a step.'}
        </div>
        
        <label class="rec-label">
          Workflow Name
          <input type="text" id="side-wf-name" class="rec-input" value="${escapeHtml(currentSidepanelWorkflow?.name || 'Recorded Workflow')}" />
        </label>

        <label class="rec-label">
          Step Name
          <input type="text" id="side-step-name" class="rec-input" placeholder="e.g. Click Apply or Type CTC" />
        </label>

        <label class="rec-label">
          Action Type
          <select id="side-action-select" class="rec-select">
            <option value="click" ${!hasOpenLoop ? 'selected' : ''}>Click element (auto detect)</option>
            <option value="fill">Type anything (fill text)</option>
            <option value="dropdown">Select dropdown option</option>
            <option value="checkbox">Toggle checkbox</option>
            <option value="multiple_choice">Select radio / choice</option>
            <option value="file_upload">Upload resume</option>
            <option value="ai_step">AI question &amp; answer</option>
            <option value="loop">Start loop from element</option>
            ${hasOpenLoop ? '<option value="continue_loop" selected>Continue to loop step 1</option>' : ''}
            <option value="loop_end">End loop when element appears</option>
          </select>
        </label>

        <div id="side-loop-group" style="display: none;">
          <label class="rec-label">
            Loop Count (optional)
            <input type="number" id="side-loop-count" class="rec-input" min="1" max="200" placeholder="e.g. 10 (optional - leave blank for all items)" />
          </label>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">
            Optional: How many times the loop should run. Leave blank to process all items found on the page.
          </div>
        </div>

        <div id="side-fill-group" style="display: none;">
          <label class="rec-label">
            Text to Type
            <input type="text" id="side-fill-val" class="rec-input" placeholder="Value or {{role}} or {{location}}" />
          </label>
        </div>

        <div id="side-resume-group" style="display: none;">
          <label class="rec-label">
            Select Resume PDF to Upload
            <select id="side-resume-select" class="rec-select">
              <option value="">Loading resumes...</option>
            </select>
          </label>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">
            Whichever PDF you select here will be attached during workflow execution.
          </div>
        </div>

        ${hasOpenLoop ? `
          <div style="margin-top: 6px;">
            <button class="rec-btn-orange" id="btn-side-continue-loop" style="background:#f59e0b;color:#000;font-weight:700;width:100%;padding:8px 12px;display:flex;align-items:center;justify-content:center;gap:6px;box-shadow:0 2px 8px rgba(245,158,11,0.35);">
              🔁 Continue to loop step 1
            </button>
          </div>
        ` : ''}

        <div class="rec-btn-grid" style="margin-top: 6px;">
          <button class="rec-btn-orange" id="btn-side-pick">🎯 Pick Element</button>
          <button class="rec-btn-orange" id="btn-side-add-step" style="background:#1f6feb;">+ Add Step</button>
        </div>

        <div class="rec-btn-grid">
          <button class="secondary-btn" id="btn-side-undo">↺ Undo Step &amp; back</button>
          <button class="rec-btn-green" id="btn-side-finish">💾 Finish &amp; Save</button>
        </div>
      </div>

      <!-- Recorded Steps List -->
      <div class="rec-card" style="flex:1;">
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; font-weight: 700; color: var(--text-muted);">
          <span>RECORDED STEPS (${(currentSidepanelWorkflow?.steps || []).length})</span>
          <span style="color: var(--accent-clay);">LIVE GRAPH</span>
        </div>
        <div id="side-steps-container" style="display: flex; flex-direction: column; gap: 4px; margin-top: 6px;">
          ${renderSidepanelStepsList()}
        </div>
      </div>
    </div>
  `;
}

function renderSidepanelChatView() {
  return `
    <!-- Quick Action Chips -->
    <div class="chips-container">
      <button class="chip" data-prompt="open indeed and search for AI ML Engineer jobs">💼 Open Indeed Jobs</button>
      <button class="chip" data-prompt="Upload my stored resume to the document file upload input on this page.">📄 Upload Resume</button>
      <button class="chip" data-prompt="Fill out the form on this page with my candidate profile data.">📝 Auto Fill</button>
      <button class="chip" data-prompt="Create an automated workflow to apply for this job step by step.">⚡ Record Workflow</button>
      <button class="chip" data-prompt="Summarize this page in 3 clear bullet points.">🔍 Summarize</button>
    </div>

    <!-- Chat Thread -->
    <main id="chat-thread" class="chat-thread"></main>

    <!-- Input Bar -->
    <footer class="app-footer">
      <div class="input-container">
        <textarea id="prompt-input" placeholder="Give an action command (e.g. 'open indeed' or 'upload resume')..." rows="1"></textarea>
        <div class="input-actions">
          <span class="agent-mode-tag" title="Agent stays locked to target tab in background">🎯 ${aiDecisionMode === 'autonomous' ? 'Autonomous Mode' : 'Ask Human'}</span>
          <button id="btn-clear-chat" class="subtle-button" title="Clear chat">🗑️</button>
          <button id="btn-send" class="send-button" title="Send message">
            <span class="send-icon">➤</span>
          </button>
        </div>
      </div>
    </footer>
  `;
}

function renderApp() {
  const root = document.getElementById('root');
  if (!root) return;

  root.innerHTML = `
    <div class="app-container">
      <!-- Top Navigation -->
      <header class="app-header">
        <div class="brand">
          <div class="logo-icon">✳</div>
          <div class="brand-text">
            <strong>Claude</strong>
            <span class="badge-byok">${aiDecisionMode === 'autonomous' ? 'AUTONOMOUS' : 'AGENT'}</span>
          </div>
        </div>
        <div class="header-actions">
          <button id="btn-stop-agent" class="stop-agent-btn" style="display: none;" title="Stop running agent">🛑 Stop</button>
          <select id="quick-model-select" class="quick-model-picker" title="Change active AI model"></select>
          <button id="btn-settings" class="icon-button" title="Settings">⚙️</button>
        </div>
      </header>

      <!-- Target Tab Bar (With Lock Status & Switcher) -->
      <div id="tab-info" class="tab-bar"></div>

      ${activeSidepanelView === 'recorder' ? renderSidepanelRecorderView() : renderSidepanelChatView()}

      <!-- Settings Modal -->
      <div id="settings-modal" class="modal-backdrop" style="display: none;">
        <div class="modal-card">
          <div class="modal-header">
            <h3>⚙️ Extension Settings & Autonomy</h3>
            <button id="btn-close-settings" class="close-btn">✕</button>
          </div>
          <div class="modal-body">
            <!-- Full Hub Launcher -->
            <div class="form-group" style="background: rgba(217, 119, 87, 0.1); border: 1px solid rgba(217, 119, 87, 0.3); border-radius: 8px; padding: 12px;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <strong style="font-size: 13px; color: #fff;">Claude Automation Studio</strong>
                  <div style="font-size: 11px; color: #94a3b8;">Workflow Studio • Profile • Prompts • Vault</div>
                </div>
                <button id="btn-open-options-page" class="primary-btn" style="padding: 6px 14px; font-size: 11px;">🚀 Open Full Studio</button>
              </div>
            </div>

            <!-- Decision Autonomy Setting -->
            <div class="form-group">
              <label>🤖 AI Uncertainty Decision Mode</label>
              <select id="modal-sel-autonomy" class="custom-select">
                <option value="autonomous" ${aiDecisionMode === 'autonomous' ? 'selected' : ''}>⚡ Make Own Decisions (Fully Autonomous)</option>
                <option value="ask_human" ${aiDecisionMode === 'ask_human' ? 'selected' : ''}>👤 Ask Human When Uncertain</option>
              </select>
            </div>

            <!-- Resume Status Preview -->
            <div class="form-group">
              <label>📄 Default Resume Status</label>
              <div id="side-resume-status" style="padding: 8px 12px; border-radius: 8px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); font-size: 12px; color: #34d399;">
                🔍 Checking stored resume...
              </div>
            </div>

            <div class="form-group">
              <label>Active AI Provider</label>
              <select id="sel-provider" class="custom-select">
                <option value="omniroute">OmniRoute / Claude Server (http://127.0.0.1:20128)</option>
                <option value="gemini">Google Gemini (Free AI Studio)</option>
                <option value="anthropic">Anthropic Claude (Direct API Key)</option>
              </select>
            </div>

            <!-- OmniRoute Section -->
            <div id="section-omniroute" class="provider-section">
              <div class="form-group">
                <label>OmniRoute Base URL</label>
                <input type="text" id="omniroute-url" placeholder="http://127.0.0.1:20128/v1" class="custom-input" />
              </div>
              <div class="form-group">
                <label>OmniRoute API Key</label>
                <div class="password-wrapper">
                  <input type="password" id="omniroute-key" placeholder="sk-..." class="custom-input" />
                  <button class="toggle-pass-btn" data-target="omniroute-key">👁</button>
                </div>
              </div>
              <div class="form-group">
                <div class="label-row">
                  <label>Select OmniRoute Model</label>
                  <button id="btn-refresh-models" class="link-btn">🔄 Auto-Fetch Models</button>
                </div>
                <select id="omniroute-model" class="custom-select"></select>
              </div>
            </div>

            <!-- Gemini Section -->
            <div id="section-gemini" class="provider-section" style="display: none;">
              <div class="form-group">
                <label>Google Gemini API Key</label>
                <div class="password-wrapper">
                  <input type="password" id="gemini-key" placeholder="AIzaSy..." class="custom-input" />
                  <button class="toggle-pass-btn" data-target="gemini-key">👁</button>
                </div>
              </div>
              <div class="form-group">
                <label>Gemini Model</label>
                <select id="gemini-model" class="custom-select">
                  ${GEMINI_MODELS.map(m => `<option value="${m.id}">${m.name}</option>`).join('')}
                </select>
              </div>
            </div>

            <!-- Anthropic Section -->
            <div id="section-anthropic" class="provider-section" style="display: none;">
              <div class="form-group">
                <label>Anthropic API Key</label>
                <div class="password-wrapper">
                  <input type="password" id="anthropic-key" placeholder="sk-ant-..." class="custom-input" />
                  <button class="toggle-pass-btn" data-target="anthropic-key">👁</button>
                </div>
              </div>
              <div class="form-group">
                <label>Model</label>
                <select id="anthropic-model" class="custom-select">
                  ${ANTHROPIC_MODELS.map(m => `<option value="${m.id}">${m.name}</option>`).join('')}
                </select>
              </div>
            </div>

            <div class="test-row">
              <button id="btn-test-connection" class="secondary-btn">⚡ Test Connection</button>
              <span id="test-result" class="test-result"></span>
            </div>
          </div>
          <div class="modal-footer">
            <button id="btn-save-settings" class="primary-btn">Save Settings</button>
          </div>
        </div>
      </div>
    </div>
  `;

  renderModelSelector();
  renderTabInfo();
  renderChatMessages();
}

function updateAgentControlsUI(running) {
  const stopBtn = document.getElementById('btn-stop-agent');
  const sendBtn = document.getElementById('btn-send');
  if (stopBtn) stopBtn.style.display = running ? 'block' : 'none';
  if (sendBtn) sendBtn.disabled = running;
}

function renderModelSelector() {
  const quickSelect = document.getElementById('quick-model-select');
  if (!quickSelect) return;

  const models = getAvailableModelsForCurrentProvider();
  let currentActiveModel = '';
  if (config.activeProvider === 'gemini') currentActiveModel = config.gemini.model;
  else if (config.activeProvider === 'omniroute') currentActiveModel = config.omniroute.model;
  else currentActiveModel = config.anthropic.model;

  quickSelect.innerHTML = models.map(m => `
    <option value="${m.id}" ${m.id === currentActiveModel ? 'selected' : ''}>${m.name}</option>
  `).join('');
}

async function renderTabInfo() {
  const tabEl = document.getElementById('tab-info');
  if (!tabEl) return;

  const tab = await getTargetTab();
  if (!tab) {
    tabEl.innerHTML = '<span class="tab-empty">No active tab selected</span>';
    return;
  }

  const isSecureFavicon = tab.favIconUrl && (tab.favIconUrl.startsWith('https://') || tab.favIconUrl.startsWith('data:'));
  const favIcon = isSecureFavicon ? `<img src="${escapeHtml(tab.favIconUrl)}" class="fav-icon" alt="" />` : '🌐';

  tabEl.innerHTML = `
    <div class="tab-pill" title="${escapeHtml(tab.url || '')}" style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
      <div style="display: flex; align-items: center; gap: 6px; overflow: hidden;">
        ${favIcon}
        <span class="tab-title" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 170px;">${escapeHtml(tab.title || 'New Tab')}</span>
      </div>
      <span class="badge ${isManuallyLocked ? 'badge-coral' : 'badge-sky'}" style="font-size: 9px; cursor: pointer;" id="btn-toggle-lock" title="Click to ${isManuallyLocked ? 'unlock and follow active tab' : 'lock AI to this tab'}">
        ${isManuallyLocked ? '🎯 LOCKED' : '👀 ACTIVE'}
      </span>
    </div>
  `;

  document.getElementById('btn-toggle-lock')?.addEventListener('click', async () => {
    isManuallyLocked = !isManuallyLocked;
    await updateActiveTabInfo();
    renderTabInfo();
  });
}

function addLiveStepToChat(stepNum, text) {
  chatMessages.push({
    role: 'assistant',
    isStep: true,
    content: text,
    timestamp: Date.now(),
  });
  renderChatMessages();
}

function updateLastStepInChat(text) {
  if (chatMessages.length > 0) {
    chatMessages[chatMessages.length - 1].content = text;
    renderChatMessages();
  }
}

function renderChatMessages() {
  const thread = document.getElementById('chat-thread');
  if (!thread) return;

  thread.innerHTML = chatMessages.map((m) => {
    const isUser = m.role === 'user';
    const isStep = m.isStep;
    return `
      <div class="chat-message ${isUser ? 'user-msg' : isStep ? 'step-msg' : 'assistant-msg'}">
        <div class="msg-avatar">${isUser ? '👤' : isStep ? '⚡' : '✳'}</div>
        <div class="msg-content">
          <div class="msg-bubble ${isStep ? 'step-bubble' : ''}">${formatMarkdown(m.content)}</div>
          <div class="msg-meta">${new Date(m.timestamp || Date.now()).toLocaleTimeString()}</div>
        </div>
      </div>
    `;
  }).join('');

  thread.scrollTop = thread.scrollHeight;
}

function formatMarkdown(text) {
  if (!text) return '';
  let escaped = escapeHtml(text);
  escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');
  escaped = escaped.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
  escaped = escaped.replace(/\n/g, '<br />');
  return escaped;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

// ─── Event Handling ──────────────────────────────────────────────────────────

function setupEventListeners() {

  const sendBtn = document.getElementById('btn-send');
  const promptInput = document.getElementById('prompt-input');
  const clearBtn = document.getElementById('btn-clear-chat');
  const settingsBtn = document.getElementById('btn-settings');
  const quickModelSelect = document.getElementById('quick-model-select');
  const closeSettingsBtn = document.getElementById('btn-close-settings');
  const saveSettingsBtn = document.getElementById('btn-save-settings');
  const providerSelect = document.getElementById('sel-provider');
  const refreshModelsBtn = document.getElementById('btn-refresh-models');
  const testConnBtn = document.getElementById('btn-test-connection');
  const stopAgentBtn = document.getElementById('btn-stop-agent');
  const openOptionsPageBtn = document.getElementById('btn-open-options-page');

  stopAgentBtn?.addEventListener('click', () => {
    isAgentRunning = false;
    updateAgentControlsUI(false);
    updateLastStepInChat('🛑 **Agent stopped by user.**');
  });


  // Sidepanel Recorder Controls
  const sideActSelect = document.getElementById('side-action-select');
  const sideFillGroup = document.getElementById('side-fill-group');
  const sideLoopGroup = document.getElementById('side-loop-group');
  const sideResumeGroup = document.getElementById('side-resume-group');
  const sideResumeSelect = document.getElementById('side-resume-select');

  const updateSideActionUI = (val) => {
    if (sideFillGroup) sideFillGroup.style.display = val === 'fill' ? 'block' : 'none';
    if (sideLoopGroup) sideLoopGroup.style.display = val === 'loop' ? 'block' : 'none';
    if (sideResumeGroup) sideResumeGroup.style.display = val === 'file_upload' ? 'block' : 'none';
  };

  sideActSelect?.addEventListener('change', (e) => {
    updateSideActionUI(e.target.value);
  });
  if (sideActSelect) updateSideActionUI(sideActSelect.value);

  // Populate resume list
  if (sideResumeSelect) {
    chrome.storage.local.get(['resumes', 'defaultResume', 'uploadedFiles']).then((resData) => {
      const allRes = [
        ...(Array.isArray(resData.resumes) ? resData.resumes : []),
        ...(Array.isArray(resData.uploadedFiles) ? resData.uploadedFiles : []),
      ];
      const defaultId = resData.defaultResume || allRes[0]?.id;
      if (allRes.length === 0) {
        sideResumeSelect.innerHTML = '<option value="res_default_pdf" data-filename="Ragesh_Resume.pdf">Ragesh_Resume.pdf (Default)</option>';
      } else {
        sideResumeSelect.innerHTML = allRes.map(r => {
          const fn = r.name || r.fileName || 'Resume.pdf';
          const isSel = r.id === (currentSidepanelWorkflow?.resumeId || defaultId);
          return `<option value="${r.id}" data-filename="${escapeHtml(fn)}" ${isSel ? 'selected' : ''}>${escapeHtml(r.label || fn)} (${escapeHtml(fn)})</option>`;
        }).join('');
      }
    }).catch(() => {});
  }

  // Pick Element on Page
  document.getElementById('btn-side-pick')?.addEventListener('click', async () => {
    const target = await getTargetTab();
    if (!target?.id) return alert('No active target tab found.');
    const act = document.getElementById('side-action-select')?.value || 'click';
    const statusEl = document.getElementById('side-rec-status');
    if (statusEl) statusEl.textContent = `🔍 Click an element on the website to record [${act}]...`;

    try {
      const [res] = await chrome.scripting.executeScript({
        target: { tabId: target.id },
        func: (actionType) => {
          return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(217,119,87,0.1);z-index:2147483640;cursor:crosshair;pointer-events:all;border:3px solid #d97757;box-sizing:border-box;';
            const badge = document.createElement('div');
            badge.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);background:#1f2937;color:#fff;padding:8px 16px;border-radius:8px;border:1px solid #d97757;font:700 13px sans-serif;z-index:2147483647;box-shadow:0 10px 25px rgba(0,0,0,0.5);';
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
              if (target.id && !target.id.includes('__') && !/\d{4,}/.test(target.id) && !/_[a-z0-9]{5,}/i.test(target.id)) selector = '#' + CSS.escape(target.id);
              else if (target.className && typeof target.className === 'string') {
                const c = target.className.split(/\s+/).filter(x => x && !x.includes(':'))[0];
                if (c) selector = `${target.tagName.toLowerCase()}.${CSS.escape(c)}`;
              }

              const label = (target.textContent || target.getAttribute('aria-label') || target.getAttribute('placeholder') || target.tagName).trim().substring(0, 50);

              // Detect repeated group if loop
              let repeated = null;
              if (actionType === 'loop') {
                const naukriCard = target.closest('div.cust-job-tuple, div.srp-jobtuple-wrapper, [class*="cust-job-tuple"], [class*="jobtuple"], [class*="sjw__tuple"]');
                if (naukriCard || location.hostname.includes('naukri.com')) {
                  const cards = [...document.querySelectorAll('div.cust-job-tuple, div.srp-jobtuple-wrapper, [class*="cust-job-tuple"], [class*="sjw__tuple"]')].filter(el => el.offsetHeight > 0);
                  repeated = {
                    collectionSelector: 'div.cust-job-tuple',
                    relativeSelector: 'a.title[href*="/job-listings-"], a.title, a[href*="/job-listings-"]',
                    count: Math.max(1, cards.length),
                  };
                } else {
                  const tag = target.tagName.toLowerCase();
                  const classes = [...target.classList].filter(c => !/[0-9]{4,}|active|selected/i.test(c));
                  if (classes.length > 0) {
                    const sel = `${tag}.${CSS.escape(classes[0])}`;
                    const matches = [...document.querySelectorAll(sel)].filter(el => el.offsetHeight > 0);
                    if (matches.length > 1) {
                      repeated = { collectionSelector: sel, count: matches.length };
                    }
                  }
                }
              }

              // Dispatch click so target element responds
              setTimeout(() => {
                try {
                  const clickTarget = target.closest('a, button, [role="button"]') || target;
                  clickTarget.click();
                } catch (_) {}
              }, 150);

              resolve({ selector, label, tagName: target.tagName, repeated });
            }

            document.addEventListener('click', clickHandler, true);
          });
        },
        args: [act],
      });

      if (res?.result && currentSidepanelWorkflow) {
        const picked = res.result;
        const fillVal = document.getElementById('side-fill-val')?.value.trim();

        if (act === 'loop') {
          const userLoopCount = parseInt(document.getElementById('side-loop-count')?.value, 10);
          const finalCount = (!isNaN(userLoopCount) && userLoopCount > 0) ? userLoopCount : (picked.repeated?.count || 10);
          const loopId = 'loop_' + Date.now();
          const listUrl = target.url || currentSidepanelWorkflow.startUrl;

          // Step 1: loop_start
          currentSidepanelWorkflow.steps.push({
            id: 's_' + Date.now() + '_start',
            type: 'loop_start',
            name: `Start loop (${finalCount} items)`,
            loopId,
            loopCount: finalCount,
            target: {
              collectionSelector: picked.repeated?.collectionSelector || picked.selector,
            },
            pageUrl: listUrl,
            returnUrl: listUrl,
            waitMs: 400,
            color: '#f59e0b',
            badge: 'LOOP',
            disabled: false,
            stopAfter: false,
            finalSubmit: false,
          });

          // Step 2: item click
          currentSidepanelWorkflow.steps.push({
            id: 's_' + (Date.now() + 1) + '_item',
            type: 'click',
            name: `Open loop item: ${picked.label || 'Job card'}`,
            loopId,
            useLoopIndex: true,
            target: {
              collectionSelector: picked.repeated?.collectionSelector || picked.selector,
              relativeSelector: picked.repeated?.relativeSelector || undefined,
              selector: picked.selector,
              useLoopIndex: true,
              collectionIndex: 0,
            },
            pageUrl: listUrl,
            waitMs: 800,
            onError: 'continue_loop',
            color: '#38bdf8',
            badge: 'CLK',
            disabled: false,
            stopAfter: false,
            finalSubmit: false,
          });

          await saveSidepanelWorkflow(`Started loop with ${finalCount} items! Recording inner steps.`);
          setupEventListeners();
          return;
        }

        if (act === 'file_upload') {
          const resumeSelect = document.getElementById('side-resume-select');
          const selectedOption = resumeSelect?.options[resumeSelect.selectedIndex];
          const resumeId = resumeSelect?.value || '';
          const resumeName = selectedOption?.getAttribute('data-filename') || selectedOption?.textContent?.trim() || 'Resume.pdf';
          const stepName = document.getElementById('side-step-name')?.value.trim() || `Upload resume: ${resumeName}`;

          currentSidepanelWorkflow.steps.push({
            id: 's_' + Date.now(),
            type: 'attach_resume',
            name: stepName,
            fileName: resumeName,
            resumeId: resumeId,
            value: resumeName,
            target: picked.selector || 'input[type="file"]',
            pageUrl: target.url,
            waitMs: 800,
            color: '#f97316',
            badge: 'FILE',
            disabled: false,
            stopAfter: false,
            finalSubmit: false,
          });

          if (resumeId) {
            currentSidepanelWorkflow.resumeId = resumeId;
          }

          await saveSidepanelWorkflow(`Recorded file upload: "${resumeName}" [${picked.selector}]`);
          setupEventListeners();
          return;
        }

        const stepName = document.getElementById('side-step-name')?.value.trim() || `${act === 'click' ? 'Click' : 'Interact with'} ${picked.label || picked.selector}`;

        currentSidepanelWorkflow.steps.push({
          id: 's_' + Date.now(),
          type: act === 'ai_step' ? 'ai_fallback' : act,
          name: stepName,
          value: fillVal || picked.label || '',
          target: picked.selector,
          pageUrl: target.url,
          waitMs: 400,
          color: act === 'open_url' ? '#22c55e' : act === 'click' ? '#38bdf8' : act === 'ai_step' ? '#14b8a6' : '#a855f7',
          badge: act.toUpperCase().substring(0, 3),
          disabled: false,
          stopAfter: false,
          finalSubmit: false,
        });

        await saveSidepanelWorkflow(`Recorded: "${stepName}" [${picked.selector}]`);
        setupEventListeners();
      }
    } catch (err) {
      if (statusEl) statusEl.textContent = 'Pick error: ' + err.message;
    }
  });

  // "Continue to loop step 1" Action
  const handleContinueLoop = async () => {
    if (!currentSidepanelWorkflow) return;
    const steps = currentSidepanelWorkflow.steps || [];
    const openLoop = [...steps].reverse().find(s => s.type === 'loop_start');
    const loopId = openLoop?.loopId || ('loop_' + Date.now());
    const returnUrl = openLoop?.returnUrl || openLoop?.pageUrl || currentSidepanelWorkflow.startUrl;

    currentSidepanelWorkflow.steps.push({
      id: 's_' + Date.now() + '_end',
      type: 'loop_end',
      name: 'Continue to loop step 1',
      loopId,
      target: {},
      waitMs: 400,
      color: '#f59e0b',
      badge: 'LEND',
      disabled: false,
      stopAfter: false,
      finalSubmit: false,
    });

    // Restore the browser tab to the list page / close redirected child tab
    try {
      const target = await getTargetTab();
      const stored = await chrome.storage.session.get(RECORDING_KEY).catch(() => ({}));
      const rec = stored?.[RECORDING_KEY];
      if (rec?.tabId && rec?.rootTabId && rec.tabId !== rec.rootTabId) {
        const childId = rec.tabId;
        rec.tabId = rec.rootTabId;
        await chrome.storage.session.set({ [RECORDING_KEY]: rec });
        await chrome.tabs.update(rec.rootTabId, { active: true }).catch(() => {});
        await chrome.tabs.remove(childId).catch(() => {});
      } else if (target?.id && returnUrl && target.url !== returnUrl) {
        await chrome.tabs.update(target.id, { url: returnUrl }).catch(() => {});
      }
    } catch (e) {
      console.warn('[Sidepanel] Continue loop navigation error:', e);
    }

    await saveSidepanelWorkflow('Loop closed! Added "Continue to loop step 1".');
    setupEventListeners();
  };

  document.getElementById('btn-side-continue-loop')?.addEventListener('click', handleContinueLoop);

  // Manual Add Step
  document.getElementById('btn-side-add-step')?.addEventListener('click', async () => {
    if (!currentSidepanelWorkflow) return;
    const act = document.getElementById('side-action-select')?.value || 'click';
    if (act === 'continue_loop') {
      return handleContinueLoop();
    }

    const name = document.getElementById('side-step-name')?.value.trim() || `Step ${currentSidepanelWorkflow.steps.length + 1}`;
    const fillVal = document.getElementById('side-fill-val')?.value.trim();
    const target = await getTargetTab().catch(() => null);

    if (act === 'file_upload') {
      const resumeSelect = document.getElementById('side-resume-select');
      const selectedOption = resumeSelect?.options[resumeSelect.selectedIndex];
      const resumeId = resumeSelect?.value || '';
      const resumeName = selectedOption?.getAttribute('data-filename') || selectedOption?.textContent?.trim() || 'Resume.pdf';
      const stepName = document.getElementById('side-step-name')?.value.trim() || `Upload resume: ${resumeName}`;

      currentSidepanelWorkflow.steps.push({
        id: 's_' + Date.now(),
        type: 'attach_resume',
        name: stepName,
        fileName: resumeName,
        resumeId: resumeId,
        value: resumeName,
        target: 'input[type="file"]',
        pageUrl: target?.url,
        waitMs: 800,
        color: '#f97316',
        badge: 'FILE',
        disabled: false,
        stopAfter: false,
        finalSubmit: false,
      });

      if (resumeId) {
        currentSidepanelWorkflow.resumeId = resumeId;
      }

      await saveSidepanelWorkflow(`Added step "${stepName}"!`);
      setupEventListeners();
      return;
    }

    currentSidepanelWorkflow.steps.push({
      id: 's_' + Date.now(),
      type: act === 'ai_step' ? 'ai_fallback' : act,
      name,
      value: fillVal || (act === 'ai_step' ? 'Auto answer screening questions' : ''),
      target: act === 'ai_step' ? 'Questionnaire container' : 'Target element',
      pageUrl: target?.url,
      waitMs: act === 'ai_step' ? 800 : 400,
      color: act === 'open_url' ? '#22c55e' : act === 'click' ? '#38bdf8' : act === 'ai_step' ? '#14b8a6' : '#a855f7',
      badge: act.toUpperCase().substring(0, 3),
      disabled: false,
      stopAfter: false,
      finalSubmit: false,
    });

    await saveSidepanelWorkflow(`Added step "${name}"!`);
    setupEventListeners();
  });

  // Undo Step & Back Navigation
  document.getElementById('btn-side-undo')?.addEventListener('click', async () => {
    if (!currentSidepanelWorkflow || currentSidepanelWorkflow.steps.length <= 1) return alert('Workflow must have at least one step.');
    const popped = currentSidepanelWorkflow.steps.pop();

    // Inform background session to keep in sync
    chrome.runtime.sendMessage({ action: 'WORKFLOW_RECORD_UNDO' }).catch(() => {});

    // Restore web page / close redirected child tab
    try {
      const target = await getTargetTab();
      const stored = await chrome.storage.session.get(RECORDING_KEY).catch(() => ({}));
      const rec = stored?.[RECORDING_KEY];
      if (rec?.tabId && rec?.rootTabId && rec.tabId !== rec.rootTabId) {
        const childToClose = rec.tabId;
        rec.tabId = rec.rootTabId;
        await chrome.storage.session.set({ [RECORDING_KEY]: rec });
        await chrome.tabs.update(rec.rootTabId, { active: true }).catch(() => {});
        await chrome.tabs.remove(childToClose).catch(() => {});
      } else if (target?.id) {
        const prevStep = currentSidepanelWorkflow.steps[currentSidepanelWorkflow.steps.length - 1];
        const restoreUrl = prevStep?.pageUrl || currentSidepanelWorkflow.startUrl;
        const shouldGoBack = Boolean(popped?.pageUrl && target.url && target.url !== popped.pageUrl) || Boolean(restoreUrl && target.url && target.url !== restoreUrl);
        if (shouldGoBack) {
          try {
            await chrome.tabs.goBack(target.id);
          } catch {
            if (restoreUrl) await chrome.tabs.update(target.id, { url: restoreUrl }).catch(() => {});
          }
        }
      }
    } catch (e) {
      console.warn('[Sidepanel] Undo back navigation error:', e);
    }

    await saveSidepanelWorkflow(`Undid: "${popped?.name || 'step'}"`);
    setupEventListeners();
  });

  // Finish & Save
  document.getElementById('btn-side-finish')?.addEventListener('click', async () => {
    if (currentSidepanelWorkflow) {
      const nameInput = document.getElementById('side-wf-name')?.value.trim();
      if (nameInput) currentSidepanelWorkflow.name = nameInput;
      await saveSidepanelWorkflow('Workflow saved to Studio!');
    }
  });

  // Delete Individual Step
  document.querySelectorAll('.btn-del-side-step').forEach(btn => {
    btn.addEventListener('click', async () => {
      const idx = parseInt(btn.getAttribute('data-idx'), 10);
      if (!currentSidepanelWorkflow || currentSidepanelWorkflow.steps.length <= 1) return alert('Workflow must have at least one step.');
      currentSidepanelWorkflow.steps.splice(idx, 1);
      await saveSidepanelWorkflow('Step deleted.');
      setupEventListeners();
    });
  });

  sendBtn?.addEventListener('click', handleUserSubmit);
  promptInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleUserSubmit();
    }
  });

  promptInput?.addEventListener('input', () => {
    promptInput.style.height = 'auto';
    promptInput.style.height = Math.min(promptInput.scrollHeight, 120) + 'px';
  });

  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        if (promptInput) promptInput.value = prompt;
        handleUserSubmit();
      }
    });
  });

  clearBtn?.addEventListener('click', async () => {
    if (confirm('Clear all conversation messages?')) {
      chatMessages = [{
        role: 'assistant',
        content: '👋 Chat cleared. How can I assist you?',
        timestamp: Date.now(),
      }];
      await saveChatHistory();
      renderChatMessages();
    }
  });

  quickModelSelect?.addEventListener('change', async (e) => {
    const selectedModel = e.target.value;
    if (config.activeProvider === 'gemini') config.gemini.model = selectedModel;
    else if (config.activeProvider === 'omniroute') config.omniroute.model = selectedModel;
    else config.anthropic.model = selectedModel;
    await saveConfig();
  });

  openOptionsPageBtn?.addEventListener('click', () => {
    if (chrome.runtime.openOptionsPage) {
      chrome.runtime.openOptionsPage();
    } else {
      chrome.tabs.create({ url: chrome.runtime.getURL('options.html') });
    }
  });

  const openSettings = async () => {
    populateSettingsInputs();
    const modal = document.getElementById('settings-modal');
    if (modal) modal.style.display = 'flex';

    // Check stored resume
    const resEl = document.getElementById('side-resume-status');
    if (resEl) {
      try {
        const storageData = await chrome.storage.local.get(['resumes', 'defaultResume']);
        const allRes = storageData.resumes || [];
        const def = allRes.find(r => r.id === storageData.defaultResume) || allRes[0];
        if (def) {
          resEl.innerHTML = `✅ <strong>${escapeHtml(def.name)}</strong> (${(def.size ? (def.size / 1024).toFixed(1) + ' KB' : 'PDF')}) ready for silent upload.`;
          resEl.style.borderColor = 'rgba(16, 185, 129, 0.4)';
          resEl.style.color = '#34d399';
        } else {
          resEl.innerHTML = `⚠️ No resume uploaded. Click "Open Full Studio" to add your resume.`;
          resEl.style.borderColor = 'rgba(245, 158, 11, 0.4)';
          resEl.style.color = '#fbbf24';
        }
      } catch (e) {
        resEl.textContent = '📄 Resume ready in extension storage.';
      }
    }
  };
  settingsBtn?.addEventListener('click', openSettings);

  closeSettingsBtn?.addEventListener('click', () => {
    const modal = document.getElementById('settings-modal');
    if (modal) modal.style.display = 'none';
  });

  providerSelect?.addEventListener('change', (e) => {
    updateModalProviderSections(e.target.value);
  });

  refreshModelsBtn?.addEventListener('click', async () => {
    const testRes = document.getElementById('test-result');
    if (testRes) {
      testRes.textContent = '⏳ Fetching OmniRoute models...';
      testRes.style.color = '#38bdf8';
    }
    try {
      collectSettingsFromModal();
      const models = await fetchOmniRouteModels(false);
      populateSettingsInputs();
      if (testRes) {
        testRes.textContent = `✅ Fetched ${models.length} models!`;
        testRes.style.color = '#4ade80';
      }
    } catch (err) {
      if (testRes) {
        testRes.textContent = `❌ ${err.message}`;
        testRes.style.color = '#f87171';
      }
    }
  });

  document.querySelectorAll('.toggle-pass-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (input) {
        input.type = input.type === 'password' ? 'text' : 'password';
        btn.textContent = input.type === 'password' ? '👁' : '🔒';
      }
    });
  });

  testConnBtn?.addEventListener('click', handleTestConnection);

  saveSettingsBtn?.addEventListener('click', async () => {
    collectSettingsFromModal();
    const selAutonomy = document.getElementById('modal-sel-autonomy')?.value || 'autonomous';
    aiDecisionMode = selAutonomy;
    await chrome.storage.local.set({ aiDecisionMode });
    await saveConfig();
    renderModelSelector();
    const modal = document.getElementById('settings-modal');
    if (modal) modal.style.display = 'none';
  });
}

function updateModalProviderSections(selected) {
  const geminiSec = document.getElementById('section-gemini');
  const omniSec = document.getElementById('section-omniroute');
  const anthropicSec = document.getElementById('section-anthropic');

  if (geminiSec) geminiSec.style.display = selected === 'gemini' ? 'block' : 'none';
  if (omniSec) omniSec.style.display = selected === 'omniroute' ? 'block' : 'none';
  if (anthropicSec) anthropicSec.style.display = selected === 'anthropic' ? 'block' : 'none';
}

function populateSettingsInputs() {
  const providerSelect = document.getElementById('sel-provider');
  const geminiKey = document.getElementById('gemini-key');
  const geminiModel = document.getElementById('gemini-model');
  const omniUrl = document.getElementById('omniroute-url');
  const omniKey = document.getElementById('omniroute-key');
  const omniModel = document.getElementById('omniroute-model');
  const anthropicKey = document.getElementById('anthropic-key');
  const anthropicModel = document.getElementById('anthropic-model');
  const autonomySelect = document.getElementById('modal-sel-autonomy');

  if (providerSelect) providerSelect.value = config.activeProvider;
  if (geminiKey) geminiKey.value = config.gemini.apiKey;
  if (geminiModel) geminiModel.value = config.gemini.model;
  if (omniUrl) omniUrl.value = config.omniroute.baseUrl;
  if (omniKey) omniKey.value = config.omniroute.apiKey;
  if (autonomySelect) autonomySelect.value = aiDecisionMode;

  if (omniModel) {
    const models = getAvailableModelsForCurrentProvider();
    omniModel.innerHTML = models.map(m => `
      <option value="${m.id}" ${m.id === config.omniroute.model ? 'selected' : ''}>${m.name}</option>
    `).join('');
  }

  if (anthropicKey) anthropicKey.value = config.anthropic.apiKey;
  if (anthropicModel) anthropicModel.value = config.anthropic.model;

  updateModalProviderSections(config.activeProvider);
}

function collectSettingsFromModal() {
  const providerSelect = document.getElementById('sel-provider');
  const geminiKey = document.getElementById('gemini-key');
  const geminiModel = document.getElementById('gemini-model');
  const omniUrl = document.getElementById('omniroute-url');
  const omniKey = document.getElementById('omniroute-key');
  const omniModel = document.getElementById('omniroute-model');
  const anthropicKey = document.getElementById('anthropic-key');
  const anthropicModel = document.getElementById('anthropic-model');

  if (providerSelect) config.activeProvider = providerSelect.value;
  if (geminiKey) config.gemini.apiKey = geminiKey.value.trim();
  if (geminiModel) config.gemini.model = geminiModel.value;
  if (omniUrl) config.omniroute.baseUrl = omniUrl.value.trim();
  if (omniKey) config.omniroute.apiKey = omniKey.value.trim();
  if (omniModel) config.omniroute.model = omniModel.value;
  if (anthropicKey) config.anthropic.apiKey = anthropicKey.value.trim();
  if (anthropicModel) config.anthropic.model = anthropicModel.value;
}

async function handleTestConnection() {
  const testRes = document.getElementById('test-result');
  if (!testRes) return;

  collectSettingsFromModal();
  testRes.textContent = '⏳ Testing connection...';
  testRes.style.color = '#38bdf8';

  const startTime = Date.now();
  try {
    const response = await callActiveModelRaw('Respond with pong', [{ role: 'user', content: 'ping' }]);
    const latency = Date.now() - startTime;
    testRes.textContent = `✅ Connected (${latency}ms)`;
    testRes.style.color = '#4ade80';
  } catch (err) {
    testRes.textContent = `❌ ${err.message}`;
    testRes.style.color = '#f87171';
  }
}

async function handleUserSubmit() {
  const promptInput = document.getElementById('prompt-input');
  if (!promptInput || isAgentRunning) return;

  const text = promptInput.value.trim();
  if (!text) return;

  // Crucial: Always refresh to user's currently viewed active tab upon submission
  if (!isManuallyLocked) {
    try {
      const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (activeTab?.id) {
        currentTab = activeTab;
        lockedTabId = activeTab.id;
      }
    } catch (e) {}
    renderTabInfo();
  }

  promptInput.value = '';
  promptInput.style.height = 'auto';

  chatMessages.push({
    role: 'user',
    content: text,
    timestamp: Date.now(),
  });
  renderChatMessages();

  await runAutonomousAgent(text);
}
