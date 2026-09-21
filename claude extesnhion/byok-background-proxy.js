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

function calculateIntelligenceScore(modelId, modelName = '') {
  const mid = String(modelId || '').toLowerCase();
  const mname = String(modelName || '').toLowerCase();
  const text = `${mid} ${mname}`;

  // Explicit benchmarks & requested scores
  if (text.includes('claude-3-7-sonnet') || text.includes('claude-3.7-sonnet')) return { score: 98, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('deepseek-r1') || text.includes('deepseek/deepseek-r1')) return { score: 97, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('o1') || text.includes('o3-mini')) return { score: 97, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('claude-3-5-sonnet') || text.includes('claude-3.5-sonnet')) return { score: 96, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('gpt-4o') && !text.includes('mini')) return { score: 95, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('deepseek-v3') || text.includes('deepseek-chat')) return { score: 95, tier: 'Elite Intelligence', badge: '🧠 Elite' };
  if (text.includes('claude-3-opus') || text.includes('claude-3.0-opus')) return { score: 95, tier: 'Elite Intelligence', badge: '🧠 Elite' };
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
  if (text.includes('claude-3-5-haiku') || text.includes('claude-3-haiku')) return { score: 81, tier: 'Fast & Balanced', badge: '⚡ Fast' };
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
        const headers = { 'Content-Type': 'application/json' };
        if (key) headers['Authorization'] = `Bearer ${key}`;
        const resp = await fetch(`${cleanUrl}/chat/completions`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ model: model || 'antigravity/gemini-3.6-flash-high', messages: [{ role: 'user', content: 'OK' }], max_tokens: 2 }),
        });
        const latencyMs = Date.now() - startTime;
        if (resp.ok) return { ok: true, status: resp.status, latencyMs, message: `✅ Active & Working (${latencyMs}ms)!` };
        const errText = await resp.text().catch(() => '');
        return { ok: false, status: resp.status, latencyMs, error: errText.slice(0, 150) };
      }
      case 'anthropic': {
        const resp = await fetch('https://api.anthropic.com/v1/messages', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': key,
            'anthropic-version': '2023-06-01',
            'dangerously-allow-browser': 'true',
          },
          body: JSON.stringify({ model: 'claude-3-5-haiku-20241022', messages: [{ role: 'user', content: 'OK' }], max_tokens: 2 }),
        });
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
          { id: 'anthropic/claude-3.7-sonnet', name: 'Claude 3.7 Sonnet' },
          { id: 'deepseek/deepseek-r1', name: 'DeepSeek R1' },
          { id: 'anthropic/claude-3.5-sonnet', name: 'Claude 3.5 Sonnet' },
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
      } else if (provider === 'anthropic') {
        rawModels = [
          { id: 'claude-3-7-sonnet-20250219', name: 'Claude 3.7 Sonnet' },
          { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet' },
          { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku' },
        ];
      }
    }

    // Attach Intelligence Scores and Sort Descending
    const scoredModels = rawModels.map(m => {
      const intel = calculateIntelligenceScore(m.id, m.name);
      return {
        id: m.id,
        name: m.name || m.id,
        score: intel.score,
        tier: intel.tier,
        badge: intel.badge,
        label: `[Score: ${intel.score} ${intel.badge}] ${m.name || m.id}`,
      };
    }).sort((a, b) => b.score - a.score);

    return { ok: true, models: scoredModels };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

async function callActiveAIModel(config, systemPrompt, messages) {
  // 1. Resolve key config: check if there is an active key configured in apiKeys list
  const activeKeyId = config?.activeKeyId;
  const apiKeys = Array.isArray(config?.apiKeys) ? config.apiKeys : [];
  const keyConfig = apiKeys.find(k => k.id === activeKeyId && k.enabled !== false) ||
    apiKeys.find(k => k.enabled !== false) || null;

  const provider = keyConfig?.provider || config?.activeProvider || 'omniroute';
  const apiKey = keyConfig?.key || config?.[provider]?.apiKey || '';
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
      return await callOmniRouteAPI(apiKey, baseUrl, model, systemPrompt, messages);
    case 'anthropic':
    default:
      if (!apiKey) throw new Error('Anthropic API key is not configured in Settings.');
      return await callAnthropicAPI(apiKey, model, systemPrompt, messages);
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
  const tag = (elemInfo?.tag || '').toLowerCase();
  const targetName = (elemInfo?.targetName || target.text || '').toLowerCase().trim();
  const selector = (target.selector || '').toLowerCase();
  const isButtonFlag = Boolean(elemInfo?.isButton);
  const text = (elemInfo?.text || '').toLowerCase().trim();

  const ACTION_REGEX = /\b(save|submit|next|continue|apply|send|confirm|done|finish|proceed|ok|agree|accept|verify|start|post)\b/i;

  // 1. Check learnedButtons
  for (const lb of learnedButtons) {
    const l = (lb || '').toLowerCase().trim();
    if (!l) continue;
    if (targetName === l || targetName.includes(l) || l.includes(targetName) || selector.includes(l) || text.includes(l)) {
      return { isButton: true, reason: `Matches learned button: "${lb}"` };
    }
  }

  // 2. Check Action Keywords
  if (ACTION_REGEX.test(targetName)) {
    return { isButton: true, reason: `Action button keyword matched in name ("${targetName}")` };
  }
  if (ACTION_REGEX.test(selector)) {
    return { isButton: true, reason: `Action button keyword matched in selector ("${selector}")` };
  }
  if (text.length <= 40 && ACTION_REGEX.test(text)) {
    return { isButton: true, reason: `Action button keyword matched in text ("${text}")` };
  }

  // 3. Native Button elements
  if (isButtonFlag || ['button', 'a'].includes(tag) || selector.includes('button') || selector.includes('.btn') || selector.includes('.send')) {
    return { isButton: true, reason: `Element is a button (<${tag}>)` };
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
  if (!clean || clean.length < 2) return;
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

  const storeData = await chrome.storage.local.get(['byok_config', 'userProfile', 'customAnswers', 'aiDecisionMode', 'learnedButtons']);
  const config = storeData.byok_config || {
    activeProvider: 'omniroute',
    omniroute: { baseUrl: 'http://127.0.0.1:20128/v1', apiKey: 'sk-f46d845e6a300177-0a895e-fbfbd25b', model: 'antigravity/gemini-3.6-flash-high' },
    gemini: { apiKey: '', model: 'gemini-2.0-flash' },
    anthropic: { apiKey: '', model: 'claude-3-7-sonnet-20250219' },
  };
  const profile = storeData.userProfile || {};
  const customAnswers = Array.isArray(storeData.customAnswers) ? storeData.customAnswers : [];
  const learnedButtons = Array.isArray(storeData.learnedButtons) ? storeData.learnedButtons : [];
  const aiDecisionMode = storeData.aiDecisionMode || 'ask_human';
  const actionHistory = [];

  // Multi-round conversational loop: can handle up to 20 question rounds in a chatbot
  const MAX_ROUNDS = step.isAiLoop === false && !step.loopId && total <= 1 ? 1 : Math.max(1, Math.min(25, step.maxQuestions || 15));
  let lastRecordedQuestion = '';

  runState.logs.push(`[AI Loop] 🚀 Starting conversational AI execution (${total} element(s) per round, max ${MAX_ROUNDS} rounds)...`);
  await chrome.storage.local.set({ workflowRunState: runState });

  for (let round = 1; round <= MAX_ROUNDS; round++) {
    if (round > 1) {
      runState.logs.push(`[AI Loop] 🔄 Starting Conversational Round ${round} of ${MAX_ROUNDS}...`);
      await chrome.storage.local.set({ workflowRunState: runState });
    }

    // Process all elements configured in this step sequentially
    for (let idx = 0; idx < total; idx++) {
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
      const targetQuestion = extractedQuestion || (tag === 'div' && visibleText.length > 5 ? visibleText : '') || targetName;
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
        await saveLearnedButton(learnedButtons, targetName || target.selector);
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
        runState.logs.push(`[AI Loop] ⚡ Dropdown has only 1 option ("${singleOption}"). Auto-selecting without AI.`);
        if (targetQuestion) {
          await saveLearnedAnswer(customAnswers, targetQuestion, singleOption);
        }
      }
      // C. DROPDOWN WITH 2 OR MORE OPTIONS: Check customAnswers first; if none, ask AI!
      else if (options.length >= 2) {
        const smartMatch = findSmartAnswerMatch(targetQuestion, visibleText, targetName, customAnswers, profile);
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
            reasoning: `⚡ Reused saved answer for dropdown: "${matchedOption}" (source: ${smartMatch.source})`
          };
          runState.logs.push(`[AI Loop] ⚡ Dropdown has ${options.length} options, but question was already answered ("${matchedOption}"). Bypassing AI.`);
        } else {
          // Ask AI what to do for this 2+ option dropdown!
          runState.logs.push(`[AI Loop] 🤖 Dropdown has ${options.length} options: ${JSON.stringify(options.slice(0, 10))}. Asking AI to choose...`);
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
Available Dropdown Options (${options.length} choices):
${JSON.stringify(options.slice(0, 30))}

INSTRUCTION: You must pick EXACTLY ONE option from the Available Dropdown Options list that best fits the candidate profile.
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

            // Auto-save AI's choice to customAnswers so future dropdowns don't need AI!
            if (targetQuestion && aiDecision.value) {
              await saveLearnedAnswer(customAnswers, targetQuestion, aiDecision.value);
              runState.logs.push(`[AI Loop] 💾 Auto-memorized dropdown answer for "${targetQuestion}" ➔ "${aiDecision.value}" for future jobs.`);
            }
          } catch (aiErr) {
            console.warn(`[AI Loop] AI dropdown call failed:`, aiErr);
            aiDecision = { action: 'select_option', value: options[0], reasoning: 'Fallback: first option selected' };
          }
        }
      }
      // D. TEXT QUESTION / INPUT FIELD / CHAT INPUT CONTAINER
      else {
        // Check if question was already answered previously or is in candidate profile!
        const smartMatch = findSmartAnswerMatch(targetQuestion, visibleText, targetName, customAnswers, profile);
        if (smartMatch && smartMatch.answer && (['input', 'textarea'].includes(tag) || hasInnerInput || tag === 'div')) {
          aiDecision = {
            action: 'fill',
            value: smartMatch.answer,
            reasoning: `⚡ Reused saved answer for "${targetQuestion || targetName}": "${smartMatch.answer}" (source: ${smartMatch.source})`
          };
          runState.logs.push(`[AI Loop] ⚡ Question already asked/known ("${targetQuestion || targetName}"). Bypassing AI and directly typing: "${smartMatch.answer}"`);
        } else {
          // Unknown question: Ask AI to think and answer
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
            } else if (aiDecision.action === 'click') {
              // If AI told us to click, memorize this button!
              await saveLearnedButton(learnedButtons, targetName || target.selector);
            }
          } catch (aiErr) {
            console.warn(`[AI Loop] AI call failed for Element ${elemNumber}:`, aiErr);
            if (isButton || ['button', 'a'].includes(tag) || /button|submit|save|continue|next/i.test(targetName)) {
              aiDecision = { action: 'click', value: '', reasoning: 'Fallback: button detected' };
              await saveLearnedButton(learnedButtons, targetName || target.selector);
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

      // 4. Execute the chosen action with 3-ATTEMPT RETRY MECHANISM & DIAGNOSTIC HUD
      const MAX_ATTEMPTS = 3;
      let actionSuccess = false;
      let lastFailureReason = '';

      for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
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
      if (!valid) {
        const activeTabs = await chrome.tabs.query({ currentWindow: true, active: true });
        if (activeTabs[0]?.id) activeTabId = activeTabs[0].id;
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

      await updateTabHud(activeTabId, {
        workflowName: runState.workflowName,
        stepIndex: i,
        totalSteps: steps.length,
        stepName: step.name || step.type,
        status: 'running',
        actionTaken: `Executing ${step.type}...`,
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
    console.error('[BYOK] Workflow execution error:', err);
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
      stepName: 'Execution Error',
      status: 'error',
      actionTaken: runState.error,
    });
  }
}

