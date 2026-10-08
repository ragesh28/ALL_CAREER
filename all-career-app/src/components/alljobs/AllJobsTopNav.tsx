import React from 'react';
import { History, RotateCcw, Search, Send } from 'lucide-react';

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
  return (
    <header className="topnav">
      {/* Left: Global Brand Logo */}
      <div className="topnav-left">
        <div className="topnav-logo" onClick={onGoHub}>
          <img src="/String_Theory.png" alt="Logo" />
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
            value={searchTerm}
            onChange={e => onSearchChange(e.target.value)}
          />
        </div>
      </div>

      {/* Right: Actions */}
      <div className="topnav-right">
        <button className="auto-apply-nav-btn" onClick={onAutoApply} title="Auto Apply with Extension">
          <Send size={15} strokeWidth={2.1} aria-hidden="true" />
          <span>Auto Apply</span>
        </button>

        <button className="history-nav-btn">
          <History size={15} strokeWidth={2.1} aria-hidden="true" />
          <span>History</span>
          <span style={{ color: '#fff', fontWeight: 700 }}>0</span>
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
