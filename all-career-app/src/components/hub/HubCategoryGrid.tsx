import React from 'react';

interface HubCategoryGridProps {
  onNavigate: (view: 'career_explorer' | 'big_company_jobs' | 'all_jobs' | 'practice') => void;
}

export const HubCategoryGrid: React.FC<HubCategoryGridProps> = ({ onNavigate }) => {
  return (
    <section className="grid-panel" id="categoryGrid" aria-label="Career categories">
      <div className="glass-orb" aria-hidden="true"></div>
      <div className="grid-menu">
        {/* 1. Big Company Name List */}
        <div 
          onClick={() => onNavigate('career_explorer')} 
          className="menu-card card-blue"
        >
          <div className="icon-box">
            <svg viewBox="0 0 24 24" fill="#3b82f6">
              <path d="M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10zm-2-8h-2v2h2v-2zm0 4h-2v2h2v-2z" />
            </svg>
          </div>
          <div className="card-title">Big Company Name List</div>
          <div className="card-desc">
            Browse 150+ top tech companies with career page links.
            <span className="salary-highlight">Salary range: 5-45 LPA+</span>
          </div>
        </div>

        {/* 2. Big Company Jobs */}
        <div 
          onClick={() => onNavigate('big_company_jobs')} 
          className="menu-card card-violet"
          style={{ borderColor: 'rgba(6, 182, 212, 0.3)' }}
        >
          <div className="icon-box">
            <svg viewBox="0 0 24 24" fill="#06b6d4">
              <path d="M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z" />
            </svg>
          </div>
          <div className="card-title">Big Company Jobs</div>
          <div className="card-desc">
            Live jobs from 150+ top companies with direct apply links.
            <span className="salary-highlight" style={{ color: '#10b981' }}>Auto-scraped daily at 7 AM</span>
          </div>
        </div>

        {/* 3. All Jobs */}
        <div 
          onClick={() => onNavigate('all_jobs')} 
          className="menu-card card-green"
          style={{ borderColor: 'rgba(16, 185, 129, 0.3)' }}
        >
          <div className="icon-box">
            <svg viewBox="0 0 24 24" fill="#10b981">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
            </svg>
          </div>
          <div className="card-title">All Jobs</div>
          <div className="card-desc">
            All tech & non-tech roles from Google, LinkedIn, Portals & Telegram.
            <span className="salary-highlight" style={{ color: '#10b981' }}> 36 roles &bull; 13 sources &bull; AI-powered</span>
          </div>
        </div>

        {/* 4. Learn Coding */}
        <div 
          onClick={() => onNavigate('practice')} 
          className="menu-card card-orange"
        >
          <div className="icon-box">
            <svg viewBox="0 0 24 24" fill="#f59e0b">
              <path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z" />
            </svg>
          </div>
          <div className="card-title">Learn Coding</div>
          <div className="card-desc">
            Master DSA with the Top 150 LeetCode questions and company-specific sets.
          </div>
        </div>
      </div>
    </section>
  );
};
