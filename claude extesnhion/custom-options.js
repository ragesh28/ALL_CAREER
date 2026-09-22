/**
 * AutoFill V4 — Automation Studio & Options Hub
 * Pixel-accurate Workflow Studio matching Autofill V4
 * Full 3-Column Architecture: Workflows List, Dot-Grid Graph Canvas, and Node Inspector.
 */

const STORAGE_KEYS = {
  BYOK_CONFIG: 'byok_config',
  API_KEYS: 'apiKeys',
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
  FILE_UPLOAD_MODE: 'fileUploadMode',
  HISTORY_RETENTION_DAYS: 'historyRetentionDays',
};

const DEFAULT_MASTER_SYSTEM_PROMPT = `You are AutoFill V4, an elite autonomous browser agent and job application assistant with direct browser execution capabilities.
You inspect interactive accessibility trees, click elements, upload resumes silently, auto-fill forms, manage browser tabs, and record workflows.

### AUTONOMY & DECISION RULES:
1. Grounding: Use information from the user details profile and attached documents.
2. Near-Miss Hints: Always prioritize matching previous answers from application history.
3. Uncertainty & Autonomy:
   - If Autonomous Decision Mode is ON: Answer all fields decisively. Never stop to ask human.
   - If Supervised Mode is ON: If a mandatory question is completely unknown and not in profile, ask the user in chat.

### CAPABILITIES & TOOLS:
- Click: {"thought": "...", "action": "click", "ref_id": "ref_1"}
- Type: {"thought": "...", "action": "type", "ref_id": "ref_2", "text": "value", "press_enter": false}
- Upload Resume: {"thought": "...", "action": "upload_resume", "ref_id": "ref_3"}
- Select Dropdown: {"thought": "...", "action": "select_option", "ref_id": "ref_4", "value": "Option"}
- AutoFill Form: {"thought": "...", "action": "autofill_page"}
- List Workflows: {"thought": "...", "action": "list_workflows"}
- Update Workflow Input: {"thought": "...", "action": "update_workflow_input", "workflowName": "...", "stepIndex": 1, "value": "New Value"}
- Run Workflow: {"thought": "...", "action": "run_workflow", "workflowName": "..."}
- Create Workflow: {"thought": "...", "action": "create_workflow", "workflowName": "...", "steps": [...]}
- Delete Workflow: {"thought": "...", "action": "delete_workflow", "workflowName": "..."}
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
let historyRetentionDays = 2; // Default 2 days retention
let profile = { ...DEFAULT_PROFILE };
let byokConfig = {
  activeProvider: 'omniroute',
  activeKeyId: '',
  apiKeys: [],
  omniroute: { baseUrl: 'http://127.0.0.1:20128/v1', apiKey: 'sk-f46d845e6a300177-0a895e-fbfbd25b', model: 'antigravity/gemini-3.6-flash-high' },
  gemini: { apiKey: '', model: 'gemini-2.0-flash' },
  openai: { apiKey: '', model: 'gpt-4o' },
};

const PROVIDER_METADATA = {
  omniroute: { name: 'OmniRoute Local Server', icon: '🔴', tag: 'Local Routing', placeholder: 'sk-...', defaultModel: 'antigravity/gemini-3.6-flash-high', needsBaseUrl: true, defaultBaseUrl: 'http://127.0.0.1:20128/v1' },
  openai: { name: 'OpenAI', icon: '🟢', tag: 'Official GPT & o1/o3', placeholder: 'sk-proj-...', defaultModel: 'gpt-4o', defaultBaseUrl: 'https://api.openai.com/v1' },
  gemini: { name: 'Google Gemini', icon: '✨', tag: 'Gemini 2.5 & 3.8', placeholder: 'AIzaSy...', defaultModel: 'gemini-2.0-flash', defaultBaseUrl: 'https://generativelanguage.googleapis.com' },
  openrouter: { name: 'OpenRouter', icon: '🟣', tag: 'Aggregator 300+', placeholder: 'sk-or-v1-...', defaultModel: 'google/gemini-2.0-flash-001', defaultBaseUrl: 'https://openrouter.ai/api/v1' },
  groq: { name: 'Groq', icon: '⚡', tag: 'LPU Inference', placeholder: 'gsk_...', defaultModel: 'llama-3.3-70b-versatile', defaultBaseUrl: 'https://api.groq.com/openai/v1' },
  nvidia: { name: 'Nvidia NIM', icon: '🟢', tag: 'Microservices', placeholder: 'nvapi-...', defaultModel: 'meta/llama-3.3-70b-instruct', defaultBaseUrl: 'https://integrate.api.nvidia.com/v1' },
  ollama: { name: 'Ollama (Local URL)', icon: '🦙', tag: 'Local Host', placeholder: 'No key needed', defaultModel: 'llama3:latest', needsBaseUrl: true, defaultBaseUrl: 'http://localhost:11434' },
  huggingface: { name: 'Hugging Face', icon: '🤗', tag: 'Inference API', placeholder: 'hf_...', defaultModel: 'meta-llama/Llama-3.3-70B-Instruct', defaultBaseUrl: 'https://api-inference.huggingface.co/v1' },
  mistral: { name: 'Mistral AI', icon: '📝', tag: 'Large & NeMo', placeholder: 'API Key', defaultModel: 'mistral-large-latest', defaultBaseUrl: 'https://api.mistral.ai/v1' },
  cohere: { name: 'Cohere', icon: '💬', tag: 'Command R+', placeholder: 'API Key', defaultModel: 'command-r-plus-08-2024', defaultBaseUrl: 'https://api.cohere.ai/v1' },
  cloudflare: { name: 'Cloudflare Workers AI', icon: '☁️', tag: 'Serverless AI', placeholder: 'API Token', defaultModel: '@cf/meta/llama-3.3-70b-instruct-fp8-fast', needsAccountId: true, defaultBaseUrl: 'https://api.cloudflare.com/client/v4' },
};

const PRESET_MODELS = {
  openai: [
    { id: 'gpt-4o', name: 'GPT-4o (Omni Flagship)' },
    { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
    { id: 'o1', name: 'o1 Reasoning Model' },
    { id: 'o3-mini', name: 'o3 Mini' },
    { id: 'chatgpt-4o-latest', name: 'ChatGPT-4o Latest' },
    { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' },
  ],
  gemini: [
    { id: 'gemini-3.8-flash-high', name: 'Gemini 3.8 Flash High' },
    { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash' },
    { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro' },
    { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' },
    { id: 'gemini-3.6-light-flash', name: 'Gemini 3.6 Light Flash' },
  ],
  openrouter: [
    { id: 'deepseek/deepseek-r1', name: 'DeepSeek R1' },
    { id: 'openai/gpt-4o', name: 'GPT-4o' },
    { id: 'google/gemini-2.0-flash-001', name: 'Gemini 2.0 Flash' },
    { id: 'meta-llama/llama-3.3-70b-instruct', name: 'Llama 3.3 70B Instruct' },
    { id: 'google/gemini-2.0-flash-lite-001', name: 'Gemini 2.0 Flash Lite' },
  ],
  groq: [
    { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B Versatile' },
    { id: 'llama-3.1-8b-instant', name: 'Llama 3.1 8B Instant' },
    { id: 'deepseek-r1-distill-llama-70b', name: 'DeepSeek R1 Distill 70B' },
    { id: 'mixtral-8x7b-32768', name: 'Mixtral 8x7B' },
  ],
  cloudflare: [
    { id: '@cf/meta/llama-3.3-70b-instruct-fp8-fast', name: 'Llama 3.3 70B Instruct (Fast)' },
    { id: '@cf/deepseek-ai/deepseek-r1-distill-qwen-32b', name: 'DeepSeek R1 Distill 32B' },
    { id: '@cf/meta/llama-3.1-8b-instruct', name: 'Llama 3.1 8B Instruct' },
    { id: '@cf/qwen/qwen2.5-72b-instruct', name: 'Qwen 2.5 72B Instruct' },
  ],
  huggingface: [
    { id: 'meta-llama/Llama-3.3-70B-Instruct', name: 'Llama 3.3 70B Instruct' },
    { id: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-32B', name: 'DeepSeek R1 Distill Qwen 32B' },
    { id: 'Qwen/Qwen2.5-72B-Instruct', name: 'Qwen 2.5 72B Instruct' },
    { id: 'meta-llama/Llama-3.1-8B-Instruct', name: 'Llama 3.1 8B Instruct' },
  ],
  mistral: [
    { id: 'mistral-large-latest', name: 'Mistral Large' },
    { id: 'mistral-small-latest', name: 'Mistral Small' },
    { id: 'open-mistral-nemo', name: 'Mistral NeMo' },
  ],
  cohere: [
    { id: 'command-r-plus-08-2024', name: 'Command R+' },
    { id: 'command-r-08-2024', name: 'Command R' },
  ],
  nvidia: [
    { id: 'meta/llama-3.3-70b-instruct', name: 'Llama 3.3 70B Instruct' },
    { id: 'nvidia/llama-3.1-nemotron-70b-instruct', name: 'Llama 3.1 Nemotron 70B' },
    { id: 'meta/llama-3.1-8b-instruct', name: 'Llama 3.1 8B Instruct' },
  ],
  ollama: [
    { id: 'llama3:latest', name: 'Llama 3 (Local)' },
    { id: 'mistral:latest', name: 'Mistral (Local)' },
    { id: 'deepseek-r1:latest', name: 'DeepSeek R1 (Local)' },
  ],
  omniroute: [
    { id: 'antigravity/gemini-3.6-flash-high', name: 'Gemini 3.6 Flash High' },
    { id: 'auto/fast', name: 'Fastest Model (Auto Routing)' },
    { id: 'auto/best-coding', name: 'Best Coding Model' },
    { id: 'auto/smart', name: 'Smartest Model' },
  ],
};

function getProviderLogoSvg(provider, size = 24) {
  const p = String(provider || '').toLowerCase();
  switch (p) {
    case 'openai':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M22.28 9.82a5.98 5.98 0 0 0-.51-4.91 6.05 6.05 0 0 0-6.51-2.9A6.07 6.07 0 0 0 4.98 4.18a5.98 5.98 0 0 0-4 2.9 6.05 6.05 0 0 0 .74 7.1 5.98 5.98 0 0 0 .51 4.91 6.05 6.05 0 0 0 6.52 2.9A5.98 5.98 0 0 0 13.26 24a6.06 6.06 0 0 0 5.77-4.2 5.99 5.99 0 0 0 4-2.9 6.06 6.06 0 0 0-.75-7.08zm-9.02 12.61a4.48 4.48 0 0 1-2.88-1.04l.14-.08 4.78-2.76a.79.79 0 0 0 .39-.68v-6.74l2.02 1.17c.02.01.03.03.04.05v5.58a4.5 4.5 0 0 1-4.49 4.5zm-9.66-4.13a4.47 4.47 0 0 1-.53-3.01l.14.08 4.78 2.76a.77.77 0 0 0 .78 0l5.85-3.37v2.33a.08.08 0 0 1-.03.06L9.74 19.95a4.5 4.5 0 0 1-6.14-1.65zM2.34 7.9a4.48 4.48 0 0 1 2.37-1.98V11.6c0 .28.15.53.39.68l5.81 3.35-2.02 1.17a.08.08 0 0 1-.07 0l-4.83-2.79A4.5 4.5 0 0 1 2.34 7.9zm16.6 3.85L13.1 8.38l2.02-1.16a.08.08 0 0 1 .07 0l4.83 2.79a4.5 4.5 0 0 1-.68 8.1V12.44a.79.79 0 0 0-.4-.69zm2.01-3.02l-.14-.09-4.77-2.78a.78.78 0 0 0-.79 0L9.41 9.23V6.9a.07.07 0 0 1 .03-.06l4.83-2.79a4.5 4.5 0 0 1 6.68 4.66zM8.31 12.86l-2.02-1.16a.08.08 0 0 1-.04-.06V6.07a4.5 4.5 0 0 1 7.38-3.45l-.14.08-4.79 2.76a.79.79 0 0 0-.39.68v6.72zm1.1-2.36l2.6-1.5 2.6 1.5v3l-2.6 1.5-2.6-1.5Z" fill="#10A37F"/>
      </svg>`;
    case 'gemini':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 0C12 6.627 6.627 12 0 12C6.627 12 12 17.373 12 24C12 17.373 17.373 12 24 12C17.373 12 12 6.627 12 0Z" fill="url(#gemini-gradient-${size})"/>
        <defs>
          <linearGradient id="gemini-gradient-${size}" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#4E82EE"/>
            <stop offset="50%" stop-color="#9B72CB"/>
            <stop offset="100%" stop-color="#D96570"/>
          </linearGradient>
        </defs>
      </svg>`;
    case 'groq':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="11" fill="rgba(245, 80, 54, 0.15)"/>
        <path d="M13.5 3L5.5 13.5h5l-1.5 7.5 8-10.5h-5l1.5-7.5z" fill="#F55036"/>
      </svg>`;
    case 'openrouter':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path fill-rule="evenodd" clip-rule="evenodd" d="M10 4C5.58 4 2 7.58 2 12C2 16.42 5.58 20 10 20H18C19.1 20 19.8 19 19.3 18.1L17.2 14.5C18.3 13.5 19 12 19 10.5C19 6.9 16.1 4 12.5 4H10ZM10 8C7.79 8 6 9.79 6 12C6 14.21 7.79 16 10 16C12.21 16 14 14.21 14 12C14 9.79 12.21 8 10 8Z" fill="#6B11F4"/>
      </svg>`;
    case 'mistral':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="3" width="4" height="4" fill="#F97316"/>
        <rect x="18" y="3" width="4" height="4" fill="#F97316"/>
        <rect x="2" y="7" width="8" height="4" fill="#F97316"/>
        <rect x="14" y="7" width="8" height="4" fill="#F97316"/>
        <rect x="2" y="11" width="20" height="4" fill="#F97316"/>
        <rect x="2" y="15" width="8" height="4" fill="#F97316"/>
        <rect x="14" y="15" width="8" height="4" fill="#F97316"/>
        <rect x="2" y="19" width="4" height="4" fill="#F97316"/>
        <rect x="18" y="19" width="4" height="4" fill="#F97316"/>
      </svg>`;
    case 'cohere':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="12" r="6" fill="#D47559"/>
        <circle cx="16" cy="12" r="6" fill="#39594C" fill-opacity="0.85"/>
      </svg>`;
    case 'nvidia':
      return `<svg width="${size}" height="${size}" viewBox="0 0 28 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="13" y="3" width="14" height="18" rx="1.5" fill="#76B900"/>
        <path d="M13 5.2C15.8 5.2 18.6 6.3 20.6 8.2L18.8 9.9C17.2 8.4 15.1 7.5 13 7.5V5.2Z" fill="#FFFFFF"/>
        <path d="M13 8.8C14.8 8.8 16.5 9.6 17.7 11L16 12.3C15.2 11.3 14.1 10.7 13 10.7V8.8Z" fill="#FFFFFF"/>
        <path d="M13 12C14.1 12 15.2 12.7 16 13.7L17.7 15C16.5 16.4 14.8 17.2 13 17.2V15.3C14.1 15.3 15.2 14.7 16 13.7" fill="#FFFFFF"/>
        <path d="M13 16.5C15.1 16.5 17.2 15.6 18.8 14.1L20.6 15.8C18.6 17.7 15.8 18.8 13 18.8V16.5Z" fill="#FFFFFF"/>
        <path d="M13 5.2V7.5C10.6 7.5 8.4 8.6 6.8 10.5C5.4 12.1 5.4 14.4 6.8 16C8.4 17.9 10.6 19 13 19V21.2C9.8 21.2 6.9 19.8 4.8 17.4C2.8 15.1 2.8 11.9 4.8 9.6C6.9 7.2 9.8 5.2 13 5.2Z" fill="#76B900"/>
        <path d="M13 8.8V10.7C11.5 10.7 10.2 11.4 9.3 12.6C8.7 13.3 8.7 14.2 9.3 14.9C10.2 16.1 11.5 16.8 13 16.8V18.8C10.8 18.8 8.8 17.8 7.5 16.1C6.4 14.7 6.4 12.8 7.5 11.4C8.8 9.7 10.8 8.8 13 8.8Z" fill="#76B900"/>
        <circle cx="13" cy="13.7" r="1.5" fill="#76B900"/>
      </svg>`;
    case 'cloudflare':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M19.4 11.2c-.3-2.6-2.5-4.7-5.2-4.7-2.1 0-3.9 1.2-4.7 3-.4-.1-.9-.2-1.3-.2-2.3 0-4.2 1.9-4.2 4.2 0 .2 0 .4.1.6C2.2 14.5 1 16.1 1 18c0 2.2 1.8 4 4 4h14.5c2.5 0 4.5-2 4.5-4.5 0-2.4-1.9-4.3-4.3-4.3-.1-1.1-.7-2.1-1.6-2.7l1.3.7z" fill="#F38020"/>
      </svg>`;
    case 'huggingface':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="11.5" r="9.5" fill="#FFD21E" stroke="#FF9D00" stroke-width="0.8"/>
        <path d="M7.8 9.5C8.2 8.5 9.4 8.5 9.8 9.5" stroke="#2B2D42" stroke-width="1.8" stroke-linecap="round"/>
        <path d="M14.2 9.5C14.6 8.5 15.8 8.5 16.2 9.5" stroke="#2B2D42" stroke-width="1.8" stroke-linecap="round"/>
        <path d="M8.8 12.5C8.8 12.5 9.5 16 12 16C14.5 16 15.2 12.5 15.2 12.5H8.8Z" fill="#2B2D42"/>
        <path d="M10.2 14.5C10.8 15.4 11.4 15.8 12 15.8C12.6 15.8 13.2 15.4 13.8 14.5C13.2 13.8 12.6 13.5 12 13.5C11.4 13.5 10.8 13.8 10.2 14.5Z" fill="#EF476F"/>
        <path d="M2.5 18C2.5 15.5 4.5 14 6.5 14.5C7.2 13 8.5 13.5 8.8 15C9.8 14 11 15 10.5 16.8C10.2 18 8.5 20.5 5.5 20.5C3.5 20.5 2.5 19.5 2.5 18Z" fill="#FFD21E" stroke="#FF9D00" stroke-width="0.9"/>
        <path d="M21.5 18C21.5 15.5 19.5 14 17.5 14.5C16.8 13 15.5 13.5 15.2 15C14.2 14 13 15 13.5 16.8C13.8 18 15.5 20.5 18.5 20.5C20.5 20.5 21.5 19.5 21.5 18Z" fill="#FFD21E" stroke="#FF9D00" stroke-width="0.9"/>
      </svg>`;
    case 'ollama':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M7 6.5C7 4.5 7.8 3 8.8 3C9.8 3 10.5 4.5 10.5 6.5C11 6.2 11.5 6 12 6C12.5 6 13 6.2 13.5 6.5C13.5 4.5 14.2 3 15.2 3C16.2 3 17 4.5 17 6.5C18.5 7.5 19.5 9 19.5 11C19.5 12.5 19 13.5 18.5 14.5C19 16 19.5 17.5 19.5 19.5V21H4.5V19.5C4.5 17.5 5 16 5.5 14.5C5 13.5 4.5 12.5 4.5 11C4.5 9 5.5 7.5 7 6.5Z" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M8.8 4.2C8.5 4.8 8.5 5.8 8.8 6.5" stroke="#FFFFFF" stroke-width="1.2" stroke-linecap="round"/>
        <path d="M15.2 4.2C15.5 4.8 15.5 5.8 15.2 6.5" stroke="#FFFFFF" stroke-width="1.2" stroke-linecap="round"/>
        <circle cx="8.5" cy="11.5" r="1.2" fill="#FFFFFF"/>
        <circle cx="15.5" cy="11.5" r="1.2" fill="#FFFFFF"/>
        <ellipse cx="12" cy="13.8" rx="2.4" ry="1.8" stroke="#FFFFFF" stroke-width="1.3" fill="none"/>
        <path d="M11.3 13.2L12 14M12.7 13.2L12 14M12 14V14.8" stroke="#FFFFFF" stroke-width="1.2" stroke-linecap="round"/>
      </svg>`;
    case 'omniroute':
    default:
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="24" height="24" rx="5.5" fill="#E5484D"/>
        <line x1="12" y1="12" x2="12" y2="5.5" stroke="#FFFFFF" stroke-width="1.3" stroke-linecap="round"/>
        <line x1="12" y1="11.5" x2="6.2" y2="7.5" stroke="#FFFFFF" stroke-width="1.3" stroke-linecap="round"/>
        <line x1="12" y1="11.5" x2="17.8" y2="7.5" stroke="#FFFFFF" stroke-width="1.3" stroke-linecap="round"/>
        <line x1="12" y1="12.5" x2="6.2" y2="17" stroke="#FFFFFF" stroke-width="1.3" stroke-linecap="round"/>
        <line x1="12" y1="13" x2="12" y2="19.5" stroke="#FFFFFF" stroke-width="1.3" stroke-linecap="round"/>
        <line x1="12" y1="12.5" x2="17.8" y2="17" stroke="#FFFFFF" stroke-width="1.3" stroke-linecap="round"/>
        <path d="M12 9.5C13.2 9.5 14 10.5 14 11.8C14 13.5 12 15.5 12 15.5C12 15.5 10 13.5 10 11.8C10 10.5 10.8 9.5 12 9.5Z" fill="#FFFFFF"/>
        <circle cx="12" cy="5.5" r="1.5" fill="#FFFFFF"/>
        <circle cx="6.2" cy="7.5" r="1.5" fill="#FFFFFF"/>
        <circle cx="17.8" cy="7.5" r="1.5" fill="#FFFFFF"/>
        <circle cx="6.2" cy="17" r="1.5" fill="#FFFFFF"/>
        <circle cx="12" cy="19.5" r="1.5" fill="#FFFFFF"/>
        <circle cx="17.8" cy="17" r="1.5" fill="#FFFFFF"/>
      </svg>`;
  }
}

function pruneOldHistory(days, chatList = [], runState = null) {
  let wasPruned = false;
  let prunedChat = [...chatList];
  let prunedRunState = runState;

  if (days === 0) {
    if (prunedChat.length > 0 || prunedRunState !== null) wasPruned = true;
    return { prunedChat: [], prunedRunState: null, wasPruned };
  }

  if (days > 0) {
    const cutoff = Date.now() - (days * 24 * 60 * 60 * 1000);
    const beforeCount = prunedChat.length;
    prunedChat = prunedChat.filter(msg => !msg.timestamp || msg.timestamp >= cutoff);
    if (prunedChat.length !== beforeCount) wasPruned = true;

    if (prunedRunState && (prunedRunState.finishedAt || prunedRunState.startedAt)) {
      const runTime = prunedRunState.finishedAt || prunedRunState.startedAt;
      if (runTime < cutoff) {
        prunedRunState = null;
        wasPruned = true;
      }
    }
  }

  return { prunedChat, prunedRunState, wasPruned };
}

let testResults = {};
let keyFetchedModels = {};
let addFormFetchedModels = [];
let selectedAddProvider = 'openai';
let resumes = [];
let defaultResumeId = null;
let selectedDocCategory = 'all';
let workflowRunHistory = null;
let chatHistoryList = [];

function getDocumentCategory(filename = '', mimeType = '') {
  const ext = (filename.split('.').pop() || '').toLowerCase();
  if (['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'bmp', 'ico'].includes(ext) || (mimeType && mimeType.startsWith('image/'))) {
    return 'photo';
  }
  if (ext === 'pdf' || (mimeType && mimeType.includes('pdf'))) {
    return 'pdf';
  }
  if (['doc', 'docx', 'txt', 'rtf', 'odt', 'csv', 'xls', 'xlsx'].includes(ext) || (mimeType && mimeType.startsWith('text/'))) {
    return 'document';
  }
  if (['mp4', 'mov', 'webm', 'mkv', 'avi', 'flv', 'wmv'].includes(ext) || (mimeType && mimeType.startsWith('video/'))) {
    return 'videos';
  }
  if (['zip', 'rar', '7z', 'tar', 'gz', 'bz2'].includes(ext) || (mimeType && (mimeType.includes('zip') || mimeType.includes('compressed')))) {
    return 'zip';
  }
  return 'document';
}

function getCategoryBadge(category) {
  switch (category) {
    case 'pdf': return '<span class="doc-badge badge-pdf">📕 PDF</span>';
    case 'photo': return '<span class="doc-badge badge-photo">🖼️ Photo</span>';
    case 'videos': return '<span class="doc-badge badge-video">🎬 Video</span>';
    case 'zip': return '<span class="doc-badge badge-zip">🗜️ Zip</span>';
    case 'document':
    default: return '<span class="doc-badge badge-doc">📝 Document</span>';
  }
}
let customAnswers = [
  { id: 'qa_1', question: 'Are you willing to relocate?', answer: 'Yes, absolutely.', matchType: 'contains' },
  { id: 'qa_2', question: 'Notice Period', answer: 'Immediate (0 days)', matchType: 'contains' },
  { id: 'qa_3', question: 'Years of Python / ML experience', answer: '2+ years', matchType: 'contains' },
];
let fileUploadMode = 'workflow_only';

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
let aiDecisionMode = 'ask_human';
let allowMultiTabControl = true;
let allowSettingsAccess = true;

function syncTabFromHash() {
  const hash = (window.location.hash || '').replace('#', '').toLowerCase();
  const validTabs = ['workflows', 'profile', 'apikeys', 'customanswers', 'documents', 'resumes', 'history', 'settings'];
  if (validTabs.includes(hash)) {
    if (hash === 'resumes') currentTab = 'documents';
    else currentTab = hash;
  } else if (hash === 'answers') {
    currentTab = 'customanswers';
  } else if (hash === 'batch') {
    currentTab = 'workflows';
  } else if (hash === 'prompts') {
    currentTab = 'settings';
  } else if (hash === 'userdetails') {
    currentTab = 'profile';
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

function getNextDefaultWorkflowName(existingWorkflows = []) {
  const wfs = Array.isArray(existingWorkflows) ? existingWorkflows : [];
  let maxNum = 0;
  const regex = /^Workflow\s*(\d+)$/i;
  for (const wf of wfs) {
    const name = (wf?.name || '').trim();
    const match = name.match(regex);
    if (match) {
      const num = parseInt(match[1], 10);
      if (!isNaN(num) && num > maxNum) {
        maxNum = num;
      }
    }
  }
  let nextNum = maxNum > 0 ? maxNum + 1 : 1;
  while (wfs.some(w => (w?.name || '').trim().toLowerCase() === `workflow ${nextNum}`.toLowerCase())) {
    nextNum++;
  }
  return `Workflow ${nextNum}`;
}

// Cross-tab / background real-time sync
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes[STORAGE_KEYS.WORKFLOWS]) {
    const list = changes[STORAGE_KEYS.WORKFLOWS].newValue || [];
    list.sort((a, b) => {
      const timeA = a.updatedAt || a.createdAt || 0;
      const timeB = b.updatedAt || b.createdAt || 0;
      if (timeA && timeB) return timeB - timeA;
      return 0;
    });
    workflows = list;
    if (selectedWfIndex >= workflows.length) selectedWfIndex = 0;
    renderAppHub();
  }
});

async function loadAllData() {
  try {
    const data = await chrome.storage.local.get([
      STORAGE_KEYS.BYOK_CONFIG,
      STORAGE_KEYS.API_KEYS,
      STORAGE_KEYS.USER_PROFILE,
      STORAGE_KEYS.RESUMES,
      STORAGE_KEYS.DEFAULT_RESUME,
      STORAGE_KEYS.CUSTOM_ANSWERS,
      STORAGE_KEYS.WORKFLOWS,
      STORAGE_KEYS.SYSTEM_PROMPT,
      STORAGE_KEYS.AI_DECISION_MODE,
      STORAGE_KEYS.ALLOW_MULTI_TAB,
      STORAGE_KEYS.ALLOW_SETTINGS_ACCESS,
      STORAGE_KEYS.FILE_UPLOAD_MODE,
    ]);

    if (data[STORAGE_KEYS.USER_PROFILE]) profile = { ...DEFAULT_PROFILE, ...data[STORAGE_KEYS.USER_PROFILE] };
    if (data[STORAGE_KEYS.BYOK_CONFIG]) byokConfig = { ...byokConfig, ...data[STORAGE_KEYS.BYOK_CONFIG] };

    // Sync apiKeys from either apiKeys or byok_config.apiKeys
    const storedKeys = data[STORAGE_KEYS.API_KEYS] || byokConfig.apiKeys;
    if (Array.isArray(storedKeys) && storedKeys.length > 0) {
      byokConfig.apiKeys = storedKeys;
    } else {
      byokConfig.apiKeys = [];
      if (byokConfig.omniroute?.apiKey || byokConfig.omniroute?.baseUrl) {
        byokConfig.apiKeys.push({
          id: 'omniroute_init',
          provider: 'omniroute',
          key: byokConfig.omniroute.apiKey || '',
          label: 'Local OmniRoute Server',
          baseUrl: byokConfig.omniroute.baseUrl || 'http://127.0.0.1:20128/v1',
          model: byokConfig.omniroute.model || 'antigravity/gemini-3.6-flash-high',
          enabled: true,
        });
      }
      if (byokConfig.gemini?.apiKey) {
        byokConfig.apiKeys.push({
          id: 'gemini_init',
          provider: 'gemini',
          key: byokConfig.gemini.apiKey,
          label: 'Google Gemini Studio',
          model: byokConfig.gemini.model || 'gemini-3.8-flash-high',
          enabled: true,
        });
      }
    }

    if (!byokConfig.activeKeyId && byokConfig.apiKeys.length > 0) {
      byokConfig.activeKeyId = byokConfig.apiKeys[0].id;
    }

    if (Array.isArray(data[STORAGE_KEYS.RESUMES]) && data[STORAGE_KEYS.RESUMES].length > 0) {
      resumes = data[STORAGE_KEYS.RESUMES];
    } else {
      resumes = [{ id: 'res_1', name: 'Ragesh_Resume.pdf', label: 'Default resume', size: 65536, isDefault: true }];
    }
    defaultResumeId = data[STORAGE_KEYS.DEFAULT_RESUME] || resumes[0]?.id;
    if (Array.isArray(data[STORAGE_KEYS.CUSTOM_ANSWERS])) customAnswers = data[STORAGE_KEYS.CUSTOM_ANSWERS];
    if (Array.isArray(data[STORAGE_KEYS.WORKFLOWS]) && data[STORAGE_KEYS.WORKFLOWS].length > 0) {
      workflows = data[STORAGE_KEYS.WORKFLOWS];
      workflows.sort((a, b) => {
        const timeA = a.updatedAt || a.createdAt || 0;
        const timeB = b.updatedAt || b.createdAt || 0;
        if (timeA && timeB) return timeB - timeA;
        return 0;
      });
    }
    if (data[STORAGE_KEYS.SYSTEM_PROMPT]) systemPrompt = data[STORAGE_KEYS.SYSTEM_PROMPT];
    if (data[STORAGE_KEYS.AI_DECISION_MODE]) aiDecisionMode = data[STORAGE_KEYS.AI_DECISION_MODE];
    if (data[STORAGE_KEYS.FILE_UPLOAD_MODE]) fileUploadMode = data[STORAGE_KEYS.FILE_UPLOAD_MODE];
    if (typeof data[STORAGE_KEYS.ALLOW_MULTI_TAB] === 'boolean') allowMultiTabControl = data[STORAGE_KEYS.ALLOW_MULTI_TAB];
    if (typeof data[STORAGE_KEYS.ALLOW_SETTINGS_ACCESS] === 'boolean') allowSettingsAccess = data[STORAGE_KEYS.ALLOW_SETTINGS_ACCESS];
    if (typeof data[STORAGE_KEYS.HISTORY_RETENTION_DAYS] === 'number') {
      historyRetentionDays = data[STORAGE_KEYS.HISTORY_RETENTION_DAYS];
    } else {
      historyRetentionDays = 2; // Default 2 days retention
    }

    const histData = await chrome.storage.local.get(['workflowRunState', 'byok_chat_history']);
    workflowRunHistory = histData.workflowRunState || null;
    chatHistoryList = Array.isArray(histData.byok_chat_history) ? histData.byok_chat_history : [];

    // Auto-prune based on historyRetentionDays
    const { prunedChat, prunedRunState, wasPruned } = pruneOldHistory(historyRetentionDays, chatHistoryList, workflowRunHistory);
    chatHistoryList = prunedChat;
    workflowRunHistory = prunedRunState;
    if (wasPruned) {
      await chrome.storage.local.set({
        byok_chat_history: chatHistoryList,
        workflowRunState: workflowRunHistory,
      }).catch(() => {});
    }
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
        <button class="tab-btn ${currentTab === 'profile' ? 'active' : ''}" data-tab="profile">👤 User Details</button>
        <button class="tab-btn ${currentTab === 'apikeys' ? 'active' : ''}" data-tab="apikeys">🔑 AI & API Keys</button>
        <button class="tab-btn ${currentTab === 'customanswers' ? 'active' : ''}" data-tab="customanswers">📝 Custom Answers</button>
        <button class="tab-btn ${currentTab === 'documents' || currentTab === 'resumes' ? 'active' : ''}" data-tab="documents">📁 Documents</button>
        <button class="tab-btn ${currentTab === 'history' ? 'active' : ''}" data-tab="history">📜 History</button>
        <button class="tab-btn ${currentTab === 'settings' ? 'active' : ''}" data-tab="settings">⚙️ Settings</button>
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
    case 'customanswers': return renderCustomAnswersTab();
    case 'documents':
    case 'resumes': return renderDocumentsTab();
    case 'history': return renderHistoryTab();
    case 'settings': return renderSettingsTab();
    default: return renderWorkflowsTab();
  }
}


// ─── 1. Exact 3-Column Workflow Studio (Image 1 Layout) ──────────────────────

function renderWorkflowsTab() {
  const currentWf = workflows[selectedWfIndex] || workflows[0];
  const nextDefaultName = getNextDefaultWorkflowName(workflows);
  if (!currentWf) {
    return `
      <div class="heading-row">
        <div class="title-box">
          <h3>Workflow Studio</h3>
          <p>Record once, edit the graph, then replay locally. Explicit AI nodes handle selected live questions.</p>
        </div>
      </div>

      <!-- Create manual workflow bar -->
      <div class="manual-bar">
        <div class="manual-title">Create manual workflow</div>
        <input type="text" id="manual-wf-name" class="dark-input" style="max-width: 220px;" placeholder="e.g. ${nextDefaultName}" />
        <input type="text" id="manual-wf-url" class="dark-input" style="max-width: 320px;" placeholder="https://www.naukri.com/" />
        <button class="btn-success-green" id="btn-manual-open-record">Open and record</button>
      </div>

      <div style="margin-top: 24px; padding: 56px 24px; text-align: center; background: #0f121d; border: 1px dashed #334155; border-radius: 8px; color: #94a3b8;">
        <div style="font-size: 40px; margin-bottom: 12px;">⚡</div>
        <strong style="color: #e2e8f0; font-size: 16px; display: block; margin-bottom: 8px;">No Workflows Found</strong>
        <p style="font-size: 13px; max-width: 480px; margin: 0 auto; line-height: 1.5;">
          All workflows have been deleted. Enter a workflow name and start URL above, then click <strong>"Open and record"</strong> to record a new workflow.
        </p>
      </div>
    `;
  }

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
      <input type="text" id="manual-wf-name" class="dark-input" style="max-width: 220px;" placeholder="e.g. ${nextDefaultName}" />
      <input type="text" id="manual-wf-url" class="dark-input" style="max-width: 320px;" placeholder="https://www.naukri.com/" />
      <button class="btn-success-green" id="btn-manual-open-record">Open and record</button>
    </div>

    <!-- 3-Column Studio Workspace -->
    <div class="studio-workspace">
      <!-- 1. Left Sidebar: Workflow List -->
      <aside class="wf-sidebar">
        <input type="text" id="wf-search-input" class="wf-search-input" placeholder="Search workflows" value="${escapeHtml(wfSearchQuery)}" />
        <div class="wf-list">
          ${filteredWfs.map((w) => {
            const realIdx = workflows.indexOf(w);
            return `
              <button class="wf-item-btn ${realIdx === selectedWfIndex ? 'active' : ''}" data-widx="${realIdx}">
                <span class="wf-item-name">${escapeHtml(w.name)}</span>
                <span class="wf-item-meta">Main workflow | ${w.steps?.length || 0} nodes</span>
              </button>
            `;
          }).join('')}
        </div>
        <div class="wf-sidebar-footer">
          <button class="btn-delete-all-wf" id="btn-delete-all-wf" title="Delete all workflows">🗑️ Delete all workflows (${workflows.length})</button>
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
                  <span class="wf-badge" style="background: ${badgeColor};">${step.badge || (step.isAiLoop ? 'AI LOOP' : String(stepType).toUpperCase().substring(0, 3))}</span>
                  <div class="wf-node-title">${escapeHtml(step.name || 'Step ' + (idx + 1))}</div>
                </div>
                <div class="wf-node-sub">
                  ${stepType === 'open_url' ? 'Open page' : stepType === 'click' ? 'Click element' : stepType === 'ai_fallback' ? (step.isAiLoop ? '🔄 AI Loop' : 'Ask AI') : 'Action'} | Step ${idx + 1}<br />
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
          <button class="btn-danger-outline" id="btn-del-all-wf-canvas" style="border-color: #ef4444; color: #fca5a5; background: rgba(239, 68, 68, 0.1);">Delete all workflows</button>
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

        ${activeStep.type === 'ai_fallback' ? `
          <div style="background:rgba(20,184,166,0.1);border:1.5px solid #14b8a6;border-radius:6px;padding:10px;margin-bottom:12px;">
            <label class="toggle-row" style="margin-bottom:0;color:#2dd4bf;font-weight:700;">
              <input type="checkbox" id="insp-chk-ai-loop" ${activeStep.isAiLoop !== false ? 'checked' : ''} />
              <span>🔄 AI Loop (process elements one by one)</span>
            </label>
            <div style="font-size:11px;color:#94a3b8;margin-top:6px;">
              Elements in this loop: ${activeStep.elementCount || (Array.isArray(activeStep.targets) ? activeStep.targets.length : 1)}
            </div>
          </div>
        ` : ''}

        <textarea id="insp-target-code" class="dark-textarea" readonly>${escapeHtml(activeStep.target || activeStep.value || '')}</textarea>

        <button class="btn-primary-blue" id="btn-test-node-btn" style="width: 100%; margin-top: 4px;">Test to this node</button>
        <button class="btn-danger-outline" id="btn-del-node-btn" style="width: 100%;">Delete node</button>
      </aside>
    </div>
  `;
}

