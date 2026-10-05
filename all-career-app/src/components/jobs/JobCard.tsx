import React, { useState } from 'react';
import { Job } from '../../types/jobs';
import { getCompanyLogoData, getPortalLogo } from '../../utils/companyLogos';

interface JobCardProps {
  job: Job;
  index?: number;
}

export const JobCard: React.FC<JobCardProps> = ({ job, index = 0 }) => {
  const [logoStage, setLogoStage] = useState<number>(0);
  const logo = getCompanyLogoData(job.company || 'Job');
  const portalLogo = getPortalLogo(job.source);

  const rawLoc = (job.location || '').trim();
  const hasLoc = rawLoc && !['nan', 'none', 'null'].includes(rawLoc.toLowerCase());
  const cityLoc = hasLoc ? rawLoc.split(',')[0].trim() : '';

  const isWalkin = Boolean(
    job.walkin_date || 
    (job.walkin_dates && job.walkin_dates.length > 0) || 
    (job.title && /walk-?in/i.test(job.title)) ||
    (job.category === 'walkin')
  );

  const walkinDate = (job.walkin_dates && job.walkin_dates.length > 0)
    ? job.walkin_dates.join(' – ')
    : (job.walkin_date || 'Upcoming');

  const source = job.source || 'Portal';
  const cleanTitle = job.title || job.role || 'Career Opportunity';

  // Construct max 3 action buttons
  const buttons: React.ReactNode[] = [];

  const mainUrl = job.url || job.telegram_url || job.flyer_image_url;
  if (mainUrl && mainUrl.startsWith('http')) {
    buttons.push(
      <a
        key="apply"
        href={mainUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="apply-btn"
        title="Open Application"
      >
        Apply →
      </a>
    );
  }

  const mail = job.contact_email || (job.url?.startsWith('mailto:') ? job.url.replace('mailto:', '') : '');
  if (mail) {
    buttons.push(
      <a
        key="mail"
        href={`mailto:${mail}`}
        className="apply-btn"
        style={{ background: 'linear-gradient(135deg, #0ea5e9, #0284c7)', color: '#fff', borderColor: 'transparent' }}
        title="Send Direct Email"
      >
        ✉️ Email
      </a>
    );
  }

  const phone = job.contact_phone;
  if (phone) {
    const cleanPhone = phone.replace(/[^\d+]/g, '');
    if (cleanPhone) {
      buttons.push(
        <a
          key="call"
          href={`tel:${cleanPhone}`}
          className="apply-btn"
          style={{ background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff', borderColor: 'transparent' }}
          title="Direct Call / WhatsApp"
        >
          📞 Call / WA
        </a>
      );
    }
  }

  // Strictly maximum 3 buttons
  const displayButtons = buttons.slice(0, 3);

  const handleLogoError = () => {
    setLogoStage(prev => prev + 1);
  };

  return (
    <div 
      className="job-card normal-job" 
      style={{ animationDelay: `${Math.min(index * 0.02, 0.4)}s` }}
    >
      <div className="card-top">
        {/* Company Logo with fallback */}
        <div className="logo-box">
          {logoStage === 0 ? (
            <img 
              src={logo.clearbit} 
              alt={job.company} 
              className="company-logo" 
              onError={handleLogoError} 
            />
          ) : (
            <div className="logo-fallback" style={{ display: 'flex' }}>
              {logo.initial}
            </div>
          )}
        </div>

        {/* Company & Title info */}
        <div className="card-info">
          <span className="company-name" title={job.company}>{job.company || 'Verified Recruiter'}</span>
          <span className="job-title" title={cleanTitle}>{cleanTitle}</span>
        </div>
      </div>

      {/* Walk-in badge */}
      {isWalkin && (
        <div className="walkin-badge">
          🚶 Walk-in: {walkinDate}
        </div>
      )}

      {/* Meta rows */}
      <div className="job-meta">
        <div className="meta-row">
          {cityLoc && (
            <div className="meta-badge loc" title={`Location: ${rawLoc}`}>
              <span className="meta-icon">📍</span>
              <span>{cityLoc}</span>
            </div>
          )}
          {job.experience && (
            <div className="meta-badge exp" title={`Experience: ${job.experience}`}>
              <span className="meta-icon">💼</span>
              <span>{job.experience}</span>
            </div>
          )}
        </div>

        <div className="meta-row">
          {job.date && (
            <div className="meta-badge date" title={`Posted: ${job.date}`}>
              <span className="meta-icon">🕒</span>
              <span>{job.date}</span>
            </div>
          )}
          {source && (
            <div className="portal-badge" title={`Source: ${source}`}>
              {portalLogo ? (
                <img
                  src={portalLogo}
                  alt={source}
                  className="portal-logo"
                  style={{ width: 14, height: 14, objectFit: 'contain', borderRadius: 2 }}
                  onError={e => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              ) : (
                <span style={{ fontSize: '0.72rem', color: '#38bdf8' }}>⚡</span>
              )}
              <span className="capitalize">{source}</span>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="card-footer">
        <span className="card-role" title={job.role_search || job.category || ''}>
          {job.role_search || job.category || 'Direct'}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'nowrap' }}>
          {displayButtons}
        </div>
      </div>
    </div>
  );
};
