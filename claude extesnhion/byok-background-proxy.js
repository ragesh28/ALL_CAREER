/**
 * Background Service Worker Proxy for BYOK Requests & Workflow Manager
 * Handles local API proxying, Workflow Recording sessions, Element Tracking, and Content Script orchestration.
 */

const RECORDING_KEY = 'workflowRecording';
const WORKFLOWS_KEY = 'browserWorkflows';

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

        // Sync with browserWorkflows in chrome.storage.local
        const stored = await chrome.storage.local.get(WORKFLOWS_KEY);
        let list = Array.isArray(stored[WORKFLOWS_KEY]) ? stored[WORKFLOWS_KEY] : [];

        let workflowName = String(message.name || message.workflowName || '').trim();
        if (!workflowName || workflowName.toLowerCase() === 'recorded workflow') {
          workflowName = getNextDefaultWorkflowName(list);
        }

        let urlObj;
        try {
          urlObj = new URL(startUrl.startsWith('http') ? startUrl : 'https://' + startUrl);
        } catch {
          urlObj = new URL('https://www.naukri.com/');
        }

        const recording = {
          tabId,
          rootTabId: tabId,
          childTabIds: [],
          creatorTabId: sender.tab?.id,
          manual: true,
          paused: false,
          loopStack: [],
          lastClickAt: Date.now(),
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

        list = list.filter(w => w.id !== recording.workflow.id);
        list.unshift(recording.workflow);
        await chrome.storage.local.set({ [WORKFLOWS_KEY]: list, workflowRecordingActive: true, activeSidepanelView: 'recorder' });

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

        // Configure dedicated recorder side panel for this tab and open it
        try {
          if (chrome.sidePanel && typeof chrome.sidePanel.setOptions === 'function') {
            await chrome.sidePanel.setOptions({
              tabId: tabId,
              path: `recorder.html?tabId=${tabId}&wf=${recording.workflow.id}`,
              enabled: true,
            });
          }
          if (chrome.sidePanel && typeof chrome.sidePanel.open === 'function') {
            await chrome.sidePanel.open({ tabId });
          }
        } catch (err) {
          console.warn('[BYOK] Could not open recorder sidePanel:', err);
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
        // Verify that at least one recorded target tab still exists!
        const currentTarget = await chrome.tabs.get(recording.tabId).catch(() => null);
        const rootTarget = await chrome.tabs.get(recording.rootTabId).catch(() => null);
        if (!currentTarget && !rootTarget) {
          // Both target and root tabs were closed! Clean up recording immediately
          await chrome.storage.session.remove(RECORDING_KEY);
          await chrome.storage.local.remove('recordingPaused');
          await chrome.storage.local.set({ workflowRecordingActive: false, recordingPaused: false });
          sendResponse({ success: true, active: false });
          return;
        }

        // Respond active: true for the recorded target tab, root tab, or any child tab created during recording!
        const isRecordedTab = senderTabId && (
          recording.tabId === senderTabId ||
          recording.rootTabId === senderTabId ||
          (Array.isArray(recording.childTabIds) && recording.childTabIds.includes(senderTabId))
        );

        if (isRecordedTab) {
          sendResponse({
            success: true,
            active: true,
            manual: true,
            stepCount: recording.workflow.steps.length,
            loopDepth: recording.loopStack ? recording.loopStack.length : 0,
            workflowName: recording.workflow.name,
            paused: recording.paused === true,
          });
          return;
        }

        // Any other tab (including newly opened tabs) is NOT recording!
        sendResponse({
          success: true,
          active: false,
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

const DEFAULT_FALLBACK_PDF_BASE64 = 'JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA0NQo+PgpzdHJlYW0KQlQgL0YxIDEyIFRmIDcyIDcwOCBUZCAoUmVzdW1lIERvY3VtZW50IC0gQXV0b0ZpbGwpIFRqIEVUCmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDUKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDE4IDAwMDAwIG4gCjAwMDAwMDAwNjggMDAwMDAgbiAKMDAwMDAwMDEyNSAwMDAwMCBuIAowMDAwMDAwMjE4IDAwMDAwIG4gCnRyYWlsZXIKPDwKL1NpemUgNQovUm9vdCAxIDAgUgo+PgpzdGFydHhyZWYKMzEzCiUlRU9G';

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
            file_upload: 'FILE',
            ai_fallback: 'AI',
            loop_start: 'LOOP',
            loop_end: 'LEND',
            stop: 'END',
          };
          step.badge = badges[step.type] || 'ACT';
        }

        if (step.type === 'file_upload' || step.type === 'attach_resume') {
          step.type = 'attach_resume';
          step.badge = 'FILE';
          step.color = '#f97316';
          if (step.fileName && !step.value) step.value = step.fileName;
          if (step.fileName && (!step.name || step.name === 'Upload resume')) {
            step.name = `Upload resume: ${step.fileName}`;
          }
          if (step.resumeId) {
            recording.workflow.resumeId = step.resumeId;
          }
        }

        // Manage loop stack
        if (step.type === 'loop_start') {
          if (!Array.isArray(recording.loopStack)) recording.loopStack = [];
          const tab = sender.tab?.id ? await chrome.tabs.get(sender.tab.id).catch(() => null) : null;
          const loopId = step.loopId || ('loop_' + Date.now());
          step.loopId = loopId;
          recording.loopStack.push({
            loopId,
            tabId: sender.tab?.id || recording.tabId,
            url: tab?.url || step.returnUrl || step.pageUrl || recording.workflow.startUrl,
          });
        }
        if (step.type === 'loop_end') {
          if (!Array.isArray(recording.loopStack)) recording.loopStack = [];
          const frame = recording.loopStack[recording.loopStack.length - 1];
          if (frame) {
            step.loopId = frame.loopId;
          }
        }

        if (step.type === 'click') {
          recording.lastClickAt = Date.now();
        }
        if (sender.tab?.id) {
          recording.tabId = sender.tab.id;
        }

        recording.workflow.steps.push(step);
        recording.workflow.updatedAt = Date.now();
        await chrome.storage.session.set({ [RECORDING_KEY]: recording });

        // If loop_end was recorded, restore the list tab and close child tab if applicable
        if (step.type === 'loop_end' && Array.isArray(recording.loopStack) && recording.loopStack.length > 0) {
          const frame = recording.loopStack.pop();
          if (frame) {
            const currentTabId = sender.tab?.id || recording.tabId;
            if (currentTabId && frame.tabId && currentTabId !== frame.tabId) {
              await chrome.tabs.sendMessage(currentTabId, { action: 'WORKFLOW_RECORD_STOP' }).catch(() => {});
              recording.tabId = frame.tabId;
              await chrome.storage.session.set({ [RECORDING_KEY]: recording });
              const listTab = await chrome.tabs.get(frame.tabId).catch(() => null);
              const restoreUrl = listTab?.url !== frame.url ? frame.url : undefined;
              await chrome.tabs.update(frame.tabId, { active: true, ...(restoreUrl ? { url: restoreUrl } : {}) }).catch(() => {});
              await chrome.tabs.remove(currentTabId).catch(() => {});
              await chrome.tabs.sendMessage(frame.tabId, {
                action: 'WORKFLOW_RECORD_START',
                manual: true,
                stepCount: recording.workflow.steps.length,
                loopDepth: recording.loopStack.length,
                workflowName: recording.workflow.name,
                paused: recording.paused === true,
              }).catch(() => {});
            }
          }
        }

        // Sync with browserWorkflows in chrome.storage.local
        const wfStored = await chrome.storage.local.get(WORKFLOWS_KEY);
        let list = Array.isArray(wfStored[WORKFLOWS_KEY]) ? wfStored[WORKFLOWS_KEY] : [];
        list = list.filter(w => w.id !== recording.workflow.id);
        list.unshift(recording.workflow);
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
        if (!Array.isArray(recording.loopStack)) recording.loopStack = [];
        const activeLoop = recording.loopStack[recording.loopStack.length - 1];
        if (removed.type === 'loop_start' && activeLoop?.loopId === removed.loopId) {
          recording.loopStack.pop();
        }
        if (removed.type === 'loop_end' && removed.loopId) {
          const start = [...recording.workflow.steps].reverse().find(s => s.type === 'loop_start' && s.loopId === removed.loopId);
          if (start) {
            recording.loopStack.push({
              loopId: removed.loopId,
              tabId: recording.tabId,
              url: start.returnUrl || start.pageUrl || recording.workflow.startUrl,
            });
          }
        }

        recording.lastClickAt = undefined;
        recording.workflow.updatedAt = Date.now();
        await chrome.storage.session.set({ [RECORDING_KEY]: recording });

        // Check if there was a redirected child tab opened during recording
        let activeTabId = recording.tabId;
        const rootTabId = recording.rootTabId || activeTabId;
        if (activeTabId && rootTabId && activeTabId !== rootTabId) {
          console.log('[BYOK] Undo closing redirected child tab:', activeTabId, 'returning to root:', rootTabId);
          const childToClose = activeTabId;
          recording.tabId = rootTabId;
          activeTabId = rootTabId;
          if (Array.isArray(recording.childTabIds)) {
            recording.childTabIds = recording.childTabIds.filter(id => id !== childToClose);
          }
          await chrome.storage.session.set({ [RECORDING_KEY]: recording });
          await chrome.tabs.update(rootTabId, { active: true }).catch(() => {});
          await chrome.tabs.remove(childToClose).catch(() => {});
        } else if (activeTabId) {
          // Check if page navigated or changed URL on the same tab
          const tab = await chrome.tabs.get(activeTabId).catch(() => null);
          const prevStep = recording.workflow.steps[recording.workflow.steps.length - 1];
          const targetUrl = prevStep?.pageUrl || recording.workflow.startUrl;
          const shouldNavigateBack = Boolean(removed.pageUrl && tab?.url && tab.url !== removed.pageUrl) || Boolean(targetUrl && tab?.url && tab.url !== targetUrl);
          if (shouldNavigateBack) {
            try {
              await chrome.tabs.goBack(activeTabId);
            } catch {
              if (targetUrl) {
                await chrome.tabs.update(activeTabId, { url: targetUrl }).catch(() => {});
              }
            }
          }
        }

        const wfStored = await chrome.storage.local.get(WORKFLOWS_KEY);
        let list = Array.isArray(wfStored[WORKFLOWS_KEY]) ? wfStored[WORKFLOWS_KEY] : [];
        list = list.filter(w => w.id !== recording.workflow.id);
        list.unshift(recording.workflow);
        await chrome.storage.local.set({ [WORKFLOWS_KEY]: list });

        // Notify active tab of updated state
        if (activeTabId) {
          chrome.tabs.sendMessage(activeTabId, {
            action: 'WORKFLOW_RECORD_START',
            manual: true,
            stepCount: recording.workflow.steps.length,
            loopDepth: recording.loopStack.length,
            workflowName: recording.workflow.name,
            paused: recording.paused === true,
          }).catch(() => {});
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
        await chrome.storage.local.remove('recordingPaused');
        await chrome.storage.local.set({ workflowRecordingActive: false, recordingPaused: false });

        // Tell all open tabs to remove floating recorder panel and hover tracker
        try {
          const allTabs = await chrome.tabs.query({});
          for (const t of allTabs) {
            if (t.id) chrome.tabs.sendMessage(t.id, { action: 'WORKFLOW_RECORD_STOP' }).catch(() => {});
          }
        } catch (_) {}

        recording.workflow.updatedAt = Date.now();
        const wfStored = await chrome.storage.local.get(WORKFLOWS_KEY);
        let list = Array.isArray(wfStored[WORKFLOWS_KEY]) ? wfStored[WORKFLOWS_KEY] : [];
        if (!recording.workflow.name || recording.workflow.name.trim().toLowerCase() === 'recorded workflow') {
          recording.workflow.name = getNextDefaultWorkflowName(list.filter(w => w.id !== recording.workflow.id));
        }
        list = list.filter(w => w.id !== recording.workflow.id);
        list.unshift(recording.workflow);
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

  // 10. Run Workflow Execution Engine
  if (message?.action === 'WORKFLOW_RUN') {
    (async () => {
      try {
        const { workflowId, workflow: passedWf, stopAfterIndex, variables, tabId: requestedTabId } = message;
        let wf = passedWf;
        if (!wf && workflowId) {
          const stored = await chrome.storage.local.get(WORKFLOWS_KEY);
          const list = Array.isArray(stored[WORKFLOWS_KEY]) ? stored[WORKFLOWS_KEY] : [];
          wf = list.find(w => w.id === workflowId);
        }
        if (!wf) {
          sendResponse({ success: false, error: 'Workflow was not found.' });
          return;
        }

        const rawUrl = wf.startUrl || (wf.steps && wf.steps[0] ? (wf.steps[0].value || wf.steps[0].target) : '') || 'https://www.naukri.com/';
        const targetUrl = normalizeUrl(rawUrl);

        let targetTabId = null;
        if (typeof requestedTabId === 'number') {
          const validReq = await getValidTab(requestedTabId);
          if (validReq?.id) {
            targetTabId = validReq.id;
          }
        }

        if (!targetTabId) {
          // Open target website tab cleanly WITHOUT opening Claude AI chat sidebar
          const newTab = await chrome.tabs.create({ url: targetUrl, active: true }).catch(() => null);
          if (newTab?.id) {
            targetTabId = newTab.id;
          }
        }

        if (!targetTabId) {
          targetTabId = await ensureActiveTab(null, targetUrl).catch(() => null);
        }

        if (!targetTabId) {
          sendResponse({ success: false, error: 'Failed to find or create browser tab.' });
          return;
        }

        executeWorkflowRun(wf, targetTabId, stopAfterIndex, variables).catch(err => {
          console.error('[BYOK] executeWorkflowRun error:', err);
        });

        sendResponse({ success: true, started: true, tabId: targetTabId, workflowId: wf.id });
      } catch (err) {
        sendResponse({ success: false, error: err instanceof Error ? err.message : String(err) });
      }
    })();
    return true;
  }

  // 11. Workflow Run Status
  if (message?.action === 'WORKFLOW_STATUS') {
    (async () => {
      try {
        const stored = await chrome.storage.local.get('workflowRunState');
        sendResponse({ success: true, state: stored.workflowRunState || null });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  // 12. Delete All Workflows
  if (message?.action === 'WORKFLOW_DELETE_ALL') {
    (async () => {
      try {
        await chrome.storage.local.set({ [WORKFLOWS_KEY]: [] });
        sendResponse({ success: true });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  // 13. Delete Single Workflow
  if (message?.action === 'WORKFLOW_DELETE') {
    (async () => {
      try {
        const stored = await chrome.storage.local.get(WORKFLOWS_KEY);
        let list = Array.isArray(stored[WORKFLOWS_KEY]) ? stored[WORKFLOWS_KEY] : [];
        list = list.filter(w => w.id !== message.workflowId);
        await chrome.storage.local.set({ [WORKFLOWS_KEY]: list });
        sendResponse({ success: true });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }
});

// Automatically track child tabs opened from the recorded tab (e.g. redirect links or job cards opened in new tab)
chrome.tabs.onCreated.addListener(async (newTab) => {
  try {
    if (!newTab?.id) return;
    if (newTab.url && newTab.url.startsWith('chrome-extension://')) return;

    const stored = await chrome.storage.session.get(RECORDING_KEY);
    const recording = stored[RECORDING_KEY];
    if (!recording) return;

    const isChild = (
      recording.tabId === newTab.openerTabId ||
      recording.rootTabId === newTab.openerTabId ||
      (!newTab.openerTabId && newTab.active && Date.now() - (recording.lastClickAt || 0) < 4000)
    );

    if (isChild) {
      console.log('[BYOK] Recording tracking new child tab:', newTab.id, 'from opener:', newTab.openerTabId);
      recording.tabId = newTab.id;
      if (!Array.isArray(recording.childTabIds)) recording.childTabIds = [];
      if (!recording.childTabIds.includes(newTab.id)) recording.childTabIds.push(newTab.id);
      await chrome.storage.session.set({ [RECORDING_KEY]: recording });

      // Configure recorder side panel for the new child tab!
      try {
        if (chrome.sidePanel && typeof chrome.sidePanel.setOptions === 'function') {
          await chrome.sidePanel.setOptions({
            tabId: newTab.id,
            path: `recorder.html?tabId=${newTab.id}&wf=${recording.workflow.id}`,
            enabled: true,
          });
        }
      } catch (_) {}
    }
  } catch (e) {}
});

// Re-arm recording and side panel when recorded tabs update or navigate (redirect links in same or child tabs)
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  try {
    if (changeInfo.status !== 'complete' && !changeInfo.url) return;
    const stored = await chrome.storage.session.get(RECORDING_KEY);
    const recording = stored[RECORDING_KEY];
    if (!recording) return;

    const isRecordedTab = (
      tabId === recording.tabId ||
      tabId === recording.rootTabId ||
      (Array.isArray(recording.childTabIds) && recording.childTabIds.includes(tabId))
    );

    if (isRecordedTab && tab?.url && /^https?:/i.test(tab.url)) {
      try {
        if (chrome.sidePanel && typeof chrome.sidePanel.setOptions === 'function') {
          await chrome.sidePanel.setOptions({
            tabId: tabId,
            path: `recorder.html?tabId=${tabId}&wf=${recording.workflow.id}`,
            enabled: true,
          });
        }
      } catch (_) {}

      const startMsg = {
        action: 'WORKFLOW_RECORD_START',
        manual: true,
        paused: recording.paused === true,
        stepCount: recording.workflow.steps.length,
        loopDepth: recording.loopStack?.length || 0,
        workflowName: recording.workflow.name,
      };
      chrome.tabs.sendMessage(tabId, startMsg).catch(() => {});
    }
  } catch (e) {}
});

// Automatically stop and clean up recording when the target tab or creator tab is closed
chrome.tabs.onRemoved.addListener(async (closedTabId) => {
  try {
    const stored = await chrome.storage.session.get(RECORDING_KEY);
    const recording = stored[RECORDING_KEY];
    if (!recording) return;

    if (recording.creatorTabId === closedTabId) {
      console.log('[BYOK] Creator tab closed. Stopping workflow recording.');
      await chrome.storage.session.remove(RECORDING_KEY);
      await chrome.storage.local.remove('recordingPaused');
      await chrome.storage.local.set({ workflowRecordingActive: false, recordingPaused: false });
      try {
        const allTabs = await chrome.tabs.query({});
        for (const t of allTabs) {
          if (t.id && t.id !== closedTabId) {
            chrome.tabs.sendMessage(t.id, { action: 'WORKFLOW_RECORD_STOP' }).catch(() => {});
          }
        }
      } catch (_) {}
      return;
    }

    if (Array.isArray(recording.childTabIds) && recording.childTabIds.includes(closedTabId)) {
      recording.childTabIds = recording.childTabIds.filter(id => id !== closedTabId);
      if (recording.tabId === closedTabId) {
        recording.tabId = recording.rootTabId;
      }
      await chrome.storage.session.set({ [RECORDING_KEY]: recording });
      return;
    }

    if (recording.tabId === closedTabId || recording.rootTabId === closedTabId) {
      const rootOpen = recording.rootTabId && recording.rootTabId !== closedTabId ? await chrome.tabs.get(recording.rootTabId).catch(() => null) : null;
      const childOpen = recording.childTabIds?.find(id => id !== closedTabId);
      if (rootOpen) {
        recording.tabId = recording.rootTabId;
        await chrome.storage.session.set({ [RECORDING_KEY]: recording });
        return;
      }
      if (childOpen) {
        recording.tabId = childOpen;
        await chrome.storage.session.set({ [RECORDING_KEY]: recording });
        return;
      }

      console.log('[BYOK] All recorded tabs closed. Stopping workflow recording.');
      await chrome.storage.session.remove(RECORDING_KEY);
      await chrome.storage.local.remove('recordingPaused');
      await chrome.storage.local.set({ workflowRecordingActive: false, recordingPaused: false });
      try {
        const allTabs = await chrome.tabs.query({});
        for (const t of allTabs) {
          if (t.id && t.id !== closedTabId) {
            chrome.tabs.sendMessage(t.id, { action: 'WORKFLOW_RECORD_STOP' }).catch(() => {});
          }
        }
      } catch (_) {}
    }
  } catch (e) {}
});

// ─── Workflow Runner Helpers ──────────────────────────────────────────────────

function normalizeUrl(input) {
  let u = (input || '').trim();
  if (!u) return 'https://www.naukri.com/';
  if (u.startsWith('http://') || u.startsWith('https://')) return u;
  if (!u.includes('.')) return `https://www.google.com/search?q=${encodeURIComponent(u)}`;
  return 'https://' + u;
}

async function getValidTab(tabId) {
  if (!tabId || typeof tabId !== 'number') return null;
  try {
    const tab = await chrome.tabs.get(tabId);
    return tab?.id ? tab : null;
  } catch {
    return null;
  }
}

async function ensureActiveTab(currentTabId, fallbackUrl, runState = null) {
  // 1. Check if the current tab is still valid and alive
  const existing = await getValidTab(currentTabId);
  if (existing?.id) {
    return existing.id;
  }

  console.warn(`[BYOK] Tab ${currentTabId} is not available. Searching for replacement tab...`);

  // 2. Look for an active web tab in the current window
  try {
    const activeTabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const validActive = activeTabs.find(t => t.id && t.url && /^https?:/i.test(t.url) && !t.url.startsWith('chrome-extension://'));
    if (validActive?.id) {
      if (runState) {
        runState.tabId = validActive.id;
        runState.logs.push(`[BYOK] Tab ${currentTabId} was unavailable. Resumed on active tab ${validActive.id} (${validActive.url || ''})`);
        await chrome.storage.local.set({ workflowRunState: runState }).catch(() => {});
      }
      return validActive.id;
    }
  } catch (_) {}

  // 3. Search for ANY web tab currently open
  try {
    const allTabs = await chrome.tabs.query({});
    const validWeb = allTabs.find(t => t.id && t.url && /^https?:/i.test(t.url) && !t.url.startsWith('chrome-extension://'));
    if (validWeb?.id) {
      await chrome.tabs.update(validWeb.id, { active: true }).catch(() => {});
      if (runState) {
        runState.tabId = validWeb.id;
        runState.logs.push(`[BYOK] Tab ${currentTabId} was unavailable. Switched to open tab ${validWeb.id} (${validWeb.url || ''})`);
        await chrome.storage.local.set({ workflowRunState: runState }).catch(() => {});
      }
      return validWeb.id;
    }
  } catch (_) {}

  // 4. If no living web tab exists, create a new one
  const targetUrl = normalizeUrl(fallbackUrl || 'https://www.naukri.com/');
  const newTab = await chrome.tabs.create({ url: targetUrl, active: true }).catch(() => null);
  if (newTab?.id) {
    await waitForTabReady(newTab.id);
    if (runState) {
      runState.tabId = newTab.id;
      runState.logs.push(`[BYOK] Tab ${currentTabId} was unavailable. Created replacement tab ${newTab.id} (${targetUrl})`);
      await chrome.storage.local.set({ workflowRunState: runState }).catch(() => {});
    }
    return newTab.id;
  }

  throw new Error(`Unable to find or create a valid browser tab for workflow execution.`);
}

async function waitForTabReady(tabId, timeoutMs = 35000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const tab = await chrome.tabs.get(tabId);
      if (tab?.status === 'complete') return tab;
    } catch {
      return null;
    }
    await new Promise(r => setTimeout(r, 250));
  }
  return null;
}

function isNaukriJobClick(step) {
  if (!step || step.type !== 'click' || !step.target) return false;
  const target = step.target;
  const descriptor = `${target.collectionSelector ?? ''} ${target.relativeSelector ?? ''} ${target.selector ?? ''} ${(target.selectors ?? []).join(' ')} ${step.name || ''}`.toLowerCase();
  return /cust-job-tuple|srp-jobtuple|jobtuple|\/job-listings-|a\.title/.test(descriptor);
}

function matchesExpectedNaukriJobUrl(actualUrl, expectedUrl) {
  if (!actualUrl || !expectedUrl) return false;
  try {
    const actual = new URL(actualUrl);
    const expected = new URL(expectedUrl);
    const actualPath = actual.pathname.replace(/\/+$/, '');
    const expectedPath = expected.pathname.replace(/\/+$/, '');
    const isNaukriHost = (hostname) => hostname === 'naukri.com' || hostname.endsWith('.naukri.com');
    return isNaukriHost(actual.hostname)
      && isNaukriHost(expected.hostname)
      && Boolean(expectedPath)
      && actualPath.includes('/job-listings-')
      && (actualPath === expectedPath || actualPath.includes(expectedPath));
  } catch {
    return actualUrl === expectedUrl;
  }
}

async function waitForExpectedNaukriDestination(sourceTabId, beforeTabs, expectedUrl, timeoutMs = 3500) {
  const deadline = Date.now() + timeoutMs;
  const createdTabs = [];
  while (Date.now() <= deadline) {
    const tabs = await chrome.tabs.query({}).catch(() => []);
    const newTabs = tabs.filter((t) => t.id !== undefined && !beforeTabs.has(t.id));
    for (const tab of newTabs) {
      if (!createdTabs.some((c) => c.id === tab.id)) createdTabs.push(tab);
    }
    const source = await getValidTab(sourceTabId);
    const candidates = [...newTabs, ...(source ? [source] : [])];
    for (const candidate of candidates) {
      if (matchesExpectedNaukriJobUrl(candidate.url, expectedUrl)) {
        return { destination: candidate, actualUrl: candidate.url, createdTabs };
      }
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  const source = await getValidTab(sourceTabId);
  return { actualUrl: source?.url, createdTabs };
}

// ─── AI Model Calling & Sequential AI Loop Execution ─────────────────────────

async function callOmniRouteAPI(apiKey, baseUrl, model, systemPrompt, messages) {
  let activeBaseUrl = (baseUrl || 'http://127.0.0.1:20128/v1').trim();
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
    max_tokens: 1500,
    stream: false,
  });

  let response;
  try {
    response = await fetch(endpoint, { method: 'POST', headers, body });
  } catch (err) {
    if (activeBaseUrl.includes('localhost')) {
      endpoint = `${activeBaseUrl.replace('localhost', '127.0.0.1').replace(/\/+$/, '')}/chat/completions`;
      response = await fetch(endpoint, { method: 'POST', headers, body });
    } else if (activeBaseUrl.includes('127.0.0.1')) {
      endpoint = `${activeBaseUrl.replace('127.0.0.1', 'localhost').replace(/\/+$/, '')}/chat/completions`;
      response = await fetch(endpoint, { method: 'POST', headers, body });
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

async function callGeminiAPI(apiKey, model, systemPrompt, messages) {
  const activeModel = model || 'gemini-2.0-flash';
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(activeModel)}:generateContent?key=${encodeURIComponent(apiKey)}`;

  const contents = messages.map(m => ({
    role: m.role === 'assistant' ? 'model' : 'user',
    parts: [{ text: m.content }],
  }));

  const payload = {
    contents,
    systemInstruction: { parts: [{ text: systemPrompt }] },
    generationConfig: { temperature: 0.2, maxOutputTokens: 1500 },
  };

  const response = await fetch(url, {
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

async function callAnthropicAPI(apiKey, model, systemPrompt, messages) {
  const url = 'https://api.anthropic.com/v1/messages';
  const formattedMessages = messages.map(m => ({
    role: m.role === 'assistant' ? 'assistant' : 'user',
    content: m.content,
  }));

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'dangerously-allow-browser': 'true',
    },
    body: JSON.stringify({
      model: model || 'claude-3-7-sonnet-20250219',
      system: systemPrompt,
      messages: formattedMessages,
      max_tokens: 1500,
      temperature: 0.2,
    }),
  });

  if (!response.ok) throw new Error(`Anthropic API Error (${response.status}): ${await response.text()}`);
  const data = await response.json();
  const text = data.content?.[0]?.text;
  if (!text) throw new Error('Anthropic API returned an empty response.');
  return text;
}

async function callActiveAIModel(config, systemPrompt, messages) {
  const provider = config?.activeProvider || 'omniroute';
  if (provider === 'gemini') {
    if (!config?.gemini?.apiKey) throw new Error('Gemini API key is not configured in Settings.');
    return await callGeminiAPI(config.gemini.apiKey, config.gemini.model, systemPrompt, messages);
  } else if (provider === 'omniroute') {
    return await callOmniRouteAPI(config?.omniroute?.apiKey, config?.omniroute?.baseUrl, config?.omniroute?.model, systemPrompt, messages);
  } else {
    if (!config?.anthropic?.apiKey) throw new Error('Anthropic API key is not configured in Settings.');
    return await callAnthropicAPI(config.anthropic.apiKey, config.anthropic.model, systemPrompt, messages);
  }
}

function parseAiActionJson(text) {
  if (!text) return { action: 'click', value: '', reasoning: 'Empty response fallback' };

  const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/) || text.match(/\{[\s\S]*?\}/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse((jsonMatch[1] || jsonMatch[0]).trim());
      const rawAction = String(parsed.action || '').toLowerCase().trim();
      let normAction = 'click';
      if (['fill', 'type', 'answer', 'text'].includes(rawAction)) normAction = 'fill';
      else if (['select', 'select_option', 'dropdown', 'choose'].includes(rawAction)) normAction = 'select_option';
      else if (['check', 'checkbox'].includes(rawAction)) normAction = 'check';
      else normAction = 'click';

      return {
        action: normAction,
        value: typeof parsed.value === 'string' ? parsed.value : (parsed.value !== undefined ? String(parsed.value) : ''),
        reasoning: parsed.reasoning || parsed.thought || '',
      };
    } catch (_) {}
  }

  const lower = text.toLowerCase();
  if (lower.includes('"action": "fill"') || lower.includes('fill') || lower.includes('type')) {
    return { action: 'fill', value: text.replace(/^[^:]*:\s*/, '').trim(), reasoning: 'Heuristic text parsing' };
  }
  return { action: 'click', value: '', reasoning: 'Default click action' };
}

function extractStepTargets(step) {
  if (Array.isArray(step.targets) && step.targets.length > 0) {
    return step.targets.map(t => typeof t === 'string' ? { selector: t, selectors: [t] } : t);
  }
  if (Array.isArray(step.targetDetails) && step.targetDetails.length > 0) {
    return step.targetDetails.map(t => ({ selector: t.selector, selectors: [t.selector], text: t.label || '' }));
  }
  const fallback = [];
  if (step.sourceTarget) {
    fallback.push(typeof step.sourceTarget === 'string' ? { selector: step.sourceTarget, selectors: [step.sourceTarget] } : step.sourceTarget);
  }
  if (step.target) {
    const sSel = typeof step.sourceTarget === 'string' ? step.sourceTarget : step.sourceTarget?.selector;
    const tSel = typeof step.target === 'string' ? step.target : step.target?.selector;
    if (!sSel || sSel !== tSel) {
      fallback.push(typeof step.target === 'string' ? { selector: step.target, selectors: [step.target] } : step.target);
    }
  }
  return fallback.length > 0 ? fallback : [{ selector: '', text: step.name || '' }];
}

async function executeAIStepOneByOne(tabId, step, runState) {
  let activeTabId = tabId;
  const targets = extractStepTargets(step);
  const total = targets.length;

  const storeData = await chrome.storage.local.get(['byok_config', 'userProfile', 'customAnswers']);
  const config = storeData.byok_config || {
    activeProvider: 'omniroute',
    omniroute: { baseUrl: 'http://127.0.0.1:20128/v1', apiKey: 'sk-f46d845e6a300177-0a895e-fbfbd25b', model: 'antigravity/gemini-3.6-flash-high' },
    gemini: { apiKey: '', model: 'gemini-2.0-flash' },
    anthropic: { apiKey: '', model: 'claude-3-7-sonnet-20250219' },
  };
  const profile = storeData.userProfile || {};
  const customAnswers = Array.isArray(storeData.customAnswers) ? storeData.customAnswers : [];
  const actionHistory = [];

  runState.logs.push(`[AI Loop] 🚀 Starting sequential execution of ${total} element(s) one by one...`);
  await chrome.storage.local.set({ workflowRunState: runState });

  for (let idx = 0; idx < total; idx++) {
    const target = targets[idx];
    const elemNumber = idx + 1;
    runState.logs.push(`[AI Loop] 🔍 [Element ${elemNumber}/${total}] Inspecting element: "${target.selector || target.text || 'element'}"...`);
    await chrome.storage.local.set({ workflowRunState: runState });

    // 1. Inspect single element in tab
    let elemInfo = null;
    try {
      elemInfo = await chrome.tabs.sendMessage(activeTabId, {
        action: 'WORKFLOW_READ_TARGET',
        target,
      });
    } catch (err) {
      try {
        await chrome.scripting.executeScript({ target: { tabId: activeTabId }, files: ['content.js'] });
        await new Promise(r => setTimeout(r, 400));
        elemInfo = await chrome.tabs.sendMessage(activeTabId, { action: 'WORKFLOW_READ_TARGET', target });
      } catch (_) {}
    }

    // Wait up to 4s if element not yet rendered
    if (!elemInfo?.success && target.selector) {
      const startWait = Date.now();
      while (Date.now() - startWait < 4000) {
        await new Promise(r => setTimeout(r, 400));
        try {
          elemInfo = await chrome.tabs.sendMessage(activeTabId, { action: 'WORKFLOW_READ_TARGET', target });
          if (elemInfo?.success) break;
        } catch (_) {}
      }
    }

    const tag = (elemInfo?.tag || '').toLowerCase();
    const targetName = elemInfo?.targetName || target.text || '';
    const visibleText = elemInfo?.text || '';
    const options = Array.isArray(elemInfo?.options) ? elemInfo.options : [];
    const htmlSnippet = (elemInfo?.htmlSnippet || '').slice(0, 800);

    // 2. Check Custom Answers first
    let directAnswer = null;
    const questionText = `${targetName} ${visibleText}`.trim().toLowerCase();
    if (questionText) {
      const match = customAnswers.find(qa => {
        const q = (qa.question || '').toLowerCase().trim();
        return q && (questionText.includes(q) || q.includes(questionText));
      });
      if (match) directAnswer = match.answer;
    }

    // 3. Formulate system & user prompts for THIS SINGLE ELEMENT ONLY
    const systemPrompt = `You are an expert autonomous browser agent filling out job applications and answering recruiter screening questions.
You are given details about ONE specific HTML element on the page (Element ${elemNumber} of ${total}).
You have ALL capabilities:
- "click": Click a button, link, radio option, or tab (e.g. Next, Submit, Save, Continue, Apply).
- "fill": Type text or numbers into an input field or textarea.
- "select_option": Select an option from a dropdown or choice list.
- "check": Toggle a checkbox.

Your task is to analyze THIS SINGLE ELEMENT and output the exact action to execute on it.

Candidate Profile:
${JSON.stringify(profile, null, 2)}

Saved Custom Answers:
${customAnswers.map(qa => `- Q: ${qa.question} -> A: ${qa.answer}`).join('\n')}

${step.customPrompt ? `User Instruction for this step: ${step.customPrompt}` : ''}

Previous actions in this loop:
${actionHistory.length > 0 ? actionHistory.map(h => `- Step ${h.elementNumber}: ${h.action.toUpperCase()} on "${h.target}" ${h.value ? `("${h.value}")` : ''}`).join('\n') : 'None (this is the first element)'}

CRITICAL RULES:
1. Return ONLY a valid JSON object wrapped in \`\`\`json ... \`\`\`.
2. Format:
{
  "action": "click" | "fill" | "select_option" | "check",
  "value": "string value to type or option text to select (leave empty string for click/check)",
  "reasoning": "brief 1-sentence reasoning"
}
3. If the element is a button (e.g. "Next", "Save", "Submit", "Continue", "Apply"), choose "click".
4. If the element is an input or textarea asking for salary, experience, notice period, location, etc., answer accurately from the Candidate Profile and choose "fill".
5. If the element is a dropdown, pick the best matching option from the available options list and choose "select_option".
6. If a matching saved answer is available, use it!`;

    const userPrompt = `Element ${elemNumber} of ${total}:
Tag: <${tag || 'element'}>
Label / Name: "${targetName}"
Visible Text / Context: "${visibleText.slice(0, 400)}"
${options.length > 0 ? `Available Options: ${JSON.stringify(options.slice(0, 30))}` : ''}
HTML: ${htmlSnippet}`;

    let aiDecision = null;
    if (directAnswer && ['input', 'textarea'].includes(tag)) {
      aiDecision = { action: 'fill', value: directAnswer, reasoning: `Matched saved Custom Answer for "${targetName}"` };
    } else {
      try {
        runState.logs.push(`[AI Loop] 🤖 Sending Element ${elemNumber}/${total} to AI...`);
        await chrome.storage.local.set({ workflowRunState: runState });
        const rawResponse = await callActiveAIModel(config, systemPrompt, [{ role: 'user', content: userPrompt }]);
        aiDecision = parseAiActionJson(rawResponse);
      } catch (aiErr) {
        console.warn(`[AI Loop] AI call failed for Element ${elemNumber}:`, aiErr);
        // Heuristic fallbacks
        if (['button', 'a'].includes(tag) || /button|submit|save|continue|next/i.test(targetName)) {
          aiDecision = { action: 'click', value: '', reasoning: 'Fallback: button detected' };
        } else if (options.length > 0) {
          aiDecision = { action: 'select_option', value: options[0], reasoning: 'Fallback: first option selected' };
        } else {
          aiDecision = { action: 'fill', value: profile.noticePeriod || 'Immediate', reasoning: 'Fallback: profile fill' };
        }
      }
    }

    runState.logs.push(`[AI Loop] ✅ [Element ${elemNumber}/${total}] AI Decision: ${aiDecision.action.toUpperCase()} ${aiDecision.value ? `("${aiDecision.value}")` : ''} - ${aiDecision.reasoning || ''}`);
    await chrome.storage.local.set({ workflowRunState: runState });

    // 4. Execute the chosen action on the element in active tab
    try {
      if (aiDecision.action === 'click') {
        await sendWorkflowStepToTab(activeTabId, {
          type: 'click',
          target,
          name: `AI Click: ${targetName || target.selector}`,
        });
      } else if (aiDecision.action === 'fill') {
        let fillSuccess = false;
        try {
          const fillRes = await chrome.tabs.sendMessage(activeTabId, {
            action: 'WORKFLOW_APPLY_AI_OUTPUT',
            target,
            outputAction: 'fill',
            answer: aiDecision.value,
          });
          fillSuccess = !!fillRes?.success;
        } catch (_) {}

        if (!fillSuccess) {
          await sendWorkflowStepToTab(activeTabId, {
            type: 'fill',
            target,
            value: aiDecision.value,
            name: `AI Fill: ${targetName || target.selector}`,
          });
        }
      } else if (aiDecision.action === 'select_option') {
        await sendWorkflowStepToTab(activeTabId, {
          type: 'select_option',
          target,
          value: aiDecision.value,
          name: `AI Select: ${targetName || target.selector}`,
        });
      } else if (aiDecision.action === 'check') {
        await sendWorkflowStepToTab(activeTabId, {
          type: 'check',
          target,
          checked: true,
          name: `AI Check: ${targetName || target.selector}`,
        });
      }

      actionHistory.push({
        elementNumber: elemNumber,
        action: aiDecision.action,
        target: targetName || target.selector,
        value: aiDecision.value,
      });
    } catch (execErr) {
      runState.logs.push(`[AI Loop] ⚠️ Error on Element ${elemNumber}: ${execErr.message}`);
      await chrome.storage.local.set({ workflowRunState: runState });
    }

    // Brief pause between elements for DOM reaction
    await new Promise(r => setTimeout(r, 600));

    // Refresh activeTabId in case action switched tab or navigated
    const valid = await getValidTab(activeTabId);
    if (!valid) {
      const activeTabs = await chrome.tabs.query({ currentWindow: true, active: true });
      if (activeTabs[0]?.id) activeTabId = activeTabs[0].id;
    }
  }

  runState.logs.push(`[AI Loop] 🎉 Completed all ${total} elements in AI Loop!`);
  await chrome.storage.local.set({ workflowRunState: runState });
  return { success: true, activeTabId, actionHistory };
}

async function sendWorkflowStepToTab(tabId, step, loopIndex = 0, clickMode = 'dom') {
  const msg = {
    action: 'WORKFLOW_EXECUTE_STEP',
    step,
    loopIndex,
    clickMode,
  };

  const validTab = await getValidTab(tabId);
  if (!validTab) {
    throw new Error(`No tab with id: ${tabId}`);
  }

  try {
    return await chrome.tabs.sendMessage(tabId, msg);
  } catch (err) {
    // If receiving end does not exist, verify tab is still alive before executeScript
    const recheck = await getValidTab(tabId);
    if (!recheck) {
      throw new Error(`No tab with id: ${tabId}`);
    }

    try {
      await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] });
      await new Promise(r => setTimeout(r, 600));
      return await chrome.tabs.sendMessage(tabId, msg);
    } catch (injectErr) {
      console.warn(`[BYOK] sendWorkflowStepToTab failed on tab ${tabId}:`, injectErr);
      throw injectErr;
    }
  }
}

async function executeWorkflowRun(workflow, initialTabId, stopAfterIndex, variables = {}) {
  let activeTabId = initialTabId;
  const steps = Array.isArray(workflow.steps) ? workflow.steps : [];
  const loopFrames = [];
  const runState = {
    runId: 'run_' + Date.now(),
    status: 'running',
    workflowId: workflow.id,
    workflowName: workflow.name,
    tabId: initialTabId,
    stepIndex: 0,
    stepCount: steps.length,
    variables: { ...(workflow.variables || {}), ...variables },
    stopAfterIndex: typeof stopAfterIndex === 'number' ? stopAfterIndex : undefined,
    startedAt: Date.now(),
    logs: [`Workflow "${workflow.name}" started in tab ${initialTabId}`],
  };
  await chrome.storage.local.set({ workflowRunState: runState });

  try {
    // Verify initial tab exists and heal if needed
    activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);
    await waitForTabReady(activeTabId);
    // Allow single page apps / frameworks to finish initial DOM render
    await new Promise(r => setTimeout(r, 1000));

    for (let i = 0; i < steps.length; i++) {
      if (typeof stopAfterIndex === 'number' && i > stopAfterIndex) {
        break;
      }

      // Ensure activeTabId is valid and alive before each step
      activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);

      const sourceStep = steps[i];
      if (!sourceStep) continue;

      const step = JSON.parse(JSON.stringify(sourceStep));

      // Resolve step variables {{var}}
      if (typeof step.value === 'string' && step.value.includes('{{')) {
        for (const [k, v] of Object.entries(runState.variables)) {
          step.value = step.value.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), v || '');
        }
      }

      if (step.disabled) {
        runState.logs.push(`Skipped disabled Step ${i + 1}: ${step.name || step.type}`);
        await chrome.storage.local.set({ workflowRunState: runState });
        continue;
      }

      runState.stepIndex = i;
      runState.logs.push(`Executing Step ${i + 1} of ${steps.length}: ${step.name || step.type}`);
      await chrome.storage.local.set({ workflowRunState: runState });

      // 1. Handle open_url step
      if (step.type === 'open_url') {
        const rawTarget = step.value || (typeof step.target === 'string' ? step.target : step.target?.selector) || workflow.startUrl;
        const targetUrl = normalizeUrl(rawTarget);
        activeTabId = await ensureActiveTab(activeTabId, targetUrl, runState);
        const curTab = await getValidTab(activeTabId);
        if (curTab && curTab.url !== targetUrl) {
          await chrome.tabs.update(activeTabId, { url: targetUrl }).catch(() => {});
          await waitForTabReady(activeTabId);
          await new Promise(r => setTimeout(r, 800));
        }
        if (step.stopAfter || (typeof stopAfterIndex === 'number' && i === stopAfterIndex)) {
          runState.status = 'completed';
          runState.message = `Test stopped after Step ${i + 1}: ${step.name || step.type}`;
          runState.finishedAt = Date.now();
          await chrome.storage.local.set({ workflowRunState: runState });
          return;
        }
        continue;
      }

      // 2. Handle loop_start step
      if (step.type === 'loop_start') {
        activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);
        const loopId = step.loopId || ('loop_' + i);
        const endIndex = steps.findIndex((c, cIdx) => cIdx > i && c.type === 'loop_end' && (c.loopId === loopId || !c.loopId));
        let detectedCount = 0;
        try {
          const countRes = await sendWorkflowStepToTab(activeTabId, { action: 'WORKFLOW_COUNT_TARGETS', target: step.target });
          detectedCount = Number(countRes?.count ?? 0);
        } catch (_) {}
        const count = Math.min(200, detectedCount || step.loopCount || 10);
        const curTab = await getValidTab(activeTabId);
        const frame = {
          loopId,
          startIndex: i,
          endIndex: endIndex >= 0 ? endIndex : steps.length,
          current: 0,
          count,
          listTabId: activeTabId,
          listUrl: curTab?.url || workflow.startUrl,
        };
        loopFrames.push(frame);
        runState.logs.push(`Loop "${step.name}" initialized for ${count} items. Starting loop iteration 1.`);
        await chrome.storage.local.set({ workflowRunState: runState });
        continue;
      }

      // 3. Handle loop_end step ("Continue to loop step 1")
      if (step.type === 'loop_end') {
        const frame = loopFrames[loopFrames.length - 1];
        if (frame) {
          if (frame.current + 1 < frame.count) {
            // Restore list tab and close child tab if one was opened
            if (activeTabId !== frame.listTabId) {
              await chrome.tabs.remove(activeTabId).catch(() => {});
              activeTabId = await ensureActiveTab(frame.listTabId, frame.listUrl || workflow.startUrl, runState);
              frame.listTabId = activeTabId;
              runState.tabId = activeTabId;
              await chrome.tabs.update(activeTabId, { active: true }).catch(() => {});
              await waitForTabReady(activeTabId);
            } else {
              activeTabId = await ensureActiveTab(activeTabId, frame.listUrl || workflow.startUrl, runState);
            }
            const cur = await getValidTab(activeTabId);
            if (frame.listUrl && cur?.url !== frame.listUrl) {
              await chrome.tabs.update(activeTabId, { url: frame.listUrl }).catch(() => {});
              await waitForTabReady(activeTabId);
            }
            frame.current += 1;
            runState.logs.push(`Completed loop item ${frame.current} of ${frame.count}. Continuing to loop step 1 for item ${frame.current + 1}...`);
            await chrome.storage.local.set({ workflowRunState: runState });
            i = frame.startIndex; // Next loop cycle will execute frame.startIndex + 1
            continue;
          } else {
            // Loop finished
            if (activeTabId !== frame.listTabId) {
              await chrome.tabs.remove(activeTabId).catch(() => {});
              activeTabId = await ensureActiveTab(frame.listTabId, frame.listUrl || workflow.startUrl, runState);
              runState.tabId = activeTabId;
              await chrome.tabs.update(activeTabId, { active: true }).catch(() => {});
            }
            loopFrames.pop();
            runState.logs.push(`Loop completed successfully (${frame.count} items).`);
            await chrome.storage.local.set({ workflowRunState: runState });
            continue;
          }
        }
      }

      // 4. Ensure target format is compatible with content.js runtime
      if (typeof step.target === 'string') {
        step.target = { selector: step.target, selectors: [step.target], text: step.name || '' };
      } else if (!step.target && step.targetSelector) {
        step.target = { selector: step.targetSelector, selectors: [step.targetSelector], text: step.name || '' };
      } else if (!step.target) {
        step.target = { selector: '', text: step.name || '' };
      }

      // Active loop index calculation
      const activeFrame = loopFrames[loopFrames.length - 1];
      const activeLoopIndex = activeFrame ? activeFrame.current : 0;
      if (activeFrame && (step.target?.useLoopIndex || step.useLoopIndex || isNaukriJobClick(step))) {
        step.target.useLoopIndex = true;
      }

      // If it's a Naukri click step without collectionIndex, default to the first job (0)
      if (isNaukriJobClick(step) && step.target && step.target.collectionIndex === undefined && !step.target.useLoopIndex) {
        step.target.collectionIndex = 0;
      }

      // 5. Handle AI Fallback / AI Loop step (Sequential one-by-one element execution)
      if (step.type === 'ai_fallback') {
        const isAiLoop = step.isAiLoop !== false;
        runState.logs.push(`[Workflow] Running AI step "${step.name || 'AI Step'}" (${isAiLoop ? '🔄 AI Loop: 1-by-1' : 'AI step'})...`);
        await chrome.storage.local.set({ workflowRunState: runState });
        activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);

        const aiResult = await executeAIStepOneByOne(activeTabId, step, runState);
        if (aiResult?.activeTabId) {
          activeTabId = aiResult.activeTabId;
          runState.tabId = activeTabId;
        }

        const waitMs = Math.max(400, Math.min(5000, step.waitMs || 800));
        await new Promise(r => setTimeout(r, waitMs));
        await chrome.storage.local.set({ workflowRunState: runState });

        if (step.stopAfter || (typeof stopAfterIndex === 'number' && i === stopAfterIndex)) {
          runState.status = 'completed';
          runState.message = `Test stopped after Step ${i + 1}: ${step.name || step.type}`;
          runState.finishedAt = Date.now();
          await chrome.storage.local.set({ workflowRunState: runState });
          return;
        }
        continue;
      }

      // 6. Attach resume if step type is attach_resume or file_upload
      if (step.type === 'attach_resume' || step.type === 'file_upload') {
        const resumeStore = await chrome.storage.local.get(['resumes', 'defaultResume', 'uploadedFiles']);
        const resumesList = [
          ...(Array.isArray(resumeStore.resumes) ? resumeStore.resumes : []),
          ...(Array.isArray(resumeStore.uploadedFiles) ? resumeStore.uploadedFiles : []),
        ];

        const stepFileName = (step.fileName || step.value || '').trim().toLowerCase();
        const stepNameLower = (step.name || '').trim().toLowerCase();
        const stepResumeId = (step.resumeId || '').trim();

        // 1. Direct inline file payload if present
        let targetFile = null;
        if (step.filePayload && step.filePayload.data) {
          targetFile = {
            name: step.filePayload.name || step.fileName || 'resume.pdf',
            type: step.filePayload.type || 'application/pdf',
            data: step.filePayload.data,
          };
        }

        // 2. Exact or best match in stored resumes
        if (!targetFile) {
          const matched = resumesList.find(r => {
            const rId = (r.id || '').trim();
            const rName = (r.name || r.fileName || '').trim().toLowerCase();
            const rLabel = (r.label || '').trim().toLowerCase();

            if (stepResumeId && rId === stepResumeId) return true;
            if (stepFileName && (rName === stepFileName || rLabel === stepFileName)) return true;
            if (stepNameLower && rName && (stepNameLower === rName || stepNameLower.includes(rName))) return true;
            return false;
          }) || resumesList.find(r => {
            const rId = (r.id || '').trim();
            return (workflow.resumeId && rId === workflow.resumeId) || (resumeStore.defaultResume && rId === resumeStore.defaultResume);
          }) || resumesList[0];

          if (matched) {
            targetFile = {
              name: matched.name || matched.fileName || step.fileName || 'resume.pdf',
              type: matched.type || 'application/pdf',
              data: matched.data || DEFAULT_FALLBACK_PDF_BASE64,
            };
          } else {
            targetFile = {
              name: step.fileName || 'resume.pdf',
              type: 'application/pdf',
              data: DEFAULT_FALLBACK_PDF_BASE64,
            };
          }
        }

        runState.logs.push(`[Workflow] Uploading resume "${targetFile.name}" (Step ${i + 1})...`);
        await chrome.storage.local.set({ workflowRunState: runState });

        const uploadTarget = step.target || { selector: 'input[type="file"]' };
        if (uploadTarget && !uploadTarget.selector) {
          uploadTarget.selector = 'input[type="file"]';
        }

        const attachMsg = {
          action: 'WORKFLOW_ATTACH_RESUME',
          target: uploadTarget,
          file: targetFile,
          step: { ...step, type: 'attach_resume', target: uploadTarget, file: targetFile },
        };

        try {
          activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);
          const attachRes = await chrome.tabs.sendMessage(activeTabId, attachMsg);
          if (attachRes?.attached || attachRes?.success) {
            runState.logs.push(`[Workflow] Successfully attached resume "${targetFile.name}".`);
          }
        } catch (tabErr) {
          try {
            activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);
            await chrome.scripting.executeScript({ target: { tabId: activeTabId }, files: ['content.js'] });
            await new Promise(r => setTimeout(r, 600));
            const attachRes = await chrome.tabs.sendMessage(activeTabId, attachMsg);
            if (attachRes?.attached || attachRes?.success) {
              runState.logs.push(`[Workflow] Attached resume "${targetFile.name}" after content script reinjection.`);
            }
          } catch (retryErr) {
            console.warn('[BYOK] WORKFLOW_ATTACH_RESUME failed:', retryErr);
            throw new Error(`Failed to upload resume "${targetFile.name}": ${retryErr.message}`);
          }
        }

        const waitMs = Math.max(800, Math.min(5000, step.waitMs || 800));
        await new Promise(r => setTimeout(r, waitMs));
        await chrome.storage.local.set({ workflowRunState: runState });
      } else {
        // Normal step execution (click, fill, select_option, checkbox, multiple_choice, etc.)
        const beforeTabs = new Set((await chrome.tabs.query({}).catch(() => [])).map(t => t.id));
        const isNaukri = isNaukriJobClick(step);
        activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);

        let execRes = null;
        try {
          execRes = await sendWorkflowStepToTab(activeTabId, step, activeLoopIndex, isNaukri ? 'mouse' : 'dom');
        } catch (stepErr) {
          if (/no tab with id|receiving end does not exist|closed/i.test(stepErr?.message || '')) {
            runState.logs.push(`[BYOK] Connection to tab ${activeTabId} lost. Re-establishing connection...`);
            await chrome.storage.local.set({ workflowRunState: runState }).catch(() => {});
            activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);
            await waitForTabReady(activeTabId);
            try {
              await chrome.scripting.executeScript({ target: { tabId: activeTabId }, files: ['content.js'] });
              await new Promise(r => setTimeout(r, 500));
            } catch (_) {}
            execRes = await sendWorkflowStepToTab(activeTabId, step, activeLoopIndex, isNaukri ? 'mouse' : 'dom');
          } else {
            throw stepErr;
          }
        }

        const isNaukriExec = execRes?.siteHandler === 'naukri-job-card' || isNaukri;
        if (isNaukriExec && execRes?.href) {
          const expectedUrl = execRes.href;
          runState.logs.push(`[Naukri] Waiting for job destination: ${expectedUrl}`);
          await chrome.storage.local.set({ workflowRunState: runState });

          const check = await waitForExpectedNaukriDestination(activeTabId, beforeTabs, expectedUrl, 3000);
          if (check.destination?.id) {
            runState.logs.push(`[Naukri] Job tab opened via click: tab ${check.destination.id}`);
            activeTabId = check.destination.id;
            runState.tabId = activeTabId;
            await waitForTabReady(activeTabId);
            await chrome.tabs.update(activeTabId, { active: true }).catch(() => {});
            await chrome.storage.local.set({ workflowRunState: runState });
          } else {
            // Fallback: create tab directly with expectedUrl if native popup/target=_blank was suppressed
            runState.logs.push(`[Naukri] Opening job in new tab fallback: ${expectedUrl}`);
            const curTab = await getValidTab(activeTabId);
            const fallbackTab = await chrome.tabs.create({
              url: expectedUrl,
              active: true,
              ...(curTab?.id ? { openerTabId: curTab.id } : {}),
              ...(typeof curTab?.windowId === 'number' ? { windowId: curTab.windowId } : {}),
            }).catch(() => null);
            if (fallbackTab?.id) {
              activeTabId = fallbackTab.id;
              runState.tabId = activeTabId;
              await waitForTabReady(activeTabId);
              await chrome.tabs.update(activeTabId, { active: true }).catch(() => {});
              await chrome.storage.local.set({ workflowRunState: runState });
            }
          }
        } else {
          const waitMs = Math.max(350, Math.min(5000, step.waitMs || 500));
          await new Promise(r => setTimeout(r, waitMs));

          // Check if action opened a new tab
          const afterTabs = await chrome.tabs.query({}).catch(() => []);
          const newTab = afterTabs.find(t => !beforeTabs.has(t.id) && t.id && /^https?:/i.test(t.url || ''));
          if (newTab?.id) {
            console.log('[BYOK] Action opened new tab:', newTab.id, newTab.url);
            activeTabId = newTab.id;
            runState.tabId = activeTabId;
            await waitForTabReady(activeTabId);
            await chrome.tabs.update(activeTabId, { active: true }).catch(() => {});
            await chrome.storage.local.set({ workflowRunState: runState });
          } else {
            // Re-verify that activeTabId is still alive after action
            activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);
          }
        }
      }

      if (step.stopAfter || (typeof stopAfterIndex === 'number' && i === stopAfterIndex)) {
        runState.status = 'completed';
        runState.message = `Test stopped after Step ${i + 1}: ${step.name || step.type}`;
        runState.finishedAt = Date.now();
        await chrome.storage.local.set({ workflowRunState: runState });
        return;
      }
    }

    runState.status = 'completed';
    runState.message = 'Workflow completed successfully!';
    runState.finishedAt = Date.now();
    runState.logs.push('All steps executed successfully.');
    await chrome.storage.local.set({ workflowRunState: runState });
  } catch (err) {
    console.error('[BYOK] Workflow execution error:', err);
    runState.status = 'error';
    runState.error = err instanceof Error ? err.message : String(err);
    runState.finishedAt = Date.now();
    runState.logs.push(`Error: ${runState.error}`);
    await chrome.storage.local.set({ workflowRunState: runState });
  }
}

