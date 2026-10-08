import React from 'react';
import { ArrowUpRight, BriefcaseBusiness, Building2, Landmark, MapPin } from 'lucide-react';
import { BigCompanyItem } from '../../data/bigCompaniesData';
import { CompanyLogo } from '../common/CompanyLogo';

interface CompanyCardProps {
  company: BigCompanyItem;
}

export const CompanyCard: React.FC<CompanyCardProps> = ({ company }) => {
  // Refined badge classification by type
  const typeLower = (company.type || '').toLowerCase();
  let tagClass = 'tag-product';
  if (typeLower.includes('fintech')) tagClass = 'tag-fintech';
  else if (typeLower.includes('service')) tagClass = 'tag-service';
  else if (typeLower.includes('saas')) tagClass = 'tag-saas';
  else if (typeLower.includes('deeptech') || typeLower.includes('ai')) tagClass = 'tag-deeptech';
  else if (typeLower.includes('auto')) tagClass = 'tag-autotech';

  return (
    <div className="bigcompany-card">
      <div className="bigcompany-top">
        {/* Logo with high-contrast white rounded backing */}
        <CompanyLogo 
          name={company.name} 
          size={46} 
          style={{ borderRadius: 12, background: '#ffffff', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.18)' }} 
        />

        <div className="bigcompany-title-row">
          <div className="bigcompany-name" title={company.name}>{company.name}</div>
          <span className={`bigcompany-tag ${tagClass}`}>
            <span className="tag-pulse-dot" aria-hidden="true" />
            <Building2 size={11} aria-hidden="true" />
            <span>{company.type}</span>
          </span>
        </div>
      </div>

      {/* Role */}
      <div className="bigcompany-meta-item">
        <BriefcaseBusiness size={14} className="meta-icon" aria-hidden="true" />
        <span className="meta-text">{company.role}</span>
      </div>

      {/* Location */}
      <div className="bigcompany-meta-item">
        <MapPin size={14} className="meta-icon" aria-hidden="true" />
        <span className="meta-text-muted">{company.location}</span>
      </div>

      {/* Salary in Luxury Gold */}
      <div className="bigcompany-salary-row">
        <Landmark size={14} className="salary-icon" aria-hidden="true" />
        <span className="bigcompany-salary">{company.salary}</span>
      </div>

      {/* Luxury Nested Action CTA (Button-in-Button Pattern) */}
      <a
        href={company.url}
        target="_blank"
        rel="noopener noreferrer"
        className="bigcompany-btn"
        aria-label={`View and apply at ${company.name}`}
      >
        <span className="btn-label">View & Apply</span>
        <span className="btn-icon-bubble">
          <ArrowUpRight size={14} className="btn-arrow" aria-hidden="true" />
        </span>
      </a>
    </div>
  );
};
