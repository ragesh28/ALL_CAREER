/**
 * Claude in Chrome — Automation Studio & Options Hub
 * Pixel-accurate Workflow Studio matching Autofill V4
 * Full 3-Column Architecture: Workflows List, Dot-Grid Graph Canvas, and Node Inspector.
 */

const STORAGE_KEYS = {
  BYOK_CONFIG: 'byok_config',
  USER_PROFILE: 'userProfile',
  RESUMES: 'resumes',
  DEFAULT_RESUME: 'defaultResume',
  CUSTOM_ANSWERS: 'customAnswers',
  WORKFLOWS: 'browserWorkflows',
  SYSTEM_PROMPT: 'fullSystemPrompt',
  PROMPT_MODE: 'promptMode',
  AI_DECISION_MODE: 'aiDecisionMode',
  ALLOW_MULTI_TAB: 'allowMultiTabControl',
  ALLOW_SETTINGS_ACCESS: 'allowSettingsAccess',
};

const DEFAULT_MASTER_SYSTEM_PROMPT = `You are Claude in Chrome, an elite autonomous browser agent and job application assistant with direct browser execution capabilities.
You inspect interactive accessibility trees, click elements, upload resumes silently, auto-fill forms, manage browser tabs, and record workflows.

### AUTONOMY & DECISION RULES:
1. Grounding: Use information from the candidate profile and resume.
2. Near-Miss Hints: Always prioritize matching previous answers from candidate history.
3. Uncertainty & Autonomy:
   - If Autonomous Decision Mode is ON: Answer all fields decisively. Never stop to ask human.
   - If Ask Human Mode is ON: If a mandatory question is completely unknown and not in profile, ask the user in chat.

### CAPABILITIES & TOOLS:
- Click: {"thought": "...", "action": "click", "ref_id": "ref_1"}
- Type: {"thought": "...", "action": "type", "ref_id": "ref_2", "text": "value", "press_enter": false}
- Upload Resume: {"thought": "...", "action": "upload_resume", "ref_id": "ref_3"}
- Select Dropdown: {"thought": "...", "action": "select_option", "ref_id": "ref_4", "value": "Option"}
- AutoFill Form: {"thought": "...", "action": "autofill_page"}
- Create Workflow: {"thought": "...", "action": "create_workflow", "workflowName": "...", "steps": [...]}
- Save Custom Answer: {"thought": "...", "action": "save_custom_answer", "question": "...", "answer": "..."}
- Tab Control: {"thought": "...", "action": "switch_tab", "tabIndex": 1} / {"action": "new_tab", "url": "..."}
- Ask Human: {"thought": "...", "action": "ask_human", "question": "..."}
- Done: {"thought": "...", "action": "done", "message": "..."}

Respond with a single JSON action block enclosed in triple backticks.`;

const DEFAULT_PROFILE = {
  fullName: 'Ragesh L',
  email: 'lragesh28@gmail.com',
  phone: '9952963081',
  altPhone: '',
  address: 'Cuddalore',
  city: 'Cuddalore',
  state: 'Tamil Nadu',
  country: 'India',
  pincode: '608801',
  degree: 'B.Tech in Artificial Intelligence',
  graduationYear: '2026',
  university: 'Anna University',
  experienceYears: '2',
  skills: 'Python, Machine Learning, JavaScript, React, TypeScript, AI Agents, Web Automation',
  linkedin: 'https://linkedin.com/in/ragesh',
  github: 'https://github.com/ragesh28',
  currentSalary: '6 LPA',
  expectedSalary: '12 LPA',
  noticePeriod: 'Immediate',
};

let currentTab = 'workflows';
let profile = { ...DEFAULT_PROFILE };
let byokConfig = {
  activeProvider: 'omniroute',
  omniroute: { baseUrl: 'http://127.0.0.1:20128/v1', apiKey: 'sk-f46d845e6a300177-0a895e-fbfbd25b', model: 'antigravity/gemini-3.6-flash-high' },
  gemini: { apiKey: '', model: 'gemini-2.0-flash' },
  anthropic: { apiKey: '', model: 'claude-3-7-sonnet-20250219' },
};
let resumes = [];
let defaultResumeId = null;
let customAnswers = [
  { id: 'qa_1', question: 'Are you willing to relocate?', answer: 'Yes, absolutely.', matchType: 'contains' },
  { id: 'qa_2', question: 'Notice Period', answer: 'Immediate (0 days)', matchType: 'contains' },
  { id: 'qa_3', question: 'Years of Python / ML experience', answer: '2+ years', matchType: 'contains' },
];

let workflows = [
  {
    id: 'wf_1',
    name: 'Naukri job workflow',
    startUrl: 'https://www.naukri.com/job-listings-ai-ml-engine',
    resumeId: '',
    variables: { role: '', location: '' },
    steps: [
      {
        id: 's1',
        type: 'open_url',
        name: 'Open www.naukri.com',
        value: 'https://www.naukri.com/job-listings-ai-ml-engine',
        waitMs: 400,
        color: '#22c55e',
        badge: 'URL',
        target: 'https://www.naukri.com/job-listings-ai-ml-engineer-focally-bengaluru-0-to-3-years-211125015233?src=jobsearchDesk&sid=1787292242337',
        disabled: false,
        stopAfter: false,
        finalSubmit: false,
      },
      {
        id: 's2',
        type: 'click',
        name: 'click search',
        value: '',
        waitMs: 400,
        color: '#38bdf8',
        badge: 'CLK',
        target: 'button.styles_apply-button__135fA',
        disabled: false,
        stopAfter: false,
        finalSubmit: false,
      },
      {
        id: 's3',
        type: 'ai_fallback',
        name: 'AI answer: Hi Ragesh...',
        value: 'Hi Ragesh L, thank you for your application',
        waitMs: 800,
        color: '#14b8a6',
        badge: 'AI',
        target: 'Form screening question fields',
        disabled: false,
        stopAfter: false,
        finalSubmit: false,
      },
    ],
  },
];

let selectedWfIndex = 0;
let selectedStepIndex = 0;
let wfSearchQuery = '';
let systemPrompt = DEFAULT_MASTER_SYSTEM_PROMPT;
let aiDecisionMode = 'autonomous';
let allowMultiTabControl = true;
let allowSettingsAccess = true;

