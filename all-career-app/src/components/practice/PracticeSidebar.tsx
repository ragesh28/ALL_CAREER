import React, { useState } from 'react';
import { CompanyLogo } from '../common/CompanyLogo';

interface PracticeSidebarProps {
  selectedMode: string;
  onSelectMode: (mode: string) => void;
  selectedCompany: string;
  onSelectCompany: (company: string) => void;
  companiesList: { name: string; count: number }[];
}

export const PracticeSidebar: React.FC<PracticeSidebarProps> = ({
  selectedMode,
  onSelectMode,
  selectedCompany,
  onSelectCompany,
  companiesList
}) => {
  const [search, setSearch] = useState('');

  const filteredCompanies = companiesList.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <aside className="practice-sidebar">
      {/* Search Box */}
      <div className="practice-search-box">
        <input
          type="text"
          placeholder="Search Company..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Company & Category List */}
      <div className="practice-company-list">
        {/* 1. ★ Top 150 Interview Qs (Yellow) */}
        <div
          className={`practice-company-item ${selectedMode === 'top150' ? 'active' : ''}`}
          style={{ border: '1px solid #fbbf24' }}
          onClick={() => onSelectMode('top150')}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '20px', height: '20px', background: '#fbbf24', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'black', fontWeight: 'bold', fontSize: '0.8rem' }}>
              ★
            </div>
            <span style={{ color: '#fbbf24', fontWeight: 'bold' }}>Top 150 Interview Qs</span>
          </div>
          <span className="practice-count-tag" style={{ background: '#fbbf24', color: 'black', fontWeight: 'bold' }}>
            150
          </span>
        </div>

        {/* 2. All Questions (Master) (Purple) */}
        <div
          className={`practice-company-item ${selectedMode === 'all_questions' ? 'active' : ''}`}
          style={{ border: '1px solid #a855f7' }}
          onClick={() => onSelectMode('all_questions')}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '20px', height: '20px', background: '#a855f7', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold', fontSize: '1rem' }}>
              ∞
            </div>
            <span style={{ color: '#a855f7', fontWeight: 'bold' }}>All Questions</span>
          </div>
          <span className="practice-count-tag" style={{ background: '#a855f7', color: 'white', fontWeight: 'bold' }}>
            Master
          </span>
        </div>

        {/* 3. Companies List with Authentic Logos */}
        {filteredCompanies.map(c => {
          const isSelected = selectedMode === 'company' && selectedCompany.toLowerCase() === c.name.toLowerCase();
          return (
            <div
              key={c.name}
              className={`practice-company-item ${isSelected ? 'active' : ''}`}
              onClick={() => onSelectCompany(c.name)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <CompanyLogo name={c.name} size={20} />
                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '170px' }}>
                  {c.name}
                </span>
              </div>
              <span className="practice-count-tag">{c.count}</span>
            </div>
          );
        })}
      </div>
    </aside>
  );
};
