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
  // 0. Heartbeat / Extension Ping
  if (message?.action === 'PING') {
    sendResponse({ ok: true, pong: true, time: Date.now() });
    return true;
  }

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

  // 1b. Test API Key Live
  if (message?.action === 'TEST_API_KEY') {
    (async () => {
      try {
        const result = await testApiKeyBackend(message.payload || {});
        sendResponse(result);
      } catch (err) {
        sendResponse({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    })();
    return true;
  }

  // 1c. Fetch Provider Models Live
  if (message?.action === 'FETCH_PROVIDER_MODELS') {
    (async () => {
      try {
        const result = await fetchProviderModelsBackend(message.payload || {});
        sendResponse(result);
      } catch (err) {
        sendResponse({ ok: false, error: err instanceof Error ? err.message : String(err) });
      }
    })();
    return true;
  }

  // 1d. AI Extract User Details from Resume / Document / Text
  if (message?.action === 'AI_EXTRACT_USER_DETAILS') {
    (async () => {
      try {
        const storeData = await chrome.storage.local.get(['byok_config', 'userProfile']);
        const config = storeData.byok_config || {
          activeProvider: 'omniroute',
          omniroute: { baseUrl: 'http://127.0.0.1:20128/v1', apiKey: 'sk-f46d845e6a300177-0a895e-fbfbd25b', model: 'antigravity/gemini-3.6-flash-high' },
        };
        const rawContent = String(message.text || '').trim();
        if (!rawContent) {
          sendResponse({ success: false, error: 'No text or resume content provided.' });
          return;
        }

        const sysPrompt = `You are an expert HR data parser and professional profile assistant.
Your task is to analyze the provided resume, CV, or candidate summary text, and extract all relevant candidate profile details into a clean, structured JSON object.
Return ONLY valid JSON matching this schema:
{
  "fullName": "Candidate full name",
  "email": "Email address",
  "phone": "Phone number without special characters",
  "altPhone": "Alternate contact number if available",
  "address": "Street address / location",
  "city": "Current city",
  "state": "State or region",
  "country": "Country",
  "pincode": "Postal code",
  "degree": "Highest qualification / degree",
  "graduationYear": "Year of graduation",
  "university": "College or university name",
  "experienceYears": "Total years of relevant experience as a number or string",
  "skills": "Comma-separated list of technical and soft skills",
  "currentSalary": "Current compensation / CTC if mentioned",
  "expectedSalary": "Expected compensation / CTC if mentioned",
  "noticePeriod": "Notice period (e.g. Immediate, 15 days, 30 days)",
  "linkedin": "LinkedIn profile URL",
  "github": "GitHub / portfolio URL"
}`;

        const userMsg = `Here is the candidate resume / profile content to extract:\n\n${rawContent.slice(0, 15000)}`;
        const rawAiRes = await callActiveAIModel(config, sysPrompt, [{ role: 'user', content: userMsg }]);
        
        let extracted = {};
        const jsonMatch = rawAiRes.match(/```(?:json)?\s*([\s\S]*?)\s*```/) || rawAiRes.match(/\{[\s\S]*?\}/);
        if (jsonMatch) {
          try {
            extracted = JSON.parse((jsonMatch[1] || jsonMatch[0]).trim());
          } catch (_) {}
        }

        // Merge with existing profile
        const currentProfile = storeData.userProfile || {};
        const merged = { ...currentProfile };
        for (const [k, v] of Object.entries(extracted)) {
          if (v && typeof v === 'string' && v.trim()) {
            merged[k] = v.trim();
          }
        }

        await chrome.storage.local.set({ userProfile: merged });
        sendResponse({ success: true, profile: merged });
      } catch (err) {
        sendResponse({ success: false, error: err instanceof Error ? err.message : String(err) });
      }
    })();
    return true;
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

  // 6. Finish / Cancel Workflow Recording
  if (message?.action === 'WORKFLOW_RECORD_STOP' || message?.action === 'WORKFLOW_RECORD_CANCEL') {
    (async () => {
      try {
        const isCancel = message.action === 'WORKFLOW_RECORD_CANCEL' || message.save === false || message.cancel === true;
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

        if (isCancel) {
          console.log('[BYOK] Workflow recording was cancelled/exited. Discarding without saving.');
          sendResponse({ success: true, saved: false, cancelled: true });
          return;
        }

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
          // Open target website tab cleanly WITHOUT opening AI chat sidebar
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
          const isAi = /omniroute|api key|ai health|ai not working|127\.0\.0\.1:20128/i.test(err?.message || '');
          if (isAi) {
            console.warn('[BYOK] executeWorkflowRun AI notice:', err?.message || String(err));
          } else {
            console.error('[BYOK] executeWorkflowRun error:', err);
          }
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

  // 14. Start Batch Auto Apply Across Jobs
  if (message?.action === 'START_BATCH_APPLY') {
    (async () => {
      try {
        const jobs = Array.isArray(message.jobs) ? message.jobs : [];
        const mainTabId = sender?.tab?.id || null;
        const res = await startBatchAutoApply(jobs, mainTabId);
        sendResponse(res);
      } catch (err) {
        sendResponse({ success: false, error: err instanceof Error ? err.message : String(err) });
      }
    })();
    return true;
  }

  // 15. Stop Batch Auto Apply & All Workflows
  if (message?.action === 'STOP_BATCH_APPLY' || message?.action === 'WORKFLOW_RUN_STOP' || message?.action === 'STOP_WORKFLOW_RUN') {
    (async () => {
      try {
        const stored = await chrome.storage.local.get('workflowRunState');
        if (stored?.workflowRunState) {
          stored.workflowRunState.status = 'cancelled';
          stored.workflowRunState.error = 'Process stopped by user.';
          await chrome.storage.local.set({ workflowRunState: stored.workflowRunState });
        }
      } catch (_) {}
      const res = stopBatchAutoApply();
      sendResponse(res);
    })();
    return true;
  }

  // 15b. Skip Current Job in Batch Auto Apply
  if (message?.action === 'SKIP_CURRENT_JOB' || message?.action === 'SKIP_THIS_JOB') {
    (async () => {
      console.log('[BYOK] User requested SKIP_CURRENT_JOB.');
      if (currentBatchController) {
        currentBatchController.skipRequested = true;
        if (currentBatchController.currentJobTabId) {
          const tabToClose = currentBatchController.currentJobTabId;
          currentBatchController.currentJobTabId = null;
          chrome.tabs.remove(tabToClose).catch(() => {});
        }
      }
      try {
        const stored = await chrome.storage.local.get('workflowRunState');
        if (stored?.workflowRunState) {
          stored.workflowRunState.status = 'skipped';
          stored.workflowRunState.error = 'Job skipped by user.';
          await chrome.storage.local.set({ workflowRunState: stored.workflowRunState });
        }
      } catch (_) {}
      sendResponse({ success: true, skipped: true });
    })();
    return true;
  }

  // 16. Get Batch Status
  if (message?.action === 'GET_BATCH_STATUS') {
    sendResponse({ success: true, status: currentBatchController || { running: false } });
    return true;
  }

  // 17. Get Application History
  if (message?.action === 'GET_APPLY_HISTORY') {
    (async () => {
      try {
        const store = await chrome.storage.local.get('allCareerApplyHistory');
        sendResponse({ success: true, history: store.allCareerApplyHistory || [] });
      } catch (err) {
        sendResponse({ success: false, error: err instanceof Error ? err.message : String(err) });
      }
    })();
    return true;
  }

  // 18. Clear Application History
  if (message?.action === 'CLEAR_APPLY_HISTORY') {
    (async () => {
      try {
        await chrome.storage.local.set({ allCareerApplyHistory: [] });
        sendResponse({ success: true });
      } catch (err) {
        sendResponse({ success: false, error: err instanceof Error ? err.message : String(err) });
      }
    })();
    return true;
  }

  // 19. Open Extension Settings / Options Page
  if (message?.action === 'OPEN_OPTIONS_PAGE' || message?.action === 'OPEN_SETTINGS') {
    if (chrome.runtime.openOptionsPage) {
      chrome.runtime.openOptionsPage();
    } else {
      chrome.tabs.create({ url: chrome.runtime.getURL('options.html') });
    }
    sendResponse({ success: true });
    return true;
  }

  // 20b. Evaluate Page State via AI / Fast Regex
  if (message?.action === 'PAGE_EVALUATE') {
    (async () => {
      try {
        const text = String(message.pageText || '').slice(0, 3000);
        if (/already\s*applied|you\s*(have\s*)?already\s*applied|applied\s*\d+\s*(days?|hours?|months?|weeks?|mins?|minutes?)\s*ago|applied\s*on\s*[a-z0-9, ]+|you\s*applied\s*(on|to|for)?/i.test(text)) {
          sendResponse({ success: true, decision: 'fully job applied', reason: 'Detected already applied on page' });
          return;
        }
        if (/thank\s*you\s*for\s*(submitting|applying)|application\s*(has\s*been\s*)?(submitted|received)|submitted\s*successfully/i.test(text)) {
          sendResponse({ success: true, decision: 'fully job applied', reason: 'Detected confirmation text on page' });
          return;
        }
        if (/this\s*job\s*(is\s*)?(no\s*longer\s*available|expired|closed)|no\s*longer\s*accepting\s*applications/i.test(text)) {
          sendResponse({ success: true, decision: 'not job application', reason: 'Job posting is expired or closed' });
          return;
        }

        const aiCheck = await verifyActiveAIWorking();
        if (aiCheck.ok) {
          const configRes = await chrome.storage.local.get(null);
          const prompt = `Analyze this page text from a job application website:
"${text}"
Determine if the application is:
1. "fully job applied" (candidate already applied or application completed)
2. "not job application" (posting is closed, expired, login wall, or not a job)
3. "continue monitoring" (application form or buttons are still in progress)
Respond strictly with JSON: { "decision": "fully job applied" | "not job application" | "continue monitoring", "reason": "brief explanation" }`;
          const resp = await callActiveAIModel(configRes, 'You evaluate job application web pages.', [{ role: 'user', content: prompt }]);
          const jsonMatch = resp.match(/```(?:json)?\s*([\s\S]*?)\s*```/) || resp.match(/\{[\s\S]*?\}/);
          if (jsonMatch) {
            const parsed = JSON.parse((jsonMatch[1] || jsonMatch[0]).trim());
            sendResponse({ success: true, decision: parsed.decision || 'continue monitoring', reason: parsed.reason || '' });
            return;
          }
        }
        sendResponse({ success: true, decision: 'continue monitoring', reason: 'Deterministic checks passed' });
      } catch (err) {
        sendResponse({ success: false, error: err.message, decision: 'continue monitoring' });
      }
    })();
    return true;
  }

  // 20. Reload Extension Service Worker
  if (message?.action === 'RELOAD_EXTENSION') {
    sendResponse({ success: true });
    setTimeout(() => {
      try { chrome.runtime.reload(); } catch (_) {}
    }, 150);
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
    // Stop batch auto apply immediately ONLY if the main All Career portal tab is closed
    if (currentBatchController && currentBatchController.running && currentBatchController.mainTabId === closedTabId) {
      console.log('[BYOK] Main All Career tab was closed. Terminating batch auto apply immediately.');
      stopBatchAutoApply('Main All Career tab was closed.');
      return;
    }

    // If an individual job tab was closed, just clear the reference so batch can proceed to the next job
    if (currentBatchController && currentBatchController.currentJobTabId === closedTabId) {
      console.log(`[BYOK] Job tab ${closedTabId} was closed. Batch auto apply will continue with next job.`);
      currentBatchController.currentJobTabId = null;
    }

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

function isAllCareerPageTab(t) {
  if (!t) return false;
  if (currentBatchController && currentBatchController.mainTabId && t.id === currentBatchController.mainTabId) return true;
  const normUrl = String(t.url || '').toLowerCase();
  const normTitle = String(t.title || '').toLowerCase();
  return normUrl.includes('all_jobs') ||
         normUrl.includes('big_company_jobs') ||
         normUrl.includes('allcareer') ||
         normUrl.includes('all_career') ||
         normUrl.includes('career_explorer') ||
         normTitle.includes('all career') ||
         normTitle.includes('career portal');
}

async function isAnyAllCareerTabOpen(mainTabId = null) {
  if (mainTabId) {
    const tab = await getValidTab(mainTabId);
    if (tab && isAllCareerPageTab(tab)) return tab;
  }
  const allTabs = await chrome.tabs.query({}).catch(() => []);
  const found = (allTabs || []).find(t => isAllCareerPageTab(t));
  return found || null;
}

async function checkJobPageStatus(tabId) {
  if (!tabId) return { status: 'open' };
  try {
    const res = await chrome.tabs.sendMessage(tabId, { action: 'CHECK_JOB_PAGE_STATUS' });
    if (res && res.status) {
      return res;
    }
  } catch (_) {
    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => {
          const appliedRegex = /\b(already\s*applied|you\s*(have\s*)?already\s*applied|applied\s*\d+\s*(days?|hours?|months?|weeks?|mins?|minutes?)\s*ago|applied\s*on\s*[a-z0-9, ]+|you\s*applied\s*(on|to|for)?|application\s*(has\s*been\s*)?(already\s*)?submitted|already\s*submitted\s*(an?\s*)?application)\b/i;
          const closedRegex = /\b(this\s*job\s*(is\s*)?(no\s*longer\s*available|expired|closed)|no\s*longer\s*accepting\s*applications|job\s*(posting\s*)?(has\s*been\s*)?(closed|expired|removed)|applications\s*(are\s*)?closed)\b/i;
          const bodyText = (document.body.innerText || document.body.textContent || '').slice(0, 10000);
          if (appliedRegex.test(bodyText) || document.querySelector('.already-applied, span.already-applied, [class*="already-applied"], [data-testid="applied-badge"], .ia-AppliedBadge')) {
            return { status: 'already_applied', reason: 'Detected already applied on page' };
          }
          if (closedRegex.test(bodyText) || document.querySelector('[class*="job-expired"], [class*="job-closed"], .expired-tag')) {
            return { status: 'closed', reason: 'Detected job is closed/expired' };
          }
          return { status: 'open' };
        },
      });
      if (results && results[0] && results[0].result) {
        return results[0].result;
      }
    } catch (_) {}
  }
  return { status: 'open' };
}

async function ensureActiveTab(currentTabId, fallbackUrl, runState = null) {
  // If batch auto apply is cancelled or stopped, abort immediately
  if (currentBatchController && (currentBatchController.cancelled || !currentBatchController.running)) {
    throw new Error('Workflow execution cancelled or stopped by user.');
  }

  // 1. Check if the current tab is still valid and alive
  const existing = await getValidTab(currentTabId);
  if (existing?.id) {
    if (isAllCareerPageTab(existing)) {
      throw new Error('Cannot execute job application workflow on the main All Career page.');
    }
    return existing.id;
  }

  // If in batch auto apply and the tab closed, the user closed the job tab - abort this job cleanly
  if (currentBatchController && currentBatchController.running) {
    console.warn(`[BYOK] Job tab ${currentTabId} was closed. Ending workflow for this job without touching other tabs.`);
    throw new Error('Job application tab was closed by user.');
  }

  console.warn(`[BYOK] Tab ${currentTabId} is not available. Searching for replacement tab...`);

  // 2. Look for an active web tab in the current window (EXCLUDING All Career tab)
  try {
    const activeTabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const validActive = activeTabs.find(t => t.id && t.url && /^https?:/i.test(t.url) && !t.url.startsWith('chrome-extension://') && !isAllCareerPageTab(t));
    if (validActive?.id) {
      if (runState) {
        runState.tabId = validActive.id;
        runState.logs.push(`[BYOK] Tab ${currentTabId} was unavailable. Resumed on active tab ${validActive.id} (${validActive.url || ''})`);
        await chrome.storage.local.set({ workflowRunState: runState }).catch(() => {});
      }
      return validActive.id;
    }
  } catch (_) {}

  // 3. Search for ANY web tab currently open (EXCLUDING All Career tab)
  try {
    const allTabs = await chrome.tabs.query({});
    const validWeb = allTabs.find(t => t.id && t.url && /^https?:/i.test(t.url) && !t.url.startsWith('chrome-extension://') && !isAllCareerPageTab(t));
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

  // 4. If no living external web tab exists, create a new one
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
    if (currentBatchController && (currentBatchController.cancelled || !currentBatchController.running)) {
      return null;
    }
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
    if (rawText.includes('data:')) {
      const chunks = [];
      const lines = rawText.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data:') && !trimmed.includes('[DONE]')) {
          try {
            const parsed = JSON.parse(trimmed.replace(/^data:\s*/, ''));
            const delta = parsed.choices?.[0]?.delta?.content || parsed.choices?.[0]?.message?.content;
            if (delta) chunks.push(delta);
          } catch (_) {}
        }
      }
      if (chunks.length > 0) return chunks.join('');
    }
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

function calculateIntelligenceScore(modelId, modelName = '') {
  const mid = String(modelId || '').toLowerCase();
  const mname = String(modelName || '').toLowerCase();
  const text = `${mid} ${mname}`;

  // Explicit benchmarks & requested scores
  if (text.includes('sonnet-3-7') || text.includes('sonnet-3.7') || text.includes('3.7-sonnet')) return { score: 98, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('deepseek-r1') || text.includes('deepseek/deepseek-r1')) return { score: 97, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('o1') || text.includes('o3-mini')) return { score: 97, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('sonnet-3-5') || text.includes('sonnet-3.5') || text.includes('3.5-sonnet')) return { score: 96, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('gpt-4o') && !text.includes('mini')) return { score: 95, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('deepseek-v3') || text.includes('deepseek-chat')) return { score: 95, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('opus-3') || text.includes('3-opus') || text.includes('opus')) return { score: 95, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('gemini-2.5-pro') || text.includes('gemini-1.5-pro') || text.includes('gemini-pro')) return { score: 93, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('qwen-2.5-72b') || text.includes('qwen2.5-72b')) return { score: 91, tier: 'High Intelligence', badge: '🔥 High' };

  // User explicit request: gemini 3.8 flash high 90 score
  if (text.includes('gemini-3.8-flash-high') || text.includes('gemini-3.8-flash') || text.includes('gemini 3.8 flash') || text.includes('gemini-2.5-flash')) {
    return { score: 90, tier: 'High Intelligence', badge: '🔥 High' };
  }
  if (text.includes('mistral-large')) return { score: 90, tier: 'High Intelligence', badge: '🔥 High' };
  if (text.includes('llama-3.3-70b') || text.includes('llama-3.1-70b') || text.includes('70b-instruct')) return { score: 89, tier: 'High Intelligence', badge: '🔥 High' };
  if (text.includes('nemotron-70b') || text.includes('llama-3.1-nemotron-70b')) return { score: 89, tier: 'High Intelligence', badge: '🔥 High' };
  if (text.includes('gemini-2.0-flash') && !text.includes('lite')) return { score: 88, tier: 'High Intelligence', badge: '🔥 High' };
  if (text.includes('command-r-plus') || text.includes('command-r+')) return { score: 88, tier: 'High Intelligence', badge: '🔥 High' };

  if (text.includes('gpt-4o-mini')) return { score: 82, tier: 'Fast & Balanced', badge: '⚡ Fast' };
  if (text.includes('haiku-3-5') || text.includes('haiku-3') || text.includes('3.5-haiku')) return { score: 81, tier: 'Fast & Balanced', badge: '⚡ Fast' };
  if (text.includes('command-r') && !text.includes('plus')) return { score: 79, tier: 'Fast & Balanced', badge: '⚡ Fast' };
  if (text.includes('gemini-1.5-flash')) return { score: 78, tier: 'Fast & Balanced', badge: '⚡ Fast' };
  if (text.includes('qwen-2.5-32b') || text.includes('32b')) return { score: 83, tier: 'Fast & Balanced', badge: '⚡ Fast' };
  if (text.includes('qwen-2.5-14b') || text.includes('14b')) return { score: 77, tier: 'Fast & Balanced', badge: '⚡ Fast' };
  if (text.includes('mistral-small') || text.includes('mistral-nemo') || text.includes('open-mistral-nemo')) return { score: 75, tier: 'Fast & Balanced', badge: '⚡ Fast' };
  if (text.includes('llama-3.1-8b') || text.includes('llama-3-8b') || text.includes('8b-instant')) return { score: 70, tier: 'Fast & Balanced', badge: '⚡ Fast' };

  // User explicit request: gemini 3.6 light flash 50 score
  if (text.includes('gemini-3.6-light-flash') || text.includes('gemini 3.6 light flash') || text.includes('gemini-3.6-flash-lite') || text.includes('gemini-2.0-flash-lite') || text.includes('flash-lite') || text.includes('flash-light')) {
    return { score: 50, tier: 'Lightweight / Fast', badge: '🌱 Lite' };
  }
  if (text.includes('llama-3.2-3b') || text.includes('3b')) return { score: 52, tier: 'Lightweight / Fast', badge: '🌱 Lite' };
  if (text.includes('llama-3.2-1b') || text.includes('1b')) return { score: 45, tier: 'Lightweight / Fast', badge: '🌱 Lite' };
  if (text.includes('mistral-7b') || text.includes('7b')) return { score: 60, tier: 'Lightweight / Fast', badge: '🌱 Lite' };

  // Heuristic based on parameter size and keywords
  let score = 70;
  if (/405b/i.test(text)) score = 95;
  else if (/70b|72b/i.test(text)) score = 89;
  else if (/32b|33b|34b/i.test(text)) score = 82;
  else if (/14b|13b/i.test(text)) score = 77;
  else if (/7b|8b/i.test(text)) score = 68;
  else if (/3b|2b|1b/i.test(text)) score = 48;

  if (/r1|reasoning|thinking/i.test(text)) score = Math.min(99, score + 12);
  if (/pro|large|plus|high|max/i.test(text)) score = Math.min(99, score + 8);
  if (/lite|light|nano|micro|mini/i.test(text)) score = Math.max(30, score - 18);
  if (/turbo|flash|instant|fast/i.test(text)) score = Math.min(90, Math.max(50, score));

  let tier = 'Fast & Balanced';
  let badge = '⚡ Fast';
  if (score >= 93) {
    tier = 'Elite Intelligence';
    badge = '🧠 Elite';
  } else if (score >= 85) {
    tier = 'High Intelligence';
    badge = '🔥 High';
  } else if (score < 68) {
    tier = 'Lightweight / Fast';
    badge = '🌱 Lite';
  }

  return { score, tier, badge };
}

async function callOpenRouterAPI(apiKey, model, systemPrompt, messages) {
  const url = 'https://openrouter.ai/api/v1/chat/completions';
  const formattedMessages = [
    { role: 'system', content: systemPrompt },
    ...messages.map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content })),
  ];

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
      'HTTP-Referer': 'https://allcareer.ai',
      'X-Title': 'AllCareer Automation Extension',
    },
    body: JSON.stringify({
      model: model || 'google/gemini-2.0-flash-001',
      messages: formattedMessages,
      temperature: 0.2,
      max_tokens: 1500,
    }),
  });

  if (!response.ok) {
    const errText = await response.text().catch(() => '');
    throw new Error(`OpenRouter Error (${response.status}): ${errText}`);
  }
  const data = await response.json();
  const text = data.choices?.[0]?.message?.content;
  if (!text) throw new Error('OpenRouter returned an empty response.');
  return text;
}

