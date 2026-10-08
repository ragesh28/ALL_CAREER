import React, { useState } from 'react';
import { BriefcaseBusiness, CalendarDays, Mail, MapPin, Phone, Route, Send } from 'lucide-react';
import { Job } from '../../types/jobs';
import { getCompanyLogoData, getPortalLogo, formatAuthenticDate, formatWalkinDate, detectPortalInfo } from '../../utils/companyLogos';
import { getJobWalkinDates, isWalkinJob } from '../../utils/filterUtils';

interface JobCardProps {
  job: Job;
  index?: number;
  onSelectCompany?: (comp: string) => void;
}

export const AuthenticLogoBox: React.FC<{ company: string }> = ({ company }) => {
  const [stage, setStage] = useState<number>(0);
  const logo = getCompanyLogoData(company);

  return (
    <div className="logo-box">
      {stage === 0 && (
        <img
          src={logo.local || logo.unavatar}
          alt={company}
          className="company-logo"
          loading="lazy"
          decoding="async"
          onError={() => setStage(1)}
        />
      )}
      {stage === 1 && (
        <img
          src={logo.duckduckgo}
          alt={company}
          className="company-logo"
          loading="lazy"
          decoding="async"
          onError={() => setStage(2)}
        />
      )}
      {stage === 2 && (
        <img
          src={logo.google}
          alt={company}
          className="company-logo"
          loading="lazy"
          decoding="async"
          onError={() => setStage(3)}
        />
      )}
      {stage === 3 && (
        <img
          src={logo.clearbit}
          alt={company}
          className="company-logo"
          loading="lazy"
          decoding="async"
          onError={() => setStage(4)}
        />
      )}
      {stage >= 4 && (
        <div className="logo-fallback" style={{ display: 'flex' }}>
          {logo.initial}
        </div>
      )}
    </div>
  );
};

export const JobCard = React.memo<JobCardProps>(({ job, index, onSelectCompany }) => {
  const companyName = job.company || 'DIRECT RECRUITER';
  const portalInfo = detectPortalInfo(job);

  const rawLoc = (job.location || '').trim();
  const hasLoc = rawLoc && !['nan', 'none', 'null'].includes(rawLoc.toLowerCase());
  const cityLoc = hasLoc ? rawLoc.split(',')[0].trim() : 'India';

  const exp = job.experience;
  const isWalkin = isWalkinJob(job);
  const rawDate = job.date || (job as any).date_posted || (job as any).posted || (job as any).fetchedAt || '';
  const walkinDate = getJobWalkinDates(job)[0] || job.walkin_date || rawDate;
  const dateStr = isWalkin ? formatWalkinDate(walkinDate, rawDate) : formatAuthenticDate(rawDate);
  const cleanTitle = job.title || job.role || 'Position';
  const applyUrl = job.url || (job as any).apply_url || job.telegram_url || job.flyer_image_url || '';

  const isDirectSpecialSource =
    portalInfo.id === 'telegram_message' ||
    portalInfo.id === 'telegram_post' ||
    portalInfo.id === 'telegram' ||
    portalInfo.id === 'google_images';

  return (
    <div className="job-card" style={index !== undefined ? { animationDelay: `${(index % 30) * 0.03}s` } : undefined}>
      <div className="card-top">
        <AuthenticLogoBox company={companyName} />
        <div className="card-info">
          <div
            className="company-name"
            onClick={() => onSelectCompany && onSelectCompany(companyName)}
            style={{ cursor: onSelectCompany ? 'pointer' : 'default' }}
            title={`Filter jobs by ${companyName}`}
          >
            {companyName}
          </div>
          <div className="job-title" title={cleanTitle}>
            {cleanTitle}
          </div>
        </div>

        {/* Top Source Badge: ONLY for Telegram Messages (unique direct URL viewable without login) and Google Images (flyer link) */}
        {isDirectSpecialSource && portalInfo.logo ? (
          portalInfo.url ? (
            <a
              href={portalInfo.url}
              target="_blank"
              rel="noopener noreferrer"
              className={`top-source-badge src-${portalInfo.id}`}
              title={
                portalInfo.id.includes('telegram')
                  ? 'View original Telegram message (no login required)'
                  : 'View original Flyer / Image link'
              }
              onClick={e => e.stopPropagation()}
            >
              <img
                src={portalInfo.logo}
                alt={portalInfo.label}
                className="top-source-logo"
                loading="lazy"
                decoding="async"
                onError={e => (e.currentTarget.style.display = 'none')}
              />
              <span className="top-source-name">{portalInfo.label}</span>
            </a>
          ) : (
            <div className={`top-source-badge src-${portalInfo.id}`} title={portalInfo.label}>
              <img
                src={portalInfo.logo}
                alt={portalInfo.label}
                className="top-source-logo"
                loading="lazy"
                decoding="async"
                onError={e => (e.currentTarget.style.display = 'none')}
              />
              <span className="top-source-name">{portalInfo.label}</span>
            </div>
          )
        ) : null}
      </div>

      <div className="job-meta">
        <div className="meta-row">
          <div className="meta-badge loc"><MapPin size={13} aria-hidden="true" />{cityLoc}</div>
          {exp && <div className="meta-badge exp"><BriefcaseBusiness size={13} aria-hidden="true" />{exp}</div>}
        </div>

        <div className="meta-row">
          {isWalkin ? (
            <div className="meta-badge walkin-date-badge" title="Walk-in Interview Drive">
              <Route size={13} aria-hidden="true" />
              <span>Walk-in: {dateStr}</span>
            </div>
          ) : (
            dateStr && (
              <div className="meta-badge date" title={`Posted: ${dateStr}`}>
                <CalendarDays size={13} aria-hidden="true" />
                <span>{dateStr}</span>
              </div>
            )
          )}
          <div className="meta-badge" style={{ color: 'var(--text-main)', borderColor: 'var(--border)' }}>
            {portalInfo.label ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                {portalInfo.logo && (
                  <img
                    src={portalInfo.logo}
                    alt=""
                    className="portal-logo"
                    loading="lazy"
                    decoding="async"
                    onError={e => (e.currentTarget.style.display = 'none')}
                  />
                )}
                <span>{portalInfo.label}</span>
              </span>
            ) : (
              'Direct Apply'
            )}
          </div>
        </div>
      </div>

      <div className="card-footer">
        <span className="card-role" title={cleanTitle}>
          {cleanTitle}
        </span>
        {applyUrl ? (
          <a
            href={applyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="apply-btn"
          >
            <Send size={13} aria-hidden="true" /> Apply
          </a>
        ) : null}
        {isWalkin && job.contact_phone ? (
          <a className="contact-action contact-call" href={`tel:${job.contact_phone}`} title={`Call ${job.contact_phone}`}>
            <Phone size={13} aria-hidden="true" /> Call
          </a>
        ) : null}
        {isWalkin && job.contact_email ? (
          <a className="contact-action contact-email" href={`mailto:${job.contact_email}`} title={`Email ${job.contact_email}`}>
            <Mail size={13} aria-hidden="true" /> Email
          </a>
        ) : null}
      </div>
    </div>
  );
});
