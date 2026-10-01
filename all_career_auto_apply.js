/**
 * ALL CAREER AUTO APPLY & APPLICATION HISTORY ENGINE
 * Connects page UI to AutoFill V4 Chrome Extension
 * Supports Workflow Studio (Naukri, Indeed, etc.) + AI Form Orchestrator fallback
 */

(function () {
    let currentBatchState = {
        running: false,
        total: 0,
        currentIndex: 0,
        appliedCount: 0,
        failedCount: 0,
        currentJob: null,
    };

    let cachedHistory = [];
    let currentFilterTab = 'all';
    let historySearchQuery = '';

    // Initialize once DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        injectDOMModals();
        setupMessageListeners();
        loadHistoryFromStorage();
        requestExtensionHistory();
    }

    /* ════════════════════════════════════════════════════════════════
       DOM INJECTION: HUD & MODALS
    ════════════════════════════════════════════════════════════════ */
    function injectDOMModals() {
        if (!document.getElementById('batchApplyHUD')) {
            const hud = document.createElement('div');
            hud.id = 'batchApplyHUD';
            hud.className = 'batch-apply-hud';
            hud.innerHTML = `
                <div class="hud-header">
                    <div class="hud-title-wrap">
                        <div class="hud-pulse-dot" id="hudPulseDot"></div>
                        <span class="hud-title" id="hudTitle">Auto Apply Engine</span>
                    </div>
                    <button class="hud-close-btn" onclick="window.AllCareerAutoApply.onHudCloseClick()" title="Stop & Close HUD">✕</button>
                </div>
                <div class="hud-body">
                    <div class="hud-current-job" id="hudJobTitle">Starting application queue...</div>
                    <div class="hud-portal-mode" id="hudPortalMode">
                        <span class="hud-badge portal" id="hudPortalBadge">Detecting Portal</span>
                        <span class="hud-badge mode-workflow" id="hudModeBadge">Checking Workflows</span>
                    </div>
                    <div class="hud-progress-bar-bg">
                        <div class="hud-progress-bar-fill" id="hudProgressBar"></div>
                    </div>
                    <div class="hud-stats-row">
                        <div class="hud-stat-item success">
                            <span>✅</span> Applied: <span id="hudAppliedCount">0</span>
                        </div>
                        <div class="hud-stat-item failed">
                            <span>❌</span> Skipped: <span id="hudFailedCount">0</span>
                        </div>
                        <div class="hud-stat-item remaining">
                            <span>⏳</span> Remaining: <span id="hudRemainingCount">0</span>
                        </div>
                    </div>
                </div>
                <div class="hud-footer">
                    <button class="hud-btn-stop" id="hudStopBtn" onclick="window.AllCareerAutoApply.stopBatch()">⏹ Stop Auto Apply</button>
                    <button class="hud-btn-history" onclick="window.AllCareerAutoApply.openHistory()">📋 View History</button>
                </div>
            `;
            document.body.appendChild(hud);
        }

        if (!document.getElementById('applicationHistoryModal')) {
            const modal = document.createElement('div');
            modal.id = 'applicationHistoryModal';
            modal.className = 'history-modal-backdrop';
            modal.onclick = function (e) {
                if (e.target === modal) window.AllCareerAutoApply.closeHistory();
            };
            modal.innerHTML = `
                <div class="history-modal-container" onclick="event.stopPropagation()">
                    <div class="history-modal-header">
                        <div class="history-modal-title-area">
                            <div class="history-modal-icon">📋</div>
                            <div>
                                <h3 class="history-modal-title">Application History</h3>
                                <p class="history-modal-subtitle">Auto-applied jobs, recorded portal workflows & detailed failure reasons</p>
                            </div>
                        </div>
                        <button class="history-modal-close" onclick="window.AllCareerAutoApply.closeHistory()" title="Close">✕</button>
                    </div>

                    <div class="history-summary-bar">
                        <div class="history-metric-card total">
                            <span class="history-metric-label">Total Jobs Processed</span>
                            <span class="history-metric-value" id="metricTotal">0</span>
                        </div>
                        <div class="history-metric-card applied">
                            <span class="history-metric-label">Successfully Applied</span>
                            <span class="history-metric-value" id="metricApplied">0</span>
                        </div>
                        <div class="history-metric-card failed">
                            <span class="history-metric-label">Not Applied / Skipped</span>
                            <span class="history-metric-value" id="metricFailed">0</span>
                        </div>
                    </div>

                    <div class="history-toolbar">
                        <div class="history-filter-tabs">
                            <button class="history-tab-btn active" id="tabAll" onclick="window.AllCareerAutoApply.setFilterTab('all')">All (<span id="countTabAll">0</span>)</button>
                            <button class="history-tab-btn" id="tabApplied" onclick="window.AllCareerAutoApply.setFilterTab('applied')">Applied (<span id="countTabApplied">0</span>)</button>
                            <button class="history-tab-btn" id="tabFailed" onclick="window.AllCareerAutoApply.setFilterTab('failed')">Not Applied (<span id="countTabFailed">0</span>)</button>
                        </div>
                        <input type="text" class="history-search-input" id="historySearchInput" placeholder="Filter by company, role..." oninput="window.AllCareerAutoApply.onSearchHistory(this.value)">
                        <button class="history-clear-btn" onclick="window.AllCareerAutoApply.clearHistory()" title="Clear all history">🗑️ Clear History</button>
                    </div>

                    <div class="history-modal-body" id="historyListContainer">
                        <!-- Populated by JavaScript -->
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        if (!document.getElementById('extensionHelperModal')) {
            const helper = document.createElement('div');
            helper.id = 'extensionHelperModal';
            helper.className = 'ext-helper-modal';
            helper.onclick = function (e) {
                if (e.target === helper) helper.classList.remove('open');
            };
            helper.innerHTML = `
                <div class="ext-helper-content" onclick="event.stopPropagation()">
                    <div class="ext-helper-header">
                        <h3>⚡ Extension Required</h3>
                        <button class="ext-helper-close" onclick="document.getElementById('extensionHelperModal').classList.remove('open')" title="Close">✕</button>
                    </div>
                    <p>Please add or enable the extension to start Auto Apply across job portals.</p>
                    <div class="ext-helper-actions">
                        <button class="ext-helper-btn ext-helper-primary-btn" id="extAddBtn">Add Extension</button>
                        <button class="ext-helper-btn ext-helper-secondary-btn" onclick="document.getElementById('extensionHelperModal').classList.remove('open')">Got It</button>
                    </div>
                </div>
            `;
            document.body.appendChild(helper);

            const addBtn = helper.querySelector('#extAddBtn');
            if (addBtn) {
                addBtn.onclick = function () {
                    if (window.EXTENSION_DOWNLOAD_URL) {
                        window.open(window.EXTENSION_DOWNLOAD_URL, '_blank');
                    } else {
                        showToast('Extension download link will be available soon.', 'info');
                    }
                };
            }
        }
    }

    /* ════════════════════════════════════════════════════════════════
       MESSAGE BRIDGE & LISTENERS
    ════════════════════════════════════════════════════════════════ */
    function setupMessageListeners() {
        window.addEventListener('message', function (event) {
            if (!event.data || typeof event.data !== 'object' || !event.data.type) return;
            const { type, data } = event.data;

            if (type === 'ALL_CAREER_BATCH_PROGRESS') {
                handleBatchProgress(data);
            } else if (type === 'ALL_CAREER_START_BATCH_RESPONSE') {
                if (!event.data.success) {
                    showToast(event.data.error || 'Failed to start batch application.', 'error');
                    toggleHUD(false);
                    resetAutoApplyButton();
                }
            } else if (type === 'ALL_CAREER_STOP_BATCH' || type === 'ALL_CAREER_STOP_BATCH_RESPONSE') {
                showToast('Auto Apply batch has been stopped.', 'info');
                currentBatchState.running = false;
                currentBatchState.cancelled = true;
                updateHUDView(currentBatchState);
                resetAutoApplyButton();
            } else if (type === 'ALL_CAREER_HISTORY_RESPONSE') {
                if (Array.isArray(event.data.history)) {
                    cachedHistory = event.data.history;
                    saveHistoryToStorage(cachedHistory);
                    updateHistoryBadge();
                    renderHistoryList();
                }
            } else if (type === 'ALL_CAREER_CLEAR_HISTORY_RESPONSE') {
                cachedHistory = [];
                saveHistoryToStorage(cachedHistory);
                updateHistoryBadge();
                renderHistoryList();
                showToast('Application history cleared.', 'success');
            }
        });

        // Automatically signal stop when the user closes or navigates away from the All Career tab
        window.addEventListener('beforeunload', function () {
            if (currentBatchState && currentBatchState.running) {
                try {
                    window.postMessage({ type: 'ALL_CAREER_STOP_BATCH' }, '*');
                } catch (_) {}
            }
        });
    }

    function handleBatchProgress(controller) {
        if (!controller) return;
        currentBatchState = controller;
        updateHUDView(controller);

        const applyBtn = document.getElementById('autoApplyBtn');
        if (applyBtn) {
            if (controller.running) {
                applyBtn.classList.add('running');
                const txt = applyBtn.querySelector('.auto-apply-text');
                if (txt) txt.textContent = `⏹ Stop (${controller.currentIndex}/${controller.total})`;
                applyBtn.title = 'Click to Stop Auto Apply';
            } else {
                resetAutoApplyButton();
            }
        }

        // Refresh history from storage or query
        requestExtensionHistory();

        if (!controller.running && controller.currentIndex >= controller.total) {
            showToast(`Batch completed! Applied: ${controller.appliedCount}, Skipped: ${controller.failedCount}`, 'success');
            setTimeout(() => {
                const pulse = document.getElementById('hudPulseDot');
                if (pulse) pulse.style.animation = 'none';
            }, 3000);
        }
    }

    function resetAutoApplyButton() {
        const applyBtn = document.getElementById('autoApplyBtn');
        if (applyBtn) {
            applyBtn.classList.remove('running');
            const txt = applyBtn.querySelector('.auto-apply-text');
            if (txt) txt.textContent = 'Auto Apply';
        }
    }

    function updateHUDView(ctrl) {
        const hud = document.getElementById('batchApplyHUD');
        if (!hud) return;

        hud.classList.add('visible');

        const titleEl = document.getElementById('hudTitle');
        const jobTitleEl = document.getElementById('hudJobTitle');
        const portalBadge = document.getElementById('hudPortalBadge');
        const modeBadge = document.getElementById('hudModeBadge');
        const progressBar = document.getElementById('hudProgressBar');
        const appliedCount = document.getElementById('hudAppliedCount');
        const failedCount = document.getElementById('hudFailedCount');
        const remainingCount = document.getElementById('hudRemainingCount');
        const stopBtn = document.getElementById('hudStopBtn');
        const pulseDot = document.getElementById('hudPulseDot');

        if (titleEl) {
            titleEl.textContent = ctrl.running 
                ? `Auto Apply Running (${ctrl.currentIndex}/${ctrl.total})` 
                : (ctrl.cancelled ? 'Auto Apply Stopped' : 'Auto Apply Completed');
        }

        if (pulseDot) {
            pulseDot.style.background = ctrl.running ? '#34d399' : (ctrl.cancelled ? '#f59e0b' : '#38bdf8');
        }

        if (ctrl.currentJob) {
            const company = ctrl.currentJob.company || 'Company';
            const title = ctrl.currentJob.title || 'Job Opening';
            if (jobTitleEl) jobTitleEl.textContent = `[${ctrl.currentIndex}/${ctrl.total}] ${title} at ${company}`;

            const portal = detectJobPortalName(ctrl.currentJob);
            if (portalBadge) {
                portalBadge.textContent = `🏢 ${portal}`;
            }

            if (modeBadge) {
                if (ctrl.latestItem?.workflowName) {
                    modeBadge.textContent = `⚡ ${ctrl.latestItem.workflowName}`;
                    modeBadge.className = 'hud-badge mode-workflow';
                } else if (ctrl.latestItem?.mode === 'ai') {
                    modeBadge.textContent = '🤖 AI Control';
                    modeBadge.className = 'hud-badge mode-ai';
                } else {
                    modeBadge.textContent = '⚡ Checking Workflow Studio...';
                    modeBadge.className = 'hud-badge mode-workflow';
                }
            }
        } else if (!ctrl.running) {
            if (jobTitleEl) jobTitleEl.textContent = `Batch finished. ${ctrl.appliedCount} applied, ${ctrl.failedCount} skipped.`;
        }

        const pct = ctrl.total > 0 ? Math.round((ctrl.currentIndex / ctrl.total) * 100) : 0;
        if (progressBar) progressBar.style.width = `${pct}%`;

        if (appliedCount) appliedCount.textContent = ctrl.appliedCount || 0;
        if (failedCount) failedCount.textContent = ctrl.failedCount || 0;
        if (remainingCount) remainingCount.textContent = Math.max(0, ctrl.total - ctrl.currentIndex);

        if (stopBtn) {
            stopBtn.style.display = ctrl.running ? 'block' : 'none';
        }
    }

    function toggleHUD(show) {
        const hud = document.getElementById('batchApplyHUD');
        if (hud) {
            if (show) hud.classList.add('visible');
            else hud.classList.remove('visible');
        }
    }

    /* ════════════════════════════════════════════════════════════════
       ACTIONS: START / STOP BATCH APPLY
    ════════════════════════════════════════════════════════════════ */
    async function startBatchAutoApply() {
        // Toggle to STOP immediately if batch is already running!
        if (currentBatchState && currentBatchState.running) {
            console.log('[AllCareerAutoApply] Stop requested via navbar button.');
            stopBatchAutoApply();
            return;
        }

        const visibleJobs = getVisibleJobsFromPage();
        if (!visibleJobs || visibleJobs.length === 0) {
            showToast('No jobs available on this page to apply.', 'warning');
            return;
        }

        // Test if extension is installed and listening
        const isExtensionReady = await pingExtension();
        if (!isExtensionReady) {
            const helperModal = document.getElementById('extensionHelperModal');
            if (helperModal) helperModal.classList.add('open');
            return;
        }

        const applyBtn = document.getElementById('autoApplyBtn');
        if (applyBtn) {
            applyBtn.classList.add('running');
            const txt = applyBtn.querySelector('.auto-apply-text');
            if (txt) txt.textContent = `Starting (0/${visibleJobs.length})...`;
            applyBtn.title = 'Click to Stop Auto Apply';
        }

        // Open HUD
        toggleHUD(true);
        currentBatchState = {
            running: true,
            total: visibleJobs.length,
            currentIndex: 0,
            appliedCount: 0,
            failedCount: 0,
            currentJob: visibleJobs[0] || null,
        };
        updateHUDView(currentBatchState);

        // Send start message to extension content script bridge
        window.postMessage({
            type: 'ALL_CAREER_START_BATCH',
            data: { jobs: visibleJobs }
        }, '*');

        showToast(`Auto Apply started for ${visibleJobs.length} jobs on this page.`, 'info');
    }

    function stopBatchAutoApply() {
        // Immediate local state reset so UI responds without delay
        currentBatchState.running = false;
        currentBatchState.cancelled = true;
        updateHUDView(currentBatchState);
        resetAutoApplyButton();

        // Dispatch stop signal to extension background
        window.postMessage({ type: 'ALL_CAREER_STOP_BATCH' }, '*');
        const stopBtn = document.getElementById('hudStopBtn');
        if (stopBtn) stopBtn.textContent = '⏹ Stopping...';
        showToast('Auto Apply stopped.', 'info');
    }

    function onHudCloseClick() {
        if (currentBatchState && currentBatchState.running) {
            stopBatchAutoApply();
        }
        toggleHUD(false);
    }

    function pingExtension() {
        return new Promise((resolve) => {
            let answered = false;
            const listener = (event) => {
                if (event.data?.type === 'ALL_CAREER_PONG') {
                    answered = true;
                    window.removeEventListener('message', listener);
                    resolve(event.data.alive === true);
                }
            };
            window.addEventListener('message', listener);
            window.postMessage({ type: 'ALL_CAREER_PING_EXTENSION' }, '*');

            setTimeout(() => {
                if (!answered) {
                    window.removeEventListener('message', listener);
                    resolve(false);
                }
            }, 900);
        });
    }

    function getVisibleJobsFromPage() {
        // 1. If page exposed current page array
        if (window.__allCareerCurrentPageJobs && Array.isArray(window.__allCareerCurrentPageJobs)) {
            return window.__allCareerCurrentPageJobs;
        }

        // 2. Fallback: inspect filteredJobs and pagination in all_jobs.html or big_company_jobs.html
        if (typeof filteredJobs !== 'undefined' && Array.isArray(filteredJobs)) {
            const perPage = typeof JOBS_PER_PAGE !== 'undefined' ? JOBS_PER_PAGE : 100;
            const curPage = typeof currentPage !== 'undefined' ? currentPage : 1;
            const start = (curPage - 1) * perPage;
            return filteredJobs.slice(start, start + perPage);
        }

        // 3. Fallback: parse from rendered job card DOM elements
        const cards = document.querySelectorAll('.job-card');
        const jobs = [];
        cards.forEach((card, idx) => {
            const titleEl = card.querySelector('.job-title, .card-role, h3');
            const companyEl = card.querySelector('.company-name, .card-company');
            const linkEl = card.querySelector('a.apply-btn, a[href*="http"]');
            const applyUrl = linkEl?.getAttribute('href') || '';
            jobs.push({
                id: `card_${idx}`,
                title: titleEl?.textContent?.trim() || 'Job Opening',
                company: companyEl?.textContent?.trim() || 'Company',
                url: applyUrl,
                apply_url: applyUrl
            });
        });
        return jobs;
    }

    /* ════════════════════════════════════════════════════════════════
       HISTORY MANAGEMENT & MODAL RENDERING
    ════════════════════════════════════════════════════════════════ */
    function requestExtensionHistory() {
        window.postMessage({ type: 'ALL_CAREER_GET_HISTORY' }, '*');
    }

    function loadHistoryFromStorage() {
        try {
            const raw = localStorage.getItem('allCareerApplyHistory');
            if (raw) {
                cachedHistory = JSON.parse(raw);
                updateHistoryBadge();
                renderHistoryList();
            }
        } catch (_) {}
    }

    function saveHistoryToStorage(history) {
        try {
            localStorage.setItem('allCareerApplyHistory', JSON.stringify(history));
        } catch (_) {}
    }

    function updateHistoryBadge() {
        const badge = document.getElementById('historyNavBadge');
        if (!badge) return;

        const total = cachedHistory.length;
        const applied = cachedHistory.filter(h => h.status === 'applied').length;
        const failed = total - applied;

        if (total === 0) {
            badge.textContent = '0';
            badge.classList.remove('has-counts');
        } else {
            badge.textContent = `${applied}/${failed}`;
            badge.classList.add('has-counts');
            badge.title = `${applied} Applied, ${failed} Not Applied (${total} Total)`;
        }

        // Update modal metrics if open
        const metricTotal = document.getElementById('metricTotal');
        const metricApplied = document.getElementById('metricApplied');
        const metricFailed = document.getElementById('metricFailed');
        const countTabAll = document.getElementById('countTabAll');
        const countTabApplied = document.getElementById('countTabApplied');
        const countTabFailed = document.getElementById('countTabFailed');

        if (metricTotal) metricTotal.textContent = total;
        if (metricApplied) metricApplied.textContent = applied;
        if (metricFailed) metricFailed.textContent = failed;

        if (countTabAll) countTabAll.textContent = total;
        if (countTabApplied) countTabApplied.textContent = applied;
        if (countTabFailed) countTabFailed.textContent = failed;
    }

    function openHistoryModal() {
        requestExtensionHistory();
        const modal = document.getElementById('applicationHistoryModal');
        if (modal) modal.classList.add('open');
        renderHistoryList();
    }

    function closeHistoryModal() {
        const modal = document.getElementById('applicationHistoryModal');
        if (modal) modal.classList.remove('open');
    }

    function setFilterTab(tab) {
        currentFilterTab = tab;
        ['tabAll', 'tabApplied', 'tabFailed'].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.classList.remove('active');
        });
        const activeBtn = document.getElementById(tab === 'applied' ? 'tabApplied' : tab === 'failed' ? 'tabFailed' : 'tabAll');
        if (activeBtn) activeBtn.classList.add('active');
        renderHistoryList();
    }

    function onSearchHistory(query) {
        historySearchQuery = (query || '').toLowerCase().trim();
        renderHistoryList();
    }

    function clearAllHistory() {
        if (!confirm('Are you sure you want to clear your entire Auto Apply history?')) return;
        window.postMessage({ type: 'ALL_CAREER_CLEAR_HISTORY' }, '*');
    }

    function renderHistoryList() {
        const container = document.getElementById('historyListContainer');
        if (!container) return;

        let items = [...cachedHistory];

        // 1. Status Filter
        if (currentFilterTab === 'applied') {
            items = items.filter(i => i.status === 'applied');
        } else if (currentFilterTab === 'failed') {
            items = items.filter(i => i.status !== 'applied');
        }

        // 2. Search Query Filter
        if (historySearchQuery) {
            items = items.filter(i => {
                const hay = `${i.title} ${i.company} ${i.portal} ${i.reason} ${i.workflowName}`.toLowerCase();
                return hay.includes(historySearchQuery);
            });
        }

        if (items.length === 0) {
            container.innerHTML = `
                <div class="history-empty-state">
                    <div class="history-empty-icon">📭</div>
                    <div class="history-empty-text">No application records found</div>
                    <div class="history-empty-hint">${cachedHistory.length === 0 ? 'Click the "Auto Apply" button above to start applying to jobs automatically.' : 'No records match the current filter or search criteria.'}</div>
                </div>
            `;
            return;
        }

        container.innerHTML = items.map(item => {
            const isApplied = item.status === 'applied';
            const portal = item.portal || 'Direct';
            const mode = item.mode === 'workflow' ? (item.workflowName ? `⚡ Workflow: ${item.workflowName}` : '⚡ Workflow Studio') : '🤖 AI Orchestrator';
            const modeClass = item.mode === 'workflow' ? 'workflow' : 'ai';
            const dateStr = item.dateStr || (item.timestamp ? new Date(item.timestamp).toLocaleString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' }) : 'Recently');
            
            // Format descriptive reason why it was or was not applied
            let reasonHtml = '';
            if (isApplied) {
                reasonHtml = `
                    <div class="history-reason-box success">
                        <span class="history-reason-icon">✅</span>
                        <div class="history-reason-text">
                            <strong>Applied Successfully:</strong> ${escapeHtml(item.reason || 'Submitted application via automated pipeline.')}
                        </div>
                    </div>
                `;
            } else {
                reasonHtml = `
                    <div class="history-reason-box failure">
                        <span class="history-reason-icon">⚠️</span>
                        <div class="history-reason-text">
                            <strong>Why Not Applied:</strong> ${escapeHtml(item.reason || 'External portal requires manual review or login.')}
                        </div>
                    </div>
                `;
            }

            return `
                <div class="history-item-card ${isApplied ? 'status-applied' : 'status-failed'}">
                    <div class="history-card-top">
                        <div class="history-card-main">
                            <div class="history-card-title">
                                <span>${escapeHtml(item.title || 'Job Opening')}</span>
                            </div>
                            <div class="history-card-company">
                                <span>🏢 ${escapeHtml(item.company || 'Company')}</span>
                                <span>•</span>
                                <span>🕒 ${escapeHtml(dateStr)}</span>
                            </div>
                        </div>
                        <div class="history-card-meta">
                            <span class="portal-pill">${escapeHtml(portal)}</span>
                            <span class="mode-pill ${modeClass}">${escapeHtml(mode)}</span>
                            <span class="status-pill ${isApplied ? 'applied' : 'not-applied'}">
                                ${isApplied ? '✓ Applied' : '✕ Not Applied'}
                            </span>
                        </div>
                    </div>

                    ${reasonHtml}

                    <div class="history-card-footer">
                        <span>Application Target: ${escapeHtml(portal)}</span>
                        ${item.url ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">View Job Page ↗</a>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    /* ════════════════════════════════════════════════════════════════
       HELPERS & UTILITIES
    ════════════════════════════════════════════════════════════════ */
    function detectJobPortalName(job) {
        if (!job) return 'Company Career Site';
        const u = String(job.apply_url || job.url || job.link || '').toLowerCase();
        const src = String(job.source || job.portal || job.platform || job.site || '').toLowerCase();
        const co = String(job.company || '').toLowerCase();
        const title = String(job.title || '').toLowerCase();
        const combined = `${u} ${src} ${co} ${title}`;

        if (combined.includes('naukri')) return 'Naukri';
        if (combined.includes('indeed')) return 'Indeed';
        if (combined.includes('linkedin')) return 'LinkedIn';
        if (combined.includes('workday') || combined.includes('myworkdayjobs')) return 'Workday';
        if (combined.includes('internshala')) return 'Internshala';
        if (combined.includes('unstop')) return 'Unstop';
        if (combined.includes('foundit') || combined.includes('monster')) return 'Foundit';
        if (combined.includes('shine')) return 'Shine';
        if (combined.includes('glassdoor')) return 'Glassdoor';
        if (combined.includes('greenhouse')) return 'Greenhouse';
        if (combined.includes('lever')) return 'Lever';
        if (combined.includes('smartrecruiters')) return 'SmartRecruiters';
        return 'Company Career Site';
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function showToast(message, type = 'info') {
        const existing = document.getElementById('allCareerToast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.id = 'allCareerToast';
        toast.style.cssText = `
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 10005;
            background: ${type === 'success' ? '#065f46' : type === 'error' ? '#991b1b' : type === 'warning' ? '#92400e' : '#1e1b4b'};
            color: #ffffff;
            border-left: 4px solid ${type === 'success' ? '#34d399' : type === 'error' ? '#f87171' : type === 'warning' ? '#fcd34d' : '#818cf8'};
            padding: 12px 18px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            font-family: 'Inter', sans-serif;
            font-size: 0.86rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.3s ease;
            max-width: 380px;
        `;
        toast.innerHTML = `
            <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️'}</span>
            <span style="flex:1;">${escapeHtml(message)}</span>
        `;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // Expose Global Public API
    window.AllCareerAutoApply = {
        startBatch: startBatchAutoApply,
        stopBatch: stopBatchAutoApply,
        onHudCloseClick: onHudCloseClick,
        openHistory: openHistoryModal,
        closeHistory: closeHistoryModal,
        setFilterTab: setFilterTab,
        onSearchHistory: onSearchHistory,
        clearHistory: clearAllHistory,
        toggleHUD: toggleHUD,
        updateCountBadge: function (count) {
            const badge = document.getElementById('autoApplyCountBadge');
            if (badge) {
                badge.style.display = 'none';
                badge.textContent = '';
            }
        }
    };
})();
