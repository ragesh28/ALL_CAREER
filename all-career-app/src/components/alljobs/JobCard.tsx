import React, { useState, useEffect, useMemo } from 'react';
import { BriefcaseBusiness, CalendarDays, Mail, MapPin, Phone, Route, Send } from 'lucide-react';
import { Job } from '../../types/jobs';
import { getCompanyLogoData, getPortalLogo, formatAuthenticDate, formatWalkinDate, detectPortalInfo } from '../../utils/companyLogos';
import { getJobWalkinDates, isWalkinJob } from '../../utils/filterUtils';

interface JobCardProps {
  job: Job;
  index?: number;
  onSelectCompany?: (comp: string) => void;
}

export const AuthenticLogoBox: React.FC<{ company: string; job?: Job }> = ({ company, job }) => {
  const [stage, setStage] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [discovered, setDiscovered] = useState<string[]>([]);
  const logo = getCompanyLogoData(company);
  const record = job as any;
  const safe = (value: unknown): string => {
    if (typeof value !== 'string' || !value.trim()) return '';
    try { const url = new URL(value, window.location.href); return ['https:', 'http:'].includes(url.protocol) ? url.href : ''; } catch { return ''; }
  };
  const websiteValue = record?.company_website;
  const website = safe(typeof websiteValue === 'string' && !websiteValue.includes('://') ? `https://${websiteValue}` : websiteValue);
  const domain = website ? new URL(website).hostname : logo.domain;
  const candidates = useMemo(() => [...new Set([
    safe(logo.local), safe(record?.company_logo), ...discovered,
    domain ? `https://unavatar.io/${encodeURIComponent(domain)}?fallback=false` : '',
    domain ? `https://icons.duckduckgo.com/ip3/${encodeURIComponent(domain)}.ico` : '',
    domain ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=128` : ''
  ].filter(Boolean))], [company, record?.company_logo, domain, logo.local, discovered]);
  useEffect(() => { setStage(0); setLoaded(false); setDiscovered([]); }, [company, record?.company_logo, record?.company_website]);
  useEffect(() => {
    if (stage < candidates.length || !job?.url || discovered.length) return;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    const jobUrl = safe(job.url);
    if (!jobUrl) return () => clearTimeout(timeout);
    fetch(jobUrl, { signal: controller.signal }).then(r => r.ok ? r.text() : '').then(html => {
      if (!html) return;
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const found: string[] = [];
      for (const el of doc.querySelectorAll('script[type="application/ld+json"]')) {
        try {
          const visit = (value: any) => {
            if (!value || typeof value !== 'object') return;
            if (Array.isArray(value)) { value.forEach(visit); return; }
            const org = value.hiringOrganization;
            if (org && typeof org === 'object') {
              const raw = typeof org.logo === 'string' ? org.logo : org.logo?.url;
              if (typeof raw === 'string') { const u = new URL(raw, jobUrl); if (u.protocol === 'https:' || u.protocol === 'http:') found.push(u.href); }
            }
            if (value['@graph']) visit(value['@graph']);
          };
          visit(JSON.parse(el.textContent || ''));
        } catch { /* Ignore invalid structured data. */ }
      }
      if (found.length) { setDiscovered(found); setStage(0); }
    }).catch(() => {}).finally(() => clearTimeout(timeout));
    return () => { clearTimeout(timeout); controller.abort(); };
  }, [stage, candidates.length, job?.url, discovered.length]);
  useEffect(() => {
    if (loaded || stage >= candidates.length) return;
    const timeout = setTimeout(() => setStage(n => n + 1), 5000);
    return () => clearTimeout(timeout);
  }, [stage, candidates, loaded]);
  return <div className="logo-box">{stage < candidates.length ?
    <img key={candidates[stage]} src={candidates[stage]} alt={company} className="company-logo" loading="lazy" decoding="async" onLoad={e => { if (e.currentTarget.naturalWidth <= 1) setStage(n => n + 1); else setLoaded(true); }} onError={() => setStage(n => n + 1)} /> :
    <div className="logo-fallback" style={{ display: 'flex', fontWeight: 700, color: '#8ea4c9' }} aria-label={`${company} logo unavailable`}>?</div>}
  </div>;
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
  const walkinDates = job._walkinDatesList || getJobWalkinDates(job);
  let dateStr = '';
  if (isWalkin) {
    if (walkinDates && walkinDates.length === 1) {
      dateStr = walkinDates[0];
    } else if (walkinDates && walkinDates.length > 1) {
      dateStr = `${walkinDates[0]} – ${walkinDates[walkinDates.length - 1]}`;
    } else if (job.walkin_date) {
      dateStr = formatWalkinDate(job.walkin_date);
    } else {
      dateStr = 'Upcoming';
    }
  } else {
    dateStr = formatAuthenticDate(rawDate);
  }
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
        <AuthenticLogoBox company={companyName} job={job} />
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
