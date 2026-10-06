import React, { useState, useMemo } from 'react';
import { Building2, MapPin, SlidersHorizontal } from 'lucide-react';
import { GlobalLogoPill } from '../common/GlobalLogoPill';
import { CompanyCard } from './CompanyCard';
import { bigCompaniesData } from '../../data/bigCompaniesData';

interface BigCompanyViewProps {
  onGoHub: () => void;
  title?: string;
}

export const BigCompanyView: React.FC<BigCompanyViewProps> = ({ onGoHub, title = 'Big Company Name List' }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [locationFilter, setLocationFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [sortBy, setSortBy] = useState('default');

  const filteredCompanies = useMemo(() => {
    const companies = bigCompaniesData.filter(c => {
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

    return [...companies].sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      if (sortBy === 'salary') return parseFloat(b.salary.replace(/[^0-9.]/g, '')) - parseFloat(a.salary.replace(/[^0-9.]/g, ''));
      return 0;
    });
  }, [searchTerm, locationFilter, typeFilter, sortBy]);

  return (
    <div className="bigcompany-page">
      {/* Top-left Global Logo Pill */}
      <GlobalLogoPill onGoHome={onGoHub} />

      {/* Glowing Header */}
      <div className="bigcompany-header">
        <h1 onClick={onGoHub}>{title}</h1>
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
          <label className="directory-filter-control">
            <MapPin size={14} aria-hidden="true" />
            <select value={locationFilter} onChange={e => setLocationFilter(e.target.value)} aria-label="Filter by location">
            <option value="all">Location: All</option>
            <option value="bengaluru">Bengaluru</option>
            <option value="chennai">Chennai</option>
            <option value="remote">Remote</option>
            <option value="pan-india">Pan-India</option>
            </select>
          </label>

          {/* Type Select */}
          <label className="directory-filter-control">
            <Building2 size={14} aria-hidden="true" />
            <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} aria-label="Filter by company type">
            <option value="all">Type: All</option>
            <option value="product">Product</option>
            <option value="fintech">Fintech</option>
            <option value="saas">SaaS</option>
            <option value="deeptech">DeepTech</option>
            <option value="service">Service</option>
            </select>
          </label>

          {/* Sort Select */}
          <label className="directory-filter-control">
            <SlidersHorizontal size={14} aria-hidden="true" />
            <select value={sortBy} onChange={e => setSortBy(e.target.value)} aria-label="Sort companies">
            <option value="default">Sort: Default</option>
            <option value="salary">Salary: High to Low</option>
            <option value="name">Company Name</option>
            </select>
          </label>

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