// ─── 2. User Details & AI Auto-Fill ─────────────────────────────────────────

function renderProfileTab() {
  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>👤 User Details</h3>
        <p>Candidate credentials and professional information used to auto-populate job forms.</p>
      </div>
      <button class="btn-primary-blue" id="btn-save-profile">Save User Details</button>
    </div>

    <!-- AI Auto-Extract & Auto-Fill Details Card -->
    <div class="ai-fill-card">
      <div class="ai-fill-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 20px;">✨</span>
          <div>
            <h4 style="margin: 0; font-size: 13px; font-weight: 700; color: #fff;">AI Auto-Extract & Fill User Details</h4>
            <p style="margin: 2px 0 0 0; font-size: 11px; color: #94a3b8;">Upload your resume (PDF, DOCX, TXT) or paste profile text. AI will parse your credentials and auto-fill the form fields below.</p>
          </div>
        </div>
      </div>

      <div class="ai-fill-options-grid">
        <!-- Option 1: File Upload -->
        <div class="ai-fill-source-box">
          <label class="ai-source-label">📄 Option 1: Upload Resume or Document</label>
          <div style="display: flex; align-items: center; gap: 8px; margin-top: 6px;">
            <input type="file" id="ai-extract-file" accept=".pdf,.doc,.docx,.txt,.rtf" style="display: none;" />
            <label for="ai-extract-file" class="btn-colorful-choose-small">
              <span>📎</span> Choose File
            </label>
            <span id="ai-extract-filename" class="chosen-filename-label">No file chosen</span>
          </div>
          <div style="font-size: 10px; color: #64748b; margin-top: 6px;">Supports PDF, DOC, DOCX, TXT formats.</div>
        </div>

        <!-- Option 2: Paste Text -->
        <div class="ai-fill-source-box">
          <label class="ai-source-label">✍️ Option 2: Or Paste Resume / Bio Text</label>
          <textarea id="ai-extract-text" class="dark-textarea" rows="2" placeholder="Paste resume text, skills, experience, or LinkedIn bio here..." style="font-size: 11px; min-height: 48px;"></textarea>
        </div>
      </div>

      <div class="ai-fill-footer">
        <div id="ai-extract-status" class="ai-status-indicator" style="display: none;"></div>
        <button class="btn-colorful-extract" id="btn-ai-extract-profile">
          <span>🤖</span> Extract & Fill All Details with AI
        </button>
      </div>
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
  const keys = Array.isArray(byokConfig.apiKeys) ? byokConfig.apiKeys : [];
  const activeCount = keys.filter(k => k.enabled !== false).length;

  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>🔑 AI & API Keys</h3>
        <p>Configure OmniRoute, OpenAI, Google Gemini, and other providers in compact short rectangle boxes.</p>
      </div>
      <button class="btn-primary-blue" id="btn-save-all-keys">💾 Save All Keys</button>
    </div>

    <!-- Provider Dropdown Bar: Select provider & Add -->
    <div class="provider-dropdown-bar">
      <div class="provider-dropdown-left">
        <label for="sel-add-provider" class="provider-bar-label">Provider:</label>
        <div class="provider-select-wrapper">
          <span id="selected-provider-logo" class="provider-bar-icon">
            ${getProviderLogoSvg(selectedAddProvider, 22)}
          </span>
          <select id="sel-add-provider" class="dark-select provider-bar-select">
            ${Object.entries(PROVIDER_METADATA).map(([id, meta]) => `
              <option value="${id}" ${selectedAddProvider === id ? 'selected' : ''}>${escapeHtml(meta.name)}</option>
            `).join('')}
          </select>
        </div>
      </div>
      <button type="button" class="btn-primary-blue" id="btn-quick-add-provider">+ Add Provider</button>
    </div>

    <!-- Status Banner -->
    <div class="status-banner" style="margin-bottom: 14px; background: ${activeCount > 0 ? 'rgba(34, 197, 94, 0.08)' : 'rgba(239, 68, 68, 0.08)'}; border-color: ${activeCount > 0 ? 'rgba(34, 197, 94, 0.25)' : 'rgba(239, 68, 68, 0.25)'}; color: ${activeCount > 0 ? '#4ade80' : '#f87171'};">
      <div>
        <strong>${activeCount > 0 ? `✅ ${activeCount} Provider(s) Configured` : '⚠️ No Providers Configured'}</strong>
        <span style="font-size: 11px; margin-left: 8px; color: var(--text-muted);">${activeCount > 0 ? 'Workflows and auto-fill will use your active providers.' : 'Choose a provider from the dropdown above to add keys.'}</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted);">
        Primary: <strong style="color: #38bdf8;">${(keys.find(k => k.id === byokConfig.activeKeyId)?.label || byokConfig.activeProvider || 'None')}</strong>
      </div>
    </div>

    <!-- Configured Providers: Compact Short Rectangle Boxes -->
    <div class="provider-compact-list">
      ${keys.length === 0 ? `
        <div style="padding: 24px; text-align: center; color: var(--text-muted); background: #11131c; border: 1px dashed var(--border-color); border-radius: 8px; font-size: 13px;">
          No API keys configured yet. Select a provider from the dropdown above to add one!
        </div>
      ` : keys.map(k => {
        const meta = PROVIDER_METADATA[k.provider] || { name: k.provider, icon: '🔑', tag: k.provider };
        const currentModelId = k.model || meta.defaultModel || 'default';
        const fetched = keyFetchedModels[k.id];
        const presets = PRESET_MODELS[k.provider] || [{ id: currentModelId, name: currentModelId }];
        const rawList = Array.isArray(fetched) && fetched.length > 0 ? fetched : presets;
        
        const modelsList = rawList.map(m => ({ id: m.id, name: m.name || m.id }));
        if (!modelsList.some(m => m.id === currentModelId)) {
          modelsList.unshift({ id: currentModelId, name: currentModelId });
        }

        const testRes = testResults[k.id];
        const isPrimary = byokConfig.activeKeyId === k.id;
        const currentBaseUrl = k.baseUrl !== undefined ? k.baseUrl : (meta.defaultBaseUrl || '');

        return `
          <div class="provider-box-compact ${k.enabled !== false ? 'active-key' : 'disabled-key'}" id="card-key-${k.id}">
            <!-- Header Row: Logo, Title, Status, Quick Actions -->
            <div class="provider-box-header">
              <div class="provider-box-title">
                <div class="provider-logo-compact">
                  ${getProviderLogoSvg(k.provider, 22)}
                </div>
                <strong class="provider-name-text">${escapeHtml(k.label || meta.name)}</strong>
                ${isPrimary 
                  ? '<span class="status-pill status-pill-primary">★ PRIMARY</span>' 
                  : (k.enabled !== false 
                      ? '<span class="status-pill status-pill-active">ACTIVE</span>' 
                      : '<span class="status-pill status-pill-disabled">DISABLED</span>')}
              </div>
              <div class="provider-box-actions">
                ${!isPrimary && k.enabled !== false ? `<button type="button" class="btn-secondary-gray btn-set-primary-key" data-id="${k.id}" style="padding: 4px 10px; font-size: 11px;">★ Primary</button>` : ''}
                <button type="button" class="btn-secondary-gray btn-test-key" data-id="${k.id}" style="padding: 4px 10px; font-size: 11px;">⚡ Test</button>
                <button type="button" class="btn-secondary-gray btn-toggle-key" data-id="${k.id}" style="padding: 4px 10px; font-size: 11px;">${k.enabled !== false ? 'Disable' : 'Enable'}</button>
                <button type="button" class="btn-danger-outline btn-del-key" data-id="${k.id}" style="padding: 4px 8px; font-size: 11px;" title="Delete this provider">🗑️</button>
              </div>
            </div>

            <!-- Compact 3-Column Small Rectangle Row: Base URL | API Key | Model -->
            <div class="provider-box-fields ${k.provider === 'cloudflare' ? 'has-account-id' : ''}">
              <div class="compact-field">
                <label class="compact-label">Base URL</label>
                <input type="text" class="dark-input key-field-baseurl" data-id="${k.id}" value="${escapeHtml(currentBaseUrl)}" placeholder="${escapeHtml(meta.defaultBaseUrl || 'Base URL')}" />
              </div>

              <div class="compact-field">
                <label class="compact-label">API Key / Token</label>
                <div class="compact-input-eye">
                  <input type="password" class="dark-input key-field-key" id="input-key-${k.id}" data-id="${k.id}" value="${escapeHtml(k.key || '')}" placeholder="${escapeHtml(meta.placeholder || 'Enter API Key')}" />
                  <button type="button" class="btn-toggle-eye" data-id="${k.id}" title="Show / Hide Key">👁️</button>
                </div>
              </div>

              <div class="compact-field">
                <label class="compact-label">Selected Model</label>
                <div class="compact-model-wrap">
                  <select class="dark-select key-model-select" data-id="${k.id}">
                    ${modelsList.map(m => `
                      <option value="${m.id}" ${m.id === currentModelId ? 'selected' : ''}>${escapeHtml(m.name || m.id)}</option>
                    `).join('')}
                  </select>
                  <button type="button" class="btn-secondary-gray btn-fetch-models" data-id="${k.id}" title="Discover models">🔄</button>
                </div>
              </div>

              ${k.provider === 'cloudflare' ? `
                <div class="compact-field">
                  <label class="compact-label">Account ID</label>
                  <input type="text" class="dark-input key-field-accountid" data-id="${k.id}" value="${escapeHtml(k.accountId || '')}" placeholder="Cloudflare Account ID" />
                </div>
              ` : ''}
            </div>

            <!-- Inline Test Result (if test ran) -->
            ${testRes ? `
              <div class="test-result-inline ${testRes.ok ? 'success' : 'error'}">
                <span>${testRes.ok ? '✅' : '❌'}</span>
                <span>${escapeHtml(testRes.ok ? testRes.message : (testRes.error || 'Test failed'))}</span>
              </div>
            ` : ''}
          </div>
        `;
      }).join('')}
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
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
              <strong style="color: #fff; font-size: 12px;">${escapeHtml(item.question)}</strong>
              ${item.autoLearned ? '<span style="font-size: 10px; font-weight: 600; color: #c084fc; background: rgba(192, 132, 252, 0.12); border: 1px solid rgba(192, 132, 252, 0.3); padding: 1px 6px; border-radius: 4px;">🤖 Auto-Learned</span>' : ''}
            </div>
            <div style="font-size: 11px; color: #38bdf8; margin-top: 3px;">➔ ${escapeHtml(item.answer)}</div>
          </div>
          <button class="btn-danger-outline btn-del-qa" data-idx="${idx}">Delete</button>
        </div>
      `).join('')}
    </div>
  `;
}