function syncTabFromHash() {
  const hash = (window.location.hash || '').replace('#', '').toLowerCase();
  const validTabs = ['workflows', 'profile', 'apikeys', 'prompts', 'customanswers', 'resumes', 'settings'];
  if (validTabs.includes(hash)) {
    currentTab = hash;
  } else if (hash === 'answers') {
    currentTab = 'customanswers';
  } else if (hash === 'batch') {
    currentTab = 'workflows';
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  syncTabFromHash();
  await loadAllData();
  renderAppHub();
});

window.addEventListener('hashchange', () => {
  syncTabFromHash();
  renderAppHub();
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes[STORAGE_KEYS.WORKFLOWS]) {
    workflows = changes[STORAGE_KEYS.WORKFLOWS].newValue || workflows;
    if (selectedWfIndex >= workflows.length) selectedWfIndex = workflows.length - 1;
    renderAppHub();
  }
});

async function loadAllData() {
  try {
    const data = await chrome.storage.local.get([
      STORAGE_KEYS.BYOK_CONFIG,
      STORAGE_KEYS.USER_PROFILE,
      STORAGE_KEYS.RESUMES,
      STORAGE_KEYS.DEFAULT_RESUME,
      STORAGE_KEYS.CUSTOM_ANSWERS,
      STORAGE_KEYS.WORKFLOWS,
      STORAGE_KEYS.SYSTEM_PROMPT,
      STORAGE_KEYS.AI_DECISION_MODE,
      STORAGE_KEYS.ALLOW_MULTI_TAB,
      STORAGE_KEYS.ALLOW_SETTINGS_ACCESS,
    ]);

    if (data[STORAGE_KEYS.USER_PROFILE]) profile = { ...DEFAULT_PROFILE, ...data[STORAGE_KEYS.USER_PROFILE] };
    if (data[STORAGE_KEYS.BYOK_CONFIG]) byokConfig = { ...byokConfig, ...data[STORAGE_KEYS.BYOK_CONFIG] };
    if (Array.isArray(data[STORAGE_KEYS.RESUMES]) && data[STORAGE_KEYS.RESUMES].length > 0) {
      resumes = data[STORAGE_KEYS.RESUMES];
    } else {
      resumes = [{ id: 'res_1', name: 'Ragesh_Resume.pdf', label: 'Default resume', size: 65536, isDefault: true }];
    }
    defaultResumeId = data[STORAGE_KEYS.DEFAULT_RESUME] || resumes[0]?.id;
    if (Array.isArray(data[STORAGE_KEYS.CUSTOM_ANSWERS])) customAnswers = data[STORAGE_KEYS.CUSTOM_ANSWERS];
    if (Array.isArray(data[STORAGE_KEYS.WORKFLOWS]) && data[STORAGE_KEYS.WORKFLOWS].length > 0) workflows = data[STORAGE_KEYS.WORKFLOWS];
    if (data[STORAGE_KEYS.SYSTEM_PROMPT]) systemPrompt = data[STORAGE_KEYS.SYSTEM_PROMPT];
    if (data[STORAGE_KEYS.AI_DECISION_MODE]) aiDecisionMode = data[STORAGE_KEYS.AI_DECISION_MODE];
    if (typeof data[STORAGE_KEYS.ALLOW_MULTI_TAB] === 'boolean') allowMultiTabControl = data[STORAGE_KEYS.ALLOW_MULTI_TAB];
    if (typeof data[STORAGE_KEYS.ALLOW_SETTINGS_ACCESS] === 'boolean') allowSettingsAccess = data[STORAGE_KEYS.ALLOW_SETTINGS_ACCESS];
  } catch (e) {}
}

async function persist(key, val, msg = 'Saved successfully!') {
  try {
    await chrome.storage.local.set({ [key]: val });
    showToast(msg);
  } catch (e) {
    showToast('Save failed: ' + e.message, true);
  }
}

function showToast(msg, isError = false) {
  const toast = document.getElementById('global-toast');
  if (!toast) return;
  toast.textContent = (isError ? '❌ ' : '✨ ') + msg;
  toast.style.display = 'block';
  toast.style.borderColor = isError ? '#ef4444' : '#3b82f6';
  setTimeout(() => {
    if (toast) toast.style.display = 'none';
  }, 2400);
}

// ─── Main Hub Layout ─────────────────────────────────────────────────────────

function renderAppHub() {
  const root = document.getElementById('root');
  if (!root) return;

  root.innerHTML = `
    <div class="options-container">
      <!-- Top Navigation Tabs -->
      <nav class="tabs-nav">
        <button class="tab-btn ${currentTab === 'workflows' ? 'active' : ''}" data-tab="workflows">⚡ Workflow Studio</button>
        <button class="tab-btn ${currentTab === 'profile' ? 'active' : ''}" data-tab="profile">👤 Candidate Profile</button>
        <button class="tab-btn ${currentTab === 'apikeys' ? 'active' : ''}" data-tab="apikeys">🔑 AI & API Keys</button>
        <button class="tab-btn ${currentTab === 'prompts' ? 'active' : ''}" data-tab="prompts">🧠 Master System Prompt</button>
        <button class="tab-btn ${currentTab === 'customanswers' ? 'active' : ''}" data-tab="customanswers">📝 Custom Answers</button>
        <button class="tab-btn ${currentTab === 'resumes' ? 'active' : ''}" data-tab="resumes">📄 Resumes</button>
        <button class="tab-btn ${currentTab === 'settings' ? 'active' : ''}" data-tab="settings">⚙️ Autonomy & Settings</button>
      </nav>

      <!-- Main Content Card -->
      <main class="tab-card">
        ${renderActiveTabBody()}
      </main>

      <div id="global-toast" class="global-toast"></div>
    </div>
  `;

  attachEvents();
}

function renderActiveTabBody() {
  switch (currentTab) {
    case 'workflows': return renderWorkflowsTab();
    case 'profile': return renderProfileTab();
    case 'apikeys': return renderApiKeysTab();
    case 'prompts': return renderPromptsTab();
    case 'customanswers': return renderCustomAnswersTab();
    case 'resumes': return renderResumesTab();
    case 'settings': return renderSettingsTab();
    default: return renderWorkflowsTab();
  }
}

// ─── 1. Exact 3-Column Workflow Studio (Image 1 Layout) ──────────────────────