async function callOpenAIAPI(apiKey, model, systemPrompt, messages) {
  const url = 'https://api.openai.com/v1/chat/completions';
  const formattedMessages = [
    { role: 'system', content: systemPrompt },
    ...messages.map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content })),
  ];

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: model || 'gpt-4o',
      messages: formattedMessages,
      temperature: 0.2,
      max_tokens: 1500,
    }),
  });

  if (!response.ok) {
    const errText = await response.text().catch(() => '');
    throw new Error(`OpenAI Error (${response.status}): ${errText}`);
  }
  const data = await response.json();
  const text = data.choices?.[0]?.message?.content;
  if (!text) throw new Error('OpenAI returned an empty response.');
  return text;
}

async function callGroqAPI(apiKey, model, systemPrompt, messages) {
  const url = 'https://api.groq.com/openai/v1/chat/completions';
  const formattedMessages = [
    { role: 'system', content: systemPrompt },
    ...messages.map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content })),
  ];

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: model || 'llama-3.3-70b-versatile',
      messages: formattedMessages,
      temperature: 0.2,
      max_tokens: 1500,
    }),
  });

  if (!response.ok) throw new Error(`Groq Error (${response.status}): ${await response.text()}`);
  const data = await response.json();
  return data.choices?.[0]?.message?.content || '';
}

async function callMistralAPI(apiKey, model, systemPrompt, messages) {
  const url = 'https://api.mistral.ai/v1/chat/completions';
  const formattedMessages = [
    { role: 'system', content: systemPrompt },
    ...messages.map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content })),
  ];

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: model || 'mistral-large-latest',
      messages: formattedMessages,
      temperature: 0.2,
      max_tokens: 1500,
    }),
  });

  if (!response.ok) throw new Error(`Mistral Error (${response.status}): ${await response.text()}`);
  const data = await response.json();
  return data.choices?.[0]?.message?.content || '';
}

async function callCohereAPI(apiKey, model, systemPrompt, messages) {
  const url = 'https://api.cohere.com/v2/chat';
  const formattedMessages = [
    { role: 'system', content: systemPrompt },
    ...messages.map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content })),
  ];

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: model || 'command-r-plus-08-2024',
      messages: formattedMessages,
    }),
  });

  if (!response.ok) throw new Error(`Cohere Error (${response.status}): ${await response.text()}`);
  const data = await response.json();
  return data.message?.content?.[0]?.text || '';
}

async function callNvidiaAPI(apiKey, model, systemPrompt, messages) {
  const url = 'https://integrate.api.nvidia.com/v1/chat/completions';
  const formattedMessages = [
    { role: 'system', content: systemPrompt },
    ...messages.map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content })),
  ];

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: model || 'meta/llama-3.3-70b-instruct',
      messages: formattedMessages,
      temperature: 0.2,
      max_tokens: 1500,
    }),
  });

  if (!response.ok) throw new Error(`Nvidia NIM Error (${response.status}): ${await response.text()}`);
  const data = await response.json();
  return data.choices?.[0]?.message?.content || '';
}

async function callCloudflareAPI(apiKey, accountId, model, systemPrompt, messages) {
  if (!accountId) throw new Error('Cloudflare Account ID is required');
  const activeModel = model || '@cf/meta/llama-3.3-70b-instruct-fp8-fast';
  const cleanModel = activeModel.startsWith('@cf/') ? activeModel : `@cf/${activeModel}`;
  const url = `https://api.cloudflare.com/client/v4/accounts/${accountId}/ai/run/${cleanModel}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      messages: [
        { role: 'system', content: systemPrompt },
        ...messages.map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content })),
      ],
    }),
  });

  if (!response.ok) throw new Error(`Cloudflare Error (${response.status}): ${await response.text()}`);
  const data = await response.json();
  return data.result?.response || '';
}

async function callHuggingFaceAPI(apiKey, model, systemPrompt, messages) {
  const url = 'https://router.huggingface.co/hf-inference/v1/chat/completions';
  const formattedMessages = [
    { role: 'system', content: systemPrompt },
    ...messages.map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content })),
  ];

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: model || 'meta-llama/Llama-3.3-70B-Instruct',
      messages: formattedMessages,
      temperature: 0.2,
      max_tokens: 1500,
    }),
  });

  if (!response.ok) throw new Error(`Hugging Face Error (${response.status}): ${await response.text()}`);
  const data = await response.json();
  return data.choices?.[0]?.message?.content || '';
}

async function callOllamaAPI(baseUrl, model, systemPrompt, messages) {
  const cleanUrl = (baseUrl || 'http://localhost:11434').replace(/\/+$/, '');
  const url = `${cleanUrl}/api/chat`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: model || 'llama3:latest',
      messages: [
        { role: 'system', content: systemPrompt },
        ...messages.map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content })),
      ],
      stream: false,
    }),
  });

  if (!response.ok) throw new Error(`Ollama Error (${response.status}): ${await response.text()}`);
  const data = await response.json();
  return data.message?.content || '';
}

async function testApiKeyBackend({ provider, key, baseUrl, accountId, model }) {
  const startTime = Date.now();
  try {
    switch (provider) {
      case 'openai': {
        const testModel = model || 'gpt-4o-mini';
        const resp = await fetch('https://api.openai.com/v1/chat/completions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${key}`,
          },
          body: JSON.stringify({
            model: testModel,
            messages: [{ role: 'user', content: 'Say OK' }],
            max_tokens: 2,
          }),
        });
        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Active & Working (${latencyMs}ms)!` };
        const errText = await resp.text().catch(() => '');
        let desc = `Error ${resp.status}`;
        try {
          const parsed = JSON.parse(errText);
          if (parsed?.error?.message) desc = parsed.error.message;
        } catch (_) {
          if (resp.status === 401) desc = 'OpenAI API key expired or invalid';
        }
        return { ok: false, status: resp.status, latencyMs, error: desc };
      }
      case 'openrouter': {
        const resp = await fetch('https://openrouter.ai/api/v1/chat/completions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${key}`,
            'HTTP-Referer': 'https://allcareer.ai',
            'X-Title': 'AllCareer Test',
          },
          body: JSON.stringify({
            model: model || 'google/gemini-2.0-flash-lite-001',
            messages: [{ role: 'user', content: 'Say OK' }],
            max_tokens: 2,
          }),
        });
        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Active & Working (${latencyMs}ms)!` };
        const errText = await resp.text().catch(() => '');
        let desc = `Error ${resp.status}`;
        try {
          const parsed = JSON.parse(errText);
          if (parsed?.error?.message) desc = parsed.error.message;
        } catch (_) {
          if (resp.status === 401) desc = 'API key expired or invalid';
        }
        return { ok: false, status: resp.status, latencyMs, error: desc };
      }
      case 'gemini': {
        const testModel = model || 'gemini-2.0-flash';
        const resp = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(testModel)}:generateContent?key=${encodeURIComponent(key)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ contents: [{ parts: [{ text: 'OK' }] }], generationConfig: { maxOutputTokens: 2 } }),
        });
        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Active & Working (${latencyMs}ms)!` };
        const errText = await resp.text().catch(() => '');
        return { ok: false, status: resp.status, latencyMs, error: errText.slice(0, 150) };
      }
      case 'groq': {
        const resp = await fetch('https://api.groq.com/openai/v1/chat/completions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
          body: JSON.stringify({ model: 'llama-3.1-8b-instant', messages: [{ role: 'user', content: 'OK' }], max_tokens: 2 }),
        });
        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Active & Working (${latencyMs}ms)!` };
        const errText = await resp.text().catch(() => '');
        return { ok: false, status: resp.status, latencyMs, error: errText.slice(0, 150) };
      }
      case 'mistral': {
        const resp = await fetch('https://api.mistral.ai/v1/chat/completions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
          body: JSON.stringify({ model: 'open-mistral-nemo', messages: [{ role: 'user', content: 'OK' }], max_tokens: 2 }),
        });
        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Active & Working (${latencyMs}ms)!` };
        const errText = await resp.text().catch(() => '');
        return { ok: false, status: resp.status, latencyMs, error: errText.slice(0, 150) };
      }
      case 'cohere': {
        const resp = await fetch('https://api.cohere.com/v2/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
          body: JSON.stringify({ model: 'command-r', messages: [{ role: 'user', content: 'OK' }] }),
        });
        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Active & Working (${latencyMs}ms)!` };
        const errText = await resp.text().catch(() => '');
        return { ok: false, status: resp.status, latencyMs, error: errText.slice(0, 150) };
      }
      case 'nvidia': {
        const resp = await fetch('https://integrate.api.nvidia.com/v1/chat/completions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
          body: JSON.stringify({ model: 'meta/llama-3.1-8b-instruct', messages: [{ role: 'user', content: 'OK' }], max_tokens: 2 }),
        });
        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Active & Working (${latencyMs}ms)!` };
        const errText = await resp.text().catch(() => '');
        return { ok: false, status: resp.status, latencyMs, error: errText.slice(0, 150) };
      }
      case 'cloudflare': {
        if (!accountId) return { ok: false, error: 'Account ID required' };
        const resp = await fetch(`https://api.cloudflare.com/client/v4/accounts/${accountId}/ai/run/@cf/meta/llama-3.1-8b-instruct`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
          body: JSON.stringify({ messages: [{ role: 'user', content: 'OK' }] }),
        });
        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Active & Working (${latencyMs}ms)!` };
        const errText = await resp.text().catch(() => '');
        return { ok: false, status: resp.status, latencyMs, error: errText.slice(0, 150) };
      }
      case 'huggingface': {
        const resp = await fetch('https://router.huggingface.co/hf-inference/v1/chat/completions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
          body: JSON.stringify({ model: 'meta-llama/Llama-3.1-8B-Instruct', messages: [{ role: 'user', content: 'OK' }], max_tokens: 2 }),
        });
        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Active & Working (${latencyMs}ms)!` };
        const errText = await resp.text().catch(() => '');
        return { ok: false, status: resp.status, latencyMs, error: errText.slice(0, 150) };
      }
      case 'ollama': {
        const cleanUrl = (baseUrl || 'http://localhost:11434').replace(/\/+$/, '');
        const resp = await fetch(`${cleanUrl}/api/tags`);
        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Connected to Ollama server (${latencyMs}ms)!` };
        return { ok: false, status: resp.status, latencyMs, error: `HTTP ${resp.status}` };
      }
      case 'omniroute': {
        const cleanUrl = (baseUrl || 'http://127.0.0.1:20128/v1').replace(/\/+$/, '');
        const rootUrl = cleanUrl.replace(/\/v1$/, '') || 'http://127.0.0.1:20128';
        const headers = { 'Content-Type': 'application/json' };
        if (key) headers['Authorization'] = `Bearer ${key}`;

        // 1. Fast probe: check HEAD on /models or root first (takes ~20-50ms, skips 190KB body)
        let modelsOk = false;
        try {
          const ctrl = new AbortController();
          const tId = setTimeout(() => ctrl.abort(), 2000);
          const mResp = await fetch(`${cleanUrl}/models`, { method: 'HEAD', signal: ctrl.signal, headers }).catch(() => null);
          clearTimeout(tId);
          if (mResp && mResp.status >= 200 && mResp.status < 400) modelsOk = true;
        } catch (_) {}

        if (!modelsOk) {
          try {
            const ctrlRoot = new AbortController();
            const tIdRoot = setTimeout(() => ctrlRoot.abort(), 2000);
            const rResp = await fetch(rootUrl, { method: 'HEAD', redirect: 'manual', signal: ctrlRoot.signal, headers }).catch(() => null);
            clearTimeout(tIdRoot);
            if (rResp && rResp.status >= 200 && rResp.status < 400) modelsOk = true;
          } catch (_) {}
        }

        if (!modelsOk) {
          // Try localhost <-> 127.0.0.1 fallback
          try {
            const altUrl = cleanUrl.includes('127.0.0.1')
              ? cleanUrl.replace('127.0.0.1', 'localhost')
              : cleanUrl.replace('localhost', '127.0.0.1');
            const ctrlAlt = new AbortController();
            const tIdAlt = setTimeout(() => ctrlAlt.abort(), 2000);
            const mRespAlt = await fetch(`${altUrl}/models`, { method: 'HEAD', signal: ctrlAlt.signal, headers }).catch(() => null);
            clearTimeout(tIdAlt);
            if (mRespAlt && mRespAlt.status >= 200 && mRespAlt.status < 400) modelsOk = true;
          } catch (_) {}
        }

        if (modelsOk) {
          const latencyMs = Date.now() - startTime;
          return { ok: true, status: 200, latencyMs, message: `✅ OmniRoute Active & Connected (${latencyMs}ms)!` };
        }

        // 2. Fallback: try chat/completions with 15s timeout
        let resp;
        try {
          const ctrlChat = new AbortController();
          const tIdChat = setTimeout(() => ctrlChat.abort(), 15000);
          resp = await fetch(`${cleanUrl}/chat/completions`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ model: model || 'antigravity/gemini-3.6-flash-high', messages: [{ role: 'user', content: 'OK' }], max_tokens: 2, stream: false }),
            signal: ctrlChat.signal,
          });
          clearTimeout(tIdChat);
        } catch (chatErr) {
          const latencyMs = Date.now() - startTime;
          return { ok: false, status: 0, latencyMs, error: chatErr.message || 'OmniRoute server not reachable' };
        }

        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Active & Working (${latencyMs}ms)!` };
        const errText = await resp.text().catch(() => '');
        return { ok: false, status: resp.status, latencyMs, error: errText.slice(0, 150) };
      }
      default:
        return { ok: false, error: `Unknown provider: ${provider}` };
    }
  } catch (err) {
    return { ok: false, latencyMs: Date.now() - startTime, error: err instanceof Error ? err.message : 'Network error' };
  }
}

