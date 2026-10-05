import React from 'react';
import { BigCompanyItem } from '../../data/bigCompaniesData';
import { getCompanyLogoData } from '../../utils/companyLogos';

interface CompanyCardProps {
  company: BigCompanyItem;
}

export const CompanyCard: React.FC<CompanyCardProps> = ({ company }) => {
  const logo = getCompanyLogoData(company.name);

  // Badge class by type
  const typeLower = (company.type || '').toLowerCase();
  let tagClass = 'tag-product';
  if (typeLower.includes('fintech')) tagClass = 'tag-fintech';
  else if (typeLower.includes('service')) tagClass = 'tag-service';
  else if (typeLower.includes('saas')) tagClass = 'tag-saas';
  else if (typeLower.includes('deeptech') || typeLower.includes('ai')) tagClass = 'tag-deeptech';

  return (
    <div className="bigcompany-card">
      <div className="bigcompany-top">
        {/* Logo */}
        <img
          src={logo.google}
          alt={company.name}
          className="bigcompany-logo"
          onError={(e) => {
            (e.target as HTMLImageElement).src = logo.clearbit;
          }}
        />

        <div className="bigcompany-title-row">
          <div className="bigcompany-name">{company.name}</div>
          <span className={`bigcompany-tag ${tagClass}`}>
            ⚡ {company.type}
          </span>
        </div>
      </div>

      {/* Role */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#cbd5e1', fontSize: '0.88rem' }}>
        <span>💼</span>
        <span>{company.role}</span>
      </div>

      {/* Location */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '0.88rem' }}>
        <span>📍</span>
        <span>{company.location}</span>
      </div>

      {/* Salary in Gold */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ color: '#fbbf24' }}>💰</span>
        <span className="bigcompany-salary">{company.salary}</span>
      </div>

      {/* View & Apply Button */}
      <a
        href={company.url}
        target="_blank"
        rel="noopener noreferrer"
        className="bigcompany-btn"
      >
        View & Apply
      </a>
    </div>
  );
};