function renderWorkflowsTab() {
  const currentWf = workflows[selectedWfIndex] || workflows[0];
  const activeStep = currentWf?.steps?.[selectedStepIndex] || currentWf?.steps?.[0] || {
    id: 's1', type: 'open_url', name: 'Open page', value: '', waitMs: 400, color: '#22c55e', badge: 'URL', target: ''
  };

  const filteredWfs = workflows.filter(w => (w.name || '').toLowerCase().includes(wfSearchQuery.toLowerCase()));

  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>Workflow Studio</h3>
        <p>Record once, edit the graph, then replay locally. Explicit AI nodes handle selected live questions.</p>
      </div>
      <div class="top-actions">
        <button class="btn-secondary-gray" id="btn-wf-status">Status</button>
        <button class="btn-secondary-gray" id="btn-wf-save-main">Save</button>
        <button class="btn-primary-blue" id="btn-wf-run-main">Run workflow</button>
      </div>
    </div>

    <!-- Create manual workflow bar -->
    <div class="manual-bar">
      <div class="manual-title">Create manual workflow</div>
      <input type="text" id="manual-wf-name" class="dark-input" style="max-width: 220px;" placeholder="Workflow name" />
      <input type="text" id="manual-wf-url" class="dark-input" style="max-width: 320px;" placeholder="https://www.naukri.com/" />
      <button class="btn-success-green" id="btn-manual-open-record">Open and record</button>
    </div>

    <!-- 3-Column Studio Workspace -->
    <div class="studio-workspace">
      <!-- 1. Left Sidebar: Workflow List -->
      <aside class="wf-sidebar">
        <input type="text" id="wf-search-input" class="wf-search-input" placeholder="Search workflows" value="${escapeHtml(wfSearchQuery)}" />
        <div class="wf-list">
          ${filteredWfs.map((w, idx) => `
            <button class="wf-item-btn ${idx === selectedWfIndex ? 'active' : ''}" data-widx="${idx}">
              <span class="wf-item-name">${escapeHtml(w.name)}</span>
              <span class="wf-item-meta">Main workflow | ${w.steps?.length || 0} nodes</span>
            </button>
          `).join('')}
        </div>
      </aside>

      <!-- 2. Center Column: Properties, Dot Canvas, Bottom Bar -->
      <main class="wf-center-main">
        <!-- Top Properties Row -->
        <div class="properties-bar">
          <div class="prop-field">
            <label>Workflow name</label>
            <input type="text" id="wf-prop-name" class="dark-input" value="${escapeHtml(currentWf.name)}" />
          </div>
          <div class="prop-field">
            <label>Start URL</label>
            <input type="text" id="wf-prop-url" class="dark-input" value="${escapeHtml(currentWf.startUrl)}" />
          </div>
          <div class="prop-field">
            <label>Resume</label>
            <select id="wf-prop-resume" class="dark-select">
              <option value="">Default resume</option>
              ${resumes.map(r => `<option value="${r.id}" ${r.id === currentWf.resumeId ? 'selected' : ''}>${escapeHtml(r.label || r.name)}</option>`).join('')}
            </select>
          </div>
          <div class="prop-field">
            <label>Role variable</label>
            <input type="text" id="wf-prop-role" class="dark-input" value="${escapeHtml(currentWf.variables?.role || '')}" />
          </div>
          <div class="prop-field">
            <label>Location variable</label>
            <input type="text" id="wf-prop-loc" class="dark-input" value="${escapeHtml(currentWf.variables?.location || '')}" />
          </div>
        </div>

        <!-- Node Add Buttons Bar -->
        <div class="prop-buttons-row">
          <button class="btn-ai-teal" id="btn-add-ai-node-btn">Add AI node</button>
          <button class="btn-danger-outline" id="btn-add-stop-node-btn">Add stop node</button>
        </div>

        <!-- Dot Grid Flow Canvas -->
        <div class="dot-canvas">
          ${(currentWf.steps || []).map((step, idx) => {
            const stepType = (step?.type || 'action');
            const badgeColor = step.color || (stepType === 'open_url' ? '#22c55e' : stepType === 'click' ? '#38bdf8' : stepType === 'ai_fallback' ? '#14b8a6' : '#a855f7');
            return `
              <div class="wf-node-block ${idx === selectedStepIndex ? 'selected' : ''}" style="border-left-color: ${badgeColor};" data-sidx="${idx}">
                <div class="wf-node-head">
                  <span class="wf-badge" style="background: ${badgeColor};">${step.badge || String(stepType).toUpperCase().substring(0, 3)}</span>
                  <div class="wf-node-title">${escapeHtml(step.name || 'Step ' + (idx + 1))}</div>
                </div>
                <div class="wf-node-sub">
                  ${stepType === 'open_url' ? 'Open page' : stepType === 'click' ? 'Click element' : stepType === 'ai_fallback' ? 'Ask AI' : 'Action'} | Step ${idx + 1}<br />
                  ${escapeHtml(step.value || step.target || '')}
                </div>
              </div>
              ${idx < currentWf.steps.length - 1 ? '<div class="wf-connector-line">➔</div>' : ''}
            `;
          }).join('')}
        </div>

        <!-- Bottom Branch Actions Bar -->
        <div class="bottom-bar">
          <input type="text" id="branch-name-input" class="dark-input" style="max-width: 200px;" placeholder="New branch name" />
          <button class="btn-secondary-gray" id="btn-create-branch">Create branch</button>
          <button class="btn-secondary-gray" id="btn-create-branch-nodisabled">Branch without disabled nodes</button>
          <div style="flex: 1;"></div>
          <button class="btn-danger-outline" id="btn-del-wf-main">Delete workflow</button>
        </div>
      </main>

      <!-- 3. Right Column: Dedicated Node Inspector Panel (Never Clipped!) -->
      <aside class="wf-inspector">
        <div class="inspector-header" style="border-bottom-color: ${activeStep.color || '#22c55e'};">
          <span class="wf-badge" style="background: ${activeStep.color || '#22c55e'};">${activeStep.badge || String(activeStep.type || 'ACT').toUpperCase().substring(0, 3)}</span>
          <div class="inspector-title">${activeStep.type === 'open_url' ? 'Open page' : activeStep.type === 'click' ? 'Click element' : activeStep.type === 'ai_fallback' ? 'Ask AI' : 'Action'} Step ${selectedStepIndex + 1}</div>
        </div>

        <div class="form-group">
          <label>Node name</label>
          <input type="text" id="insp-name" class="dark-input" value="${escapeHtml(activeStep.name || '')}" />
        </div>

        <div class="form-group">
          <label>Value</label>
          <input type="text" id="insp-val" class="dark-input" value="${escapeHtml(activeStep.value || '')}" placeholder="URL, text or {{variable}}" />
        </div>

        <div class="form-group">
          <label>Wait after node (ms)</label>
          <input type="number" id="insp-wait" class="dark-input" value="${activeStep.waitMs || 400}" min="250" max="5000" />
        </div>

        <div class="form-group">
          <label>Connect to</label>
          <select id="insp-connect" class="dark-select">
            <option value="">Next node</option>
            ${(currentWf.steps || []).map((s, i) => i !== selectedStepIndex ? `<option value="${s.id}">Step ${i + 1}: ${escapeHtml(s.name)}</option>` : '').join('')}
          </select>
        </div>

        <div class="form-group">
          <label>If this node fails</label>
          <select id="insp-onerror" class="dark-select">
            <option value="stop">Stop with error</option>
            <option value="ask_ai">Ask AI to recover</option>
            <option value="skip">Skip to next step</option>
          </select>
        </div>

        <label class="toggle-row">
          <input type="checkbox" id="insp-chk-disable" ${activeStep.disabled ? 'checked' : ''} />
          <span>Disable and skip this node</span>
        </label>

        <label class="toggle-row">
          <input type="checkbox" id="insp-chk-stop" ${activeStep.stopAfter ? 'checked' : ''} />
          <span>Stop after this node</span>
        </label>

        <label class="toggle-row">
          <input type="checkbox" id="insp-chk-final" ${activeStep.finalSubmit ? 'checked' : ''} />
          <span>Final submission review</span>
        </label>

        <textarea id="insp-target-code" class="dark-textarea" readonly>${escapeHtml(activeStep.target || activeStep.value || '')}</textarea>

        <button class="btn-primary-blue" id="btn-test-node-btn" style="width: 100%; margin-top: 4px;">Test to this node</button>
        <button class="btn-danger-outline" id="btn-del-node-btn" style="width: 100%;">Delete node</button>
      </aside>
    </div>
  `;
}

// ─── 2. Candidate Profile ───────────────────────────────────────────────────

function renderProfileTab() {
  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>👤 Candidate Profile</h3>
        <p>Candidate information used to populate forms and answer job questions.</p>
      </div>
      <button class="btn-primary-blue" id="btn-save-profile">Save Profile</button>
    </div>

    <div class="form-grid-2">
      <div class="form-group">
        <label>Full Name</label>
        <input type="text" id="prof-fullName" class="dark-input" value="${escapeHtml(profile.fullName)}" />
      </div>
      <div class="form-group">
        <label>Email Address</label>
        <input type="email" id="prof-email" class="dark-input" value="${escapeHtml(profile.email)}" />
      </div>
      <div class="form-group">
        <label>Primary Phone</label>
        <input type="tel" id="prof-phone" class="dark-input" value="${escapeHtml(profile.phone)}" />
      </div>
      <div class="form-group">
        <label>Alternative Phone</label>
        <input type="tel" id="prof-altPhone" class="dark-input" value="${escapeHtml(profile.altPhone)}" />
      </div>
      <div class="form-group span-full">
        <label>Street Address</label>
        <input type="text" id="prof-address" class="dark-input" value="${escapeHtml(profile.address)}" />
      </div>
      <div class="form-group">
        <label>City</label>
        <input type="text" id="prof-city" class="dark-input" value="${escapeHtml(profile.city)}" />
      </div>
      <div class="form-group">
        <label>State / Region</label>
        <input type="text" id="prof-state" class="dark-input" value="${escapeHtml(profile.state)}" />
      </div>
      <div class="form-group">
        <label>Degree / Major</label>
        <input type="text" id="prof-degree" class="dark-input" value="${escapeHtml(profile.degree)}" />
      </div>
      <div class="form-group">
        <label>Graduation Year</label>
        <input type="text" id="prof-gradYear" class="dark-input" value="${escapeHtml(profile.graduationYear)}" />
      </div>
      <div class="form-group span-full">
        <label>University / College Name</label>
        <input type="text" id="prof-university" class="dark-input" value="${escapeHtml(profile.university)}" />
      </div>
      <div class="form-group span-full">
        <label>Key Technical Skills</label>
        <textarea id="prof-skills" class="dark-textarea" rows="2">${escapeHtml(profile.skills)}</textarea>
      </div>
      <div class="form-group">
        <label>LinkedIn Profile URL</label>
        <input type="url" id="prof-linkedin" class="dark-input" value="${escapeHtml(profile.linkedin)}" />
      </div>
      <div class="form-group">
        <label>GitHub Profile URL</label>
        <input type="url" id="prof-github" class="dark-input" value="${escapeHtml(profile.github)}" />
      </div>
      <div class="form-group">
        <label>Expected Salary</label>
        <input type="text" id="prof-expectedSalary" class="dark-input" value="${escapeHtml(profile.expectedSalary)}" />
      </div>
      <div class="form-group">
        <label>Notice Period</label>
        <input type="text" id="prof-noticePeriod" class="dark-input" value="${escapeHtml(profile.noticePeriod)}" />
      </div>
    </div>
  `;
}

