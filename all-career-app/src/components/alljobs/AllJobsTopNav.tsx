import React, { useState } from 'react';

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
  categoryCounts,
  onGoHub,
  onAutoApply,
  onClearAll,
  hasActiveFilters
}) => {
  const [showPopover, setShowPopover] = useState(false);

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
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
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
        {/* ⚡ Auto Apply Button */}
        <button className="auto-apply-nav-btn" onClick={onAutoApply} title="Auto Apply with Extension">
          <span style={{ fontSize: '0.95rem' }}>⚡</span>
          <span>Auto Apply</span>
        </button>

        {/* 📋 History 0 Button */}
        <button className="history-nav-btn">
          <span>📋 History</span>
          <span style={{ color: '#fff', fontWeight: 700 }}>0</span>
        </button>

        {/* Showing jobs count with Popover */}
        <div 
          style={{ position: 'relative' }}
          onMouseEnter={() => setShowPopover(true)}
          onMouseLeave={() => setShowPopover(false)}
        >
          <button className="topnav-count-btn">
            <span>Showing</span>
            <span className="count-num">{(totalJobsCount || 912651).toLocaleString()}</span>
            <span>jobs</span>
            <span style={{ fontSize: '0.70rem', padding: '2px 7px', borderRadius: '5px', background: 'rgba(56, 189, 248, 0.14)', color: '#38bdf8', fontWeight: 700 }}>
              📊 Breakdown ▾
            </span>
          </button>

          {showPopover && (
            <div className="category-dropdown-popover" style={{ display: 'block' }}>
              <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#475775', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px', paddingBottom: '6px', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', justifyContent: 'space-between' }}>
                <span>Category Breakdown</span>
                <span style={{ color: '#34d399' }}>{(totalJobsCount || 912651).toLocaleString()}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {Object.entries(categoryCounts).map(([cat, cnt]) => (
                  <div key={cat} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', padding: '5px 8px', borderRadius: '6px', background: 'rgba(255,255,255,0.03)' }}>
                    <span style={{ color: '#7c8db5', textTransform: 'capitalize' }}>{cat.replace('_', ' ')}</span>
                    <span style={{ fontWeight: 700, color: '#f1f5f9' }}>{cnt.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Clear All button matching line 1599 of original all_jobs.html */}
        {hasActiveFilters && (
          <button className="clear-all-btn" onClick={onClearAll} title="Clear all active filters">
            ✕ Clear All
          </button>
        )}
      </div>
    </header>
  );
};
