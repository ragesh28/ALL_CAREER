import React, { useState, useMemo } from 'react';
import { Building2, MapPin, Search, SlidersHorizontal } from 'lucide-react';
import { GlobalLogoPill } from '../common/GlobalLogoPill';
import { CompanyCard } from './CompanyCard';
import { CustomDropdown, DropdownOption } from '../common/CustomDropdown';
import { bigCompaniesData } from '../../data/bigCompaniesData';

interface BigCompanyViewProps {
  onGoHub: () => void;
  title?: string;
}

const LOCATION_OPTIONS: DropdownOption[] = [
  { value: 'all', label: 'All Locations' },
  { value: 'bengaluru', label: 'Bengaluru' },
  { value: 'chennai', label: 'Chennai' },
  { value: 'remote', label: 'Remote' },
  { value: 'pan-india', label: 'Pan-India' },
];

const TYPE_OPTIONS: DropdownOption[] = [
  { value: 'all', label: 'All Types' },
  { value: 'product', label: 'Product' },
  { value: 'fintech', label: 'Fintech' },
  { value: 'saas', label: 'SaaS' },
  { value: 'deeptech', label: 'DeepTech' },
  { value: 'service', label: 'Service' },
];

const SORT_OPTIONS: DropdownOption[] = [
  { value: 'default', label: 'Default' },
  { value: 'salary', label: 'Salary: High to Low' },
  { value: 'name', label: 'Company Name' },
];

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

      {/* Sticky Glass Bar with Spacious Responsive Controls */}
      <div className="sticky-container">
        <div className="glass-bar">
          {/* Search Input with Integrated Icon */}
          <div className="directory-search-wrapper">
            <Search size={15} className="directory-search-icon" aria-hidden="true" />
            <input
              type="text"
              placeholder="Search companies, roles..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              aria-label="Search companies"
            />
          </div>

          {/* Location Custom Dropdown */}
          <CustomDropdown
            id="filter-location"
            className="filter-location"
            value={locationFilter}
            onChange={setLocationFilter}
            options={LOCATION_OPTIONS}
            icon={<MapPin size={14} className="control-icon" aria-hidden="true" />}
            prefix="Location"
            ariaLabel="Filter by location"
          />

          {/* Type Custom Dropdown */}
          <CustomDropdown
            id="filter-type"
            className="filter-type"
            value={typeFilter}
            onChange={setTypeFilter}
            options={TYPE_OPTIONS}
            icon={<Building2 size={14} className="control-icon" aria-hidden="true" />}
            prefix="Type"
            ariaLabel="Filter by company type"
          />

          {/* Sort Custom Dropdown */}
          <CustomDropdown
            id="filter-sort"
            className="filter-sort"
            value={sortBy}
            onChange={setSortBy}
            options={SORT_OPTIONS}
            icon={<SlidersHorizontal size={14} className="control-icon" aria-hidden="true" />}
            prefix="Sort"
            ariaLabel="Sort companies"
          />

          {/* Count Badge */}
          <div className="glass-count-badge">
            {filteredCompanies.length}
          </div>
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
