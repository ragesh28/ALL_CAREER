import React, { useState, useMemo } from 'react';
import { GlobalLogoPill } from '../common/GlobalLogoPill';
import { CompanyCard } from './CompanyCard';
import { bigCompaniesData } from '../../data/bigCompaniesData';

interface BigCompanyViewProps {
  onGoHub: () => void;
}

export const BigCompanyView: React.FC<BigCompanyViewProps> = ({ onGoHub }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [locationFilter, setLocationFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [sortBy, setSortBy] = useState('default');

  const filteredCompanies = useMemo(() => {
    return bigCompaniesData.filter(c => {
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchName = c.name.toLowerCase().includes(term);
        const matchRole = c.role.toLowerCase().includes(term);
        if (!matchName && !matchRole) return false;
      }

      if (locationFilter !== 'all') {
        if (!c.location.toLowerCase().includes(locationFilter.toLowerCase())) return false;
      }

      if (typeFilter !== 'all') {
        if (c.type.toLowerCase() !== typeFilter.toLowerCase()) return false;
      }

      return true;
    });
  }, [searchTerm, locationFilter, typeFilter, sortBy]);

  return (
    <div className="bigcompany-page">
      {/* Top-left Global Logo Pill */}
      <GlobalLogoPill onGoHome={onGoHub} />

      {/* Screenshot 5: Glowing Header */}
      <div className="bigcompany-header">
        <h1 onClick={onGoHub}>ALL_CAREER</h1>
      </div>

      {/* Screenshot 5: Sticky Glass Bar */}
      <div className="sticky-container">
        <div className="glass-bar">
          {/* Search Input */}
          <input
            type="text"
            placeholder="Search..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />

          {/* Location Select */}
          <select value={locationFilter} onChange={e => setLocationFilter(e.target.value)}>
            <option value="all">Location: All</option>
            <option value="bengaluru">Bengaluru</option>
            <option value="chennai">Chennai</option>
            <option value="remote">Remote</option>
            <option value="pan-india">Pan-India</option>
          </select>

          {/* Type Select */}
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
            <option value="all">Type: All</option>
            <option value="product">Product</option>
            <option value="fintech">Fintech</option>
            <option value="saas">SaaS</option>
            <option value="deeptech">DeepTech</option>
            <option value="service">Service</option>
          </select>

          {/* Sort Select */}
          <select value={sortBy} onChange={e => setSortBy(e.target.value)}>
            <option value="default">Sort: Default</option>
            <option value="salary">Salary: High to Low</option>
            <option value="name">Company Name</option>
          </select>

          {/* Count Badge */}
          <div className="glass-count-badge">
            {filteredCompanies.length}
          </div>

          {/* Hub Button */}
          <button 
            onClick={onGoHub}
            className="btn-hub-nav"
            style={{ borderRadius: '20px', padding: '8px 16px' }}
          >
            Hub
          </button>
        </div>
      </div>

      {/* Cards Grid */}
      <div className="bigcompany-grid">
        {filteredCompanies.map(c => (
          <CompanyCard key={c.id} company={c} />
        ))}
      </div>
    </div>
  );
};
