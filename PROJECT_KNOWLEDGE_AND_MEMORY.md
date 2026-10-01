# ALL_CAREER_3: Project Memory, Architecture & AI Knowledge Base

> **Document Type**: Comprehensive Knowledge Dump & AI Memory Context  
> **Repository**: `ALL_CAREER_3`  
> **User / Candidate**: Ragesh (`ragesh28`)  
> **Environment**: Windows, PowerShell, Chrome Extension (Manifest V3), Vanilla JS / TS  
> **Purpose**: Serves as persistent, high-fidelity context for any AI assistant or developer working on this project. Contains all domain knowledge, architecture decisions, behavioral constraints, fixed bugs, and operational workflows.

---

## 1. System Overview & Core Purpose

`ALL_CAREER_3` is an end-to-end automated job search and application platform combining:
1. **All Career Web Portal** (`all_jobs.html`, `big_company_jobs.html`, `all_career_auto_apply.js`):
   - Aggregates jobs across multiple portals (Naukri, LinkedIn, Indeed, Internshala, Hirist, Foundit, company career sites, etc.).
   - Provides filtering (date posted, keywords, job types), batch selection, and a one-click **"Start Batch Auto Apply"** engine.
2. **Chrome Extension (Workflow Studio & Auto Applier)** (`Auto-Fill-V5/` & `autofill-v4/`):
   - Injects automation engines and HUDs into job application pages.
   - Supports recorded deterministic workflows (`Workflow Studio`) as well as AI-powered dynamic question answering and form completion.
   - Operates with Bring-Your-Own-Key (BYOK) APIs (OpenAI, Gemini, Groq, Anthropic) or local AI routers (OmniRoute `127.0.0.1:20128`).
3. **Workflow Studio / Recorder** (`recorder.js`, `recorder.html`):
   - Allows users to record multi-step application journeys per portal or company (clicks, fills, dropdowns, AI questions, resume uploads).
   - Replays steps sequentially with DOM readiness, retry mechanisms, and reactive error recovery.

---

## 2. Hard Behavioral Constraints & Golden Rules

These rules have been explicitly specified by the user and must **never** be violated:

### Rule 1: STRICTLY NO Web AI
- **No ChatGPT Web, No Claude Web, No Gemini Web scraping/web sessions.**
- Applications must strictly utilize:
  - Configured BYOK cloud API keys (Gemini, OpenAI, Groq, Anthropic), OR
  - Local OmniRoute server (`http://127.0.0.1:20128`).

### Rule 2: Never Run Steps on All Career Portal Tabs
- The extension executes workflows on **external job tabs only**.
- Main portal pages (`all_jobs.html`, `big_company_jobs.html`, `mainTabId`, `chrome://`, extension pages) are strictly guarded via `isAllCareerPageTab()`.
- If a job tab closes or is stopped, the runner must **never fallback** to the active All Career tab.

### Rule 3: Stop / Cancel Must Halt Immediately & Cleanly
- When the user clicks **"Stop Auto Apply"** or closes the target job tab:
  - All running loops, retry intervals, and AI calls must immediately terminate via `isProcessStopped()`.
  - `workflowRunState` in `chrome.storage.local` must be reset.
  - The HUD overlay banner must be removed immediately from all open tabs (`removeTabHud`).
  - No pending steps should execute on whatever tab becomes active.

### Rule 4: Live AI Health-Check Before Execution (No Blind Clicking)
- Before running any AI step (`ai_fallback`, interactive chatbot question, or missing element fallback):
  - The extension runs a live 4-second health check via `verifyActiveAIWorking()`.
  - **OmniRoute Offline Check**: If OmniRoute is selected but `127.0.0.1:20128` is not started, the runner **must halt** and notify the user with an explicit warning banner:
    `"OmniRoute local server is not running on http://127.0.0.1:20128. Please start the OmniRoute server, or add an AI API key (Gemini, OpenAI, Groq) in Extension Settings (⚙️)."`
  - **Missing API Key Check**: Explicitly prompts the user with `⚠️ AI Not Working` banner with buttons:
    - **⚙️ Open Settings** (opens options to configure key)
    - **⏹ Stop Auto Apply** (terminates cleanly)
  - **CRITICAL**: The extension must **never silently swallow** AI errors or default to randomly clicking buttons (e.g., clicking filters, save buttons, or first options) when the AI fails.

### Rule 5: Workflow Recorder Exit / Cancel Never Saves
- Clicking **"Exit / Cancel Recording"** (`#wf-exit-record`) must **only close the sidebar**.
- It must **never** save the partially recorded steps into `storedWorkflows`.

---

## 3. Architecture & Key Files

### 3.1 Chrome Extension (`Auto-Fill-V5/`)