// ─── 3. AI Providers & Keys ─────────────────────────────────────────────────

function renderApiKeysTab() {
  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>🔑 AI & API Keys</h3>
        <p>Configure OmniRoute, Google Gemini, and Anthropic providers.</p>
      </div>
      <button class="btn-primary-blue" id="btn-save-apikeys">Save Keys</button>
    </div>

    <div class="provider-card-deck">
      <!-- OmniRoute Card -->
      <div class="provider-box">
        <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="font-size: 13px; color: #22c55e;">● OmniRoute Server (http://127.0.0.1:20128)</strong>
            <button class="btn-secondary-gray btn-test-provider" data-provider="omniroute">⚡ Test</button>
          </div>
          <div class="form-grid-3">
            <div class="form-group">
              <label>Base URL</label>
              <input type="text" id="key-omni-url" class="dark-input" value="${escapeHtml(byokConfig.omniroute.baseUrl)}" />
            </div>
            <div class="form-group">
              <label>API Key</label>
              <input type="password" id="key-omni-key" class="dark-input" value="${escapeHtml(byokConfig.omniroute.apiKey)}" />
            </div>
            <div class="form-group">
              <label>Selected Model</label>
              <input type="text" id="key-omni-model" class="dark-input" value="${escapeHtml(byokConfig.omniroute.model)}" />
            </div>
          </div>
        </div>
      </div>

      <!-- Gemini Card -->
      <div class="provider-box">
        <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="font-size: 13px; color: #38bdf8;">● Google Gemini Studio</strong>
            <button class="btn-secondary-gray btn-test-provider" data-provider="gemini">⚡ Test</button>
          </div>
          <div class="form-grid-2">
            <div class="form-group">
              <label>Gemini API Key</label>
              <input type="password" id="key-gemini-key" class="dark-input" value="${escapeHtml(byokConfig.gemini.apiKey)}" />
            </div>
            <div class="form-group">
              <label>Gemini Model</label>
              <select id="key-gemini-model" class="dark-select">
                <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ─── 4. Master AI System Prompt (Single Unified Editor) ──────────────────────

function renderPromptsTab() {
  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>🧠 Master AI System Prompt</h3>
        <p>Single master system prompt. AI agent uses this unified prompt for all browser reasoning.</p>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="btn-secondary-gray" id="btn-reset-prompt">↺ Reset Default</button>
        <button class="btn-primary-blue" id="btn-save-prompt">Save Prompt</button>
      </div>
    </div>

    <div class="form-group">
      <textarea id="master-system-prompt" class="dark-textarea" style="min-height: 440px; font-size: 12px;">${escapeHtml(systemPrompt)}</textarea>
    </div>
  `;
}

// ─── 5. Custom Answers ──────────────────────────────────────────────────────

function renderCustomAnswersTab() {
  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>📝 Custom Question & Answers</h3>
        <p>Exact answers for recurrent recruiter questions.</p>
      </div>
      <button class="btn-primary-blue" id="btn-open-qa-modal">+ Add Answer</button>
    </div>

    <div id="new-qa-drawer" style="display: none; background: #11131c; border: 1px solid var(--border-color); border-radius: 6px; padding: 14px; margin-bottom: 12px;">
      <div class="form-grid-3">
        <div class="form-group">
          <label>Question Pattern</label>
          <input type="text" id="qa-new-q" class="dark-input" placeholder="e.g. willing to relocate" />
        </div>
        <div class="form-group">
          <label>Match Type</label>
          <select id="qa-new-type" class="dark-select">
            <option value="contains">Contains</option>
            <option value="exact">Exact</option>
          </select>
        </div>
        <div class="form-group">
          <label>Exact Answer</label>
          <input type="text" id="qa-new-a" class="dark-input" placeholder="Yes, I am happy to relocate." />
        </div>
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
        <button class="btn-secondary-gray" id="btn-cancel-qa">Cancel</button>
        <button class="btn-primary-blue" id="btn-save-qa-entry">Save Rule</button>
      </div>
    </div>

    <div class="qa-card-list">
      ${customAnswers.map((item, idx) => `
        <div class="qa-entry">
          <div>
            <strong style="color: #fff; font-size: 12px;">${escapeHtml(item.question)}</strong>
            <div style="font-size: 11px; color: #38bdf8; margin-top: 2px;">➔ ${escapeHtml(item.answer)}</div>
          </div>
          <button class="btn-danger-outline btn-del-qa" data-idx="${idx}">Delete</button>
        </div>
      `).join('')}
    </div>
  `;
}

// ─── 6. Resumes Management ──────────────────────────────────────────────────

function renderResumesTab() {
  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>📄 Candidate Resumes</h3>
        <p>Resumes stored in binary format for silent background upload.</p>
      </div>
    </div>

    <div style="background: #11131c; border: 1px dashed var(--border-color); border-radius: 6px; padding: 14px; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;">
      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 24px;">📄</span>
        <div>
          <strong style="font-size: 13px;">Upload Resume File (PDF / DOCX)</strong>
          <p style="font-size: 11px; color: var(--text-muted);">Stored locally for silent injection.</p>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <input type="text" id="resume-label" class="dark-input" placeholder="Resume label" style="width: 150px;" />
        <input type="file" id="resume-file-input" accept=".pdf,.docx,.doc" style="color: var(--text-muted); font-size: 11px;" />
        <button class="btn-primary-blue" id="btn-upload-file">Attach & Save</button>
      </div>
    </div>

    <div class="resume-deck" style="margin-top: 14px;">
      ${resumes.map(r => `
        <div class="resume-item-card">
          <div>
            <strong style="font-size: 13px; color: #fff;">${escapeHtml(r.label || r.name)} ${r.id === defaultResumeId || r.isDefault ? '<span style="color: #22c55e; font-size: 10px; margin-left: 6px;">[DEFAULT]</span>' : ''}</strong>
            <div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">${escapeHtml(r.name)} • ${(r.size ? (r.size / 1024).toFixed(1) + ' KB' : 'PDF')}</div>
          </div>
          <div style="display: flex; gap: 8px;">
            ${r.id !== defaultResumeId ? `<button class="btn-secondary-gray btn-set-default" data-id="${r.id}">Set as Default</button>` : ''}
            <button class="btn-danger-outline btn-del-res" data-id="${r.id}">Delete</button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

// ─── 7. Autonomy & Settings Tab ─────────────────────────────────────────────

function renderSettingsTab() {
  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>⚙️ Autonomy & Settings</h3>
        <p>Control AI decision making and permissions.</p>
      </div>
      <button class="btn-primary-blue" id="btn-save-settings-tab">Save Settings</button>
    </div>

    <div class="form-grid-2">
      <div class="form-group span-full" style="background: #11131c; border: 1px solid var(--border-color); border-radius: 6px; padding: 14px;">
        <label style="font-size: 13px; color: #fff; margin-bottom: 6px;">🤖 AI Decision Making on Ambiguous / Unknown Questions</label>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <label class="toggle-row" style="background: #1b1e2b; padding: 10px; border-radius: 4px;">
            <input type="radio" name="rad-decision" value="autonomous" ${aiDecisionMode === 'autonomous' ? 'checked' : ''} />
            <div>
              <strong style="color: #fff;">Make Own Decisions (Fully Autonomous)</strong>
              <div style="font-size: 10px; color: var(--text-muted);">AI deduces answers from profile/resume and fills all fields without stopping.</div>
            </div>
          </label>
          <label class="toggle-row" style="background: #1b1e2b; padding: 10px; border-radius: 4px;">
            <input type="radio" name="rad-decision" value="ask_human" ${aiDecisionMode === 'ask_human' ? 'checked' : ''} />
            <div>
              <strong style="color: #fff;">Ask Human When Uncertain</strong>
              <div style="font-size: 10px; color: var(--text-muted);">AI pauses and asks in the sidepanel chat whenever an unknown question arises.</div>
            </div>
          </label>
        </div>
      </div>

      <div class="form-group" style="background: #11131c; border: 1px solid var(--border-color); border-radius: 6px; padding: 12px;">
        <label class="toggle-row">
          <input type="checkbox" id="chk-multi-tab" ${allowMultiTabControl ? 'checked' : ''} />
          <div>
            <strong style="color: #fff;">🌐 Allow Multi-Tab Control</strong>
            <div style="font-size: 10px; color: var(--text-muted);">Allow AI to switch, open, and close browser tabs across job portals.</div>
          </div>
        </label>
      </div>

      <div class="form-group" style="background: #11131c; border: 1px solid var(--border-color); border-radius: 6px; padding: 12px;">
        <label class="toggle-row">
          <input type="checkbox" id="chk-settings-access" ${allowSettingsAccess ? 'checked' : ''} />
          <div>
            <strong style="color: #fff;">🔧 Allow AI Access to Settings & Workflows</strong>
            <div style="font-size: 10px; color: var(--text-muted);">Allow AI to read/write workflows and custom answers directly.</div>
          </div>
        </label>
      </div>
    </div>
  `;
}

// ─── Event Binding ───────────────────────────────────────────────────────────

function attachEvents() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      currentTab = btn.getAttribute('data-tab');
      renderAppHub();
    });
  });

  // Search Workflows in left column
  const searchInput = document.getElementById('wf-search-input');
  searchInput?.addEventListener('input', (e) => {
    wfSearchQuery = e.target.value;
    renderAppHub();
  });

  // Select workflow from left column
  document.querySelectorAll('.wf-item-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      selectedWfIndex = parseInt(btn.getAttribute('data-widx'), 10) || 0;
      selectedStepIndex = 0;
      renderAppHub();
    });
  });

  // Select node from dot-canvas
  document.querySelectorAll('.wf-node-block').forEach(block => {
    block.addEventListener('click', () => {
      selectedStepIndex = parseInt(block.getAttribute('data-sidx'), 10) || 0;
      renderAppHub();
    });
  });

  // Inspector updates
  const curWf = workflows[selectedWfIndex];
  if (curWf && curWf.steps?.[selectedStepIndex]) {
    const activeStep = curWf.steps[selectedStepIndex];
    document.getElementById('insp-name')?.addEventListener('input', (e) => { activeStep.name = e.target.value; });
    document.getElementById('insp-val')?.addEventListener('input', (e) => { activeStep.value = e.target.value; });
    document.getElementById('insp-wait')?.addEventListener('input', (e) => { activeStep.waitMs = parseInt(e.target.value, 10) || 400; });
    document.getElementById('insp-chk-disable')?.addEventListener('change', (e) => { activeStep.disabled = e.target.checked; });
    document.getElementById('insp-chk-stop')?.addEventListener('change', (e) => { activeStep.stopAfter = e.target.checked; });
    document.getElementById('insp-chk-final')?.addEventListener('change', (e) => { activeStep.finalSubmit = e.target.checked; });
  }

  // Node deletion
  document.getElementById('btn-del-node-btn')?.addEventListener('click', () => {
    if (!curWf || curWf.steps.length <= 1) return alert('Workflow must have at least one node.');
    curWf.steps.splice(selectedStepIndex, 1);
    if (selectedStepIndex >= curWf.steps.length) selectedStepIndex = curWf.steps.length - 1;
    persist(STORAGE_KEYS.WORKFLOWS, workflows, 'Node deleted.');
    renderAppHub();
  });

  // Add AI Node
  document.getElementById('btn-add-ai-node-btn')?.addEventListener('click', () => {
    if (!curWf) return;
    curWf.steps.push({
      id: 's_' + Date.now(),
      type: 'ai_fallback',
      name: 'Ask AI for unknown fields',
      value: 'Auto answer screening questions',
      waitMs: 800,
      color: '#14b8a6',
      badge: 'AI',
      target: 'Screening questions',
      disabled: false,
      stopAfter: false,
      finalSubmit: false,
    });
    selectedStepIndex = curWf.steps.length - 1;
    persist(STORAGE_KEYS.WORKFLOWS, workflows, 'AI Node added.');
    renderAppHub();
  });

  // Add Stop Node
  document.getElementById('btn-add-stop-node-btn')?.addEventListener('click', () => {
    if (!curWf) return;
    curWf.steps.push({
      id: 's_' + Date.now(),
      type: 'stop',
      name: 'Stop workflow',
      value: '',
      waitMs: 400,
      color: '#ef4444',
      badge: 'STOP',
      target: 'button[type="submit"]',
      disabled: false,
      stopAfter: true,
      finalSubmit: true,
    });
    selectedStepIndex = curWf.steps.length - 1;
    persist(STORAGE_KEYS.WORKFLOWS, workflows, 'Stop Node added.');
    renderAppHub();
  });

  // Save Workflow
  const saveWfHandler = async () => {
    if (curWf) {
      curWf.name = document.getElementById('wf-prop-name')?.value || curWf.name;
      curWf.startUrl = document.getElementById('wf-prop-url')?.value || curWf.startUrl;
      curWf.resumeId = document.getElementById('wf-prop-resume')?.value || '';
      curWf.variables = {
        role: document.getElementById('wf-prop-role')?.value || '',
        location: document.getElementById('wf-prop-loc')?.value || '',
      };
      await persist(STORAGE_KEYS.WORKFLOWS, workflows, 'Workflow saved successfully!');
    }
  };
  document.getElementById('btn-wf-save-main')?.addEventListener('click', saveWfHandler);

  // Helper to normalize entered URLs (preserves exact URLs!)
  function normalizeUrl(input) {
    let u = (input || '').trim();
    if (!u) return 'https://www.naukri.com/';
    if (u.startsWith('http://') || u.startsWith('https://')) return u;
    const lower = u.toLowerCase();
    if (lower === 'naukri') return 'https://www.naukri.com/';
    if (lower === 'indeed' || lower === 'inded') return 'https://www.indeed.com/';
    if (lower === 'linkedin') return 'https://www.linkedin.com/jobs/';
    if (!u.includes('.')) u = `https://www.google.com/search?q=${encodeURIComponent(u)}`;
    else u = 'https://' + u;
    return u;
  }

  // Open side panel for target tab with recording mode
  async function openSidePanelForTab(tabId, wfId, mode = 'record') {
    try {
      await chrome.storage.local.set({
        activeSidepanelView: mode === 'record' ? 'recorder' : 'chat',
        currentRecordingWorkflowId: wfId,
      });
      if (chrome.sidePanel && typeof chrome.sidePanel.open === 'function' && tabId) {
        await chrome.sidePanel.open({ tabId });
        return;
      }
    } catch (e) {
      console.warn('sidePanel.open error:', e);
    }
  }

  // Manual create & record
  document.getElementById('btn-manual-open-record')?.addEventListener('click', async () => {
    const name = document.getElementById('manual-wf-name')?.value.trim() || 'Recorded workflow';
    const rawUrl = document.getElementById('manual-wf-url')?.value.trim() || 'https://www.naukri.com/';
    const targetUrl = normalizeUrl(rawUrl);

    const newWf = {
      id: 'wf_' + Date.now(),
      name,
      startUrl: targetUrl,
      resumeId: '',
      variables: { role: '', location: '' },
      steps: [
        { id: 's1', type: 'open_url', name: 'Open ' + targetUrl, value: targetUrl, waitMs: 400, color: '#22c55e', badge: 'URL', target: targetUrl, disabled: false, stopAfter: false, finalSubmit: false }
      ],
    };
    workflows.push(newWf);
    selectedWfIndex = workflows.length - 1;
    selectedStepIndex = 0;
    await persist(STORAGE_KEYS.WORKFLOWS, workflows, 'Opening website with Side Panel recorder...');
    renderAppHub();

    // Open target website tab & start in-page workflow recorder with element tracking
    try {
      const newTab = await chrome.tabs.create({ url: targetUrl, active: true });
      if (newTab?.id) {
        const startRecording = () => {
          chrome.runtime.sendMessage({
            action: 'WORKFLOW_RECORD_START',
            tabId: newTab.id,
            name,
            workflowId: newWf.id,
            startUrl: targetUrl,
          }).catch(() => {});
        };

        chrome.tabs.onUpdated.addListener(function onComplete(tabId, info) {
          if (tabId === newTab.id && info.status === 'complete') {
            chrome.tabs.onUpdated.removeListener(onComplete);
            startRecording();
          }
        });
        setTimeout(startRecording, 1200);
      }
    } catch (err) {
      showToast('Could not open browser tab: ' + err.message, true);
    }
  });

  // Run main workflow
  document.getElementById('btn-wf-run-main')?.addEventListener('click', async () => {
    if (!curWf) return;
    await saveWfHandler();
    const targetUrl = normalizeUrl(curWf.startUrl);
    try {
      const newTab = await chrome.tabs.create({ url: targetUrl, active: true });
      if (newTab?.id) {
        await openSidePanelForTab(newTab.id, curWf.id, 'run');
      }
      showToast('Workflow launched with Side Panel!');
    } catch (err) {
      showToast('Run error: ' + err.message, true);
    }
  });

  // Test to this node
  document.getElementById('btn-test-node-btn')?.addEventListener('click', async () => {
    if (!curWf) return;
    await saveWfHandler();
    const targetUrl = normalizeUrl(curWf.startUrl);
    try {
      const newTab = await chrome.tabs.create({ url: targetUrl, active: true });
      if (newTab?.id) {
        await openSidePanelForTab(newTab.id, curWf.id, 'run');
      }
      showToast(`Testing workflow up to Step ${selectedStepIndex + 1}...`);
    } catch (err) {
      showToast('Test error: ' + err.message, true);
    }
  });

  // Create Branch
  document.getElementById('btn-create-branch')?.addEventListener('click', async () => {
    if (!curWf) return;
    const branchName = document.getElementById('branch-name-input')?.value.trim() || `${curWf.name} (Branch)`;
    const newBranch = {
      ...JSON.parse(JSON.stringify(curWf)),
      id: 'wf_' + Date.now(),
      name: branchName,
      createdAt: Date.now(),
    };
    workflows.push(newBranch);
    selectedWfIndex = workflows.length - 1;
    selectedStepIndex = 0;
    await persist(STORAGE_KEYS.WORKFLOWS, workflows, `Created branch "${branchName}"!`);
    renderAppHub();
  });

  // Create Branch without disabled nodes
  document.getElementById('btn-create-branch-nodisabled')?.addEventListener('click', async () => {
    if (!curWf) return;
    const branchName = document.getElementById('branch-name-input')?.value.trim() || `${curWf.name} (Active Nodes)`;
    const activeSteps = (curWf.steps || []).filter(s => !s.disabled);
    const newBranch = {
      ...JSON.parse(JSON.stringify(curWf)),
      id: 'wf_' + Date.now(),
      name: branchName,
      steps: activeSteps.length > 0 ? activeSteps : curWf.steps,
      createdAt: Date.now(),
    };
    workflows.push(newBranch);
    selectedWfIndex = workflows.length - 1;
    selectedStepIndex = 0;
    await persist(STORAGE_KEYS.WORKFLOWS, workflows, `Created branch without disabled nodes!`);
    renderAppHub();
  });

  // Status button
  document.getElementById('btn-wf-status')?.addEventListener('click', () => {
    showToast(`Workflow "${curWf?.name || 'Main'}" has ${curWf?.steps?.length || 0} nodes.`);
  });

  // Delete Workflow
  document.getElementById('btn-del-wf-main')?.addEventListener('click', () => {
    if (workflows.length <= 1) return alert('Cannot delete the only workflow.');
    if (confirm(`Delete "${curWf?.name}"?`)) {
      workflows.splice(selectedWfIndex, 1);
      selectedWfIndex = 0;
      selectedStepIndex = 0;
      persist(STORAGE_KEYS.WORKFLOWS, workflows, 'Workflow deleted.');
      renderAppHub();
    }
  });

  // Profile Save
  document.getElementById('btn-save-profile')?.addEventListener('click', async () => {
    profile = {
      fullName: document.getElementById('prof-fullName')?.value || '',
      email: document.getElementById('prof-email')?.value || '',
      phone: document.getElementById('prof-phone')?.value || '',
      altPhone: document.getElementById('prof-altPhone')?.value || '',
      address: document.getElementById('prof-address')?.value || '',
      city: document.getElementById('prof-city')?.value || '',
      state: document.getElementById('prof-state')?.value || '',
      degree: document.getElementById('prof-degree')?.value || '',
      graduationYear: document.getElementById('prof-gradYear')?.value || '',
      university: document.getElementById('prof-university')?.value || '',
      skills: document.getElementById('prof-skills')?.value || '',
      linkedin: document.getElementById('prof-linkedin')?.value || '',
      github: document.getElementById('prof-github')?.value || '',
      expectedSalary: document.getElementById('prof-expectedSalary')?.value || '',
      noticePeriod: document.getElementById('prof-noticePeriod')?.value || '',
    };
    await persist(STORAGE_KEYS.USER_PROFILE, profile, 'Profile updated!');
  });

  // AI Keys Save
  document.getElementById('btn-save-apikeys')?.addEventListener('click', async () => {
    byokConfig.omniroute.baseUrl = document.getElementById('key-omni-url')?.value || '';
    byokConfig.omniroute.apiKey = document.getElementById('key-omni-key')?.value || '';
    byokConfig.omniroute.model = document.getElementById('key-omni-model')?.value || '';
    byokConfig.gemini.apiKey = document.getElementById('key-gemini-key')?.value || '';
    byokConfig.gemini.model = document.getElementById('key-gemini-model')?.value || 'gemini-2.0-flash';
    await persist(STORAGE_KEYS.BYOK_CONFIG, byokConfig, 'API Keys saved!');
  });

  // Master Prompt Save & Reset
  document.getElementById('btn-save-prompt')?.addEventListener('click', async () => {
    systemPrompt = document.getElementById('master-system-prompt')?.value || '';
    await persist(STORAGE_KEYS.SYSTEM_PROMPT, systemPrompt, 'Master System Prompt saved!');
  });
  document.getElementById('btn-reset-prompt')?.addEventListener('click', async () => {
    if (confirm('Reset Master Prompt to default?')) {
      systemPrompt = DEFAULT_MASTER_SYSTEM_PROMPT;
      const el = document.getElementById('master-system-prompt');
      if (el) el.value = systemPrompt;
      await persist(STORAGE_KEYS.SYSTEM_PROMPT, systemPrompt, 'Prompt reset.');
    }
  });

  // Custom Answers Events
  document.getElementById('btn-open-qa-modal')?.addEventListener('click', () => {
    const el = document.getElementById('new-qa-drawer');
    if (el) el.style.display = 'block';
  });
  document.getElementById('btn-cancel-qa')?.addEventListener('click', () => {
    const el = document.getElementById('new-qa-drawer');
    if (el) el.style.display = 'none';
  });
  document.getElementById('btn-save-qa-entry')?.addEventListener('click', async () => {
    const q = document.getElementById('qa-new-q')?.value.trim();
    const a = document.getElementById('qa-new-a')?.value.trim();
    const t = document.getElementById('qa-new-type')?.value || 'contains';
    if (!q || !a) return alert('Enter question pattern and answer.');
    customAnswers.push({ id: 'qa_' + Date.now(), question: q, answer: a, matchType: t });
    await persist(STORAGE_KEYS.CUSTOM_ANSWERS, customAnswers, 'Answer rule saved!');
    renderAppHub();
  });
  document.querySelectorAll('.btn-del-qa').forEach(btn => {
    btn.addEventListener('click', async () => {
      const idx = parseInt(btn.getAttribute('data-idx'), 10);
      customAnswers.splice(idx, 1);
      await persist(STORAGE_KEYS.CUSTOM_ANSWERS, customAnswers, 'Rule removed.');
      renderAppHub();
    });
  });

  // Resumes Events
  document.getElementById('btn-upload-file')?.addEventListener('click', () => {
    const fileInput = document.getElementById('resume-file-input');
    const labelInput = document.getElementById('resume-label');
    const file = fileInput?.files?.[0];
    if (!file) return alert('Select a resume file.');

    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = reader.result.split(',')[1];
      const newRes = {
        id: 'res_' + Date.now(),
        name: file.name,
        label: labelInput?.value || file.name.replace(/\.[^/.]+$/, ''),
        size: file.size,
        data: base64,
        type: file.type || 'application/pdf',
        isDefault: resumes.length === 0,
      };
      resumes.push(newRes);
      if (resumes.length === 1) defaultResumeId = newRes.id;
      await persist(STORAGE_KEYS.RESUMES, resumes, 'Resume uploaded!');
      await persist(STORAGE_KEYS.DEFAULT_RESUME, defaultResumeId);
      renderAppHub();
    };
    reader.readAsDataURL(file);
  });
  document.querySelectorAll('.btn-set-default').forEach(btn => {
    btn.addEventListener('click', async () => {
      defaultResumeId = btn.getAttribute('data-id');
      await persist(STORAGE_KEYS.DEFAULT_RESUME, defaultResumeId, 'Default resume set!');
      renderAppHub();
    });
  });
  document.querySelectorAll('.btn-del-res').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      resumes = resumes.filter(r => r.id !== id);
      if (defaultResumeId === id && resumes.length > 0) defaultResumeId = resumes[0].id;
      await persist(STORAGE_KEYS.RESUMES, resumes, 'Resume deleted.');
      await persist(STORAGE_KEYS.DEFAULT_RESUME, defaultResumeId);
      renderAppHub();
    });
  });

  // Settings Save
  document.getElementById('btn-save-settings-tab')?.addEventListener('click', async () => {
    const rad = document.querySelector('input[name="rad-decision"]:checked');
    aiDecisionMode = rad?.value || 'autonomous';
    allowMultiTabControl = document.getElementById('chk-multi-tab')?.checked ?? true;
    allowSettingsAccess = document.getElementById('chk-settings-access')?.checked ?? true;
    await persist(STORAGE_KEYS.AI_DECISION_MODE, aiDecisionMode);
    await persist(STORAGE_KEYS.ALLOW_MULTI_TAB, allowMultiTabControl);
    await persist(STORAGE_KEYS.ALLOW_SETTINGS_ACCESS, allowSettingsAccess, 'Settings saved!');
    renderAppHub();
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}
