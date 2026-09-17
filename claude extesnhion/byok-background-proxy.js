/**
 * Background Service Worker Proxy for BYOK Requests & Workflow Manager
 * Handles local API proxying, Workflow Recording sessions, Element Tracking, and Content Script orchestration.
 */

const RECORDING_KEY = 'workflowRecording';
const WORKFLOWS_KEY = 'browserWorkflows';

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // 1. BYOK Proxy Fetch
  if (message?.action === 'BYOK_PROXY_FETCH') {
    (async () => {
      try {
        const { url, options } = message;
        const res = await fetch(url, options || {});
        const text = await res.text();
        const headers = {};
        res.headers.forEach((value, key) => {
          headers[key] = value;
        });

        sendResponse({
          ok: res.ok,
          status: res.status,
          statusText: res.statusText,
          headers,
          text,
        });
      } catch (err) {
        sendResponse({
          ok: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    })();
    return true; // Keep message channel open for async response
  }

  // 2. Start Workflow Recording Session
  if (message?.action === 'WORKFLOW_RECORD_START') {
    (async () => {
      try {
        let tabId = typeof message.tabId === 'number' ? message.tabId : null;
        if (!tabId) {
          const candidateTabs = await chrome.tabs.query({ currentWindow: true, active: true });
          tabId = candidateTabs[0]?.id || null;
        }
        if (!tabId) {
          const allTabs = await chrome.tabs.query({ currentWindow: true });
          const webTabs = allTabs.filter(t => /^https?:/i.test(t.url || ''));
          tabId = webTabs[0]?.id || null;
        }
        if (!tabId) {
          sendResponse({ success: false, error: 'No active web tab found.' });
          return;
        }

        const tab = await chrome.tabs.get(tabId);
        const startUrl = tab.url || message.startUrl || 'https://www.naukri.com/';
        const workflowName = String(message.name || message.workflowName || 'Recorded workflow');

        let urlObj;
        try {
          urlObj = new URL(startUrl.startsWith('http') ? startUrl : 'https://' + startUrl);
        } catch {
          urlObj = new URL('https://www.naukri.com/');
        }

        const recording = {
          tabId,
          rootTabId: tabId,
          manual: true,
          loopStack: [],
          workflow: {
            id: message.workflowId || ('wf_' + Date.now()),
            name: workflowName,
            origin: urlObj.origin,
            startUrl: urlObj.href,
            variables: { role: '', location: '' },
            steps: [
              {
                id: 's1',
                type: 'open_url',
                target: {},
                name: `Open ${urlObj.hostname}`,
                value: urlObj.href,
                waitMs: 400,
                color: '#22c55e',
                badge: 'URL',
              }
            ],
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        };

        await chrome.storage.session.set({ [RECORDING_KEY]: recording });

        // Sync with browserWorkflows in chrome.storage.local
        const stored = await chrome.storage.local.get(WORKFLOWS_KEY);
        let list = Array.isArray(stored[WORKFLOWS_KEY]) ? stored[WORKFLOWS_KEY] : [];
        const existingIdx = list.findIndex(w => w.id === recording.workflow.id);
        if (existingIdx >= 0) {
          list[existingIdx] = recording.workflow;
        } else {
          list.push(recording.workflow);
        }
        await chrome.storage.local.set({ [WORKFLOWS_KEY]: list });

        // Notify content.js to mount floating recorder HUD and activate element hover overlay
        const startMsg = {
          action: 'WORKFLOW_RECORD_START',
          manual: true,
          stepCount: recording.workflow.steps.length,
          loopDepth: 0,
          workflowName: recording.workflow.name,
        };

        try {
          await chrome.tabs.sendMessage(tabId, startMsg);
        } catch (e) {
          // If content script was not yet loaded on that tab, inject it
          try {
            await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] });
            await chrome.tabs.sendMessage(tabId, startMsg);
          } catch (err) {}
        }

        sendResponse({ success: true, recording: true, workflowId: recording.workflow.id, tabId });
      } catch (err) {
        sendResponse({ success: false, error: err instanceof Error ? err.message : String(err) });
      }
    })();
    return true;
  }

  // 3. Query Active Workflow Recording State
  if (message?.action === 'WORKFLOW_RECORD_STATE') {
    (async () => {
      try {
        const stored = await chrome.storage.session.get(RECORDING_KEY);
        const recording = stored[RECORDING_KEY];
        if (!recording) {
          sendResponse({ success: true, active: false });
          return;
        }

        const senderTabId = sender.tab?.id;
        if (senderTabId && (recording.tabId === senderTabId || recording.rootTabId === senderTabId)) {
          sendResponse({
            success: true,
            active: true,
            manual: true,
            stepCount: recording.workflow.steps.length,
            loopDepth: recording.loopStack.length,
            workflowName: recording.workflow.name,
          });
          return;
        }

        // Auto-transfer if previous tab is closed or navigated
        if (senderTabId) {
          const currentTarget = await chrome.tabs.get(recording.tabId).catch(() => null);
          const currentValid = currentTarget?.url && /^https?:/i.test(currentTarget.url);
          if (!currentValid) {
            recording.tabId = senderTabId;
            await chrome.storage.session.set({ [RECORDING_KEY]: recording });
            sendResponse({
              success: true,
              active: true,
              manual: true,
              stepCount: recording.workflow.steps.length,
              loopDepth: recording.loopStack.length,
              workflowName: recording.workflow.name,
            });
            return;
          }
        }

        sendResponse({
          success: true,
          active: true,
          manual: true,
          stepCount: recording.workflow.steps.length,
          loopDepth: recording.loopStack.length,
          workflowName: recording.workflow.name,
        });
      } catch (e) {
        sendResponse({ success: true, active: false });
      }
    })();
    return true;
  }

  // 4. Capture & Record Interactive Step
  if (message?.action === 'WORKFLOW_RECORD_EVENT') {
    (async () => {
      try {
        const stored = await chrome.storage.session.get(RECORDING_KEY);
        const recording = stored[RECORDING_KEY];
        if (!recording) {
          sendResponse({ success: false, error: 'No active recording session.' });
          return;
        }

        const step = message.step;
        if (!step) {
          sendResponse({ success: false, error: 'No step data provided.' });
          return;
        }

        step.id = step.id || ('s_' + Date.now());
        if (sender.tab?.url && !step.pageUrl) {
          step.pageUrl = sender.tab.url;
        }

        // Give step proper color badge for graph canvas
        if (!step.badge) {
          const badges = {
            click: 'CLK',
            fill: 'TYP',
            select_option: 'SEL',
            checkbox: 'CHK',
            multiple_choice: 'RAD',
            attach_resume: 'FILE',
            ai_fallback: 'AI',
            loop_start: 'LOOP',
            loop_end: 'LEND',
            stop: 'END',
          };
          step.badge = badges[step.type] || 'ACT';
        }

        recording.workflow.steps.push(step);
        recording.workflow.updatedAt = Date.now();
        await chrome.storage.session.set({ [RECORDING_KEY]: recording });

        // Sync with browserWorkflows in chrome.storage.local
        const wfStored = await chrome.storage.local.get(WORKFLOWS_KEY);
        let list = Array.isArray(wfStored[WORKFLOWS_KEY]) ? wfStored[WORKFLOWS_KEY] : [];
        const idx = list.findIndex(w => w.id === recording.workflow.id);
        if (idx >= 0) {
          list[idx] = recording.workflow;
        } else {
          list.push(recording.workflow);
        }
        await chrome.storage.local.set({ [WORKFLOWS_KEY]: list });

        sendResponse({ success: true, recorded: true, stepIndex: recording.workflow.steps.length - 1 });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  // 5. Undo Workflow Step
  if (message?.action === 'WORKFLOW_RECORD_UNDO') {
    (async () => {
      try {
        const stored = await chrome.storage.session.get(RECORDING_KEY);
        const recording = stored[RECORDING_KEY];
        if (!recording || recording.workflow.steps.length <= 1) {
          sendResponse({ success: false, error: 'Initial step cannot be undone.' });
          return;
        }

        const removed = recording.workflow.steps.pop();
        recording.workflow.updatedAt = Date.now();
        await chrome.storage.session.set({ [RECORDING_KEY]: recording });

        const wfStored = await chrome.storage.local.get(WORKFLOWS_KEY);
        let list = Array.isArray(wfStored[WORKFLOWS_KEY]) ? wfStored[WORKFLOWS_KEY] : [];
        const idx = list.findIndex(w => w.id === recording.workflow.id);
        if (idx >= 0) {
          list[idx] = recording.workflow;
          await chrome.storage.local.set({ [WORKFLOWS_KEY]: list });
        }

        sendResponse({
          success: true,
          undone: true,
          removedStep: removed?.name || 'Step',
          stepCount: recording.workflow.steps.length,
          loopDepth: recording.loopStack.length,
        });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  // 6. Finish and Save Workflow Recording
  if (message?.action === 'WORKFLOW_RECORD_STOP') {
    (async () => {
      try {
        const stored = await chrome.storage.session.get(RECORDING_KEY);
        const recording = stored[RECORDING_KEY];
        if (!recording) {
          sendResponse({ success: true, saved: false });
          return;
        }

        await chrome.storage.session.remove(RECORDING_KEY);

        // Tell active tabs to remove floating recorder panel and hover tracker
        if (recording.tabId) {
          chrome.tabs.sendMessage(recording.tabId, { action: 'WORKFLOW_RECORD_STOP' }).catch(() => {});
        }

        recording.workflow.updatedAt = Date.now();
        const wfStored = await chrome.storage.local.get(WORKFLOWS_KEY);
        let list = Array.isArray(wfStored[WORKFLOWS_KEY]) ? wfStored[WORKFLOWS_KEY] : [];
        const idx = list.findIndex(w => w.id === recording.workflow.id);
        if (idx >= 0) {
          list[idx] = recording.workflow;
        } else {
          list.push(recording.workflow);
        }
        await chrome.storage.local.set({ [WORKFLOWS_KEY]: list });

        sendResponse({ success: true, saved: true, workflow: recording.workflow });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  // 7. Fullscreen Toggle -> Open Dedicated Recorder Tab
  if (message?.action === 'OPEN_RECORDER_TAB') {
    chrome.tabs.create({ url: chrome.runtime.getURL('recorder.html') });
    sendResponse({ success: true });
    return true;
  }

  // 8. Custom Answers for Autofill
  if (message?.action === 'GET_AUTOFILL_ANSWERS') {
    (async () => {
      try {
        const data = await chrome.storage.local.get(['customAnswers', 'userProfile']);
        const answers = data.customAnswers || [];
        sendResponse({
          success: true,
          customAnswers: answers.map(a => ({ fieldSignature: a.question, value: a.answer, isSecret: false })),
          matchableAnswers: answers.map(a => ({ label: a.question, value: a.answer })),
        });
      } catch (e) {
        sendResponse({ success: true, customAnswers: [], matchableAnswers: [] });
      }
    })();
    return true;
  }

  // 9. Cross-Tab Element Picker Mode
  if (message?.action === 'START_CROSS_TAB_PICKER') {
    (async () => {
      try {
        const activeTabs = await chrome.tabs.query({ active: true, currentWindow: true });
        const allTabs = await chrome.tabs.query({ currentWindow: true });
        const targetTab = allTabs.find(t => t.id !== activeTabs[0]?.id && /^https?:/i.test(t.url || '')) || activeTabs[0];
        if (!targetTab?.id) {
          sendResponse({ success: false, error: 'No website tab available to pick from.' });
          return;
        }

        try {
          await chrome.tabs.sendMessage(targetTab.id, { action: 'ENTER_PICKER_MODE' });
        } catch {
          await chrome.scripting.executeScript({ target: { tabId: targetTab.id }, files: ['content.js'] });
          await chrome.tabs.sendMessage(targetTab.id, { action: 'ENTER_PICKER_MODE' });
        }

        sendResponse({ success: true, targetTabId: targetTab.id, targetTitle: targetTab.title });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (message?.action === 'CANCEL_PICKER') {
    if (message.targetTabId) {
      chrome.tabs.sendMessage(message.targetTabId, { action: 'EXIT_PICKER_MODE' }).catch(() => {});
    }
    sendResponse({ success: true });
    return true;
  }

  if (message?.action === 'PICKER_RESULT') {
    chrome.runtime.sendMessage({ action: 'PICKER_RESULT_FORWARD', ...message }).catch(() => {});
    sendResponse({ success: true });
    return true;
  }

  if (message?.action === 'PICKER_CANCELLED') {
    chrome.runtime.sendMessage({ action: 'PICKER_CANCELLED_FORWARD' }).catch(() => {});
    sendResponse({ success: true });
    return true;
  }
});