- [`byok-background-proxy.js`](file:///c:/Users/lrage/OneDrive/Documents/VS_CODE/ALL_CAREER_3/claude%20extsnhion/byok-background-proxy.js):
  - **Central Background Service Worker**.
  - **BYOK AI Router**: `callActiveAIModel()`, `verifyActiveAIWorking()`, `checkHasConfiguredAIKey()`. Supports OmniRoute, Gemini, OpenAI, Groq, Claude.
  - **Workflow Execution Engine**: `executeWorkflowRun()`, `executeAIStepOneByOne()`, `sendWorkflowStepToTab()`.
  - **Batch Auto Apply Engine**: `startBatchAutoApply()`, `stopBatchAutoApply()`, `runWorkflowForJob()`, `runAIOrchestratorForJob()`.
  - **Tab Safety & Guards**: `isAllCareerPageTab()`, `ensureActiveTab()`, `getValidTab()`.
  - **HUD Dispatcher**: `updateTabHud()`, `removeTabHud()`.
  - **Workflow Storage**: `WORKFLOWS_KEY = 'storedWorkflows'`, `RECORDING_KEY = 'workflowRecordingState'`.

- [`content.js`](file:///c:/Users/lrage/OneDrive/Documents/VS_CODE/ALL_CAREER_3/claude%20extsnhion/content.js):
  - **Content Script Injected into Job Pages**.
  - **HUD Component**: Injects top floating HUD showing status, current step, element counts, questions, answers, and stop/settings controls.
  - **Step Executors**: Handles DOM clicks, native mouse dispatches, form fills, dropdown selection, file inputs.
  - **Interactive Question Modal**: Renders in-page modal if `ask_human` fallback mode is triggered.
  - **Stop Handler**: Immediately tears down the HUD and cancels local polling on `ALL_CAREER_STOP_BATCH`.

- [`recorder.js`](file:///c:/Users/lrage/OneDrive/Documents/VS_CODE/ALL_CAREER_3/claude%20extsnhion/recorder.js) & [`recorder.html`](file:///c:/Users/lrage/OneDrive/Documents/VS_CODE/ALL_CAREER_3/claude%20extsnhion/recorder.html):
  - **Workflow Studio Side Panel / Window**.
  - Captures user interactions on the active tab (clicks, inputs, selects, file uploads).
  - Allows marking elements as AI chat steps (`ai_fallback`) or custom prompts.
  - Provides workflow testing, export, import, saving, and clean cancellation (`WORKFLOW_RECORD_CANCEL`).

- [`options.html`](file:///c:/Users/lrage/OneDrive/Documents/VS_CODE/ALL_CAREER_3/claude%20extsnhion/options.html) & [`options.js`](file:///c:/Users/lrage/OneDrive/Documents/VS_CODE/ALL_CAREER_3/claude%20extsnhion/options.js):
  - BYOK API Configuration (OmniRoute, Gemini, OpenAI, Groq, Anthropic).
  - Candidate Profile settings (Name, Email, Phone, Experience, Skills, Education, Location, Notice Period, Current/Expected CTC).
  - Custom / Memorized Q&A editor (`customAnswers`).

### 3.2 All Career Web Application

- [`all_jobs.html`](file:///c:/Users/lrage/OneDrive/Documents/VS_CODE/ALL_CAREER_3/all_jobs.html):
  - Aggregated job list, search filters, portal badges, batch selection table, "Start Auto Apply" modal.
- [`all_career_auto_apply.js`](file:///c:/Users/lrage/OneDrive/Documents/VS_CODE/ALL_CAREER_3/all_career_auto_apply.js):
  - Frontend bridge communicating with the Chrome extension via `window.postMessage` or `chrome.runtime.sendMessage`.
  - Dispatches batch auto-apply jobs and receives live progress updates.

---

## 4. Key Mechanisms & How They Work

### 4.1 Live AI Health Check (`verifyActiveAIWorking`)
```javascript
// Located in byok-background-proxy.js
async function verifyActiveAIWorking()
```
- Retrieves active provider (`omniroute`, `gemini`, `openai`, `groq`, `anthropic`) and keys from `chrome.storage.local`.
- If `omniroute`: Pings `http://127.0.0.1:20128/v1/models` with an `AbortController` timeout (4000ms).
  - If unreachable or connection refused -> returns `{ ok: false, reason: 'OmniRoute local server is not running on http://127.0.0.1:20128...' }`.
- If cloud provider (Gemini, OpenAI, Groq, Anthropic):
  - Verifies API key exists and is non-empty.
  - Sends a minimal 1-token probe request (`[{ role: 'user', content: 'hi' }]`).
  - If invalid key, quota exceeded, or network error -> returns `{ ok: false, reason: '...' }`.

### 4.2 Tab Hijacking Guard (`isAllCareerPageTab`)
```javascript
function isAllCareerPageTab(tab) {
  if (!tab || !tab.url) return false;
  const url = tab.url.toLowerCase();
  return (
    url.includes('all_jobs.html') ||
    url.includes('big_company_jobs.html') ||
    url.startsWith('chrome://') ||
    url.startsWith('chrome-extension://') ||
    (currentBatchController && currentBatchController.mainTabId === tab.id)
  );
}
```
Used in:
- `ensureActiveTab()`: When searching for an execution tab, rejects All Career tabs.
- `sendWorkflowStepToTab()`: Throws error if target is an All Career page.
- `executeAIStepOneByOne()`: During tab refresh between elements, ensures active tab is valid and external.

### 4.3 Clean Exit / Cancel Recording
- When user clicks `#wf-exit-record` in `recorder.js`:
  ```javascript
  chrome.runtime.sendMessage({ action: 'WORKFLOW_RECORD_CANCEL', cancel: true, save: false });
  window.close();
  ```
- Background script receives `WORKFLOW_RECORD_CANCEL`, clears `workflowRecordingState` from storage, and does **not** write to `storedWorkflows`.

### 4.4 Auto-Memorized Q&A (`customAnswers`)
- When AI provides an answer or user manually supplies an answer in the in-page modal:
  - Saved to `customAnswers` in `chrome.storage.local`.
  - Next time the same question appears on any job application, the extension automatically matches it via `findSmartAnswerMatch()` and fills it immediately without calling AI.

---

## 5. Candidate Profile Context

- **Candidate Name**: Ragesh
- **Primary Domain**: Software Engineering / Full-Stack / Web Development / AI Engineering
- **Profile Fields in Storage (`profile`)**:
  - `fullName`: Ragesh
  - `email`: User's primary email
  - `phone`: User's mobile number
  - `experience`: Years of software engineering experience
  - `skills`: JavaScript, TypeScript, Node.js, Python, React, Web Automation, AI APIs
  - `noticePeriod`: Immediate / 15-30 Days
  - `currentLocation` / `preferredLocation`: Bangalore / Hybrid / Remote
  - `resume`: PDF resume stored in `uploadedFiles` / `resumes` in extension local storage.

---

## 6. Solved Issues & Bug History

| Issue | Root Cause | Solution Implemented |
|---|---|---|
| **Extension clicked "Last 3 Days" on All Career tab after stopping** | `ensureActiveTab` fell back to `chrome.tabs.query({ active: true })` which picked `all_jobs.html` when job tab closed. | Added `isAllCareerPageTab()` check everywhere, blocked step execution on main tab, cleared `workflowRunState` on stop. |
| **Silent fallback clicks when OmniRoute was offline** | `executeAIStepOneByOne` had a generic catch block that clicked buttons or first option on AI failure. | Added `verifyActiveAIWorking()`, tested AI before every step, showed red HUD warning banner with settings button, stopped execution. |
| **Workflow recorder saved on Exit / Cancel** | Recorder sent `WORKFLOW_RECORD_STOP` on `#wf-exit-record`, which background saved to storage. | Changed to `WORKFLOW_RECORD_CANCEL` with `cancel: true, save: false`, discarding steps without saving. |
| **HUD banner staying stuck on page** | Content script didn't listen to batch stop signal. | Added listener for `ALL_CAREER_STOP_BATCH` to immediately remove `#all-career-hud-root`. |
| **Naukri tab opener navigation failure** | Popup blocker or direct tab opening prevented capturing target tab. | Added URL target matching, openerTabId preservation, and manual fallback navigation. |
| **OmniRoute false offline error during auto-apply** | `verifyActiveAIWorking()` had a strict 4-second timeout that aborted while OmniRoute was waiting on remote Gemini model responses (~15s), incorrectly reporting the server was offline. | Probed `http://127.0.0.1:20128/v1/models` (responds in 20ms) for fast health check and increased completion fallback timeout to 15s/25s. |
| **Batch auto-apply didn't stop and continuously spawned tabs** | 1. Clicking navbar button while running invoked `startBatch()` again, restarting the loop; 2. Closing the job tab didn't set `controller.cancelled = true`; 3. Inter-job 1.8s sleep was non-interruptible; 4. HUD `✕` only hid element without stopping. | Added toggle-to-stop on navbar button, interruptible 100ms sleep checks, instant batch cancellation on active tab close, and wired HUD `✕` button to `stopBatchAutoApply()`. |

---

## 7. Guidelines for Any Future AI Assistant

1. **Always Check Health First**: Any new feature involving AI must call `verifyActiveAIWorking()` before executing actions on the page.
2. **Never Touch the Main Tab**: Always verify `!isAllCareerPageTab(tab)` before injecting scripts, sending messages, or clicking elements.
3. **Keep Stop / Cancellation Responsive**: Always insert `if (isProcessStopped()) throw new Error(...)` inside loops, timeouts, and retries.
4. **Preserve User UI**: The user prefers clean, modern, dark-mode, non-intrusive UI overlays (HUD) with actionable buttons (Settings, Stop, Retry).