// ─── 6. Resumes Management ──────────────────────────────────────────────────

// ─── 6. Documents & Media Management ────────────────────────────────────────

function renderDocumentsTab() {
  const catCount = (cat) => resumes.filter(r => (r.category || getDocumentCategory(r.name, r.type)) === cat).length;
  
  const filteredDocs = resumes.filter(r => {
    if (selectedDocCategory === 'all') return true;
    const cat = r.category || getDocumentCategory(r.name, r.type);
    return cat === selectedDocCategory;
  });

  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>📁 Documents & Media</h3>
        <p>Resumes, portfolios, photos, and media archives stored for silent background form injection.</p>
      </div>
    </div>

    <!-- Category Filter Bar (All, Photo, Document, PDF, Videos, Zip) -->
    <div class="doc-filter-bar">
      <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Category:</span>
      <div class="doc-filter-pills">
        <button class="doc-filter-pill ${selectedDocCategory === 'all' ? 'active' : ''}" data-cat="all">All (${resumes.length})</button>
        <button class="doc-filter-pill ${selectedDocCategory === 'photo' ? 'active' : ''}" data-cat="photo">🖼️ Photo (${catCount('photo')})</button>
        <button class="doc-filter-pill ${selectedDocCategory === 'document' ? 'active' : ''}" data-cat="document">📝 Document (${catCount('document')})</button>
        <button class="doc-filter-pill ${selectedDocCategory === 'pdf' ? 'active' : ''}" data-cat="pdf">📕 PDF (${catCount('pdf')})</button>
        <button class="doc-filter-pill ${selectedDocCategory === 'videos' ? 'active' : ''}" data-cat="videos">🎬 Videos (${catCount('videos')})</button>
        <button class="doc-filter-pill ${selectedDocCategory === 'zip' ? 'active' : ''}" data-cat="zip">🗜️ Zip (${catCount('zip')})</button>
      </div>
    </div>

    <!-- Small Colorful Choose File Upload Box -->
    <div style="background: #11131c; border: 1px dashed var(--border-color); border-radius: 6px; padding: 14px; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;">
      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 24px;">📁</span>
        <div>
          <strong style="font-size: 13px; color: #fff;">Upload Document or File</strong>
          <p style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Stored locally for 1-click & silent background injection.</p>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
        <input type="text" id="resume-label" class="dark-input" placeholder="File label" style="width: 140px;" />
        <input type="file" id="resume-file-input" accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg,.webp,.gif,.svg,.mp4,.mov,.webm,.zip,.rar,.7z" style="display: none;" />
        <label for="resume-file-input" class="btn-colorful-choose">
          <span>📂</span> Choose File
        </label>
        <span id="chosen-doc-name" class="chosen-filename-label">No file chosen</span>
        <button class="btn-primary-blue" id="btn-upload-file">Attach & Save</button>
      </div>
    </div>

    <!-- Document Deck -->
    <div class="resume-deck" style="margin-top: 14px;">
      ${filteredDocs.length === 0 ? `
        <div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 12px; background: #11131c; border-radius: 6px;">
          No documents found under the "${selectedDocCategory}" category. Click "Choose File" above to upload one.
        </div>
      ` : filteredDocs.map(r => {
        const cat = r.category || getDocumentCategory(r.name, r.type);
        const badgeHtml = getCategoryBadge(cat);
        return `
          <div class="resume-item-card">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div>
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                  <strong style="font-size: 13px; color: #fff;">${escapeHtml(r.label || r.name)}</strong>
                  ${badgeHtml}
                  ${r.id === defaultResumeId || r.isDefault ? '<span style="color: #22c55e; font-size: 10px; font-weight: 700;">[DEFAULT]</span>' : ''}
                </div>
                <div style="font-size: 11px; color: var(--text-dim); margin-top: 3px;">
                  ${escapeHtml(r.name)} • ${(r.size ? (r.size / 1024).toFixed(1) + ' KB' : 'File')}
                </div>
              </div>
            </div>
            <div style="display: flex; gap: 8px;">
              ${r.id !== defaultResumeId ? `<button class="btn-secondary-gray btn-set-default" data-id="${r.id}">Set as Default</button>` : ''}
              <button class="btn-danger-outline btn-del-res" data-id="${r.id}">Delete</button>
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

// ─── 7. Execution History & Logs ─────────────────────────────────────────────

function renderHistoryTab() {
  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>📜 Execution History & Logs</h3>
        <p>Review autonomous browser executions, workflow runs, and agent decision records.</p>
      </div>
    </div>

    <!-- 🛡️ Top History Retention & Auto-Pruning Policy Banner -->
    <div class="history-retention-card">
      <div class="retention-info-col">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">
          <span style="font-size: 20px;">🛡️</span>
          <h4 style="color: #fff; font-size: 14px; margin: 0; font-weight: 700;">History Retention & Auto-Pruning Policy</h4>
          <span class="status-pill ${historyRetentionDays === 0 ? 'status-pill-disabled' : 'status-pill-active'}">
            ${historyRetentionDays === 0 ? '🚫 History Saving Disabled' : (historyRetentionDays === -1 ? '♾️ Keep Forever' : `⚡ ${historyRetentionDays} Days Active`)}
          </span>
        </div>
        <p style="font-size: 12px; color: #cbd5e1; line-height: 1.5; margin: 0;">
          This automatic retention policy governs both <strong style="color: #38bdf8;">AI Question & Answers</strong> (Chat dialogs and learned auto-fill responses) and <strong style="color: #a855f7;">Workflow Execution History & Logs</strong> (Step progression, automated actions, and run state logs). Records older than your selected retention window are automatically pruned to keep your browser fast, private, and lightweight.
        </p>
      </div>
      <div class="retention-controls-col">
        <div style="display: flex; align-items: center; gap: 8px;">
          <label for="select-history-retention" style="font-size: 11px; font-weight: 700; color: #94a3b8; white-space: nowrap; text-transform: uppercase;">Save History For:</label>
          <select id="select-history-retention" class="dark-select" style="min-width: 205px; padding: 7px 10px; font-size: 12px;">
            <option value="0" ${historyRetentionDays === 0 ? 'selected' : ''}>🚫 Do Not Save History (Disabled)</option>
            <option value="1" ${historyRetentionDays === 1 ? 'selected' : ''}>⏱️ 1 Day Retention</option>
            <option value="2" ${historyRetentionDays === 2 ? 'selected' : ''}>⚡ 2 Days Retention (Default)</option>
            <option value="3" ${historyRetentionDays === 3 ? 'selected' : ''}>📅 3 Days Retention</option>
            <option value="7" ${historyRetentionDays === 7 ? 'selected' : ''}>🗓️ 7 Days (1 Week)</option>
            <option value="14" ${historyRetentionDays === 14 ? 'selected' : ''}>📆 14 Days (2 Weeks)</option>
            <option value="30" ${historyRetentionDays === 30 ? 'selected' : ''}>📦 30 Days (1 Month)</option>
            <option value="-1" ${historyRetentionDays === -1 ? 'selected' : ''}>♾️ Keep All (Forever)</option>
          </select>
        </div>
        <button class="btn-secondary-gray" id="btn-clear-history" style="padding: 6px 14px; font-size: 11px;">🗑️ Clear All History Now</button>
      </div>
    </div>

    <div style="display: flex; flex-direction: column; gap: 14px;">
      <!-- Workflow Execution State -->
      <div style="background: #11131c; border: 1px solid var(--border-color); border-radius: 6px; padding: 14px;">
        <h4 style="font-size: 13px; color: #fff; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
          <span>⚡</span> Recent Workflow Execution State
        </h4>
        ${!workflowRunHistory || !workflowRunHistory.workflowName ? `
          <p style="font-size: 11px; color: var(--text-muted);">No active or recent workflow execution records found.</p>
        ` : `
          <div style="background: #181c2b; border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <strong style="color: #fff; font-size: 13px;">${escapeHtml(workflowRunHistory.workflowName)}</strong>
              <span class="status-pill ${workflowRunHistory.status === 'completed' ? 'status-pill-active' : 'status-pill-disabled'}">${escapeHtml(workflowRunHistory.status || 'Active')}</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px;">
              Step Progress: ${workflowRunHistory.currentStepIndex || 0} / ${workflowRunHistory.steps?.length || 0}
            </div>
            ${workflowRunHistory.logs && workflowRunHistory.logs.length > 0 ? `
              <div style="font-family: var(--font-mono); font-size: 11px; color: #38bdf8; background: #0c0e14; padding: 8px; border-radius: 4px; max-height: 120px; overflow-y: auto;">
                ${workflowRunHistory.logs.map(l => `<div>• ${escapeHtml(l)}</div>`).join('')}
              </div>
            ` : ''}
          </div>
        `}
      </div>

      <!-- Agent Activity & Decision History -->
      <div style="background: #11131c; border: 1px solid var(--border-color); border-radius: 6px; padding: 14px;">
        <h4 style="font-size: 13px; color: #fff; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
          <span>💬</span> AI Assistant Activity Records (${chatHistoryList.length})
        </h4>
        ${chatHistoryList.length === 0 ? `
          <p style="font-size: 11px; color: var(--text-muted);">No conversational history recorded yet. Open AI Chat from the extension popup to begin.</p>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 8px; max-height: 340px; overflow-y: auto;">
            ${chatHistoryList.slice(-15).reverse().map(msg => `
              <div style="background: #181c2b; border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 10px;">
                <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-bottom: 4px;">
                  <strong style="color: ${msg.role === 'user' ? '#38bdf8' : '#a855f7'}; text-transform: uppercase;">${escapeHtml(msg.role || 'agent')}</strong>
                  <span>${msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}</span>
                </div>
                <div style="font-size: 11px; color: #e2e8f0; white-space: pre-wrap; line-height: 1.4;">${escapeHtml((msg.content || '').slice(0, 300))}</div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    </div>
  `;
}

// ─── 8. System Preferences & Autonomy Tab ────────────────────────────────────

function renderSettingsTab() {
  return `
    <div class="heading-row">
      <div class="title-box">
        <h3>⚙️ System Preferences & Autonomy</h3>
        <p>Configure autonomous decision policies, document orchestration, and agent execution boundaries.</p>
      </div>
      <button class="btn-primary-blue" id="btn-save-settings-tab">Save Preferences</button>
    </div>

    <div class="form-grid-2">
      <!-- Field Resolution Policy -->
      <div class="form-group span-full" style="background: #11131c; border: 1px solid var(--border-color); border-radius: 6px; padding: 14px;">
        <label style="font-size: 13px; color: #fff; margin-bottom: 6px; font-weight: 600;">🤖 Form Field Resolution Policy</label>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <label class="toggle-row" style="background: #1b1e2b; padding: 12px; border-radius: 6px; cursor: pointer;">
            <input type="radio" name="rad-decision" value="ask_human" ${aiDecisionMode === 'ask_human' ? 'checked' : ''} />
            <div>
              <strong style="color: #fff; font-size: 12px;">👤 Supervised Human Approval</strong>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Prompts an on-screen dialog when unknown or ambiguous inputs are detected.</div>
            </div>
          </label>
          <label class="toggle-row" style="background: #1b1e2b; padding: 12px; border-radius: 6px; cursor: pointer;">
            <input type="radio" name="rad-decision" value="autonomous" ${aiDecisionMode === 'autonomous' ? 'checked' : ''} />
            <div>
              <strong style="color: #fff; font-size: 12px;">⚡ Autonomous AI Resolution</strong>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Infers accurate field values directly from User Details and attached documents.</div>
            </div>
          </label>
        </div>
      </div>

      <!-- Document Upload Routing -->
      <div class="form-group span-full" style="background: #11131c; border: 1px solid var(--border-color); border-radius: 6px; padding: 14px;">
        <label style="font-size: 13px; color: #fff; margin-bottom: 6px; font-weight: 600;">📁 Document Upload Routing</label>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <label class="toggle-row" style="background: #1b1e2b; padding: 12px; border-radius: 6px; cursor: pointer;">
            <input type="radio" name="rad-file-upload-mode" value="workflow_only" ${fileUploadMode === 'workflow_only' ? 'checked' : ''} />
            <div>
              <strong style="color: #fff; font-size: 12px;">Workflow Execution Only (Recommended)</strong>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Routes documents during active workflows; preserves native system dialogs otherwise.</div>
            </div>
          </label>
          <label class="toggle-row" style="background: #1b1e2b; padding: 12px; border-radius: 6px; cursor: pointer;">
            <input type="radio" name="rad-file-upload-mode" value="all_web" ${fileUploadMode === 'all_web' ? 'checked' : ''} />
            <div>
              <strong style="color: #fff; font-size: 12px;">Global Portal Interception</strong>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Enables automatic document selection across all external career and job portals.</div>
            </div>
          </label>
        </div>
      </div>

      <!-- Multi-Tab Control -->
      <div class="form-group" style="background: #11131c; border: 1px solid var(--border-color); border-radius: 6px; padding: 12px;">
        <label class="toggle-row">
          <input type="checkbox" id="chk-multi-tab" ${allowMultiTabControl ? 'checked' : ''} />
          <div>
            <strong style="color: #fff; font-size: 12px;">🌐 Multi-Tab Browser Orchestration</strong>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Authorizes the agent to open, navigate, and manage multi-page application flows.</div>
          </div>
        </label>
      </div>

      <!-- Direct Knowledge Sync -->
      <div class="form-group" style="background: #11131c; border: 1px solid var(--border-color); border-radius: 6px; padding: 12px;">
        <label class="toggle-row">
          <input type="checkbox" id="chk-settings-access" ${allowSettingsAccess ? 'checked' : ''} />
          <div>
            <strong style="color: #fff; font-size: 12px;">🔧 Direct Knowledge & Profile Synchronization</strong>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Allows the automation engine to dynamically retrieve profile attributes and learned Q&A rules.</div>
          </div>
        </label>
      </div>

      <!-- Danger Zone -->
      <div class="form-group span-full" style="background: #11131c; border: 1px solid #7f1d1d; border-radius: 6px; padding: 14px; margin-top: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
          <div>
            <strong style="color: #f87171; font-size: 13px;">⚠️ Danger Zone: Reset All Workflows</strong>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Permanently purges all saved workflows and execution branches from local storage.</div>
          </div>
          <button class="btn-danger-outline" id="btn-delete-all-workflows" style="background: rgba(239, 68, 68, 0.15); border-color: #ef4444; color: #fca5a5; font-weight: 600; padding: 8px 16px;">Purge All Workflows</button>
        </div>
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
    document.getElementById('insp-chk-ai-loop')?.addEventListener('change', (e) => {
      activeStep.isAiLoop = e.target.checked;
      activeStep.badge = activeStep.isAiLoop ? 'AI LOOP' : 'AI';
      persist(STORAGE_KEYS.WORKFLOWS, workflows, 'Updated AI Loop mode.');
      renderAppHub();
    });
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
      isAiLoop: true,
      elementCount: 1,
      waitMs: 800,
      color: '#14b8a6',
      badge: 'AI LOOP',
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
      if (chrome.sidePanel && typeof chrome.sidePanel.setOptions === 'function' && tabId) {
        await chrome.sidePanel.setOptions({
          tabId,
          path: mode === 'record' ? `recorder.html?tabId=${tabId}&wf=${wfId}` : `sidepanel.html?tabId=${tabId}`,
          enabled: true,
        });
      }
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
    const rawName = document.getElementById('manual-wf-name')?.value.trim();
    const name = rawName || getNextDefaultWorkflowName(workflows);
    const rawUrl = document.getElementById('manual-wf-url')?.value.trim() || 'https://www.naukri.com/';
    const targetUrl = normalizeUrl(rawUrl);

    const newWf = {
      id: 'wf_' + Date.now(),
      name,
      startUrl: targetUrl,
      resumeId: '',
      variables: { role: '', location: '' },
      createdAt: Date.now(),
      updatedAt: Date.now(),
      steps: [
        { id: 's1', type: 'open_url', name: 'Open ' + targetUrl, value: targetUrl, waitMs: 400, color: '#22c55e', badge: 'URL', target: targetUrl, disabled: false, stopAfter: false, finalSubmit: false }
      ],
    };
    workflows.unshift(newWf);
    selectedWfIndex = 0;
    selectedStepIndex = 0;
    await persist(STORAGE_KEYS.WORKFLOWS, workflows, 'Opening website with Side Panel recorder...');
    renderAppHub();

    // Open target website tab & start in-page workflow recorder with element tracking
    try {
      const newTab = await chrome.tabs.create({ url: targetUrl, active: true });
      if (newTab?.id) {
        await openSidePanelForTab(newTab.id, newWf.id, 'record');

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

  // Run main workflow (Executes steps on page, no AI chat sidebar)
  document.getElementById('btn-wf-run-main')?.addEventListener('click', async () => {
    if (!curWf) return;
    await saveWfHandler();
    try {
      showToast(`Starting workflow "${curWf.name}"...`);
      const res = await chrome.runtime.sendMessage({
        action: 'WORKFLOW_RUN',
        workflowId: curWf.id,
        workflow: curWf,
      });
      if (res?.success) {
        showToast(`Workflow "${curWf.name}" running in target tab!`);
      } else {
        showToast(`Could not start workflow: ${res?.error || 'Unknown error'}`, true);
      }
    } catch (err) {
      showToast('Run error: ' + err.message, true);
    }
  });

  // Test to this node (Executes steps up to selected node, no AI chat sidebar)
  document.getElementById('btn-test-node-btn')?.addEventListener('click', async () => {
    if (!curWf) return;
    await saveWfHandler();
    try {
      showToast(`Testing workflow up to Step ${selectedStepIndex + 1}...`);
      const res = await chrome.runtime.sendMessage({
        action: 'WORKFLOW_RUN',
        workflowId: curWf.id,
        workflow: curWf,
        stopAfterIndex: selectedStepIndex,
      });
      if (res?.success) {
        showToast(`Testing up to Step ${selectedStepIndex + 1} running in target tab!`);
      } else {
        showToast(`Could not start test: ${res?.error || 'Unknown error'}`, true);
      }
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
      updatedAt: Date.now(),
    };
    workflows.unshift(newBranch);
    selectedWfIndex = 0;
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
      updatedAt: Date.now(),
    };
    workflows.unshift(newBranch);
    selectedWfIndex = 0;
    selectedStepIndex = 0;
    await persist(STORAGE_KEYS.WORKFLOWS, workflows, `Created branch without disabled nodes!`);
    renderAppHub();
  });

  // Status button
  document.getElementById('btn-wf-status')?.addEventListener('click', async () => {
    try {
      const res = await chrome.runtime.sendMessage({ action: 'WORKFLOW_STATUS' });
      if (res?.state && res.state.status) {
        showToast(`Status: ${res.state.status.toUpperCase()} (${res.state.stepIndex + 1}/${res.state.stepCount} nodes)`);
      } else {
        showToast(`Workflow "${curWf?.name || 'Main'}" has ${curWf?.steps?.length || 0} nodes.`);
      }
    } catch {
      showToast(`Workflow "${curWf?.name || 'Main'}" has ${curWf?.steps?.length || 0} nodes.`);
    }
  });

  // Delete Current Workflow (Allowed even if only 1 workflow remains)
  document.getElementById('btn-del-wf-main')?.addEventListener('click', async () => {
    if (!curWf) return;
    if (confirm(`Delete "${curWf?.name}"?`)) {
      workflows.splice(selectedWfIndex, 1);
      selectedWfIndex = Math.max(0, Math.min(selectedWfIndex, workflows.length - 1));
      selectedStepIndex = 0;
      await persist(STORAGE_KEYS.WORKFLOWS, workflows, 'Workflow deleted.');
      renderAppHub();
    }
  });

  // Delete All Workflows Handler (Sidebar button, Bottom bar button, and Settings tab)
  const handleDeleteAllWorkflows = async () => {
    if (!workflows || workflows.length === 0) {
      showToast('No workflows to delete.', true);
      return;
    }
    const count = workflows.length;
    if (confirm(`Are you sure you want to delete ALL ${count} recorded workflow(s)?\n\nThis will permanently remove all workflows and branches you created. This action cannot be undone.`)) {
      workflows = [];
      selectedWfIndex = 0;
      selectedStepIndex = 0;
      await persist(STORAGE_KEYS.WORKFLOWS, [], `All ${count} workflow(s) deleted.`);
      chrome.runtime.sendMessage({ action: 'WORKFLOW_DELETE_ALL' }).catch(() => {});
      renderAppHub();
    }
  };

  document.getElementById('btn-delete-all-wf')?.addEventListener('click', handleDeleteAllWorkflows);
  document.getElementById('btn-del-all-wf-canvas')?.addEventListener('click', handleDeleteAllWorkflows);
  document.getElementById('btn-delete-all-workflows')?.addEventListener('click', handleDeleteAllWorkflows);

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
    await persist(STORAGE_KEYS.USER_PROFILE, profile, 'User details updated successfully!');
  });

  // AI Extract File Input Change: show selected filename
  document.getElementById('ai-extract-file')?.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    const nameEl = document.getElementById('ai-extract-filename');
    if (nameEl && file) {
      nameEl.textContent = file.name;
    }
  });

  // AI Auto-Extract & Fill Button Action
  document.getElementById('btn-ai-extract-profile')?.addEventListener('click', async () => {
    const fileInput = document.getElementById('ai-extract-file');
    const textArea = document.getElementById('ai-extract-text');
    const statusEl = document.getElementById('ai-extract-status');
    const file = fileInput?.files?.[0];
    const pastedText = (textArea?.value || '').trim();

    if (!file && !pastedText) {
      showToast('Please choose a resume/PDF file or paste profile text.', true);
      return;
    }

    if (statusEl) {
      statusEl.style.display = 'inline-block';
      statusEl.textContent = '🤖 Analyzing credentials with AI...';
    }

    try {
      let fileText = '';
      if (file) {
        if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
          fileText = await new Promise((resolve) => {
            const r = new FileReader();
            r.onload = () => resolve(r.result || '');
            r.readAsText(file);
          });
        } else {
          fileText = await new Promise((resolve) => {
            const r = new FileReader();
            r.onload = () => {
              const uint8 = new Uint8Array(r.result);
              let text = '';
              let curWord = '';
              for (let i = 0; i < uint8.length && text.length < 30000; i++) {
                const c = uint8[i];
                if ((c >= 32 && c <= 126) || c === 10 || c === 13 || c === 9) {
                  curWord += String.fromCharCode(c);
                } else {
                  if (curWord.length >= 2) text += curWord + ' ';
                  curWord = '';
                }
              }
              if (curWord.length >= 2) text += curWord;
              const cleaned = text
                .replace(/obj[\s\S]*?endobj/g, ' ')
                .replace(/<<[\s\S]*?>>/g, ' ')
                .replace(/stream[\s\S]*?endstream/g, ' ')
                .replace(/\s+/g, ' ')
                .trim();
              resolve(cleaned.length > 100 ? cleaned : text.slice(0, 15000));
            };
            r.readAsArrayBuffer(file);
          });
        }
      }

      const combinedText = (pastedText ? pastedText + '\n\n' : '') + fileText;
      if (!combinedText.trim()) {
        showToast('Could not read text from document. Please paste resume text directly.', true);
        if (statusEl) statusEl.style.display = 'none';
        return;
      }

      const res = await chrome.runtime.sendMessage({
        action: 'AI_EXTRACT_USER_DETAILS',
        text: combinedText,
        fileName: file?.name || 'Resume Document',
      });

      if (res?.success && res.profile) {
        profile = { ...DEFAULT_PROFILE, ...res.profile };
        const setVal = (id, val) => {
          const el = document.getElementById(id);
          if (el && val !== undefined && val !== null) el.value = val;
        };
        setVal('prof-fullName', profile.fullName);
        setVal('prof-email', profile.email);
        setVal('prof-phone', profile.phone);
        setVal('prof-altPhone', profile.altPhone);
        setVal('prof-address', profile.address);
        setVal('prof-city', profile.city);
        setVal('prof-state', profile.state);
        setVal('prof-degree', profile.degree);
        setVal('prof-gradYear', profile.graduationYear);
        setVal('prof-university', profile.university);
        setVal('prof-skills', profile.skills);
        setVal('prof-linkedin', profile.linkedin);
        setVal('prof-github', profile.github);
        setVal('prof-expectedSalary', profile.expectedSalary);
        setVal('prof-noticePeriod', profile.noticePeriod);

        await persist(STORAGE_KEYS.USER_PROFILE, profile, '✨ User Details extracted & auto-filled by AI!');
        if (statusEl) {
          statusEl.textContent = '✅ Extraction complete!';
          setTimeout(() => { if (statusEl) statusEl.style.display = 'none'; }, 2400);
        }
      } else {
        showToast(`Extraction failed: ${res?.error || 'AI could not parse profile'}`, true);
        if (statusEl) statusEl.style.display = 'none';
      }
    } catch (err) {
      showToast(`Extraction error: ${err.message}`, true);
      if (statusEl) statusEl.style.display = 'none';
    }
  });

  // ── Multi-Provider & API Key Studio Events ──

  // Switch Provider in Dropdown
  document.getElementById('sel-add-provider')?.addEventListener('change', (e) => {
    selectedAddProvider = e.target.value;
    const logoEl = document.getElementById('selected-provider-logo');
    if (logoEl) logoEl.innerHTML = getProviderLogoSvg(selectedAddProvider, 22);
  });

  // Quick Add Provider Button
  document.getElementById('btn-quick-add-provider')?.addEventListener('click', async () => {
    const p = selectedAddProvider || 'omniroute';
    const meta = PROVIDER_METADATA[p] || { name: p, defaultModel: '', defaultBaseUrl: '' };
    const newKeyObj = {
      id: `${p}_${Date.now()}`,
      provider: p,
      label: meta.name,
      baseUrl: meta.defaultBaseUrl || '',
      key: '',
      model: meta.defaultModel || '',
      accountId: '',
      enabled: true,
      usedToday: 0,
      dailyLimit: 1000,
      createdAt: Date.now(),
    };

    if (!Array.isArray(byokConfig.apiKeys)) byokConfig.apiKeys = [];
    byokConfig.apiKeys.push(newKeyObj);
    if (!byokConfig.activeKeyId) {
      byokConfig.activeKeyId = newKeyObj.id;
      byokConfig.activeProvider = p;
    }

    await persist(STORAGE_KEYS.BYOK_CONFIG, byokConfig, `Added ${meta.name}!`);
    await persist(STORAGE_KEYS.API_KEYS, byokConfig.apiKeys);
    renderAppHub();
  });

  // Save All Keys
  document.getElementById('btn-save-all-keys')?.addEventListener('click', async () => {
    document.querySelectorAll('.provider-box-compact').forEach(card => {
      const id = card.id.replace('card-key-', '');
      const keyObj = (byokConfig.apiKeys || []).find(k => k.id === id);
      if (!keyObj) return;

      const urlInput = card.querySelector('.key-field-baseurl');
      const keyInput = card.querySelector('.key-field-key');
      const modelSelect = card.querySelector('.key-model-select');
      const accountInput = card.querySelector('.key-field-accountid');

      if (urlInput) keyObj.baseUrl = urlInput.value.trim();
      if (keyInput) keyObj.key = keyInput.value.trim();
      if (modelSelect) keyObj.model = modelSelect.value;
      if (accountInput) keyObj.accountId = accountInput.value.trim();

      if (keyObj.provider === 'omniroute') {
        byokConfig.omniroute = { baseUrl: keyObj.baseUrl, apiKey: keyObj.key, model: keyObj.model };
      } else if (keyObj.provider === 'gemini') {
        byokConfig.gemini = { apiKey: keyObj.key, model: keyObj.model };
      } else if (keyObj.provider === 'openai') {
        byokConfig.openai = { apiKey: keyObj.key, model: keyObj.model };
      }
    });

    await persist(STORAGE_KEYS.BYOK_CONFIG, byokConfig, '✅ All API keys saved successfully!');
    await persist(STORAGE_KEYS.API_KEYS, byokConfig.apiKeys);
    renderAppHub();
  });

  // Toggle Password Visibility in Key Input
  document.querySelectorAll('.btn-toggle-eye').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      const input = document.getElementById(`input-key-${id}`);
      if (input) {
        input.type = input.type === 'password' ? 'text' : 'password';
      }
    });
  });

  // Test Key on Individual Card
  document.querySelectorAll('.btn-test-key').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      const keyObj = (byokConfig.apiKeys || []).find(k => k.id === id);
      if (!keyObj) return;

      const card = document.getElementById(`card-key-${id}`);
      const urlInput = card?.querySelector('.key-field-baseurl');
      const keyInput = card?.querySelector('.key-field-key');
      const modelSelect = card?.querySelector('.key-model-select');
      const accountInput = card?.querySelector('.key-field-accountid');

      const currentKey = keyInput ? keyInput.value.trim() : keyObj.key;
      const currentUrl = urlInput ? urlInput.value.trim() : keyObj.baseUrl;
      const currentModel = modelSelect ? modelSelect.value : keyObj.model;
      const currentAccount = accountInput ? accountInput.value.trim() : keyObj.accountId;

      btn.textContent = '🔄 Testing...';
      btn.disabled = true;

      try {
        const res = await chrome.runtime.sendMessage({
          action: 'TEST_API_KEY',
          payload: {
            provider: keyObj.provider,
            key: currentKey,
            baseUrl: currentUrl,
            accountId: currentAccount,
            model: currentModel,
          },
        });

        testResults[id] = res;
        showToast(res.ok ? `Key Test: ${res.message}` : `Key Test Failed: ${res.error || 'Unknown error'}`, !res.ok);
      } catch (err) {
        testResults[id] = { ok: false, error: err.message };
        showToast(`Test error: ${err.message}`, true);
      } finally {
        btn.textContent = '⚡ Test';
        btn.disabled = false;
        renderAppHub();
      }
    });
  });

  // Fetch Live Models on Individual Card
  document.querySelectorAll('.btn-fetch-models').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      const keyObj = (byokConfig.apiKeys || []).find(k => k.id === id);
      if (!keyObj) return;

      const card = document.getElementById(`card-key-${id}`);
      const urlInput = card?.querySelector('.key-field-baseurl');
      const keyInput = card?.querySelector('.key-field-key');
      const accountInput = card?.querySelector('.key-field-accountid');

      const currentKey = keyInput ? keyInput.value.trim() : keyObj.key;
      const currentUrl = urlInput ? urlInput.value.trim() : keyObj.baseUrl;
      const currentAccount = accountInput ? accountInput.value.trim() : keyObj.accountId;

      btn.textContent = '⏳';
      btn.disabled = true;

      try {
        const res = await chrome.runtime.sendMessage({
          action: 'FETCH_PROVIDER_MODELS',
          payload: {
            provider: keyObj.provider,
            key: currentKey,
            baseUrl: currentUrl,
            accountId: currentAccount,
          },
        });

        if (res?.ok && Array.isArray(res.models)) {
          keyFetchedModels[id] = res.models;
          showToast(`✅ Discovered ${res.models.length} model(s) for ${keyObj.label || keyObj.provider}!`);
        } else {
          showToast(`Fetch models failed: ${res?.error || 'Unknown error'}`, true);
        }
      } catch (err) {
        showToast(`Fetch error: ${err.message}`, true);
      } finally {
        btn.textContent = '🔄';
        btn.disabled = false;
        renderAppHub();
      }
    });
  });

  // Change Model on Card
  document.querySelectorAll('.key-model-select').forEach(sel => {
    sel.addEventListener('change', async (e) => {
      const id = sel.getAttribute('data-id');
      const keyObj = (byokConfig.apiKeys || []).find(k => k.id === id);
      if (keyObj) {
        keyObj.model = e.target.value;
        await persist(STORAGE_KEYS.BYOK_CONFIG, byokConfig, `Model updated to ${keyObj.model}`);
        await persist(STORAGE_KEYS.API_KEYS, byokConfig.apiKeys);
      }
    });
  });

  // Toggle Key Enabled
  document.querySelectorAll('.btn-toggle-key').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      const keyObj = (byokConfig.apiKeys || []).find(k => k.id === id);
      if (keyObj) {
        keyObj.enabled = keyObj.enabled === false ? true : false;
        await persist(STORAGE_KEYS.BYOK_CONFIG, byokConfig, `${keyObj.label || keyObj.provider} ${keyObj.enabled ? 'Enabled' : 'Disabled'}`);
        await persist(STORAGE_KEYS.API_KEYS, byokConfig.apiKeys);
        renderAppHub();
      }
    });
  });

  // Set Key as Primary
  document.querySelectorAll('.btn-set-primary-key').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      const keyObj = (byokConfig.apiKeys || []).find(k => k.id === id);
      if (keyObj) {
        byokConfig.activeKeyId = id;
        byokConfig.activeProvider = keyObj.provider;
        await persist(STORAGE_KEYS.BYOK_CONFIG, byokConfig, `Set ${keyObj.label || keyObj.provider} as Primary active provider!`);
        await persist(STORAGE_KEYS.API_KEYS, byokConfig.apiKeys);
        renderAppHub();
      }
    });
  });

  // Delete Key
  document.querySelectorAll('.btn-del-key').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      if (!confirm('Are you sure you want to delete this API key configuration?')) return;
      byokConfig.apiKeys = (byokConfig.apiKeys || []).filter(k => k.id !== id);
      if (byokConfig.activeKeyId === id && byokConfig.apiKeys.length > 0) {
        byokConfig.activeKeyId = byokConfig.apiKeys[0].id;
        byokConfig.activeProvider = byokConfig.apiKeys[0].provider;
      }
      delete testResults[id];
      delete keyFetchedModels[id];
      await persist(STORAGE_KEYS.BYOK_CONFIG, byokConfig, 'API key deleted.');
      await persist(STORAGE_KEYS.API_KEYS, byokConfig.apiKeys);
      renderAppHub();
    });
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

  // ── Documents & Media Events ──
  // Category Filter Pills
  document.querySelectorAll('.doc-filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      selectedDocCategory = pill.getAttribute('data-cat') || 'all';
      renderAppHub();
    });
  });

  // Small Colorful File Input Change: display chosen filename & prefill label
  document.getElementById('resume-file-input')?.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    const nameLabel = document.getElementById('chosen-doc-name');
    if (nameLabel && file) {
      nameLabel.textContent = file.name;
      const labelInput = document.getElementById('resume-label');
      if (labelInput && !labelInput.value) {
        labelInput.value = file.name.replace(/\.[^/.]+$/, '');
      }
    }
  });

  // Upload Document
  document.getElementById('btn-upload-file')?.addEventListener('click', () => {
    const fileInput = document.getElementById('resume-file-input');
    const labelInput = document.getElementById('resume-label');
    const file = fileInput?.files?.[0];
    if (!file) return alert('Please choose a file to upload.');

    const cat = getDocumentCategory(file.name, file.type);
    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = reader.result.split(',')[1];
      const newRes = {
        id: 'res_' + Date.now(),
        name: file.name,
        label: labelInput?.value.trim() || file.name.replace(/\.[^/.]+$/, ''),
        size: file.size,
        data: base64,
        type: file.type || 'application/octet-stream',
        category: cat,
        isDefault: resumes.length === 0,
      };
      resumes.push(newRes);
      if (resumes.length === 1) defaultResumeId = newRes.id;
      await persist(STORAGE_KEYS.RESUMES, resumes, `Document "${newRes.label}" uploaded!`);
      await persist(STORAGE_KEYS.DEFAULT_RESUME, defaultResumeId);
      renderAppHub();
    };
    reader.readAsDataURL(file);
  });

  document.querySelectorAll('.btn-set-default').forEach(btn => {
    btn.addEventListener('click', async () => {
      defaultResumeId = btn.getAttribute('data-id');
      await persist(STORAGE_KEYS.DEFAULT_RESUME, defaultResumeId, 'Default document set!');
      renderAppHub();
    });
  });

  document.querySelectorAll('.btn-del-res').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      resumes = resumes.filter(r => r.id !== id);
      if (defaultResumeId === id && resumes.length > 0) defaultResumeId = resumes[0].id;
      await persist(STORAGE_KEYS.RESUMES, resumes, 'Document deleted.');
      await persist(STORAGE_KEYS.DEFAULT_RESUME, defaultResumeId);
      renderAppHub();
    });
  });

  // ── History Events ──
  document.getElementById('select-history-retention')?.addEventListener('change', async (e) => {
    const val = parseInt(e.target.value, 10);
    historyRetentionDays = isNaN(val) ? 2 : val;
    await persist(
      STORAGE_KEYS.HISTORY_RETENTION_DAYS,
      historyRetentionDays,
      `History retention set to ${historyRetentionDays === 0 ? 'Disabled (not saving)' : (historyRetentionDays === -1 ? 'Keep Forever' : `${historyRetentionDays} Days`)}!`
    );

    // Prune existing history immediately based on new policy
    const { prunedChat, prunedRunState, wasPruned } = pruneOldHistory(historyRetentionDays, chatHistoryList, workflowRunHistory);
    chatHistoryList = prunedChat;
    workflowRunHistory = prunedRunState;
    await chrome.storage.local.set({
      byok_chat_history: chatHistoryList,
      workflowRunState: workflowRunHistory,
    }).catch(() => {});

    renderAppHub();
  });

  document.getElementById('btn-clear-history')?.addEventListener('click', async () => {
    if (confirm('Clear all execution and agent activity history?')) {
      chatHistoryList = [];
      workflowRunHistory = null;
      await chrome.storage.local.set({ byok_chat_history: [], workflowRunState: null });
      showToast('Execution and chat history cleared!');
      renderAppHub();
    }
  });

  // ── Settings Preferences Save ──
  document.getElementById('btn-save-settings-tab')?.addEventListener('click', async () => {
    const rad = document.querySelector('input[name="rad-decision"]:checked');
    aiDecisionMode = rad?.value || 'autonomous';
    const uploadRad = document.querySelector('input[name="rad-file-upload-mode"]:checked');
    fileUploadMode = uploadRad?.value || 'workflow_only';
    allowMultiTabControl = document.getElementById('chk-multi-tab')?.checked ?? true;
    allowSettingsAccess = document.getElementById('chk-settings-access')?.checked ?? true;
    await persist(STORAGE_KEYS.AI_DECISION_MODE, aiDecisionMode);
    await persist(STORAGE_KEYS.FILE_UPLOAD_MODE, fileUploadMode);
    await persist(STORAGE_KEYS.ALLOW_MULTI_TAB, allowMultiTabControl);
    await persist(STORAGE_KEYS.ALLOW_SETTINGS_ACCESS, allowSettingsAccess, 'Preferences saved successfully!');
    renderAppHub();
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}
