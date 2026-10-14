import React, { useState, useEffect } from 'react';
import { bridgeService, BatchState } from '../../services/bridgeService';
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Square, 
  ClipboardList, 
  X, 
  Puzzle, 
  ExternalLink, 
  Trash2, 
  Search,
  Sparkles,
  Building2,
  Workflow
} from 'lucide-react';

export const AutoApplyHUD: React.FC = () => {
  const [state, setState] = useState<BatchState>(bridgeService.getState());
  const [historyFilter, setHistoryFilter] = useState<'all' | 'applied' | 'failed'>('all');
  const [historySearch, setHistorySearch] = useState('');
  const [minimized, setMinimized] = useState(false);

  useEffect(() => {
    const unsubscribe = bridgeService.subscribe((newState) => {
      setState(newState);
    });
    return unsubscribe;
  }, []);

  const {
    running,
    cancelled,
    total,
    currentIndex,
    appliedCount,
    failedCount,
    currentJob,
    latestItem,
    showHelperModal,
    showHistoryModal,
    history
  } = state;

  const showHud = running || (total > 0 && !cancelled && currentIndex < total);
  const progressPct = total > 0 ? Math.min(100, Math.round((currentIndex / total) * 100)) : 0;
  const portalName = currentJob ? bridgeService.detectPortal(currentJob) : 'Detecting Portal...';

  // Filter history items
  const filteredHistory = history.filter((item) => {
    const isApplied = item.success || item.applied || item.status === 'applied';
    if (historyFilter === 'applied' && !isApplied) return false;
    if (historyFilter === 'failed' && isApplied) return false;

    if (historySearch.trim()) {
      const q = historySearch.toLowerCase();
      const text = `${item.title || ''} ${item.company || ''} ${item.portal || ''} ${item.reason || ''}`.toLowerCase();
      return text.includes(q);
    }
    return true;
  });

  const appliedTotal = history.filter((i) => i.success || i.applied || i.status === 'applied').length;
  const failedTotal = history.length - appliedTotal;

  return (
    <>
      {/* ════════════════════════════════════════════════════════════════
          1. FLOATING BATCH APPLY HUD BANNER
      ════════════════════════════════════════════════════════════════ */}
      {showHud && (
        <aside
          role="complementary"
          aria-label="Auto Apply Ingestion Engine HUD"
          className="fixed bottom-6 right-6 z-[9990] w-96 max-w-[calc(100vw-32px)] bg-slate-950/95 backdrop-blur-xl border border-sky-500/30 rounded-2xl p-4 shadow-[0_16px_50px_rgba(0,0,0,0.8),0_0_20px_rgba(56,189,248,0.2)] text-slate-100 transition-all duration-300"
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <div className="flex items-center gap-2.5">
              <span
                className={`w-3 h-3 rounded-full ${
                  running
                    ? 'bg-emerald-400 animate-ping'
                    : cancelled
                    ? 'bg-amber-400'
                    : 'bg-sky-400'
                }`}
              />
              <span className="font-heading font-bold text-sm tracking-wide text-white">
                {running ? `Auto Apply Running (${currentIndex}/${total})` : cancelled ? 'Auto Apply Stopped' : 'Auto Apply Completed'}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setMinimized(!minimized)}
                className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-white/5 transition"
                title={minimized ? 'Expand HUD' : 'Minimize HUD'}
              >
                {minimized ? '▲' : '▼'}
              </button>
              <button
                onClick={() => bridgeService.stopBatchAutoApply()}
                className="text-slate-400 hover:text-rose-400 p-1 rounded-md hover:bg-white/5 transition"
                title="Stop & Close HUD"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {!minimized && (
            <div className="pt-3 space-y-3">
              {/* Job Title & Company */}
              <div className="bg-slate-900/90 border border-white/5 rounded-xl p-2.5">
                <div className="text-xs text-sky-400 font-semibold mb-0.5 flex items-center gap-1">
                  <Building2 size={12} />
                  <span>{currentJob?.company || 'Enterprise Candidate Selection'}</span>
                </div>
                <div className="text-sm font-bold text-white truncate" title={currentJob?.title || 'Job Opening'}>
                  {currentJob ? `[${currentIndex}/${total}] ${currentJob.title}` : 'Initializing application pipeline...'}
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-300 border border-sky-500/30">
                    🏢 {portalName}
                  </span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                    <Workflow size={10} />
                    {latestItem?.workflowName ? `⚡ ${latestItem.workflowName}` : '⚡ Auto-Fill-V5 Studio'}
                  </span>
                </div>
              </div>

              {/* Progress Bar */}
              <div>
                <div className="flex justify-between text-[11px] font-semibold text-slate-400 mb-1">
                  <span>Batch Progress</span>
                  <span className="text-sky-300">{progressPct}%</span>
                </div>
                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden border border-white/5">
                  <div
                    className="h-full bg-gradient-to-r from-sky-500 to-emerald-400 transition-all duration-300 rounded-full"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>

              {/* Stat Counters */}
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-1.5">
                  <div className="text-[10px] text-emerald-400 font-semibold flex items-center justify-center gap-1">
                    <CheckCircle2 size={11} /> Applied
                  </div>
                  <div className="font-bold text-white mt-0.5">{appliedCount}</div>
                </div>
                <div className="bg-rose-500/10 border border-rose-500/20 rounded-lg p-1.5">
                  <div className="text-[10px] text-rose-400 font-semibold flex items-center justify-center gap-1">
                    <XCircle size={11} /> Skipped
                  </div>
                  <div className="font-bold text-white mt-0.5">{failedCount}</div>
                </div>
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-1.5">
                  <div className="text-[10px] text-amber-400 font-semibold flex items-center justify-center gap-1">
                    <Clock size={11} /> Remaining
                  </div>
                  <div className="font-bold text-white mt-0.5">{Math.max(0, total - currentIndex)}</div>
                </div>
              </div>

              {/* Footer Controls */}
              <div className="flex items-center gap-2 pt-1">
                {running ? (
                  <button
                    onClick={() => bridgeService.stopBatchAutoApply()}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 text-xs font-bold transition"
                  >
                    <Square size={13} />
                    <span>Stop Batch</span>
                  </button>
                ) : (
                  <button
                    onClick={() => bridgeService.stopBatchAutoApply()}
                    className="flex-1 py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition"
                  >
                    Dismiss
                  </button>
                )}

                <button
                  onClick={() => bridgeService.openHistory()}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 text-xs font-bold transition"
                >
                  <ClipboardList size={13} />
                  <span>View History</span>
                </button>
              </div>
            </div>
          )}
        </aside>
      )}

      {/* ════════════════════════════════════════════════════════════════
          2. APPLICATION HISTORY MODAL
      ════════════════════════════════════════════════════════════════ */}
      {showHistoryModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="history-dialog-title"
          className="fixed inset-0 z-[9995] flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200"
          onClick={(e) => {
            if (e.target === e.currentTarget) bridgeService.closeHistory();
          }}
        >
          <div className="w-full max-w-2xl max-h-[85vh] bg-slate-900 border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden text-slate-100">
            {/* Header */}
            <div className="p-5 border-b border-white/10 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400">
                  <ClipboardList size={18} />
                </div>
                <div>
                  <h3 id="history-dialog-title" className="font-heading font-bold text-lg text-white">Application History</h3>
                  <p className="text-xs text-slate-400">Detailed record of auto-applied jobs and status feedback</p>
                </div>
              </div>
              <button
                onClick={() => bridgeService.closeHistory()}
                className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-white/5 transition"
              >
                <X size={18} />
              </button>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-3 gap-3 p-5 bg-slate-950/30 border-b border-white/5">
              <div className="bg-slate-800/60 border border-white/5 rounded-xl p-3 text-center">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Total Processed</span>
                <span className="text-xl font-heading font-black text-white mt-0.5 block">{history.length}</span>
              </div>
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 text-center">
                <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider block">Applied</span>
                <span className="text-xl font-heading font-black text-emerald-300 mt-0.5 block">{appliedTotal}</span>
              </div>
              <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 text-center">
                <span className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider block">Skipped / Failed</span>
                <span className="text-xl font-heading font-black text-rose-300 mt-0.5 block">{failedTotal}</span>
              </div>
            </div>

            {/* Toolbar */}
            <div className="p-4 border-b border-white/5 flex flex-wrap items-center justify-between gap-3 bg-slate-950/20">
              <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-white/10">
                <button
                  onClick={() => setHistoryFilter('all')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    historyFilter === 'all'
                      ? 'bg-sky-500 text-white shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  All ({history.length})
                </button>
                <button
                  onClick={() => setHistoryFilter('applied')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    historyFilter === 'applied'
                      ? 'bg-emerald-500 text-white shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Applied ({appliedTotal})
                </button>
                <button
                  onClick={() => setHistoryFilter('failed')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    historyFilter === 'failed'
                      ? 'bg-rose-500 text-white shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Skipped ({failedTotal})
                </button>
              </div>

              <div className="flex items-center gap-2 flex-1 max-w-xs">
                <div className="relative w-full">
                  <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Filter by company or role..."
                    value={historySearch}
                    onChange={(e) => setHistorySearch(e.target.value)}
                    className="w-full bg-slate-950 border border-white/10 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                  />
                </div>
                {history.length > 0 && (
                  <button
                    onClick={() => {
                      if (confirm('Clear all application history?')) {
                        bridgeService.clearHistory();
                      }
                    }}
                    className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-white/5 transition"
                    title="Clear All History"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>

            {/* History List Container */}
            <div className="flex-1 overflow-y-auto p-5 space-y-2.5 max-h-[450px]">
              {filteredHistory.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  <ClipboardList size={36} className="mx-auto mb-2 opacity-40" />
                  <p className="text-sm font-semibold">No applications found in history</p>
                  <p className="text-xs text-slate-600 mt-1">Start a batch auto-apply to see results recorded here</p>
                </div>
              ) : (
                filteredHistory.map((item, idx) => {
                  const isSuccess = item.success || item.applied || item.status === 'applied';
                  return (
                    <div
                      key={item.id || idx}
                      className="bg-slate-950/50 border border-white/5 rounded-xl p-3.5 hover:border-white/15 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-sm">{item.title || 'Job Opening'}</span>
                          <span className="text-slate-400 text-xs font-medium">@ {item.company || 'Company'}</span>
                        </div>
                        <div className="flex items-center gap-2 text-[11px] text-slate-400">
                          <span>🏢 {item.portal || item.source || 'Direct Portal'}</span>
                          {item.timestamp && (
                            <>
                              <span>•</span>
                              <span>{new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                            </>
                          )}
                          {item.workflowName && (
                            <>
                              <span>•</span>
                              <span className="text-purple-300">⚡ {item.workflowName}</span>
                            </>
                          )}
                        </div>
                        {item.reason && (
                          <p className="text-[11px] text-slate-400 bg-white/5 rounded px-2 py-0.5 mt-1 inline-block">
                            {item.reason}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 self-end sm:self-center">
                        <span
                          className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
                            isSuccess
                              ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                              : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                          }`}
                        >
                          {isSuccess ? 'Applied ✅' : 'Skipped ❌'}
                        </span>
                        {item.url && (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition"
                            title="Open Job Link"
                          >
                            <ExternalLink size={14} />
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════
          3. EXTENSION CONNECTION HELPER MODAL
      ════════════════════════════════════════════════════════════════ */}
      {showHelperModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="helper-dialog-title"
          className="fixed inset-0 z-[9996] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
          onClick={(e) => {
            if (e.target === e.currentTarget) bridgeService.closeHelperModal();
          }}
        >
          <div className="w-full max-w-lg bg-slate-900 border border-sky-500/30 rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.8),0_0_30px_rgba(56,189,248,0.2)] p-6 text-slate-100">
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-sky-500/20 border border-sky-500/40 flex items-center justify-center text-sky-400">
                  <Puzzle size={22} />
                </div>
                <div>
                  <h3 id="helper-dialog-title" className="font-heading font-bold text-lg text-white">Auto-Fill-V5 Extension Required</h3>
                  <p className="text-xs text-sky-400 font-semibold">Chrome Browser Extension Not Detected</p>
                </div>
              </div>
              <button
                onClick={() => bridgeService.closeHelperModal()}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/5 transition"
              >
                <X size={18} />
              </button>
            </div>

            <div className="py-4 space-y-3.5 text-sm">
              <p className="text-slate-300 leading-relaxed">
                To perform automated batch applications, your browser needs the <strong className="text-white">Auto-Fill-V5</strong> extension installed and active.
              </p>

              <div className="bg-slate-950/80 border border-white/10 rounded-xl p-4 space-y-2.5 text-xs">
                <div className="font-bold text-sky-300 flex items-center gap-1.5 mb-1">
                  <Sparkles size={14} />
                  <span>How to activate Auto-Fill-V5 in 10 seconds:</span>
                </div>
                <div className="flex items-start gap-2 text-slate-300">
                  <span className="w-5 h-5 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center font-bold shrink-0">1</span>
                  <span>Open <code className="bg-white/10 text-sky-300 px-1.5 py-0.5 rounded">chrome://extensions</code> in a new browser tab.</span>
                </div>
                <div className="flex items-start gap-2 text-slate-300">
                  <span className="w-5 h-5 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center font-bold shrink-0">2</span>
                  <span>Turn on the <strong>Developer mode</strong> toggle in the top-right corner.</span>
                </div>
                <div className="flex items-start gap-2 text-slate-300">
                  <span className="w-5 h-5 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center font-bold shrink-0">3</span>
                  <span>Click <strong>Load unpacked</strong> and select the directory:
                    <div className="mt-1 p-2 bg-slate-900 border border-white/5 rounded font-mono text-[11px] text-emerald-400 break-all select-all">
                      c:\Users\lrage\OneDrive\Documents\VS_CODE\ALL_CAREER_3\Auto-Fill-V5
                    </div>
                  </span>
                </div>
                <div className="flex items-start gap-2 text-slate-300">
                  <span className="w-5 h-5 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center font-bold shrink-0">4</span>
                  <span>Return here and click <strong>Auto Apply</strong> again!</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
              <button
                onClick={() => bridgeService.closeHelperModal()}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition"
              >
                Close
              </button>
              <button
                onClick={async () => {
                  const alive = await bridgeService.pingExtension(1000);
                  if (alive) {
                    bridgeService.closeHelperModal();
                    alert('Extension connected successfully! You can now start Auto Apply.');
                  } else {
                    alert('Extension still not detected. Please make sure Auto-Fill-V5 is loaded and enabled in chrome://extensions.');
                  }
                }}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-sky-500/20 transition"
              >
                Check Connection
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
