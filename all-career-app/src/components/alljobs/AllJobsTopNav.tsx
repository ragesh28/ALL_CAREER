import React, { useState, useEffect, useRef } from 'react';
import { History, RotateCcw, Search, Send, Square, X } from 'lucide-react';
import { resolveAssetUrl } from '../../utils/urlHelper';
import { STRING_THEORY_LOGO } from '../../utils/brandLogo';
import { bridgeService, BatchState } from '../../services/bridgeService';

interface AllJobsTopNavProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  totalJobsCount: number;
  categoryCounts: Record<string, number>;
  onGoHub: () => void;
  onAutoApply: () => void;
  onClearAll?: () => void;
  hasActiveFilters?: boolean;
}

export const AllJobsTopNav: React.FC<AllJobsTopNavProps> = ({
  searchTerm,
  onSearchChange,
  totalJobsCount,
  categoryCounts: _categoryCounts,
  onGoHub,
  onAutoApply,
  onClearAll,
  hasActiveFilters
}) => {
  // Local instant state for silky-smooth 60fps typing without any blocking lag
  const [localSearch, setLocalSearch] = useState(searchTerm);
  const [batchState, setBatchState] = useState<BatchState>(bridgeService.getState());
  const debounceTimerRef = useRef<any>(null);

  useEffect(() => {
    return bridgeService.subscribe((s) => setBatchState(s));
  }, []);

  useEffect(() => {
    setLocalSearch(searchTerm);
  }, [searchTerm]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalSearch(val);
    clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => {
      onSearchChange(val);
    }, 120);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      clearTimeout(debounceTimerRef.current);
      onSearchChange(localSearch);
    }
  };

  const handleClearSearch = () => {
    setLocalSearch('');
    clearTimeout(debounceTimerRef.current);
    onSearchChange('');
  };

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
        <div className="topnav-search colored-search">
          <Search size={16} aria-hidden="true" />
          <input
            type="text"
            placeholder="Search jobs, companies, skills..."
            value={localSearch}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
          />
          {localSearch && (
            <button
              type="button"
              onClick={handleClearSearch}
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
          title={batchState.running ? 'Click to Stop Auto Apply' : 'Auto Apply with Extension'}
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

        <div className="topnav-count-btn" aria-label={`${totalJobsCount.toLocaleString()} jobs shown`}>
          <span>Showing</span>
          <span className="count-num">{totalJobsCount.toLocaleString()}</span>
          <span>jobs</span>
        </div>
      </div>
    </header>
  );
};
