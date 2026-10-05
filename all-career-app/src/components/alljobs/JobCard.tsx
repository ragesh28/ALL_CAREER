import React, { useState } from 'react';
import { Job } from '../../types/jobs';
import { getCompanyLogoData, getPortalLogo } from '../../utils/companyLogos';
import { isWalkinJob } from '../../utils/filterUtils';

interface JobCardProps {
  job: Job;
  index?: number;
  onSelectCompany?: (comp: string) => void;
}

export const JobCard: React.FC<JobCardProps> = ({ job, onSelectCompany }) => {
  const [logoStage, setLogoStage] = useState<number>(0);
  const companyName = job.company || 'DIRECT RECRUITER';
  const logo = getCompanyLogoData(companyName);
  const portalLogo = getPortalLogo(job.source);

  const rawLoc = (job.location || '').trim();
  const hasLoc = rawLoc && !['nan', 'none', 'null'].includes(rawLoc.toLowerCase());
  const cityLoc = hasLoc ? rawLoc.split(',')[0].trim() : 'Delhi';

  const exp = job.experience || '0-2 Yrs';
  const isWalkin = isWalkinJob(job);
  const displayDate = (() => {
    const raw = (job.walkin_date && job.walkin_date !== 'Today') 
      ? job.walkin_date 
      : (job.date || (job as any).date_posted || (job as any).posted || '');
    if (!raw || raw === 'Today') return 'Today';
    
    // Check if ISO: 2026-09-22
    const isoMatch = String(raw).match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/);
    if (isoMatch) {
      const year = isoMatch[1];
      const month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][parseInt(isoMatch[2], 10) - 1];
      const day = parseInt(isoMatch[3], 10);
      return `${month} ${day}, ${year}`;
    }

    const d = new Date(raw);
    if (!isNaN(d.getTime())) {
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
    return raw;
  })();
  const dateStr = displayDate;
  const source = job.source || 'Naukri';
  const cleanTitle = job.title || job.role || 'Position';
  const applyUrl = job.url || job.telegram_url || job.flyer_image_url || '#';

  // Distinct colors for letter logos like in Screenshot 3 (teal, cyan, amber, etc.)
  const letterColors = [
    'linear-gradient(135deg, #0d9488, #14b8a6)', // Teal (V)
    'linear-gradient(135deg, #0284c7, #38bdf8)', // Cyan (T)
    'linear-gradient(135deg, #0f766e, #2dd4bf)', // Dark teal (M)
    'linear-gradient(135deg, #0891b2, #06b6d4)', // Blue cyan (K)
    'linear-gradient(135deg, #059669, #10b981)'  // Green (B)
  ];
  const charCode = (companyName.charCodeAt(0) || 65) % letterColors.length;
  const letterBg = letterColors[charCode];

  return (
    <div className="job-card">
      <div className="card-top">
        {/* Square logo box with fallback */}
        <div className="logo-box">
          {logoStage === 0 ? (
            <img 
              src={logo.clearbit} 
              alt={companyName} 
              className="company-logo" 
              onError={() => setLogoStage(1)} 
            />
          ) : logoStage === 1 ? (
            <img 
              src={logo.google} 
              alt={companyName} 
              className="company-logo" 
              onError={() => setLogoStage(2)} 
            />
          ) : (
            <div className="logo-letter" style={{ background: letterBg }}>
              {logo.initial}
            </div>
          )}
        </div>

        {/* Company & Title info */}
        <div className="card-info">
          <div 
            className="company-name"
            onClick={() => onSelectCompany && onSelectCompany(companyName)}
            style={{ cursor: onSelectCompany ? 'pointer' : 'default', transition: 'color 0.2s' }}
            title={`Filter jobs by ${companyName}`}
          >
            {companyName}
          </div>
          <div className="job-title" title={cleanTitle}>{cleanTitle}</div>
        </div>
      </div>

      {/* Meta rows matching Screenshot 3 */}
      <div className="job-meta">
        <div className="meta-row">
          <div className="meta-badge loc">
            <span>📍</span>
            <span>{cityLoc}</span>
          </div>
          <div className="meta-badge exp">
            <span>💼</span>
            <span>{exp}</span>
          </div>
        </div>

        <div className="meta-row">
          <div className="meta-badge date">
            <span>{isWalkin ? '🚶' : '🕒'}</span>
            <span>{dateStr}</span>
          </div>
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
            <span style={{ textTransform: 'capitalize' }}>{source}</span>
          </div>
        </div>
      </div>

      {/* Card Footer with Apply button */}
      <div className="card-footer">
        <div></div>
        <a 
          href={applyUrl} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="apply-btn"
        >
          Apply →
        </a>
      </div>
    </div>
  );
};
