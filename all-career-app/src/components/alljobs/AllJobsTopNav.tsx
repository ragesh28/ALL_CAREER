import React, { useState, useEffect } from 'react';
import { History, RotateCcw, Search, Send, Square, X } from 'lucide-react';
import { STRING_THEORY_LOGO } from '../../utils/brandLogo';
import { bridgeService, BatchState } from '../../services/bridgeService';

interface AllJobsTopNavProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  totalJobsCount: number | null;
  catalogLoading?: boolean;
  categoryCounts: Record<string, number>;
  onGoHub: () => void;
  onAutoApply: () => void;
  autoApplyDisabled?: boolean;
  onClearAll?: () => void;
  hasActiveFilters?: boolean;
}

export const AllJobsTopNav: React.FC<AllJobsTopNavProps> = ({
  searchTerm,
  onSearchChange,
  totalJobsCount,
  catalogLoading = false,
  categoryCounts: _categoryCounts,
  onGoHub,
  onAutoApply,
  autoApplyDisabled = false,
  onClearAll,
  hasActiveFilters
}) => {
  const [batchState, setBatchState] = useState<BatchState>(bridgeService.getState());

  useEffect(() => {
    return bridgeService.subscribe(setBatchState);
  }, []);

  return (
    <header className="topnav">
      {/* Left: Global Brand Logo */}
      <div className="topnav-left">
        <div className="topnav-logo" onClick={onGoHub}>
          <img src={STRING_THEORY_LOGO} alt="ALL_CAREER" />
          <span>ALL_CAREER</span>
        </div>
      </div>

      {/* Center: Search Box */}
      <div className="topnav-center">
        <div className="topnav-search colored-search" onClick={e => e.currentTarget.querySelector('input')?.focus()}>
          <Search size={16} aria-hidden="true" />
          <input
            type="text"
            placeholder="Search jobs, companies, skills..."
            value={searchTerm}
            onChange={event => onSearchChange(event.target.value)}
            aria-label="Search jobs, companies, and skills"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              className="search-clear-btn"
              aria-label="Clear search text"
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '4px',
                borderRadius: '50%',
                marginRight: '4px'
              }}
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Right: Actions */}
      <div className="topnav-right">
        <button
          className={`auto-apply-nav-btn ${batchState.running ? 'running ring-2 ring-emerald-400 bg-rose-600/30' : ''}`}
          onClick={onAutoApply}
          disabled={autoApplyDisabled && !batchState.running}
          title={batchState.running ? 'Click to Stop Auto Apply' : autoApplyDisabled ? 'No matching jobs available' : 'Review jobs for Auto Apply'}
        >
          {batchState.running ? (
            <>
              <Square size={14} className="animate-pulse text-amber-300" aria-hidden="true" />
              <span>Stop ({batchState.currentIndex}/{batchState.total})</span>
            </>
          ) : (
            <>
              <Send size={15} strokeWidth={2.1} aria-hidden="true" />
              <span>Auto Apply</span>
            </>
          )}
        </button>

        <button
          className="history-nav-btn"
          onClick={() => bridgeService.openHistory()}
          title="View Application History"
        >
          <History size={15} strokeWidth={2.1} aria-hidden="true" />
          <span>History</span>
          <span style={{ color: '#fff', fontWeight: 700 }}>{batchState.history.length}</span>
        </button>

        <div className="topnav-count-btn" aria-live="polite">
          <span>Catalog</span>
          <span className="count-num">{totalJobsCount === null ? (catalogLoading ? 'Loading…' : 'Unavailable') : totalJobsCount.toLocaleString()}</span>
          <span>jobs</span>
        </div>
      </div>
    </header>
  );
};
