try {
  if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.setUninstallURL) {
    chrome.runtime.setUninstallURL('');
  }
} catch (e) {}

import './assets/service-worker.ts-Qx93VBt4.js';
import './byok-background-proxy.js';