async function fetchProviderModelsBackend({ provider, key, baseUrl, accountId }) {
  try {
    let rawModels = [];

    switch (provider) {
      case 'openai': {
        const headers = key ? { 'Authorization': `Bearer ${key}` } : {};
        const resp = await fetch('https://api.openai.com/v1/models', { headers });
        if (resp.ok) {
          const data = await resp.json();
          rawModels = (data?.data || [])
            .filter(m => m.id && (m.id.startsWith('gpt-') || m.id.startsWith('o1') || m.id.startsWith('o3') || m.id.startsWith('chatgpt')))
            .map(m => ({ id: m.id, name: m.id }));
        }
        break;
      }
      case 'openrouter': {
        const headers = key ? { 'Authorization': `Bearer ${key}` } : {};
        const resp = await fetch('https://openrouter.ai/api/v1/models', { headers });
        if (resp.ok) {
          const data = await resp.json();
          rawModels = (data?.data || []).map(m => ({ id: m.id, name: m.name || m.id }));
        }
        break;
      }
      case 'gemini': {
        if (!key) break;
        const resp = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${encodeURIComponent(key)}`);
        if (resp.ok) {
          const data = await resp.json();
          rawModels = (data?.models || [])
            .filter(m => Array.isArray(m.supportedGenerationMethods) && m.supportedGenerationMethods.includes('generateContent'))
            .map(m => ({ id: (m.name || '').replace(/^models\//, ''), name: m.displayName || m.name }));
        }
        break;
      }
      case 'groq': {
        const resp = await fetch('https://api.groq.com/openai/v1/models', {
          headers: key ? { 'Authorization': `Bearer ${key}` } : {},
        });
        if (resp.ok) {
          const data = await resp.json();
          rawModels = (data?.data || []).map(m => ({ id: m.id, name: m.id }));
        }
        break;
      }
      case 'mistral': {
        const resp = await fetch('https://api.mistral.ai/v1/models', {
          headers: key ? { 'Authorization': `Bearer ${key}` } : {},
        });
        if (resp.ok) {
          const data = await resp.json();
          rawModels = (data?.data || []).map(m => ({ id: m.id, name: m.id }));
        }
        break;
      }
      case 'cohere': {
        const resp = await fetch('https://api.cohere.com/v1/models', {
          headers: key ? { 'Authorization': `Bearer ${key}` } : {},
        });
        if (resp.ok) {
          const data = await resp.json();
          rawModels = (data?.models || []).map(m => ({ id: m.name, name: m.name }));
        }
        break;
      }
      case 'nvidia': {
        const resp = await fetch('https://integrate.api.nvidia.com/v1/models', {
          headers: key ? { 'Authorization': `Bearer ${key}` } : {},
        });
        if (resp.ok) {
          const data = await resp.json();
          rawModels = (data?.data || []).map(m => ({ id: m.id, name: m.id }));
        }
        break;
      }
      case 'ollama': {
        const cleanUrl = (baseUrl || 'http://localhost:11434').replace(/\/+$/, '');
        const resp = await fetch(`${cleanUrl}/api/tags`);
        if (resp.ok) {
          const data = await resp.json();
          rawModels = (data?.models || []).map(m => ({ id: m.name, name: `${m.name} (${m.details?.parameter_size || 'local'})` }));
        }
        break;
      }
      case 'omniroute': {
        const cleanUrl = (baseUrl || 'http://127.0.0.1:20128/v1').replace(/\/+$/, '');
        const headers = key ? { 'Authorization': `Bearer ${key}` } : {};
        const resp = await fetch(`${cleanUrl}/models`, { headers });
        if (resp.ok) {
          const data = await resp.json();
          rawModels = (data?.data || []).map(m => ({ id: m.id, name: m.name || m.id }));
        }
        break;
      }
      default:
        break;
    }

    // Add fallback presets if API did not return models or returned empty
    if (!rawModels || rawModels.length === 0) {
      if (provider === 'gemini') {
        rawModels = [
          { id: 'gemini-3.8-flash-high', name: 'Gemini 3.8 Flash High' },
          { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash' },
          { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro' },
          { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' },
          { id: 'gemini-3.6-light-flash', name: 'Gemini 3.6 Light Flash' },
        ];
      } else if (provider === 'openrouter') {
        rawModels = [
          { id: 'deepseek/deepseek-r1', name: 'DeepSeek R1' },
          { id: 'openai/gpt-4o', name: 'GPT-4o' },
          { id: 'google/gemini-2.0-flash-001', name: 'Gemini 2.0 Flash' },
          { id: 'meta-llama/llama-3.3-70b-instruct', name: 'Llama 3.3 70B Instruct' },
          { id: 'google/gemini-2.0-flash-lite-001', name: 'Gemini 2.0 Flash Lite' },
        ];
      } else if (provider === 'groq') {
        rawModels = [
          { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B Versatile' },
          { id: 'llama-3.1-8b-instant', name: 'Llama 3.1 8B Instant' },
          { id: 'deepseek-r1-distill-llama-70b', name: 'DeepSeek R1 Distill 70B' },
          { id: 'mixtral-8x7b-32768', name: 'Mixtral 8x7B' },
        ];
      } else if (provider === 'cloudflare') {
        rawModels = [
          { id: '@cf/meta/llama-3.3-70b-instruct-fp8-fast', name: 'Llama 3.3 70B Instruct (Fast)' },
          { id: '@cf/deepseek-ai/deepseek-r1-distill-qwen-32b', name: 'DeepSeek R1 Distill 32B' },
          { id: '@cf/meta/llama-3.1-8b-instruct', name: 'Llama 3.1 8B Instruct' },
          { id: '@cf/qwen/qwen2.5-72b-instruct', name: 'Qwen 2.5 72B Instruct' },
        ];
      } else if (provider === 'huggingface') {
        rawModels = [
          { id: 'meta-llama/Llama-3.3-70B-Instruct', name: 'Llama 3.3 70B Instruct' },
          { id: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-32B', name: 'DeepSeek R1 Distill Qwen 32B' },
          { id: 'Qwen/Qwen2.5-72B-Instruct', name: 'Qwen 2.5 72B Instruct' },
          { id: 'meta-llama/Llama-3.1-8B-Instruct', name: 'Llama 3.1 8B Instruct' },
        ];
      } else if (provider === 'mistral') {
        rawModels = [
          { id: 'mistral-large-latest', name: 'Mistral Large' },
          { id: 'mistral-small-latest', name: 'Mistral Small' },
          { id: 'open-mistral-nemo', name: 'Mistral NeMo' },
        ];
      } else if (provider === 'cohere') {
        rawModels = [
          { id: 'command-r-plus-08-2024', name: 'Command R+' },
          { id: 'command-r-08-2024', name: 'Command R' },
        ];
      } else if (provider === 'nvidia') {
        rawModels = [
          { id: 'meta/llama-3.3-70b-instruct', name: 'Llama 3.3 70B Instruct' },
          { id: 'nvidia/llama-3.1-nemotron-70b-instruct', name: 'Llama 3.1 Nemotron 70B' },
          { id: 'meta/llama-3.1-8b-instruct', name: 'Llama 3.1 8B Instruct' },
        ];
      }
    }

    // Clean Model List
    const cleanModels = rawModels.map(m => ({
      id: m.id,
      name: m.name || m.id,
      label: m.name || m.id,
    }));

    return { ok: true, models: cleanModels };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

async function callActiveAIModel(config, systemPrompt, messages) {
  // 1. Resolve key config: check if there is an active key configured in apiKeys list
  let apiKeys = Array.isArray(config?.apiKeys) ? config.apiKeys : [];
  if (apiKeys.length === 0) {
    try {
      const topStore = await chrome.storage.local.get('apiKeys');
      if (Array.isArray(topStore?.apiKeys)) apiKeys = topStore.apiKeys;
    } catch (_) {}
  }
  const activeKeyId = config?.activeKeyId;
  const keyConfig = apiKeys.find(k => k.id === activeKeyId && k.enabled !== false) ||
    apiKeys.find(k => k.enabled !== false) || null;

  const provider = keyConfig?.provider || config?.activeProvider || 'omniroute';
  const apiKey = keyConfig?.key || config?.[provider]?.apiKey || config?.[provider]?.key || '';
  const model = keyConfig?.model || config?.[provider]?.model || '';
  const baseUrl = keyConfig?.baseUrl || config?.[provider]?.baseUrl || '';
  const accountId = keyConfig?.accountId || config?.[provider]?.accountId || '';

  switch (provider) {
    case 'openai':
      if (!apiKey) throw new Error('OpenAI API key is not configured in Settings.');
      return await callOpenAIAPI(apiKey, model, systemPrompt, messages);
    case 'openrouter':
      if (!apiKey) throw new Error('OpenRouter API key is not configured in Settings.');
      return await callOpenRouterAPI(apiKey, model, systemPrompt, messages);
    case 'gemini':
      if (!apiKey) throw new Error('Gemini API key is not configured in Settings.');
      return await callGeminiAPI(apiKey, model, systemPrompt, messages);
    case 'groq':
      if (!apiKey) throw new Error('Groq API key is not configured in Settings.');
      return await callGroqAPI(apiKey, model, systemPrompt, messages);
    case 'mistral':
      if (!apiKey) throw new Error('Mistral API key is not configured in Settings.');
      return await callMistralAPI(apiKey, model, systemPrompt, messages);
    case 'cohere':
      if (!apiKey) throw new Error('Cohere API key is not configured in Settings.');
      return await callCohereAPI(apiKey, model, systemPrompt, messages);
    case 'nvidia':
      if (!apiKey) throw new Error('Nvidia NIM API key is not configured in Settings.');
      return await callNvidiaAPI(apiKey, model, systemPrompt, messages);
    case 'cloudflare':
      if (!apiKey) throw new Error('Cloudflare API token is not configured in Settings.');
      return await callCloudflareAPI(apiKey, accountId, model, systemPrompt, messages);
    case 'huggingface':
      if (!apiKey) throw new Error('Hugging Face API token is not configured in Settings.');
      return await callHuggingFaceAPI(apiKey, model, systemPrompt, messages);
    case 'ollama':
      return await callOllamaAPI(baseUrl, model, systemPrompt, messages);
    case 'omniroute':
    default:
      return await callOmniRouteAPI(apiKey, baseUrl, model, systemPrompt, messages);
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

const UNIVERSAL_WORKFLOW_AI_SYSTEM_PROMPT = `You are an elite autonomous browser AI agent specialized in automated job application workflows, recruitment chatbots (such as Naukri, Workday, Greenhouse, Lever, Taleo, LinkedIn), and screening forms.
You inspect page elements, understand screening questions, and execute the exact right browser action.

### CHATBOT & APPLICATION FORM DOMAIN KNOWLEDGE:
1. Chatbot Dialogs: In modern applicant chatbots (e.g. Naukri), the bot asks a screening question in a chat bubble (e.g. "UG CGPA (Also mention the field) | College / university").
2. Typing Area: The answer must be typed into the chat's typing area (which may be a contenteditable div like .textArea, a textarea, or an input field).
3. Save / Send Button Activation: The Save or Send button is often initially DISABLED (e.g. has class "disabled"). It automatically activates after text is typed into the input. When you see a chat question, type the complete answer first, then click Save on the next step.
4. Composite Questions: If a question asks for multiple items (e.g. "UG CGPA (Also mention the field) | College / university"), combine the relevant details from the candidate profile into a single coherent, concise answer (e.g. "8.2 CGPA in Computer Science, Anna University").
5. Options & Dropdowns: If choice chips, dropdown items, or radio choices are provided, match the candidate's background to the best available option.

### ACTION FORMAT (Return ONLY a single valid JSON block):
\`\`\`json
{
  "action": "fill" | "click" | "select_option" | "check" | "ask_human",
  "value": "string to type or option to select (leave empty string for click/check)",
  "reasoning": "brief 1-sentence explanation"
}
\`\`\`

### DECISION GUIDELINES:
1. If the element is an input, textarea, contenteditable, or chat container with an unanswered question: Choose "fill" with the precise candidate answer.
2. If the element is a button (e.g. "Save", "Send", "Submit", "Next", "Continue", "Apply"): Choose "click".
3. If the element is a dropdown or list of options: Choose "select_option" with the exact option text.
4. If the element is a checkbox: Choose "check".
5. If the answer is completely unknown and cannot be found in the profile: Choose "ask_human" if uncertain, or infer a standard professional default if in autonomous mode.`;

async function updateTabHud(tabId, hudData) {
  if (!tabId || typeof tabId !== 'number') return;
  // NEVER show workflow HUD on the main All Career portal tab
  try {
    const tab = await getValidTab(tabId);
    if (tab && isAllCareerPageTab(tab)) {
      return;
    }
  } catch (_) {}

  try {
    await chrome.tabs.sendMessage(tabId, { action: 'WORKFLOW_UPDATE_HUD', data: hudData });
  } catch (_) {
    try {
      await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] });
      await new Promise(r => setTimeout(r, 200));
      await chrome.tabs.sendMessage(tabId, { action: 'WORKFLOW_UPDATE_HUD', data: hudData });
    } catch (_) {}
  }
}

async function removeTabHud(tabId) {
  try {
    await chrome.tabs.sendMessage(tabId, { action: 'WORKFLOW_REMOVE_HUD' });
  } catch (_) {}
}

function normalizeWorkflowText(str) {
  if (!str) return '';
  return String(str)
    .toLowerCase()
    .replace(/^bot\s*says?:?/i, '')
    .replace(/^naukri\s*bot:?/i, '')
    .replace(/[?!:;.,/\\()\[\]{}"'’“”\-+_#*]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function findSmartAnswerMatch(targetQuestion, visibleText, targetName, customAnswers = [], profile = {}) {
  const normQ = normalizeWorkflowText(targetQuestion);
  const normText = normalizeWorkflowText(visibleText);
  const normName = normalizeWorkflowText(targetName);
  const combined = `${normQ} ${normName} ${normText}`.trim();
  if (!combined) return null;

  // 1. Check Custom Answers first (exact match, substring match, token match)
  for (const item of customAnswers) {
    if (!item?.question || !item?.answer) continue;
    const itemQ = normalizeWorkflowText(item.question);
    if (!itemQ) continue;

    // Exact match
    if (normQ === itemQ || normName === itemQ || combined === itemQ) {
      return { answer: item.answer, source: 'customAnswers', matchedQuestion: item.question };
    }

    // Substring match
    if (itemQ.length >= 3) {
      if (combined.includes(itemQ) || (normQ && normQ.includes(itemQ)) || (itemQ.includes(normQ) && normQ.length >= 4)) {
        return { answer: item.answer, source: 'customAnswers', matchedQuestion: item.question };
      }
    }

    // Token keyword match (e.g. "what is your name" vs "name")
    const itemTokens = itemQ.split(' ').filter(w => !['what', 'is', 'your', 'please', 'enter', 'the', 'a', 'an', 'provide', 'tell', 'me', 'us'].includes(w) && w.length >= 2);
    if (itemTokens.length > 0) {
      const allTokensMatch = itemTokens.every(tok => combined.includes(tok));
      if (allTokensMatch) {
        return { answer: item.answer, source: 'customAnswers', matchedQuestion: item.question };
      }
    }
  }

  // 2. Candidate Profile Smart Check
  const candidateName = profile.fullName || profile.name;
  if (candidateName) {
    const isNameQuery = /\b(name|full name|first name|candidate name|your name|applicant name)\b/i.test(combined);
    const isNotCompanyOrCollege = !/\b(company|employer|college|university|school|institution|file|resume|reference|father|mother)\b/i.test(combined);
    if (isNameQuery && isNotCompanyOrCollege) {
      return { answer: candidateName, source: 'profile', matchedQuestion: 'Name' };
    }
  }

  const email = profile.email;
  if (email && /\b(email|mail|e mail|email id|email address)\b/i.test(combined) && !/\b(company|reference)\b/i.test(combined)) {
    return { answer: email, source: 'profile', matchedQuestion: 'Email' };
  }

  const phone = profile.phone || profile.mobile;
  if (phone && /\b(phone|mobile|contact|contact number|cell|telephone|whatsapp)\b/i.test(combined) && !/\b(alt|alternate|company)\b/i.test(combined)) {
    return { answer: phone, source: 'profile', matchedQuestion: 'Phone' };
  }

  const city = profile.city || profile.location || profile.address;
  if (city && /\b(city|location|current city|current location|where do you live|residence|town)\b/i.test(combined) && !/\b(company|headquarter)\b/i.test(combined)) {
    return { answer: city, source: 'profile', matchedQuestion: 'Location' };
  }

  const exp = profile.experienceYears || profile.experience;
  if (exp && /\b(experience|years of experience|total experience|work experience)\b/i.test(combined)) {
    return { answer: String(exp), source: 'profile', matchedQuestion: 'Experience' };
  }

  const salary = profile.expectedSalary || profile.currentSalary;
  if (salary && /\b(expected salary|expected ctc|ctc expectation|salary expectation)\b/i.test(combined)) {
    return { answer: String(salary), source: 'profile', matchedQuestion: 'Salary' };
  }

  const notice = profile.noticePeriod;
  if (notice && /\b(notice period|serving notice|availability)\b/i.test(combined)) {
    return { answer: String(notice), source: 'profile', matchedQuestion: 'Notice Period' };
  }

  const edu = profile.degree || profile.education;
  if (edu && /\b(highest qualification|degree|education|qualification)\b/i.test(combined)) {
    return { answer: edu, source: 'profile', matchedQuestion: 'Education' };
  }

  return null;
}

function isKnownActionButton(elemInfo, target, learnedButtons = []) {
  // CRITICAL RULE 1: If there are 2 or more options/choices, this is a MULTIPLE CHOICE question, NEVER an action button!
  if (elemInfo?.options && elemInfo.options.length >= 2) {
    return { isButton: false, reason: 'Element contains multiple options (choices)' };
  }

  // CRITICAL RULE 2: If there is an explicit question and choices or inputs are present, it is an active question!
  if (elemInfo?.question && (elemInfo?.options?.length > 0 || elemInfo?.hasInnerInput || elemInfo?.isContentEditable)) {
    return { isButton: false, reason: 'Element is an active question' };
  }

  // CRITICAL RULE 3: Never treat text inputs or contenteditable as an action button!
  if (elemInfo?.hasInnerInput || elemInfo?.isContentEditable || ['input', 'textarea', 'select'].includes((elemInfo?.tag || '').toLowerCase())) {
    return { isButton: false, reason: 'Element is an input field' };
  }

  const tag = (elemInfo?.tag || '').toLowerCase();
  const targetName = (elemInfo?.targetName || target.text || '').toLowerCase().trim();
  const selector = (target.selector || '').toLowerCase();
  const isButtonFlag = Boolean(elemInfo?.isButton);
  const text = (elemInfo?.text || '').toLowerCase().trim();

  // CRITICAL RULE 4: Radio containers, choice containers, or chat lists are NEVER action buttons!
  const isChoiceOrContainer = /radio|check|option|select|ssrc|singleselect|choice|chatlist|messages|footer/i.test(selector)
    || /radio|check|option|select|ssrc|singleselect/i.test(targetName);
  if (isChoiceOrContainer) {
    return { isButton: false, reason: 'Selector or name indicates choice/radio/container' };
  }

  // CRITICAL RULE 5: Non-button containers (div, ul, li, etc.) are NEVER action buttons unless explicitly flagged isButton by content script!
  const containerTags = ['div', 'ul', 'ol', 'li', 'form', 'section', 'span', 'p', 'main', 'article', 'body'];
  if (containerTags.includes(tag) && !isButtonFlag) {
    return { isButton: false, reason: `Container tag <${tag}> without isButton flag is not an action button` };
  }

  const ACTION_REGEX = /\b(save|submit|next|continue|apply|send|confirm|done|finish|proceed|ok|agree|accept|verify|start|post)\b/i;

  // 1. Check learnedButtons - ONLY for pure short action words, NEVER for selectors or questions!
  for (const lb of learnedButtons) {
    const l = (lb || '').toLowerCase().trim();
    if (!l || l.length > 25 || /^[#\.\[_]|>|\/|\||\?/.test(l)) continue;
    if (targetName === l || text === l) {
      return { isButton: true, reason: `Matches learned button: "${lb}"` };
    }
  }

  // 2. Check Action Keywords on real button elements (<button>, <a>, <input type="button|submit">, [role="button"])
  const isRealButtonElement = isButtonFlag || ['button', 'a'].includes(tag) || (tag === 'input' && ['button', 'submit'].includes(elemInfo?.type));
  if (isRealButtonElement) {
    if (ACTION_REGEX.test(targetName)) {
      return { isButton: true, reason: `Action button keyword matched in name ("${targetName}")` };
    }
    if (text.length <= 40 && ACTION_REGEX.test(text)) {
      return { isButton: true, reason: `Action button keyword matched in text ("${text}")` };
    }
    if (ACTION_REGEX.test(selector)) {
      return { isButton: true, reason: `Action button keyword matched in selector ("${selector}")` };
    }
    if (tag === 'button' && text.length <= 25 && ACTION_REGEX.test(text)) {
      return { isButton: true, reason: `Action button keyword in <button>` };
    }
  }

  return { isButton: false };
}

async function saveLearnedAnswer(customAnswers, question, answer) {
  if (!question || !answer || typeof answer !== 'string') return;
  const cleanQ = question.replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim();
  const cleanAns = answer.trim();
  if (!cleanQ || !cleanAns) return;

  const existingIdx = customAnswers.findIndex(qa => {
    const q1 = normalizeWorkflowText(qa.question);
    const q2 = normalizeWorkflowText(cleanQ);
    return q1 && q2 && (q1 === q2 || (q1.length >= 4 && q2.includes(q1)) || (q2.length >= 4 && q1.includes(q2)));
  });

  if (existingIdx >= 0) {
    customAnswers[existingIdx].answer = cleanAns;
    customAnswers[existingIdx].updatedAt = Date.now();
  } else {
    customAnswers.push({
      id: 'qa_' + Date.now(),
      question: cleanQ,
      answer: cleanAns,
      autoLearned: true,
      createdAt: Date.now(),
    });
  }

  try {
    await chrome.storage.local.set({ customAnswers });
  } catch (_) {}
}

async function saveLearnedButton(learnedButtons, btnIdentifier) {
  const clean = (btnIdentifier || '').trim().toLowerCase();
  if (!clean || clean.length < 2 || clean.length > 25) return;
  // NEVER save CSS selectors, dynamic IDs, or questions as buttons!
  if (/^[#\.\[_]|>|\/|\||\?|\s{3,}/.test(clean)) return;
  if (!learnedButtons.includes(clean)) {
    learnedButtons.push(clean);
    try {
      await chrome.storage.local.set({ learnedButtons });
    } catch (_) {}
  }
}

async function executeAIStepOneByOne(tabId, step, runState) {
  let activeTabId = tabId;
  const targets = extractStepTargets(step);
  const total = targets.length;

  const isProcessStopped = () => {
    return currentBatchController && (currentBatchController.cancelled || !currentBatchController.running || currentBatchController.skipRequested);
  };

  if (isProcessStopped()) {
    if (currentBatchController?.skipRequested) {
      throw new Error('Job skipped by user.');
    }
    throw new Error('Auto Apply was stopped by user.');
  }

  const storeData = await chrome.storage.local.get(['byok_config', 'userProfile', 'customAnswers', 'aiDecisionMode', 'learnedButtons']);
  const config = storeData.byok_config || {
    activeProvider: 'omniroute',
    omniroute: { baseUrl: 'http://127.0.0.1:20128/v1', apiKey: 'sk-f46d845e6a300177-0a895e-fbfbd25b', model: 'antigravity/gemini-3.6-flash-high' },
    gemini: { apiKey: '', model: 'gemini-2.0-flash' },
    openai: { apiKey: '', model: 'gpt-4o' },
  };
  const profile = storeData.userProfile || {};
  const customAnswers = Array.isArray(storeData.customAnswers) ? storeData.customAnswers : [];
  const rawLearnedButtons = Array.isArray(storeData.learnedButtons) ? storeData.learnedButtons : [];
  const learnedButtons = rawLearnedButtons.filter(b => {
    const s = String(b || '').trim().toLowerCase();
    return s && s.length >= 2 && s.length <= 25 && !/^[#\.\[_]|>|\/|\||\?/.test(s);
  });
  const aiDecisionMode = storeData.aiDecisionMode || 'ask_human';
  const actionHistory = [];
  const consecutiveButtonClicks = new Map(); // Tracks consecutive identical button clicks to prevent infinite loops (max 3)

  // Multi-round conversational loop: can handle up to 25 question rounds in a recruiter chatbot
  const MAX_ROUNDS = typeof step.maxQuestions === 'number' ? Math.max(1, Math.min(25, step.maxQuestions)) : 15;
  let lastRecordedQuestion = '';

  runState.logs.push(`[AI Loop] 🚀 Starting conversational AI execution (${total} element(s) per round, max ${MAX_ROUNDS} rounds)...`);
  await chrome.storage.local.set({ workflowRunState: runState });

  for (let round = 1; round <= MAX_ROUNDS; round++) {
    if (isProcessStopped()) {
      throw new Error('Auto Apply was stopped by user.');
    }

    if (round > 1) {
      runState.logs.push(`[AI Loop] 🔄 Starting Conversational Round ${round} of ${MAX_ROUNDS}...`);
      await chrome.storage.local.set({ workflowRunState: runState });
    }

    // Process all elements configured in this step sequentially
    for (let idx = 0; idx < total; idx++) {
      if (isProcessStopped()) {
        throw new Error('Auto Apply was stopped by user.');
      }
      const target = targets[idx];
      const elemNumber = idx + 1;
      runState.logs.push(`[AI Loop] 🔍 [Round ${round} | Element ${elemNumber}/${total}] Inspecting element: "${target.selector || target.text || 'element'}"...`);
      await chrome.storage.local.set({ workflowRunState: runState });

      // 1. Inspect element in tab with retry if element is rendering
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

      // Wait up to 3.5s if element not yet rendered
      if (!elemInfo?.success && target.selector) {
        const startWait = Date.now();
        while (Date.now() - startWait < 3500) {
          await new Promise(r => setTimeout(r, 350));
          try {
            elemInfo = await chrome.tabs.sendMessage(activeTabId, { action: 'WORKFLOW_READ_TARGET', target });
            if (elemInfo?.success) break;
          } catch (_) {}
        }
      }

      const tag = (elemInfo?.tag || '').toLowerCase();
      const targetName = elemInfo?.targetName || target.text || '';
      const visibleText = elemInfo?.text || '';
      const extractedQuestion = elemInfo?.question || '';
      const targetQuestion = extractedQuestion || (tag === 'div' && visibleText.length > 5 && visibleText.length < 300 ? visibleText : '') || targetName;
      const options = Array.isArray(elemInfo?.options) ? elemInfo.options : [];
      const hasInnerInput = Boolean(elemInfo?.hasInnerInput);
      const isButton = Boolean(elemInfo?.isButton);
      const isDisabled = Boolean(elemInfo?.isDisabled);
      const htmlSnippet = (elemInfo?.htmlSnippet || '').slice(0, 800);

      if (targetQuestion) {
        lastRecordedQuestion = targetQuestion;
      }

      // Update HUD with inspected element & question
      await updateTabHud(activeTabId, {
        workflowName: runState.workflowName,
        stepIndex: runState.stepIndex || 0,
        totalSteps: runState.stepCount || 1,
        stepName: step.name || 'AI Chat Step',
        status: 'running',
        elementIndex: elemNumber,
        totalElements: total,
        question: targetQuestion ? targetQuestion.slice(0, 150) : undefined,
        actionTaken: isButton ? `Detected button: "${targetName}" (${isDisabled ? 'Disabled - requires typing first' : 'Active'})` : 'Analyzing question context...',
      });

      // 2. Intelligent Decision Logic: Memorized Button vs 1-Option vs 2+ Options vs Known Question vs AI
      let aiDecision = null;
      const buttonCheck = isKnownActionButton(elemInfo, target, learnedButtons);

      // A. IS THIS A BUTTON? (Save, Submit, Next, Send, or in learnedButtons)
      // -> Bypass AI completely! Click directly and memorize for future jobs!
      if (buttonCheck.isButton) {
        aiDecision = {
          action: 'click',
          value: '',
          reasoning: `⚡ Auto-detected button: ${buttonCheck.reason} (bypassed AI)`
        };
        runState.logs.push(`[AI Loop] ⚡ Button detected: "${targetName || target.selector}" (${buttonCheck.reason}). Bypassing AI and directly clicking.`);
        if (targetName) {
          await saveLearnedButton(learnedButtons, targetName);
        }
      }
      // B. DROPDOWN / CHOICE WITH ONLY 1 OPTION?
      // -> Bypass AI! Auto-select that single choice directly and memorize!
      else if (options.length === 1) {
        const singleOption = options[0];
        aiDecision = {
          action: 'select_option',
          value: singleOption,
          reasoning: `⚡ Single option available: "${singleOption}" (auto-selected without AI)`
        };
        runState.logs.push(`[AI Loop] ⚡ Choice has only 1 option ("${singleOption}"). Auto-selecting without AI.`);
        if (targetQuestion) {
          await saveLearnedAnswer(customAnswers, targetQuestion, singleOption);
        }
      }
      // C. DROPDOWN / RADIO BUTTONS WITH 2 OR MORE OPTIONS: Check customAnswers first; if none, ask AI!
      else if (options.length >= 2) {
        const smartMatch = findSmartAnswerMatch(targetQuestion, visibleText, '', customAnswers, profile);
        let matchedOption = null;
        if (smartMatch && smartMatch.answer) {
          const val = smartMatch.answer.toLowerCase().trim();
          matchedOption = options.find(opt => {
            const o = opt.toLowerCase().trim();
            return o === val || o.includes(val) || val.includes(o);
          });
        }

        if (matchedOption) {
          aiDecision = {
            action: 'select_option',
            value: matchedOption,
            reasoning: `⚡ Reused saved answer for choice: "${matchedOption}" (source: ${smartMatch.source})`
          };
          runState.logs.push(`[AI Loop] ⚡ Question "${targetQuestion}" has ${options.length} options, matched saved answer ("${matchedOption}"). Reusing without AI.`);
        } else {
          // Ask AI what to do for this 2+ option multiple-choice / dropdown!
          runState.logs.push(`[AI Loop] 🤖 Question "${targetQuestion}" has ${options.length} options: ${JSON.stringify(options.slice(0, 10))}. Asking AI to choose...`);
          await chrome.storage.local.set({ workflowRunState: runState });

          const systemPrompt = `${UNIVERSAL_WORKFLOW_AI_SYSTEM_PROMPT}

Candidate Profile:
${JSON.stringify(profile, null, 2)}

Saved Custom Answers:
${customAnswers.map(qa => `- Q: ${qa.question} -> A: ${qa.answer}`).join('\n')}

${step.customPrompt ? `User Instruction for this step: ${step.customPrompt}` : ''}

Previous actions in this loop:
${actionHistory.length > 0 ? actionHistory.map(h => `- Step ${h.elementNumber}: ${h.action.toUpperCase()} on "${h.target}" ${h.value ? `("${h.value}")` : ''}`).join('\n') : 'None (this is the first element)'}`;

          const choiceUserPrompt = `Element ${elemNumber} of ${total}:
Question / Label: "${targetQuestion || targetName}"
Visible Text / Context: "${visibleText.slice(0, 300)}"
Available Options (${options.length} choices):
${JSON.stringify(options.slice(0, 30))}

INSTRUCTION: You must pick EXACTLY ONE option from the Available Options list that best fits the candidate profile.
Return valid JSON: {"thought": "...", "action": "select_option", "value": "<exact option text>"}
`;
          try {
            const rawResponse = await callActiveAIModel(config, systemPrompt, [{ role: 'user', content: choiceUserPrompt }]);
            aiDecision = parseAiActionJson(rawResponse);
            if (aiDecision.value) {
              const found = options.find(o => o.toLowerCase().trim() === aiDecision.value.toLowerCase().trim())
                || options.find(o => o.toLowerCase().includes(aiDecision.value.toLowerCase()) || aiDecision.value.toLowerCase().includes(o.toLowerCase()));
              if (found) aiDecision.value = found;
            }
            if (!aiDecision.value && options.length > 0) {
              aiDecision.value = options[0];
            }
            aiDecision.action = 'select_option';

            // Auto-save AI's choice to customAnswers so future applications don't need AI!
            if (targetQuestion && aiDecision.value) {
              await saveLearnedAnswer(customAnswers, targetQuestion, aiDecision.value);
              runState.logs.push(`[AI Loop] 💾 Auto-memorized answer for "${targetQuestion}" ➔ "${aiDecision.value}" for future jobs.`);
            }
          } catch (aiErr) {
            console.warn(`[AI Loop] AI choice call failed:`, aiErr);
            const errMsg = aiErr.message || String(aiErr);
            if (isProcessStopped()) throw aiErr;
            if (/omniroute|api key|failed to fetch|health check|connection refused|127\.0\.0\.1:20128/i.test(errMsg)) {
              let displayErr = errMsg;
              if (/failed to fetch|connection refused/i.test(errMsg)) {
                displayErr = 'OmniRoute local server is not running on http://127.0.0.1:20128. Please start the OmniRoute server, or add an AI API key (Gemini, OpenAI, Groq) in Extension Settings (⚙️).';
              }
              runState.logs.push(`[AI Loop] ❌ AI call failed: ${displayErr}`);
              runState.status = 'error';
              runState.error = displayErr;
              await chrome.storage.local.set({ workflowRunState: runState });
              await updateTabHud(activeTabId, {
                workflowName: runState.workflowName,
                stepIndex: runState.stepIndex || 0,
                totalSteps: runState.stepCount || 1,
                stepName: step.name || 'AI Chat Step',
                status: 'error',
                elementIndex: elemNumber,
                totalElements: total,
                actionTaken: `⚠️ ${displayErr}`,
                aiUnavailable: true,
                aiErrorText: displayErr,
              });
              throw new Error(displayErr);
            }
            aiDecision = { action: 'select_option', value: options[0], reasoning: 'Fallback: first option selected' };
          }
        }
      }
      // D. TEXT QUESTION / INPUT FIELD / CHAT INPUT CONTAINER
      else {
        // Check if question was already answered previously or is in candidate profile!
        const smartMatch = findSmartAnswerMatch(targetQuestion, visibleText, '', customAnswers, profile);
        if (smartMatch && smartMatch.answer && (['input', 'textarea'].includes(tag) || hasInnerInput || tag === 'div')) {
          aiDecision = {
            action: 'fill',
            value: smartMatch.answer,
            reasoning: `⚡ Reused saved answer for "${targetQuestion || targetName}": "${smartMatch.answer}" (source: ${smartMatch.source})`
          };
          runState.logs.push(`[AI Loop] ⚡ Question already asked/known ("${targetQuestion || targetName}"). Bypassing AI and directly typing: "${smartMatch.answer}"`);
        } else {
          // Unknown question: Ask AI to answer
          const systemPrompt = `${UNIVERSAL_WORKFLOW_AI_SYSTEM_PROMPT}

Candidate Profile:
${JSON.stringify(profile, null, 2)}

Saved Custom Answers:
${customAnswers.map(qa => `- Q: ${qa.question} -> A: ${qa.answer}`).join('\n')}

${step.customPrompt ? `User Instruction for this step: ${step.customPrompt}` : ''}

Previous actions in this loop:
${actionHistory.length > 0 ? actionHistory.map(h => `- Step ${h.elementNumber}: ${h.action.toUpperCase()} on "${h.target}" ${h.value ? `("${h.value}")` : ''}`).join('\n') : 'None (this is the first element)'}`;

          const userPrompt = `Element ${elemNumber} of ${total}:
Tag: <${tag || 'element'}>
Label / Name: "${targetName}"
Extracted Question: "${targetQuestion}"
Visible Text / Context: "${visibleText.slice(0, 400)}"
${hasInnerInput ? 'Has Nested Input Field: YES (contenteditable / textarea / input detected inside this container)' : ''}
${isButton ? `Is Button: YES (Currently ${isDisabled ? 'DISABLED - activates after typing' : 'ENABLED'})` : ''}
${options.length > 0 ? `Available Options: ${JSON.stringify(options.slice(0, 30))}` : ''}
HTML: ${htmlSnippet}`;

          try {
            runState.logs.push(`[AI Loop] 🤖 Sending Element ${elemNumber}/${total} to AI...`);
            await chrome.storage.local.set({ workflowRunState: runState });
            const rawResponse = await callActiveAIModel(config, systemPrompt, [{ role: 'user', content: userPrompt }]);
            aiDecision = parseAiActionJson(rawResponse);

            // AUTO-SAVE AI's response to customAnswers for ALL future jobs!
            if (aiDecision.action === 'fill' && aiDecision.value && targetQuestion) {
              await saveLearnedAnswer(customAnswers, targetQuestion, aiDecision.value);
              runState.logs.push(`[AI Loop] 💾 Auto-memorized answer for "${targetQuestion}" ➔ "${aiDecision.value}" for all future jobs.`);
            } else if (aiDecision.action === 'click' && targetName) {
              await saveLearnedButton(learnedButtons, targetName);
            }
          } catch (aiErr) {
            console.warn(`[AI Loop] AI call failed for Element ${elemNumber}:`, aiErr);
            const errMsg = aiErr.message || String(aiErr);
            if (isProcessStopped()) throw aiErr;
            if (/omniroute|api key|failed to fetch|health check|connection refused|timed out|127\.0\.0\.1:20128/i.test(errMsg)) {
              let displayErr = errMsg;
              if (/failed to fetch|connection refused|timed out/i.test(errMsg)) {
                displayErr = 'OmniRoute local server is not running on http://127.0.0.1:20128. Please start the OmniRoute server, or add an AI API key (Gemini, OpenAI, Groq) in Extension Settings (⚙️).';
              }
              runState.logs.push(`[AI Loop] ❌ AI unavailable: ${displayErr}`);
              runState.status = 'error';
              runState.error = displayErr;
              await chrome.storage.local.set({ workflowRunState: runState });
              await updateTabHud(activeTabId, {
                workflowName: runState.workflowName,
                stepIndex: runState.stepIndex || 0,
                totalSteps: runState.stepCount || 1,
                stepName: step.name || 'AI Chat Step',
                status: 'error',
                elementIndex: elemNumber,
                totalElements: total,
                actionTaken: `⚠️ ${displayErr}`,
                aiUnavailable: true,
                aiErrorText: displayErr,
              });
              throw new Error(displayErr);
            }
            if (isButton || ['button', 'a'].includes(tag) || /button|submit|save|continue|next/i.test(targetName)) {
              aiDecision = { action: 'click', value: '', reasoning: 'Fallback: button detected' };
              if (targetName) await saveLearnedButton(learnedButtons, targetName);
            } else if (options.length > 0) {
              aiDecision = { action: 'select_option', value: options[0], reasoning: 'Fallback: first option selected' };
            } else {
              const fallbackAns = profile.fullName || profile.name || 'ragesh';
              aiDecision = { action: 'fill', value: fallbackAns, reasoning: 'Fallback: profile fill' };
            }
          }
        }
      }

      // Check if Human Fallback is requested or needed when answer is unknown
      if (aiDecisionMode === 'ask_human' && (aiDecision.action === 'ask_human' || (!aiDecision.value && aiDecision.action === 'fill' && !aiDecision.reasoning?.includes('Reused saved answer')))) {
        const promptQ = targetQuestion || visibleText.slice(0, 150) || targetName || 'Application Question';
        await updateTabHud(activeTabId, {
          workflowName: runState.workflowName,
          stepIndex: runState.stepIndex || 0,
          totalSteps: runState.stepCount || 1,
          stepName: step.name || 'AI Chat Step',
          status: 'asking_human',
          elementIndex: elemNumber,
          totalElements: total,
          question: promptQ,
          actionTaken: 'Waiting for your answer in tab pop-up...',
        });

        runState.logs.push(`[AI Loop] 👤 Question unknown: "${promptQ}". Waiting for user response in tab modal...`);
        await chrome.storage.local.set({ workflowRunState: runState });

        try {
          const modalRes = await chrome.tabs.sendMessage(activeTabId, {
            action: 'SHOW_INPAGE_QUESTION_MODAL',
            data: {
              question: promptQ,
              defaultAnswer: '',
            },
          });

          if (modalRes?.success && modalRes.answer) {
            aiDecision = {
              action: 'fill',
              value: modalRes.answer,
              reasoning: 'Answer provided directly by user in tab modal',
            };
            await saveLearnedAnswer(customAnswers, promptQ, modalRes.answer);
            runState.logs.push(`[AI Loop] 💾 Auto-memorized answer for "${promptQ}" ➔ "${modalRes.answer}".`);
          } else {
            aiDecision = {
              action: 'fill',
              value: profile.education || profile.experience || '',
              reasoning: 'User skipped modal; profile fallback applied',
            };
          }
        } catch (mErr) {
          console.warn('[AI Loop] showInPageQuestionModal error:', mErr);
        }
      }

      runState.logs.push(`[AI Loop] ✅ [Element ${elemNumber}/${total}] AI Decision: ${aiDecision.action.toUpperCase()} ${aiDecision.value ? `("${aiDecision.value}")` : ''} - ${aiDecision.reasoning || ''}`);
      await chrome.storage.local.set({ workflowRunState: runState });

      // Update HUD with chosen action & answer
      await updateTabHud(activeTabId, {
        workflowName: runState.workflowName,
        stepIndex: runState.stepIndex || 0,
        totalSteps: runState.stepCount || 1,
        stepName: step.name || 'AI Chat Step',
        status: 'running',
        elementIndex: elemNumber,
        totalElements: total,
        question: targetQuestion ? targetQuestion.slice(0, 150) : undefined,
        aiOutput: aiDecision.value ? `"${aiDecision.value}"` : (aiDecision.action === 'click' ? 'Click Save / Button' : aiDecision.action),
        actionTaken: aiDecision.action === 'fill' ? 'Typing answer into chat...' : 'Clicking button...',
      });

      // 3b. Anti-Infinite Loop Guard: If a button is clicked 3 times with no progress/change, skip this job!
      if (aiDecision.action === 'click') {
        const btnKey = (targetName || target.selector || target.text || `elem_${elemNumber}`).toLowerCase().trim();
        const prevClicks = consecutiveButtonClicks.get(btnKey) || 0;
        const newClicks = prevClicks + 1;
        consecutiveButtonClicks.set(btnKey, newClicks);

        if (newClicks >= 3) {
          const skipMsg = `Button "${targetName || 'Action'}" was clicked 3 times without page change. Skipping this job to prevent an infinite loop.`;
          runState.logs.push(`[AI Loop] 🛑 ${skipMsg}`);
          runState.status = 'skipped';
          runState.error = skipMsg;
          await chrome.storage.local.set({ workflowRunState: runState });
          await updateTabHud(activeTabId, {
            workflowName: runState.workflowName,
            stepIndex: runState.stepIndex || 0,
            totalSteps: runState.stepCount || 1,
            stepName: step.name || 'AI Chat Step',
            status: 'error',
            actionTaken: `⏭ ${skipMsg}`,
          });
          throw new Error(skipMsg);
        }
      } else {
        // Reset button clicks if a fill, select_option, or check happened
        consecutiveButtonClicks.clear();
      }

      // 4. Execute the chosen action with 3-ATTEMPT RETRY MECHANISM & DIAGNOSTIC HUD
      const MAX_ATTEMPTS = 3;
      let actionSuccess = false;
      let lastFailureReason = '';

      for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
        if (isProcessStopped()) {
          if (currentBatchController?.skipRequested) {
            throw new Error('Job skipped by user.');
          }
          throw new Error('Auto Apply was stopped by user.');
        }

        // Pre-check target presence in tab
        let check = null;
        try {
          check = await chrome.tabs.sendMessage(activeTabId, { action: 'WORKFLOW_READ_TARGET', target });
        } catch (_) {}

        if (!check?.success) {
          lastFailureReason = `Target element "${targetName || target.selector || 'element'}" not visible on page`;
          if (attempt < MAX_ATTEMPTS) {
            runState.logs.push(`[AI Retry] ⚠️ Attempt ${attempt}/${MAX_ATTEMPTS} failed: ${lastFailureReason}. Retrying in 1s...`);
            await updateTabHud(activeTabId, {
              workflowName: runState.workflowName,
              stepIndex: runState.stepIndex || 0,
              totalSteps: runState.stepCount || 1,
              stepName: step.name || 'AI Chat Step',
              status: 'running',
              elementIndex: elemNumber,
              totalElements: total,
              question: targetQuestion ? targetQuestion.slice(0, 150) : undefined,
              actionTaken: `⚠️ Retry ${attempt}/${MAX_ATTEMPTS}: ${lastFailureReason}...`,
            });
            await chrome.storage.local.set({ workflowRunState: runState });
            await new Promise(r => setTimeout(r, 1000));
            continue;
          }
        }

        // Diagnostic: If clicking a disabled button, wait for activation
        if (aiDecision.action === 'click' && check?.isDisabled) {
          lastFailureReason = `Button "${targetName || 'Save'}" is currently disabled (waiting for activation)`;
          runState.logs.push(`[AI Retry] ⚠️ Attempt ${attempt}/${MAX_ATTEMPTS}: ${lastFailureReason}. Waiting for button to become active...`);
          await updateTabHud(activeTabId, {
            workflowName: runState.workflowName,
            stepIndex: runState.stepIndex || 0,
            totalSteps: runState.stepCount || 1,
            stepName: step.name || 'AI Chat Step',
            status: 'running',
            elementIndex: elemNumber,
            totalElements: total,
            question: targetQuestion ? targetQuestion.slice(0, 150) : undefined,
            actionTaken: `⚠️ Retry ${attempt}/${MAX_ATTEMPTS}: ${lastFailureReason}...`,
          });
          await chrome.storage.local.set({ workflowRunState: runState });
          await new Promise(r => setTimeout(r, 1000));
        }

        try {
          if (aiDecision.action === 'click') {
            // Try smart container save first (handles inner .sendMsg, .send, button, pointer events, and Enter key)
            let clickRes = await chrome.tabs.sendMessage(activeTabId, {
              action: 'WORKFLOW_CLICK_CONTAINER_SAVE',
              target,
            }).catch(() => null);

            if (!clickRes?.clicked) {
              clickRes = await sendWorkflowStepToTab(activeTabId, {
                type: 'click',
                target,
                name: `AI Click: ${targetName || target.selector}`,
              });
            }

            if (clickRes?.success !== false && clickRes?.clicked !== false) {
              actionSuccess = true;
            } else {
              lastFailureReason = clickRes?.error || 'Click had no effect on button';
            }
          } else if (aiDecision.action === 'fill') {
            let fillRes = await chrome.tabs.sendMessage(activeTabId, {
              action: 'WORKFLOW_APPLY_AI_OUTPUT',
              target,
              outputAction: 'fill',
              answer: aiDecision.value,
            }).catch(() => null);

            if (fillRes?.success) {
              actionSuccess = true;
            } else {
              const fbRes = await sendWorkflowStepToTab(activeTabId, {
                type: 'fill',
                target,
                value: aiDecision.value,
                name: `AI Fill: ${targetName || target.selector}`,
              }).catch(err => ({ success: false, error: err.message }));

              if (fbRes?.success !== false) {
                actionSuccess = true;
              } else {
                lastFailureReason = fbRes?.error || 'Typing into field failed';
              }
            }

            // In a 2-element chatbot workflow (Element 1: question, Element 2: typing & save container):
            // After filling answer, automatically click Save in the typing container if Save button is present!
            if (actionSuccess && (total === 2 || elemNumber === total)) {
              await new Promise(r => setTimeout(r, 500));
              const autoSaveRes = await chrome.tabs.sendMessage(activeTabId, {
                action: 'WORKFLOW_CLICK_CONTAINER_SAVE',
                target,
              }).catch(() => null);
              if (autoSaveRes?.clicked) {
                runState.logs.push(`[AI Loop] 💾 Auto-triggered Save button ("${autoSaveRes.buttonText || 'Save'}") after typing.`);
              }
            }
          } else if (aiDecision.action === 'select_option') {
            let selRes = await chrome.tabs.sendMessage(activeTabId, {
              action: 'WORKFLOW_APPLY_AI_OUTPUT',
              target,
              outputAction: 'click',
              answer: aiDecision.value,
            }).catch(() => null);

            if (!selRes?.clicked && !selRes?.success) {
              selRes = await sendWorkflowStepToTab(activeTabId, {
                type: 'select_option',
                target,
                value: aiDecision.value,
                name: `AI Select: ${targetName || target.selector}`,
              }).catch(err => ({ success: false, error: err.message }));
            }

            if (selRes?.success !== false && !selRes?.error) {
              actionSuccess = true;
            } else {
              lastFailureReason = selRes?.error || 'Option not found in dropdown';
            }
          } else if (aiDecision.action === 'check') {
            const chkRes = await sendWorkflowStepToTab(activeTabId, {
              type: 'check',
              target,
              checked: true,
              name: `AI Check: ${targetName || target.selector}`,
            }).catch(err => ({ success: false, error: err.message }));

            if (chkRes?.success !== false) {
              actionSuccess = true;
            } else {
              lastFailureReason = chkRes?.error || 'Checkbox could not be checked';
            }
          }

          if (actionSuccess) break;
        } catch (execErr) {
          lastFailureReason = execErr.message || String(execErr);
        }

        if (!actionSuccess && attempt < MAX_ATTEMPTS) {
          runState.logs.push(`[AI Retry] ⚠️ Attempt ${attempt}/${MAX_ATTEMPTS} failed: ${lastFailureReason}. Retrying in 1s...`);
          await updateTabHud(activeTabId, {
            workflowName: runState.workflowName,
            stepIndex: runState.stepIndex || 0,
            totalSteps: runState.stepCount || 1,
            stepName: step.name || 'AI Chat Step',
            status: 'running',
            elementIndex: elemNumber,
            totalElements: total,
            question: targetQuestion ? targetQuestion.slice(0, 150) : undefined,
            actionTaken: `⚠️ Retry ${attempt}/${MAX_ATTEMPTS}: ${lastFailureReason}...`,
          });
          await chrome.storage.local.set({ workflowRunState: runState });
          await new Promise(r => setTimeout(r, 1000));
        }
      }

      if (!actionSuccess) {
        runState.logs.push(`[AI Loop] ⚠️ All ${MAX_ATTEMPTS} attempts failed on Element ${elemNumber}: ${lastFailureReason}`);
        await chrome.storage.local.set({ workflowRunState: runState });
      }

      actionHistory.push({
        round,
        elementNumber: elemNumber,
        action: aiDecision.action,
        target: targetName || target.selector,
        value: aiDecision.value,
        success: actionSuccess,
      });

      // Brief pause between elements
      await new Promise(r => setTimeout(r, 500));

      // Refresh activeTabId in case action switched tab or navigated
      const valid = await getValidTab(activeTabId);
      if (!valid || isAllCareerPageTab(valid)) {
        if (isProcessStopped()) {
          throw new Error('Auto Apply was stopped by user.');
        }
        activeTabId = await ensureActiveTab(activeTabId, null, runState);
      }
    }

    // 5. POST-ROUND DOM REACTION & CONVERSATIONAL LOOP VERIFICATION
    // Check if Element 2 (or last element / chat container) closed or disappeared
    const lastTarget = targets[targets.length - 1];
    const closeCheck = await chrome.tabs.sendMessage(activeTabId, {
      action: 'WORKFLOW_CONTAINER_DISAPPEARED',
      target: lastTarget,
    }).catch(() => ({ disappeared: false }));

    if (closeCheck?.disappeared) {
      runState.logs.push(`[AI Loop] 🏁 Element 2 / Chatbot container closed! Workflow application submitted successfully.`);
      await updateTabHud(activeTabId, {
        workflowName: runState.workflowName,
        stepIndex: runState.stepIndex || 0,
        totalSteps: runState.stepCount || 1,
        stepName: step.name || 'AI Chat Step',
        status: 'completed',
        actionTaken: '✅ Application submitted / chatbot closed.',
      });
      await chrome.storage.local.set({ workflowRunState: runState });
      return { success: true, activeTabId, actionHistory };
    }

    // If single round configured, exit loop
    if (MAX_ROUNDS === 1) {
      break;
    }

    // Element 2 is STILL OPEN: Wait for page reaction before proceeding to next question!
    runState.logs.push(`[AI Loop] ⏳ Element 2 remains open. Waiting for page reaction / next chatbot question...`);
    await updateTabHud(activeTabId, {
      workflowName: runState.workflowName,
      stepIndex: runState.stepIndex || 0,
      totalSteps: runState.stepCount || 1,
      stepName: step.name || 'AI Chat Step',
      status: 'running',
      actionTaken: '⏳ Waiting for page reaction / next chatbot question...',
    });
    await chrome.storage.local.set({ workflowRunState: runState });

    const reactionRes = await chrome.tabs.sendMessage(activeTabId, {
      action: 'WORKFLOW_WAIT_REACTION',
      questionTarget: targets[0],
      inputTarget: lastTarget,
      previousQuestion: lastRecordedQuestion,
      timeoutMs: 8000,
    }).catch(() => null);

    if (reactionRes?.containerClosed) {
      runState.logs.push(`[AI Loop] 🏁 Chat container closed while waiting for reaction. Completed!`);
      await updateTabHud(activeTabId, {
        workflowName: runState.workflowName,
        stepIndex: runState.stepIndex || 0,
        totalSteps: runState.stepCount || 1,
        stepName: step.name || 'AI Chat Step',
        status: 'completed',
        actionTaken: '✅ Application submitted / chatbot closed.',
      });
      await chrome.storage.local.set({ workflowRunState: runState });
      return { success: true, activeTabId, actionHistory };
    }

    if (reactionRes?.reacted) {
      runState.logs.push(`[AI Loop] 🔄 Page reacted (${reactionRes.reason || 'new question detected'}). Continuing conversational loop to Round ${round + 1}...`);
      await new Promise(r => setTimeout(r, 600));
      continue; // Move to next round
    } else {
      // No reaction after 8s: Re-commit Save button click as requested by user
      runState.logs.push(`[AI Loop] ⚠️ No page reaction after 8s. Re-committing Save button click / Enter...`);
      await updateTabHud(activeTabId, {
        workflowName: runState.workflowName,
        stepIndex: runState.stepIndex || 0,
        totalSteps: runState.stepCount || 1,
        stepName: step.name || 'AI Chat Step',
        status: 'running',
        actionTaken: '⚠️ No page reaction; re-committing Save button...',
      });
      await chrome.storage.local.set({ workflowRunState: runState });

      await chrome.tabs.sendMessage(activeTabId, {
        action: 'WORKFLOW_CLICK_CONTAINER_SAVE',
        target: lastTarget,
      }).catch(() => {});

      await new Promise(r => setTimeout(r, 2000));

      const recheck = await chrome.tabs.sendMessage(activeTabId, {
        action: 'WORKFLOW_CONTAINER_DISAPPEARED',
        target: lastTarget,
      }).catch(() => ({ disappeared: false }));

      if (recheck?.disappeared) {
        runState.logs.push(`[AI Loop] 🏁 Container closed after re-commit Save. Completed!`);
        return { success: true, activeTabId, actionHistory };
      }
    }
  }

  runState.logs.push(`[AI Loop] 🎉 Completed conversational AI step execution.`);
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
  if (isAllCareerPageTab(validTab)) {
    throw new Error(`Cannot execute workflow step on the All Career page tab.`);
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

      // Check if user clicked Stop
      if (currentBatchController && currentBatchController.cancelled) {
        runState.status = 'cancelled';
        runState.error = 'Process stopped by user.';
        await chrome.storage.local.set({ workflowRunState: runState });
        await updateTabHud(activeTabId, {
          workflowName: runState.workflowName,
          stepIndex: i,
          totalSteps: steps.length,
          stepName: 'Stopped',
          status: 'cancelled',
          actionTaken: '⏹ Auto Apply stopped by user.',
        });
        return;
      }

      // Check if main All Career tab was closed
      if (currentBatchController && currentBatchController.mainTabId) {
        const mainTab = await getValidTab(currentBatchController.mainTabId);
        if (!mainTab) {
          runState.status = 'cancelled';
          runState.error = 'Main All Career tab closed.';
          await chrome.storage.local.set({ workflowRunState: runState });
          return;
        }
      }

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

      const stepDesc = step.type === 'click' ? `Clicking "${step.name || 'button'}"...` : (step.type === 'fill' ? `Typing into "${step.name || 'field'}"...` : `Executing ${step.name || step.type}...`);
      await updateTabHud(activeTabId, {
        workflowName: runState.workflowName,
        stepIndex: i,
        totalSteps: steps.length,
        stepName: step.name || step.type,
        status: 'running',
        actionTaken: stepDesc,
      });

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

        // LIVE TEST AI FIRST BEFORE RUNNING AI STEP
        const aiCheck = await verifyActiveAIWorking();
        if (!aiCheck.ok) {
          const errMsg = aiCheck.reason || 'AI is not configured or offline. Please configure your AI settings.';
          runState.logs.push(`[Workflow] ❌ AI Health Check: ${errMsg}`);
          runState.status = 'error';
          runState.error = errMsg;
          runState.finishedAt = Date.now();
          await chrome.storage.local.set({ workflowRunState: runState });
          await updateTabHud(activeTabId, {
            workflowName: runState.workflowName,
            stepIndex: i,
            totalSteps: steps.length,
            stepName: 'AI Config Required',
            status: 'error',
            actionTaken: `⚠️ ${errMsg}`,
            aiUnavailable: true,
            aiErrorText: errMsg,
          });
          console.warn('[BYOK] AI Configuration Required:', errMsg);
          return;
        }

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
          if (currentBatchController && currentBatchController.cancelled) {
            runState.status = 'cancelled';
            runState.error = 'Process stopped by user.';
            await chrome.storage.local.set({ workflowRunState: runState });
            return;
          }

          if (/no tab with id|receiving end does not exist|closed/i.test(stepErr?.message || '')) {
            runState.logs.push(`[BYOK] Connection to tab ${activeTabId} lost. Re-establishing connection...`);
            await chrome.storage.local.set({ workflowRunState: runState }).catch(() => {});
            activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);
            await waitForTabReady(activeTabId);
            try {
              await chrome.scripting.executeScript({ target: { tabId: activeTabId }, files: ['content.js'] });
              await new Promise(r => setTimeout(r, 500));
            } catch (_) {}
            try {
              execRes = await sendWorkflowStepToTab(activeTabId, step, activeLoopIndex, isNaukri ? 'mouse' : 'dom');
            } catch (retryErr) {
              stepErr = retryErr;
            }
          }

          // If still failed or element was not found: Check AI fallback!
          if (!execRes) {
            // Check if page indicates already applied or closed before failing!
            const midStatus = await checkJobPageStatus(activeTabId);
            if (midStatus.status === 'already_applied') {
              runState.logs.push(`[Workflow] ℹ️ Job already applied: ${midStatus.reason}`);
              runState.status = 'completed';
              runState.alreadyApplied = true;
              runState.message = 'Job was already applied previously on this portal.';
              runState.finishedAt = Date.now();
              await chrome.storage.local.set({ workflowRunState: runState });
              await updateTabHud(activeTabId, {
                workflowName: runState.workflowName,
                stepIndex: i,
                totalSteps: steps.length,
                stepName: 'Already Applied',
                status: 'completed',
                actionTaken: '✅ Job already applied previously. Moving to next job...',
              });
              return;
            }
            if (midStatus.status === 'closed') {
              runState.logs.push(`[Workflow] ⚠️ Job is closed: ${midStatus.reason}`);
              runState.status = 'skipped';
              runState.error = 'Job posting is expired or closed.';
              runState.finishedAt = Date.now();
              await chrome.storage.local.set({ workflowRunState: runState });
              await updateTabHud(activeTabId, {
                workflowName: runState.workflowName,
                stepIndex: i,
                totalSteps: steps.length,
                stepName: 'Job Closed',
                status: 'skipped',
                actionTaken: '⚠️ Job posting is closed or expired. Moving to next job...',
              });
              return;
            }

            // Directly attempt AI fallback first!
            let aiFallbackRes = null;
            try {
              aiFallbackRes = await executeAIStepForMissingElement(activeTabId, step, runState);
            } catch (fallbackErr) {
              console.warn('[Workflow] AI fallback attempt caught:', fallbackErr);
            }

            if (aiFallbackRes?.success) {
              runState.logs.push(`[Workflow] ✅ Step ${i + 1} resolved via AI fallback.`);
              await chrome.storage.local.set({ workflowRunState: runState });
              continue;
            }

            // If AI fallback failed, verify AI status to produce an accurate, helpful message
            const aiCheck = await verifyActiveAIWorking();
            const reason = !aiCheck.ok ? aiCheck.reason : (aiFallbackRes?.reason || stepErr?.message || 'Element not found on page.');
            const msg = !aiCheck.ok ? aiCheck.reason : `Element "${step.name || step.type}" not found. ${reason}`;
            runState.logs.push(`[Workflow] ⚠️ ${msg}`);
            runState.error = msg;
            runState.status = 'error';
            runState.finishedAt = Date.now();
            await chrome.storage.local.set({ workflowRunState: runState });
            await updateTabHud(activeTabId, {
              workflowName: runState.workflowName,
              stepIndex: i,
              totalSteps: steps.length,
              stepName: !aiCheck.ok ? 'AI Config Required' : (step.name || step.type),
              status: 'error',
              actionTaken: `⚠️ ${msg}`,
              aiUnavailable: !aiCheck.ok,
              aiErrorText: !aiCheck.ok ? aiCheck.reason : undefined,
            });
            if (!aiCheck.ok) {
              console.warn('[BYOK] AI Configuration Required:', msg);
              return;
            }
            throw new Error(msg);
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
            if (currentBatchController) currentBatchController.currentJobTabId = activeTabId;
            await waitForTabReady(activeTabId);
            await chrome.tabs.update(activeTabId, { active: true }).catch(() => {});
            try {
              await chrome.scripting.executeScript({ target: { tabId: activeTabId }, files: ['content.js'] });
            } catch (_) {}
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
              if (currentBatchController) currentBatchController.currentJobTabId = activeTabId;
              await waitForTabReady(activeTabId);
              await chrome.tabs.update(activeTabId, { active: true }).catch(() => {});
              try {
                await chrome.scripting.executeScript({ target: { tabId: activeTabId }, files: ['content.js'] });
              } catch (_) {}
              await chrome.storage.local.set({ workflowRunState: runState });
            }
          }
        } else if (step.type === 'click') {
          // Responsive check if click (e.g. Apply / Apply on Company Site button) opened a new tab
          const waitLimit = (execRes?.opensNewTab || execRes?.href) ? 3500 : 2200;
          let newTab = null;
          const pollStart = Date.now();

          while (Date.now() - pollStart < waitLimit) {
            if (currentBatchController && (currentBatchController.cancelled || !currentBatchController.running)) break;
            const currentTabs = await chrome.tabs.query({}).catch(() => []);
            newTab = currentTabs.find(t =>
              t.id &&
              !beforeTabs.has(t.id) &&
              !isAllCareerPageTab(t) &&
              !t.url?.startsWith('chrome-extension://')
            );
            if (newTab) break;
            await new Promise(r => setTimeout(r, 200));
          }

          if (newTab?.id) {
            console.log('[BYOK] Action opened new tab:', newTab.id, newTab.url || newTab.pendingUrl);
            runState.logs.push(`[Workflow] 🔀 Switched to newly opened tab ${newTab.id}`);
            activeTabId = newTab.id;
            runState.tabId = activeTabId;
            if (currentBatchController) currentBatchController.currentJobTabId = activeTabId;
            await waitForTabReady(activeTabId);
            await chrome.tabs.update(activeTabId, { active: true }).catch(() => {});
            try {
              await chrome.scripting.executeScript({ target: { tabId: activeTabId }, files: ['content.js'] });
            } catch (_) {}
            await chrome.storage.local.set({ workflowRunState: runState });
          } else if (execRes?.href && /^https?:/i.test(execRes.href)) {
            // If click has an href and no tab opened automatically (e.g. popup blocked), open destination
            console.log('[BYOK] Opening click destination link in new tab:', execRes.href);
            const curTab = await getValidTab(activeTabId);
            const fallbackTab = await chrome.tabs.create({
              url: execRes.href,
              active: true,
              ...(curTab?.id ? { openerTabId: curTab.id } : {}),
              ...(typeof curTab?.windowId === 'number' ? { windowId: curTab.windowId } : {}),
            }).catch(() => null);
            if (fallbackTab?.id) {
              activeTabId = fallbackTab.id;
              runState.tabId = activeTabId;
              if (currentBatchController) currentBatchController.currentJobTabId = activeTabId;
              await waitForTabReady(activeTabId);
              await chrome.tabs.update(activeTabId, { active: true }).catch(() => {});
              try {
                await chrome.scripting.executeScript({ target: { tabId: activeTabId }, files: ['content.js'] });
              } catch (_) {}
              await chrome.storage.local.set({ workflowRunState: runState });
            }
          } else {
            // Re-verify that activeTabId is still alive after action
            activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);
          }
        } else {
          const waitMs = Math.max(350, Math.min(5000, step.waitMs || 500));
          await new Promise(r => setTimeout(r, waitMs));
          activeTabId = await ensureActiveTab(activeTabId, workflow.startUrl, runState);
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
    const { historyRetentionDays: retDaysSuccess } = await chrome.storage.local.get('historyRetentionDays').catch(() => ({}));
    if (retDaysSuccess === 0) {
      await chrome.storage.local.set({ workflowRunState: null });
    } else {
      await chrome.storage.local.set({ workflowRunState: runState });
    }

    await updateTabHud(activeTabId, {
      workflowName: runState.workflowName,
      stepIndex: steps.length - 1,
      totalSteps: steps.length,
      stepName: 'Workflow Completed',
      status: 'completed',
      actionTaken: 'All steps completed successfully!',
    });
    setTimeout(() => {
      removeTabHud(activeTabId);
    }, 5000);
  } catch (err) {
    const isSkipped = currentBatchController?.skipRequested ||
      /skipped|clicked 3 times|infinite loop/i.test(err?.message || '');
    if (isSkipped) {
      console.log('[BYOK] Workflow execution skipped for this job:', err?.message || '');
      runState.status = 'skipped';
      runState.error = err?.message || 'Job skipped.';
      await chrome.storage.local.set({ workflowRunState: runState }).catch(() => {});
      removeTabHud(activeTabId);
      return;
    }

    const isCancelled = currentBatchController?.cancelled ||
      /stopped by user|cancelled by user|closed by user/i.test(err?.message || '');
    if (isCancelled) {
      console.log('[BYOK] Workflow execution stopped/cancelled cleanly.');
      runState.status = 'cancelled';
      runState.error = 'Process stopped by user.';
      await chrome.storage.local.set({ workflowRunState: runState }).catch(() => {});
      removeTabHud(activeTabId);
      return;
    }

    const isAiErr = /omniroute|api key|ai health|ai not working|127\.0\.0\.1:20128/i.test(err?.message || String(err) || runState.error || '');
    if (isAiErr) {
      console.warn('[BYOK] AI Configuration Notice:', err?.message || String(err));
    } else {
      console.error('[BYOK] Workflow execution error:', err);
    }
    runState.status = 'error';
    runState.error = err instanceof Error ? err.message : String(err);
    runState.finishedAt = Date.now();
    runState.logs.push(`Error: ${runState.error}`);
    const { historyRetentionDays: retDaysErr } = await chrome.storage.local.get('historyRetentionDays').catch(() => ({}));
    if (retDaysErr === 0) {
      await chrome.storage.local.set({ workflowRunState: null });
    } else {
      await chrome.storage.local.set({ workflowRunState: runState });
    }

    await updateTabHud(activeTabId, {
      workflowName: runState.workflowName,
      stepIndex: runState.stepIndex || 0,
      totalSteps: steps.length,
      stepName: isAiErr ? 'AI Config Required' : 'Execution Error',
      status: 'error',
      actionTaken: isAiErr ? `⚠️ ${runState.error}` : runState.error,
      aiUnavailable: isAiErr,
      aiErrorText: isAiErr ? runState.error : undefined,
    });
  }
}

// ═══════════════════════════════════════════════════════════════════
// BATCH AUTO APPLY ENGINE (PORTAL WORKFLOW STUDIO & AI ORCHESTRATOR)
// ═══════════════════════════════════════════════════════════════════

let currentBatchController = null;

function normalizeSearchText(input) {
  if (!input) return '';
  let str = String(input);
  try {
    str = decodeURIComponent(str);
  } catch (_) {}
  return str.toLowerCase().replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function normalizeSlug(input) {
  if (!input) return '';
  return normalizeSearchText(input).replace(/[^a-z0-9]/g, '');
}

async function loadAllStoredWorkflows() {
  try {
    const store = await chrome.storage.local.get([WORKFLOWS_KEY, 'workflows', 'customWorkflows', 'allWorkflows']);
    const list1 = Array.isArray(store[WORKFLOWS_KEY]) ? store[WORKFLOWS_KEY] : [];
    const list2 = Array.isArray(store.workflows) ? store.workflows : [];
    const list3 = Array.isArray(store.customWorkflows) ? store.customWorkflows : [];
    const list4 = Array.isArray(store.allWorkflows) ? store.allWorkflows : [];

    const combined = [...list1, ...list2, ...list3, ...list4];
    const seen = new Set();
    const unique = [];
    for (const w of combined) {
      if (w && (w.id || w.name)) {
        const key = w.id || w.name;
        if (!seen.has(key)) {
          seen.add(key);
          unique.push(w);
        }
      }
    }
    return unique;
  } catch (err) {
    console.warn('[BYOK] Error loading stored workflows:', err);
    return [];
  }
}

async function verifyActiveAIWorking() {
  try {
    const store = await chrome.storage.local.get(['byok_config', 'apiKeys']);
    const config = store.byok_config || {};
    const apiKeys = Array.isArray(store.apiKeys) ? store.apiKeys : (Array.isArray(config.apiKeys) ? config.apiKeys : []);

    const activeKeyId = config?.activeKeyId;
    const keyConfig = apiKeys.find(k => k.id === activeKeyId && k.enabled !== false) ||
      apiKeys.find(k => k.enabled !== false) || null;

    const provider = keyConfig?.provider || config?.activeProvider || 'omniroute';
    const apiKey = keyConfig?.key || config?.[provider]?.apiKey || config?.[provider]?.key || '';
    const baseUrl = keyConfig?.baseUrl || config?.[provider]?.baseUrl || '';
    const model = keyConfig?.model || config?.[provider]?.model || '';
    const accountId = keyConfig?.accountId || config?.[provider]?.accountId || '';

    // If cloud provider and key is missing:
    const requiresKey = ['openai', 'gemini', 'groq', 'openrouter', 'mistral', 'cohere', 'nvidia', 'cloudflare', 'huggingface'];
    if (requiresKey.includes(provider) && (!apiKey || String(apiKey).trim().length < 4)) {
      return {
        ok: false,
        provider,
        reason: `No API key configured for ${provider.toUpperCase()}. Please configure an AI API key in Extension Settings (⚙️).`,
        needKey: true,
      };
    }

    // ── SPECIFIC FAST CHECK FOR OMNIROUTE (HEAD REQUEST ~50ms, NO 190KB DOWNLOAD) ──
    if (provider === 'omniroute') {
      const cleanUrl = (baseUrl || 'http://127.0.0.1:20128/v1').replace(/\/+$/, '');
      const rootUrl = cleanUrl.replace(/\/v1$/, '') || 'http://127.0.0.1:20128';
      const headers = {};
      if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

      // 1. Probe /models with HEAD (skips 190KB body, finishes in ~50ms)
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);
        const probeResp = await fetch(`${cleanUrl}/models`, {
          method: 'HEAD',
          signal: controller.signal,
          headers,
        }).catch(() => null);
        clearTimeout(timeoutId);
        if (probeResp && probeResp.status >= 200 && probeResp.status < 400) {
          return { ok: true, provider: 'omniroute', model: model || 'antigravity/gemini-3.6-flash-high' };
        }
      } catch (_) {}

      // 2. Probe root URL with HEAD (returns 307 or 200 in ~50ms)
      try {
        const controllerRoot = new AbortController();
        const timeoutIdRoot = setTimeout(() => controllerRoot.abort(), 2000);
        const probeRoot = await fetch(rootUrl, {
          method: 'HEAD',
          redirect: 'manual',
          signal: controllerRoot.signal,
          headers,
        }).catch(() => null);
        clearTimeout(timeoutIdRoot);
        if (probeRoot && probeRoot.status >= 200 && probeRoot.status < 400) {
          return { ok: true, provider: 'omniroute', model: model || 'antigravity/gemini-3.6-flash-high' };
        }
      } catch (_) {}

      // 3. Fallback between 127.0.0.1 and localhost
      try {
        const altUrl = cleanUrl.includes('127.0.0.1')
          ? cleanUrl.replace('127.0.0.1', 'localhost')
          : cleanUrl.replace('localhost', '127.0.0.1');
        const controllerAlt = new AbortController();
        const timeoutIdAlt = setTimeout(() => controllerAlt.abort(), 2000);
        const probeAlt = await fetch(`${altUrl}/models`, {
          method: 'HEAD',
          signal: controllerAlt.signal,
          headers,
        }).catch(() => null);
        clearTimeout(timeoutIdAlt);
        if (probeAlt && probeAlt.status >= 200 && probeAlt.status < 400) {
          return { ok: true, provider: 'omniroute', model: model || 'antigravity/gemini-3.6-flash-high' };
        }
      } catch (_) {}

      // 4. Fast 1-token POST completion probe
      try {
        const controllerPost = new AbortController();
        const timeoutIdPost = setTimeout(() => controllerPost.abort(), 3000);
        const testPost = await fetch(`${cleanUrl}/chat/completions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...headers },
          body: JSON.stringify({
            model: model || 'antigravity/gemini-3.6-flash-high',
            messages: [{ role: 'user', content: 'hi' }],
            max_tokens: 1,
            stream: false,
          }),
          signal: controllerPost.signal,
        }).catch(() => null);
        clearTimeout(timeoutIdPost);
        if (testPost && testPost.ok) {
          return { ok: true, provider: 'omniroute', model: model || 'antigravity/gemini-3.6-flash-high' };
        }
      } catch (_) {}

      return {
        ok: false,
        provider: 'omniroute',
        reason: 'OmniRoute local server is not running on http://127.0.0.1:20128. Please start the OmniRoute server, or add an AI API key (Gemini, OpenAI, Groq) in Extension Settings (⚙️).',
        needKey: true,
      };
    }

    // ── GENERAL CHECK FOR CLOUD PROVIDERS WITH 15s TIMEOUT ──
    try {
      const testPromise = testApiKeyBackend({ provider, key: apiKey, baseUrl, accountId, model });
      const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('AI health check timed out (15s)')), 15000));
      const testRes = await Promise.race([testPromise, timeoutPromise]);

      if (testRes && testRes.ok) {
        return { ok: true, provider, model };
      } else {
        const errDesc = testRes?.error || 'AI service did not respond';
        return {
          ok: false,
          provider,
          reason: `AI (${provider.toUpperCase()}) test failed: ${errDesc}. Please check your API key in Extension Settings (⚙️).`,
          needKey: true,
        };
      }
    } catch (testErr) {
      const errDesc = testErr.message || String(testErr);
      return {
        ok: false,
        provider,
        reason: `AI (${provider.toUpperCase()}) connection failed: ${errDesc}. Please check your API key in Extension Settings (⚙️).`,
        needKey: true,
      };
    }
  } catch (err) {
    return { ok: false, reason: err.message || 'Error checking AI availability', needKey: true };
  }
}

async function checkHasConfiguredAIKey() {
  try {
    const store = await chrome.storage.local.get(['byok_config', 'apiKeys']);
    const config = store.byok_config || {};
    const apiKeys = Array.isArray(store.apiKeys) ? store.apiKeys : (Array.isArray(config.apiKeys) ? config.apiKeys : []);
    const activeKeyId = config?.activeKeyId;
    const keyConfig = apiKeys.find(k => k.id === activeKeyId && k.enabled !== false) ||
      apiKeys.find(k => k.enabled !== false) || null;
    const provider = keyConfig?.provider || config?.activeProvider || 'omniroute';
    if (provider === 'omniroute' || provider === 'ollama') return true;
    const apiKey = keyConfig?.key || config?.[provider]?.apiKey || config?.[provider]?.key || '';
    return typeof apiKey === 'string' && apiKey.trim().length >= 4;
  } catch (_) {
    return false;
  }
}

function detectJobPortal(job) {
  if (!job) return { name: 'Direct Portal', key: 'custom', domain: '' };

  const rawUrl = String(job.apply_url || job.url || job.link || '');
  const normUrl = normalizeSearchText(rawUrl);
  const normSource = normalizeSearchText(job.source || job.portal || job.platform || job.site || '');
  const normCompany = normalizeSearchText(job.company || '');
  const normTitle = normalizeSearchText(job.title || '');
  const combined = `${normUrl} ${normSource} ${normCompany} ${normTitle}`;

  // 1. Naukri (completely case-insensitive, slug-tolerant)
  if (normUrl.includes('naukri') || normSource.includes('naukri') || combined.includes('naukri')) {
    return { name: 'Naukri', key: 'naukri', domain: 'naukri.com' };
  }

  // 2. Indeed
  if (normUrl.includes('indeed') || normSource.includes('indeed') || combined.includes('indeed')) {
    return { name: 'Indeed', key: 'indeed', domain: 'indeed.com' };
  }

  // 3. LinkedIn
  if (normUrl.includes('linkedin') || normSource.includes('linkedin') || combined.includes('linkedin')) {
    return { name: 'LinkedIn', key: 'linkedin', domain: 'linkedin.com' };
  }

  // 4. Workday
  if (normUrl.includes('workday') || normUrl.includes('myworkdayjobs') || normSource.includes('workday') || combined.includes('workday')) {
    return { name: 'Workday', key: 'workday', domain: 'myworkdayjobs.com' };
  }

  // 5. Internshala
  if (normUrl.includes('internshala') || normSource.includes('internshala') || combined.includes('internshala')) {
    return { name: 'Internshala', key: 'internshala', domain: 'internshala.com' };
  }

  // 6. Unstop
  if (normUrl.includes('unstop') || normSource.includes('unstop') || combined.includes('unstop')) {
    return { name: 'Unstop', key: 'unstop', domain: 'unstop.com' };
  }

  // 7. Foundit / Monster
  if (normUrl.includes('foundit') || normUrl.includes('monster') || normSource.includes('foundit') || combined.includes('foundit')) {
    return { name: 'Foundit', key: 'foundit', domain: 'foundit.in' };
  }

  // 8. Shine
  if (normUrl.includes('shine.com') || normSource.includes('shine') || combined.includes('shine')) {
    return { name: 'Shine', key: 'shine', domain: 'shine.com' };
  }

  // 9. Glassdoor
  if (normUrl.includes('glassdoor') || normSource.includes('glassdoor') || combined.includes('glassdoor')) {
    return { name: 'Glassdoor', key: 'glassdoor', domain: 'glassdoor.com' };
  }

  // 10. Lever
  if (normUrl.includes('lever.co') || normSource.includes('lever')) {
    return { name: 'Lever', key: 'lever', domain: 'lever.co' };
  }

  // 11. Greenhouse
  if (normUrl.includes('greenhouse.io') || normSource.includes('greenhouse')) {
    return { name: 'Greenhouse', key: 'greenhouse', domain: 'greenhouse.io' };
  }

  // 12. SmartRecruiters
  if (normUrl.includes('smartrecruiters') || normSource.includes('smartrecruiters')) {
    return { name: 'SmartRecruiters', key: 'smartrecruiters', domain: 'smartrecruiters.com' };
  }

  // Fallback domain extraction
  try {
    const parsed = new URL(rawUrl.startsWith('http') ? rawUrl : `https://${rawUrl}`);
    const host = parsed.hostname.replace(/^www\./, '').toLowerCase();
    const cleanName = host.split('.')[0];
    return {
      name: cleanName ? (cleanName.charAt(0).toUpperCase() + cleanName.slice(1)) : (job.company || 'Career Portal'),
      key: cleanName || 'custom',
      domain: host,
    };
  } catch (_) {
    return { name: job.company ? `${job.company} Portal` : 'Direct Portal', key: 'custom', domain: '' };
  }
}

function findMatchingWorkflow(workflows, portal, job) {
  if (!Array.isArray(workflows) || workflows.length === 0) return null;

  const pKey = normalizeSlug(portal.key || '');
  const pName = normalizeSlug(portal.name || '');
  const pDomain = normalizeSearchText(portal.domain || '');

  const rawUrl = String(job.apply_url || job.url || job.link || '');
  const normUrl = normalizeSearchText(rawUrl);
  const normSource = normalizeSlug(job.source || job.portal || job.platform || '');
  const normCompany = normalizeSlug(job.company || '');

  // 1. Direct name / slug matching (COMPLETELY CASE-INSENSITIVE)
  // Handles workflows named "NAUKRI", "NAUKRI WORKFLOW", "Naukri", "NAUKRI_AUTO_APPLY"
  let match = workflows.find(w => {
    if (!w || !w.name) return false;
    const wSlug = normalizeSlug(w.name);
    const wText = normalizeSearchText(w.name);

    if (pKey && pKey.length >= 3 && (wSlug.includes(pKey) || wText.includes(pKey))) return true;
    if (pName && pName.length >= 3 && (wSlug.includes(pName) || wText.includes(pName))) return true;
    if (wSlug.length >= 3 && (normUrl.includes(wSlug) || normSource.includes(wSlug))) return true;
    return false;
  });
  if (match) return match;

  // 2. Check workflow startUrl or origin domain
  match = workflows.find(w => {
    if (!w) return false;
    const startUrl = normalizeSearchText(w.startUrl || w.url || '');
    const origin = normalizeSearchText(w.origin || '');
    if (pDomain && pDomain.length >= 4 && (startUrl.includes(pDomain) || origin.includes(pDomain))) return true;
    if (pKey && pKey.length >= 3 && (startUrl.includes(pKey) || origin.includes(pKey))) return true;
    return false;
  });
  if (match) return match;

  // 3. Check workflow tags
  match = workflows.find(w => {
    if (!w || !Array.isArray(w.tags)) return false;
    return w.tags.some(t => {
      const tSlug = normalizeSlug(t);
      return (pKey && tSlug.includes(pKey)) || (pName && tSlug.includes(pName)) || (normSource && tSlug.includes(normSource));
    });
  });
  if (match) return match;

  // 4. Company matching
  if (normCompany && normCompany.length >= 3) {
    match = workflows.find(w => {
      if (!w || !w.name) return false;
      const wSlug = normalizeSlug(w.name);
      return wSlug.includes(normCompany) || normCompany.includes(wSlug);
    });
    if (match) return match;
  }

  // 5. If Naukri job and single workflow exists with relevant name
  if (pKey === 'naukri' || normUrl.includes('naukri') || normSource.includes('naukri')) {
    match = workflows.find(w => {
      if (!w || !w.name) return false;
      const wText = normalizeSearchText(w.name);
      const wStart = normalizeSearchText(w.startUrl || '');
      return wText.includes('naukri') || wStart.includes('naukri');
    });
    if (match) return match;

    if (workflows.length === 1) {
      return workflows[0];
    }
  }

  return null;
}

async function executeAIStepForMissingElement(tabId, step, runState) {
  try {
    const hasAI = await checkHasConfiguredAIKey();
    if (!hasAI) {
      return { success: false, aiUnavailable: true, reason: 'AI API key is not configured in Extension Settings.' };
    }

    runState.logs.push(`[AI Fallback] 🤖 Element "${step.name || step.type}" not found. Requesting AI page inspection...`);
    await updateTabHud(tabId, {
      workflowName: runState.workflowName,
      stepIndex: runState.stepIndex || 0,
      totalSteps: runState.stepCount || 1,
      stepName: step.name || step.type,
      status: 'running',
      actionTaken: `🤖 Element missing: Asking AI to locate "${step.name || step.type}"...`,
    });
    await chrome.storage.local.set({ workflowRunState: runState });

    // 1. Get snapshot of page interactive elements
    const snapshot = await chrome.tabs.sendMessage(tabId, { action: 'GET_ACCESSIBILITY_SNAPSHOT', filter: 'interactive', maxDepth: 8, maxChars: 15000 }).catch(() => null);
    if (!snapshot || !snapshot.pageContent) {
      return { success: false, reason: 'Could not inspect page elements for AI fallback.' };
    }

    // 2. Load candidate profile and custom answers
    const store = await chrome.storage.local.get(['byok_config', 'userProfile', 'customAnswers']);
    const config = store.byok_config || {};
    const profile = store.userProfile || {};

    const prompt = `The automated job workflow tried to execute this step:
Step Name: "${step.name || ''}"
Step Type: "${step.type}"
Expected Target: "${step.target?.selector || step.target?.text || ''}"
${step.value ? `Expected Value to Fill: "${step.value}"` : ''}

However, that exact element was not found on the page (or page structure changed or a popup dialog opened).
Here is the accessibility tree of visible interactive elements currently on the page:
${snapshot.pageContent.slice(0, 10000)}

Candidate Profile:
${JSON.stringify(profile, null, 2)}

INSTRUCTIONS:
1. Identify which interactive element on the page should be interacted with to proceed with this job application (e.g. click "Apply", "Save", "Submit", close an overlay, or type into an input).
2. Choose one ref_id from the tree (e.g. [ref_12]).
3. Return valid JSON only:
\`\`\`json
{
  "ref_id": "ref_X",
  "action": "click" | "type" | "select_option",
  "text": "value if typing",
  "thought": "brief explanation"
}
\`\`\`
`;

    const systemPrompt = "You are an autonomous browser agent resolving missing elements in job applications. Return ONLY the requested JSON block.";
    const aiResponseText = await callActiveAIModel(config, systemPrompt, [{ role: 'user', content: prompt }]);
    const parsed = parseAiActionJson(aiResponseText);

    // Extract ref_id from AI response
    const refMatch = aiResponseText.match(/"ref_id"\s*:\s*"([^"]+)"/) || aiResponseText.match(/ref_\d+/);
    const refId = refMatch ? (refMatch[1] || refMatch[0]) : null;

    if (!refId) {
      return { success: false, reason: 'AI could not identify a replacement element on the page.' };
    }

    if (!runState.aiMissingElementClicks) {
      runState.aiMissingElementClicks = {};
    }
    if (parsed.action === 'click' && refId) {
      runState.aiMissingElementClicks[refId] = (runState.aiMissingElementClicks[refId] || 0) + 1;
      if (runState.aiMissingElementClicks[refId] >= 3) {
        const skipMsg = `AI repeatedly clicked button [${refId}] 3 times without page progress. Skipping this job.`;
        runState.logs.push(`[AI Fallback] 🛑 ${skipMsg}`);
        runState.status = 'skipped';
        runState.error = skipMsg;
        await chrome.storage.local.set({ workflowRunState: runState });
        return { success: false, skipped: true, reason: skipMsg };
      }
    }

    runState.logs.push(`[AI Fallback] ⚡ AI chose replacement action: ${parsed.action.toUpperCase()} on [${refId}] (${parsed.reasoning || ''})`);
    await updateTabHud(tabId, {
      workflowName: runState.workflowName,
      stepIndex: runState.stepIndex || 0,
      totalSteps: runState.stepCount || 1,
      stepName: step.name || step.type,
      status: 'running',
      actionTaken: `⚡ AI executing ${parsed.action} on [${refId}]...`,
    });
    await chrome.storage.local.set({ workflowRunState: runState });

    // Execute agent action on tab
    const execRes = await chrome.tabs.sendMessage(tabId, {
      action: 'EXECUTE_AGENT_ACTION',
      agentAction: parsed.action,
      ref_id: refId,
      text: parsed.value || step.value || '',
      press_enter: true,
    }).catch(err => ({ success: false, error: err.message }));

    if (execRes?.success) {
      runState.logs.push(`[AI Fallback] ✅ AI replacement action executed successfully!`);
      await new Promise(r => setTimeout(r, 1200));
      return { success: true };
    } else {
      return { success: false, reason: execRes?.error || 'AI action execution failed.' };
    }
  } catch (err) {
    return { success: false, reason: err.message || String(err) };
  }
}

function broadcastBatchStatus(controller, latestItem = null) {
  const payload = {
    action: 'ALL_CAREER_BATCH_PROGRESS',
    data: {
      running: controller.running,
      paused: controller.paused,
      total: controller.total,
      currentIndex: controller.currentIndex,
      currentJob: controller.currentJob,
      appliedCount: controller.appliedCount,
      failedCount: controller.failedCount,
      latestItem: latestItem,
    },
  };
  chrome.tabs.query({}, (tabs) => {
    (tabs || []).forEach(t => {
      if (t?.id) {
        chrome.tabs.sendMessage(t.id, payload).catch(() => {});
      }
    });
  });
}

function stopBatchAutoApply(reason = 'Process stopped by user.') {
  if (currentBatchController) {
    currentBatchController.cancelled = true;
    currentBatchController.running = false;
    if (currentBatchController.currentJobTabId) {
      chrome.tabs.remove(currentBatchController.currentJobTabId).catch(() => {});
      currentBatchController.currentJobTabId = null;
    }
    broadcastBatchStatus(currentBatchController);
  }
  // Clear workflowRunState in storage
  chrome.storage.local.set({ workflowRunState: null }).catch(() => {});
  // Remove HUD across all tabs immediately
  chrome.tabs.query({}, (tabs) => {
    (tabs || []).forEach(t => {
      if (t?.id) removeTabHud(t.id);
    });
  });
  return { success: true, stopped: true, reason };
}

async function startBatchAutoApply(jobsList, mainTabId = null) {
  if (!Array.isArray(jobsList) || jobsList.length === 0) {
    return { success: false, error: 'No jobs provided to apply for.' };
  }

  // If already running, clicking start again toggles to STOP!
  if (currentBatchController && currentBatchController.running) {
    console.log('[BatchApply] Batch already running. Stopping execution cleanly.');
    return stopBatchAutoApply('Process stopped by user.');
  }

  const batchId = 'batch_' + Date.now();
  const controller = {
    id: batchId,
    mainTabId: mainTabId,
    currentJobTabId: null,
    running: true,
    paused: false,
    cancelled: false,
    total: jobsList.length,
    currentIndex: 0,
    currentJob: null,
    appliedCount: 0,
    failedCount: 0,
  };
  currentBatchController = controller;

  // Run asynchronously in background
  (async () => {
    try {
      const workflows = await loadAllStoredWorkflows();
      const store = await chrome.storage.local.get('allCareerApplyHistory');
      let history = Array.isArray(store.allCareerApplyHistory) ? store.allCareerApplyHistory : [];

      for (let i = 0; i < jobsList.length; i++) {
        if (controller.cancelled || !controller.running || (currentBatchController && currentBatchController.cancelled)) {
          console.log('[BatchApply] Execution stopped by user.');
          break;
        }

        // Verify if main All Career tab or any All Career tab is still alive
        const anyCareerTab = await isAnyAllCareerTabOpen(controller.mainTabId);
        if (!anyCareerTab) {
          console.log('[BatchApply] All Career tab closed. Halting batch execution.');
          controller.cancelled = true;
          controller.running = false;
          break;
        } else {
          controller.mainTabId = anyCareerTab.id;
        }

        const job = jobsList[i];
        controller.currentIndex = i + 1;
        controller.currentJob = job;
        broadcastBatchStatus(controller);

        let jobResult = { success: false, reason: 'Pending' };
        let mode = 'workflow';
        const portal = detectJobPortal(job);
        const rawTargetUrl = String(job.apply_url || job.url || job.link || '').trim();
        let matchedWorkflow = null;

        try {
          matchedWorkflow = findMatchingWorkflow(workflows, portal, job);
          if (!rawTargetUrl || !rawTargetUrl.startsWith('http')) {
            jobResult = {
              success: false,
              reason: 'No direct web application link found (email/phone only or missing URL).',
            };
          } else if (matchedWorkflow) {
            mode = 'workflow';
            console.log(`[BatchApply] [${i+1}/${jobsList.length}] Found recorded workflow "${matchedWorkflow.name}" for portal "${portal.name}". Executing...`);
            jobResult = await runWorkflowForJob(matchedWorkflow, rawTargetUrl, job);

            // IF WORKFLOW FAILED (e.g. page layout is different, redirected to company site, or unmapped form fields):
            // GIVE CONTROL TO AI CONTROL INSTEAD OF SKIPPING THE JOB!
            const isJobSkipped = jobResult.skipped || controller.skipRequested || /skipped|clicked 3 times/i.test(jobResult.reason || '');
            const isJobAlreadyDone = jobResult.success || jobResult.alreadyApplied;
            if (!isJobAlreadyDone && !isJobSkipped && !controller.cancelled && controller.running && (!currentBatchController || !currentBatchController.cancelled)) {
              console.log(`[BatchApply] [${i+1}/${jobsList.length}] Workflow "${matchedWorkflow.name}" could not complete (${jobResult.reason || 'different page structure'}). Handing control over to AI Control...`);
              mode = 'ai';
              const activeTabId = currentBatchController?.currentJobTabId;
              jobResult = await aiDecideAndExecuteJob(rawTargetUrl, job, activeTabId);
            }
          } else {
            mode = 'ai';
            console.log(`[BatchApply] [${i+1}/${jobsList.length}] No recorded workflow for "${portal.name}". Handing control over to AI Control...`);
            jobResult = await aiDecideAndExecuteJob(rawTargetUrl, job);
          }
        } catch (jobErr) {
          console.warn(`[BatchApply] [${i+1}/${jobsList.length}] Error processing job "${job.title || 'Job'}":`, jobErr);
          jobResult = {
            success: false,
            reason: jobErr?.message || String(jobErr),
          };
        } finally {
          // Clean up any remaining job tab before moving to next job
          if (controller.currentJobTabId) {
            const tabToClose = controller.currentJobTabId;
            controller.currentJobTabId = null;
            chrome.tabs.remove(tabToClose).catch(() => {});
          }
        }

        // Break immediately ONLY if batch was explicitly cancelled or stopped by user
        if (controller.cancelled || !controller.running || (currentBatchController && currentBatchController.cancelled)) {
          console.log('[BatchApply] Execution stopped by user.');
          break;
        }

        if (controller.skipRequested) {
          controller.skipRequested = false;
          jobResult.success = false;
          jobResult.skipped = true;
          jobResult.reason = 'Job skipped by user.';
        }

        const isAlreadyApplied = jobResult.alreadyApplied || /already applied/i.test(jobResult.reason || '');
        if (jobResult.success || isAlreadyApplied) {
          controller.appliedCount++;
        } else {
          controller.failedCount++;
        }

        const isSkippedEntry = jobResult.skipped || /skipped|closed|expired|clicked 3 times/i.test(jobResult.reason || '');
        const historyItem = {
          id: job.id || `app_${Date.now()}_${i}`,
          jobId: job.id || '',
          title: job.title || 'Job Opening',
          company: job.company || 'Company',
          portal: portal.name,
          url: rawTargetUrl,
          status: (jobResult.success || isAlreadyApplied) ? 'applied' : (isSkippedEntry ? 'skipped' : 'not_applied'),
          reason: jobResult.reason || ((jobResult.success || isAlreadyApplied) ? (isAlreadyApplied ? 'Already applied previously on this portal.' : `Successfully submitted via ${mode === 'workflow' ? matchedWorkflow.name : 'AI Control'}`) : 'Application not completed'),
          mode: mode,
          workflowName: matchedWorkflow ? matchedWorkflow.name : null,
          timestamp: Date.now(),
          dateStr: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' }),
        };

        history.unshift(historyItem);
        if (history.length > 500) history = history.slice(0, 500);
        await chrome.storage.local.set({ allCareerApplyHistory: history });

        broadcastBatchStatus(controller, historyItem);

        // Clean up any remaining job tab before moving to next job
        if (controller.currentJobTabId) {
          const tabToClose = controller.currentJobTabId;
          controller.currentJobTabId = null;
          chrome.tabs.remove(tabToClose).catch(() => {});
        }

        // Pause briefly between applications for stability (interruptible every 100ms)
        if (i < jobsList.length - 1 && !controller.cancelled && controller.running && (!currentBatchController || !currentBatchController.cancelled)) {
          for (let s = 0; s < 18; s++) {
            if (controller.cancelled || !controller.running || (currentBatchController && currentBatchController.cancelled)) {
              break;
            }
            await new Promise(r => setTimeout(r, 100));
          }
        }
      }
    } catch (err) {
      const isAi = /omniroute|api key|ai health|ai not working|127\.0\.0\.1:20128/i.test(err?.message || '');
      if (isAi) {
        console.warn('[BatchApply] AI Configuration Notice during batch auto apply:', err?.message || String(err));
      } else {
        console.error('[BatchApply] Error during batch auto apply:', err);
      }
    } finally {
      controller.running = false;
      controller.currentJobTabId = null;
      broadcastBatchStatus(controller);
    }
  })();

  return { success: true, batchId, total: jobsList.length };
}

async function runWorkflowForJob(workflow, targetUrl, job) {
  let createdTab = null;
  try {
    if (currentBatchController && (currentBatchController.cancelled || !currentBatchController.running)) {
      return { success: false, reason: 'Batch auto-apply was stopped by user.' };
    }

    createdTab = await chrome.tabs.create({ url: targetUrl, active: true }).catch(() => null);
    if (!createdTab?.id) {
      return { success: false, reason: 'Failed to open browser tab for this job.' };
    }

    const tabId = createdTab.id;
    if (currentBatchController) {
      currentBatchController.currentJobTabId = tabId;
    }

    await waitForTabReady(tabId);

    if (currentBatchController && (currentBatchController.cancelled || !currentBatchController.running)) {
      chrome.tabs.remove(tabId).catch(() => {});
      return { success: false, reason: 'Batch auto-apply was stopped by user.' };
    }

    // Early deterministic check: Is the job already applied or closed?
    const preCheckStatus = await checkJobPageStatus(tabId);
    if (preCheckStatus.status === 'already_applied') {
      console.log(`[Workflow] ℹ️ Job already applied on "${workflow.name}":`, preCheckStatus.reason);
      await updateTabHud(tabId, {
        workflowName: workflow.name,
        stepIndex: 1,
        totalSteps: 1,
        stepName: 'Already Applied',
        status: 'completed',
        actionTaken: '✅ Job was already applied previously on this portal. Moving to next job...',
      });
      await new Promise(r => setTimeout(r, 1200));
      if (tabId) chrome.tabs.remove(tabId).catch(() => {});
      if (currentBatchController && currentBatchController.currentJobTabId === tabId) {
        currentBatchController.currentJobTabId = null;
      }
      return { success: true, alreadyApplied: true, reason: 'Already applied previously on this portal.' };
    }

    if (preCheckStatus.status === 'closed') {
      console.log(`[Workflow] ⚠️ Job closed on "${workflow.name}":`, preCheckStatus.reason);
      await updateTabHud(tabId, {
        workflowName: workflow.name,
        stepIndex: 1,
        totalSteps: 1,
        stepName: 'Job Closed',
        status: 'skipped',
        actionTaken: '⚠️ Job posting is closed or expired. Moving to next job...',
      });
      await new Promise(r => setTimeout(r, 1200));
      if (tabId) chrome.tabs.remove(tabId).catch(() => {});
      if (currentBatchController && currentBatchController.currentJobTabId === tabId) {
        currentBatchController.currentJobTabId = null;
      }
      return { success: false, skipped: true, reason: 'Job posting is expired or closed.' };
    }

    // Interruptible 1.5s delay
    for (let s = 0; s < 15; s++) {
      if (currentBatchController && (currentBatchController.cancelled || !currentBatchController.running)) {
        chrome.tabs.remove(tabId).catch(() => {});
        return { success: false, reason: 'Batch auto-apply was stopped by user.' };
      }
      await new Promise(r => setTimeout(r, 100));
    }

    // Clone workflow and inject target job URL as starting step/startUrl
    const clonedWf = JSON.parse(JSON.stringify(workflow));
    clonedWf.startUrl = targetUrl;
    if (clonedWf.steps && clonedWf.steps[0] && clonedWf.steps[0].type === 'open_url') {
      clonedWf.steps[0].value = targetUrl;
      clonedWf.steps[0].target = targetUrl;
    }

    await executeWorkflowRun(clonedWf, tabId, null, {
      JOB_TITLE: job.title || '',
      COMPANY_NAME: job.company || '',
      APPLY_URL: targetUrl,
    });

    const stateRes = await chrome.storage.local.get('workflowRunState');
    const runState = stateRes.workflowRunState;
    if (currentBatchController && currentBatchController.cancelled) {
      if (createdTab?.id) chrome.tabs.remove(tabId).catch(() => {});
      return { success: false, reason: 'Batch auto-apply was stopped by user.' };
    }

    if (currentBatchController?.skipRequested || runState?.status === 'skipped' || /skipped|clicked 3 times/i.test(runState?.error || '')) {
      if (createdTab?.id) chrome.tabs.remove(tabId).catch(() => {});
      return { success: false, skipped: true, reason: runState?.error || 'Job skipped.' };
    }

    const isSuccess = runState?.status === 'completed';
    const isAlreadyApplied = runState?.alreadyApplied || /already applied/i.test(runState?.message || '');
    const reason = (isSuccess || isAlreadyApplied)
      ? (isAlreadyApplied ? 'Already applied previously on this portal.' : `Successfully applied via "${workflow.name}" workflow!`)
      : (runState?.error || 'Workflow steps could not complete on this job listing.');

    // Close tab on completion or already applied
    if ((isSuccess || isAlreadyApplied) && createdTab?.id) {
      setTimeout(() => chrome.tabs.remove(tabId).catch(() => {}), 1500);
      if (currentBatchController && currentBatchController.currentJobTabId === tabId) {
        currentBatchController.currentJobTabId = null;
      }
    }

    return { success: isSuccess || isAlreadyApplied, alreadyApplied: isAlreadyApplied, reason };
  } catch (err) {
    if (createdTab?.id && currentBatchController?.currentJobTabId === createdTab.id) {
      currentBatchController.currentJobTabId = null;
    }
    return { success: false, reason: `Workflow failed: ${err instanceof Error ? err.message : String(err)}` };
  }
}

async function runAIOrchestratorForJob(targetUrl, job, existingTabId = null) {
  let createdTab = null;
  let tabId = null;
  try {
    if (currentBatchController && (currentBatchController.cancelled || !currentBatchController.running)) {
      return { success: false, reason: 'Batch auto-apply was stopped by user.' };
    }

    // Check if an existing open tab can be reused (e.g. newly opened external company portal)
    if (existingTabId) {
      const valid = await getValidTab(existingTabId);
      if (valid && !isAllCareerPageTab(valid)) {
        tabId = valid.id;
        console.log(`[AI Orchestrator] Reusing currently open job tab ${tabId} (${valid.url || ''})`);
      }
    }

    if (!tabId) {
      createdTab = await chrome.tabs.create({ url: targetUrl, active: true }).catch(() => null);
      if (!createdTab?.id) {
        return { success: false, reason: 'Failed to open browser tab for this job.' };
      }
      tabId = createdTab.id;
    }

    if (currentBatchController) {
      currentBatchController.currentJobTabId = tabId;
    }

    await waitForTabReady(tabId);
    await chrome.tabs.update(tabId, { active: true }).catch(() => {});

    // Ensure content script is injected on this tab
    try {
      await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] });
    } catch (_) {}

    if (currentBatchController && (currentBatchController.cancelled || !currentBatchController.running)) {
      if (tabId) chrome.tabs.remove(tabId).catch(() => {});
      return { success: false, reason: 'Batch auto-apply was stopped by user.' };
    }

    // Interruptible 1.5s delay
    for (let s = 0; s < 15; s++) {
      if (currentBatchController && (currentBatchController.cancelled || !currentBatchController.running)) {
        if (tabId) chrome.tabs.remove(tabId).catch(() => {});
        return { success: false, reason: 'Batch auto-apply was stopped by user.' };
      }
      await new Promise(r => setTimeout(r, 100));
    }

    const outcome = await new Promise((resolve) => {
      const timeoutId = setTimeout(() => {
        resolve({
          success: false,
          reason: 'Application timeout (page required external account login, Captcha, or manual review).',
        });
      }, 40000);

      const termListener = (msg, sender) => {
        if (sender.tab?.id === tabId && msg?.action === 'ORCHESTRATOR_TERMINAL') {
          clearTimeout(timeoutId);
          chrome.runtime.onMessage.removeListener(termListener);
          const ok = msg.state === 'success' || msg.completionConfirmed === true;
          let failReason = msg.reason || 'Could not complete all form fields automatically.';
          if (msg.state === 'manual_review') {
            failReason = 'Requires user input / login verification before submitting.';
          } else if (msg.state === 'blocked') {
            failReason = msg.reason || 'Job application is closed or requires external account login.';
          }
          resolve({ success: ok, reason: ok ? 'Successfully auto-applied via AI Form Orchestrator!' : failReason });
        }
      };
      chrome.runtime.onMessage.addListener(termListener);

      chrome.tabs.sendMessage(tabId, { action: 'START_ORCHESTRATOR', jobData: job }).catch(err => {
        clearTimeout(timeoutId);
        chrome.runtime.onMessage.removeListener(termListener);
        resolve({ success: false, reason: `Failed to initialize AI orchestrator: ${err.message}` });
      });
    });

    if (tabId && !isAllCareerPageTab({ id: tabId })) {
      setTimeout(() => chrome.tabs.remove(tabId).catch(() => {}), outcome.success ? 2000 : 1000);
    }

    if (currentBatchController && currentBatchController.currentJobTabId === tabId) {
      currentBatchController.currentJobTabId = null;
    }

    return outcome;
  } catch (err) {
    if (tabId && currentBatchController?.currentJobTabId === tabId) {
      currentBatchController.currentJobTabId = null;
    }
    return { success: false, reason: `AI application error: ${err instanceof Error ? err.message : String(err)}` };
  }
}




async function aiDecideAndExecuteJob(targetUrl, job, existingTabId = null) {
  let createdTab = null;
  let tabId = existingTabId;

  try {
    if (currentBatchController && (currentBatchController.cancelled || !currentBatchController.running)) {
      return { success: false, reason: 'Batch auto-apply was stopped by user.' };
    }

    if (!tabId) {
      createdTab = await chrome.tabs.create({ url: targetUrl, active: true }).catch(() => null);
      if (!createdTab?.id) {
        return { success: false, reason: 'Failed to open browser tab for this job.' };
      }
      tabId = createdTab.id;
    }

    if (currentBatchController) {
      currentBatchController.currentJobTabId = tabId;
    }

    await waitForTabReady(tabId);
    await chrome.tabs.update(tabId, { active: true }).catch(() => {});

    try {
      await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] });
    } catch (_) {}

    // Allow page to settle (interruptible 1.2s delay)
    for (let s = 0; s < 12; s++) {
      if (currentBatchController && (currentBatchController.cancelled || !currentBatchController.running)) {
        if (tabId) chrome.tabs.remove(tabId).catch(() => {});
        return { success: false, reason: 'Batch auto-apply was stopped by user.' };
      }
      await new Promise(r => setTimeout(r, 100));
    }

    // 1. FAST DETERMINISTIC PAGE STATUS CHECK
    const pageStatus = await checkJobPageStatus(tabId);
    if (pageStatus.status === 'already_applied') {
      console.log(`[AI Control] Page indicates job already applied (${pageStatus.reason}).`);
      await updateTabHud(tabId, {
        workflowName: 'AI Control',
        stepIndex: 1,
        totalSteps: 1,
        stepName: 'Already Applied',
        status: 'completed',
        actionTaken: '✅ Job was already applied previously on this portal. Moving to next job...',
      });
      await new Promise(r => setTimeout(r, 1200));
      if (tabId) chrome.tabs.remove(tabId).catch(() => {});
      if (currentBatchController && currentBatchController.currentJobTabId === tabId) {
        currentBatchController.currentJobTabId = null;
      }
      return {
        success: true,
        alreadyApplied: true,
        reason: pageStatus.reason || 'Job already applied previously on this portal.',
      };
    }

    if (pageStatus.status === 'closed') {
      console.log(`[AI Control] Job posting is closed or expired (${pageStatus.reason}).`);
      await updateTabHud(tabId, {
        workflowName: 'AI Control',
        stepIndex: 1,
        totalSteps: 1,
        stepName: 'Job Closed',
        status: 'skipped',
        actionTaken: '⚠️ Job posting is closed or expired. Moving to next job...',
      });
      await new Promise(r => setTimeout(r, 1200));
      if (tabId) chrome.tabs.remove(tabId).catch(() => {});
      if (currentBatchController && currentBatchController.currentJobTabId === tabId) {
        currentBatchController.currentJobTabId = null;
      }
      return {
        success: false,
        skipped: true,
        reason: pageStatus.reason || 'Job posting is no longer accepting applications.',
      };
    }

    // 2. CHECK AI HEALTH
    const aiCheck = await verifyActiveAIWorking();
    if (!aiCheck.ok) {
      console.warn(`[AI Control] AI is offline (${aiCheck.reason}). Falling back to form orchestrator...`);
      return await runAIOrchestratorForJob(targetUrl, job, tabId);
    }

    // 3. RETRIEVE PAGE SNAPSHOT & ACCESSIBILITY TREE FOR AI CONTROL
    await updateTabHud(tabId, {
      workflowName: 'AI Control',
      stepIndex: 1,
      totalSteps: 2,
      stepName: 'AI Analyzing Page',
      status: 'running',
      actionTaken: '🤖 AI inspecting page structure, buttons, and status to decide next action...',
    });

    let snapshot = null;
    try {
      snapshot = await chrome.tabs.sendMessage(tabId, {
        action: 'GET_ACCESSIBILITY_SNAPSHOT',
        filter: 'interactive',
        maxDepth: 10,
        maxChars: 15000,
      });
    } catch (_) {}

    let pageTextRes = null;
    try {
      pageTextRes = await chrome.tabs.sendMessage(tabId, {
        action: 'GET_FULL_PAGE_CONTENT',
        maxCharacters: 5000,
      });
    } catch (_) {}

    const pageText = (pageTextRes?.content || '').slice(0, 3000);
    const elementsTree = snapshot?.tree || 'No accessibility tree available.';

    // 4. PROMPT AI TO DECIDE ACTION
    const configRes = await chrome.storage.local.get(null);
    const systemPrompt = `You are an elite browser automation engine for job applications.
You inspect job portal web pages and decide the exact action to apply or navigate.

Available decisions:
- "already_applied": The page indicates the user/candidate has already applied to this position (e.g. "Already Applied", "Applied on [date]", "Application submitted").
- "closed": The job listing is closed, expired, filled, or no longer accepting applications.
- "click": There is a clear "Apply", "Easy Apply", "Apply Now", "Apply on Company Site", or "Continue" button/link. Provide its "ref_id".
- "fill_form": An application form is currently visible on the page with input fields (name, email, resume, questions).
- "skip": The page is a login wall, captcha, paywall, 404, or non-job page that cannot be automated.

Output strictly valid JSON with this schema:
{
  "decision": "already_applied" | "closed" | "click" | "fill_form" | "skip",
  "ref_id": number or null,
  "reason": "Brief 1-sentence reason for this decision"
}`;

    const userMessage = `Job to apply for:
Title: "${job.title || ''}"
Company: "${job.company || ''}"
Current URL: "${targetUrl}"

Page Content Preview:
${pageText}

Interactive Elements Snapshot (Accessibility Tree):
${elementsTree}

Analyze the page and determine the next action.`;

    console.log(`[AI Control] Querying AI to decide workflow action for job "${job.title || ''}"...`);
    let aiResponseText = '';
    try {
      aiResponseText = await callActiveAIModel(configRes, systemPrompt, [{ role: 'user', content: userMessage }]);
    } catch (aiErr) {
      console.warn(`[AI Control] AI call failed (${aiErr.message}), falling back to form orchestrator...`);
      return await runAIOrchestratorForJob(targetUrl, job, tabId);
    }

    // 5. PARSE AI DECISION
    let aiDecision = { decision: 'fill_form', ref_id: null, reason: 'Defaulting to form fill' };
    try {
      const jsonMatch = aiResponseText.match(/```(?:json)?\s*([\s\S]*?)\s*```/) || aiResponseText.match(/\{[\s\S]*?\}/);
      if (jsonMatch) {
        aiDecision = JSON.parse((jsonMatch[1] || jsonMatch[0]).trim());
      }
    } catch (parseErr) {
      console.warn('[AI Control] Could not parse AI response JSON:', aiResponseText);
    }

    console.log(`[AI Control] 🤖 AI Decision: "${aiDecision.decision}" - Reason: "${aiDecision.reason || ''}"`);

    // 6. EXECUTE THE AI DECISION
    if (aiDecision.decision === 'already_applied') {
      await updateTabHud(tabId, {
        workflowName: 'AI Control',
        stepIndex: 2,
        totalSteps: 2,
        stepName: 'Already Applied',
        status: 'completed',
        actionTaken: `✅ AI detected: Job already applied previously. (${aiDecision.reason || ''})`,
      });
      await new Promise(r => setTimeout(r, 1200));
      if (tabId) chrome.tabs.remove(tabId).catch(() => {});
      if (currentBatchController && currentBatchController.currentJobTabId === tabId) {
        currentBatchController.currentJobTabId = null;
      }
      return {
        success: true,
        alreadyApplied: true,
        reason: aiDecision.reason || 'AI confirmed job was already applied previously.',
      };
    }

    if (aiDecision.decision === 'closed') {
      await updateTabHud(tabId, {
        workflowName: 'AI Control',
        stepIndex: 2,
        totalSteps: 2,
        stepName: 'Job Closed',
        status: 'skipped',
        actionTaken: `⚠️ AI detected: Job closed/expired. (${aiDecision.reason || ''})`,
      });
      await new Promise(r => setTimeout(r, 1200));
      if (tabId) chrome.tabs.remove(tabId).catch(() => {});
      if (currentBatchController && currentBatchController.currentJobTabId === tabId) {
        currentBatchController.currentJobTabId = null;
      }
      return {
        success: false,
        skipped: true,
        reason: aiDecision.reason || 'Job posting is expired or closed.',
      };
    }

    if (aiDecision.decision === 'skip') {
      await updateTabHud(tabId, {
        workflowName: 'AI Control',
        stepIndex: 2,
        totalSteps: 2,
        stepName: 'Skipped by AI',
        status: 'skipped',
        actionTaken: `⏭️ AI skipped this job: ${aiDecision.reason || 'Unfillable layout'}`,
      });
      await new Promise(r => setTimeout(r, 1200));
      if (tabId) chrome.tabs.remove(tabId).catch(() => {});
      if (currentBatchController && currentBatchController.currentJobTabId === tabId) {
        currentBatchController.currentJobTabId = null;
      }
      return {
        success: false,
        skipped: true,
        reason: aiDecision.reason || 'Skipped by AI decision.',
      };
    }

    if (aiDecision.decision === 'click' && aiDecision.ref_id !== null && aiDecision.ref_id !== undefined) {
      await updateTabHud(tabId, {
        workflowName: 'AI Control',
        stepIndex: 2,
        totalSteps: 3,
        stepName: 'Clicking Apply',
        status: 'running',
        actionTaken: `🖱️ AI clicking element [${aiDecision.ref_id}]...`,
      });

      const clickRes = await chrome.tabs.sendMessage(tabId, {
        action: 'EXECUTE_AGENT_ACTION',
        agentAction: 'click',
        ref_id: Number(aiDecision.ref_id),
      }).catch(() => null);

      console.log('[AI Control] Click result:', clickRes);
      // Wait 2.5s for page transition or modal popup
      await new Promise(r => setTimeout(r, 2500));

      // Re-check page status
      const postClickStatus = await checkJobPageStatus(tabId);
      if (postClickStatus.status === 'already_applied') {
        if (tabId) chrome.tabs.remove(tabId).catch(() => {});
        if (currentBatchController && currentBatchController.currentJobTabId === tabId) {
          currentBatchController.currentJobTabId = null;
        }
        return { success: true, alreadyApplied: true, reason: 'Applied successfully after click.' };
      }

      // If page now has form fields, run orchestrator to fill them
      return await runAIOrchestratorForJob(targetUrl, job, tabId);
    }

    // Default: run AI form orchestrator
    return await runAIOrchestratorForJob(targetUrl, job, tabId);

  } catch (err) {
    console.error('[AI Control] Exception during AI decision:', err);
    if (tabId && currentBatchController?.currentJobTabId === tabId) {
      currentBatchController.currentJobTabId = null;
      chrome.tabs.remove(tabId).catch(() => {});
    }
    return { success: false, reason: `AI Control error: ${err.message}` };
  }
}
