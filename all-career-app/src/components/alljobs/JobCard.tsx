import React, { useState, useEffect, useMemo, useRef, useId } from 'react';
import { BriefcaseBusiness, CalendarDays, Mail, MapPin, Phone, Route, Send } from 'lucide-react';
import { Job } from '../../types/jobs';
import { COMPANY_SITE_ICONS, getCompanyLogoData, formatAuthenticDate, formatWalkinDate, detectPortalInfo } from '../../utils/companyLogos';
import { classifyJobCategory, getJobWalkinDates, isWalkinJob } from '../../utils/filterUtils';

interface JobCardProps {
  job: Job;
  index?: number;
  onSelectCompany?: (comp: string) => void;
}

function imageUrl(value: unknown, base = window.location.href): string {
  if (typeof value !== 'string' || !value.trim()) return '';
  try {
    const url = new URL(value, base);
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : '';
  } catch {
    return '';
  }
}

function structuredLogo(value: unknown, pageUrl: string): string[] {
  if (Array.isArray(value)) return value.flatMap(entry => structuredLogo(entry, pageUrl));
  if (!value || typeof value !== 'object') return [];
  const entry = value as { hiringOrganization?: { logo?: Job['company_logo'] }; '@graph'?: unknown };
  const logo = entry.hiringOrganization?.logo;
  const url = imageUrl(typeof logo === 'string' ? logo : logo?.url || logo?.contentUrl, pageUrl);
  return [url, ...structuredLogo(entry['@graph'], pageUrl)].filter(Boolean);
}

export const AuthenticLogoBox: React.FC<{ company: string; job?: Job }> = ({ company, job }) => (
  <JobLogo key={JSON.stringify([company, job?.company_logo, job?.company_website, job?.url])} company={company} job={job} />
);

function JobLogo({ company, job }: { company: string; job?: Job }) {
  const [stage, setStage] = useState(0);
  const [loadedSource, setLoadedSource] = useState('');
  const [discovered, setDiscovered] = useState<string[] | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const logo = getCompanyLogoData(company);
  const jobUrl = imageUrl(job?.url);
  const websiteValue = typeof job?.company_website === 'string' ? job.company_website.trim() : '';
  const website = websiteValue ? imageUrl(websiteValue.includes('://') ? websiteValue : 'https://' + websiteValue) : '';
  const websiteDomain = website ? new URL(website).hostname : '';
  const domain = logo.domain || websiteDomain;
  const jobLogo = job?.company_logo;
  const suppliedLogo = imageUrl(typeof jobLogo === 'string' ? jobLogo : jobLogo?.url || jobLogo?.contentUrl, jobUrl || undefined);
  const candidates = useMemo(() => [...new Set([
    imageUrl(logo.local),
    suppliedLogo,
    COMPANY_SITE_ICONS[domain],
    domain ? 'https://www.google.com/s2/favicons?domain=' + encodeURIComponent(domain) + '&sz=128' : '',
    domain ? 'https://icons.duckduckgo.com/ip3/' + encodeURIComponent(domain) + '.ico' : '',
    domain ? 'https://unavatar.io/' + encodeURIComponent(domain) + '?fallback=false' : '',
    ...(discovered ?? []),
  ].filter(Boolean))], [logo.local, suppliedLogo, domain, discovered]);
  const source = candidates[stage];
  const showImage = Boolean(source && source === loadedSource);

  useEffect(() => {
    if (source || !jobUrl || discovered !== null || !box.current) return;

    const controller = new AbortController();
    let timeout: ReturnType<typeof setTimeout> | undefined;
    const discover = async () => {
      timeout = setTimeout(() => controller.abort(), 4000);
      try {
        const response = await fetch(jobUrl, { signal: controller.signal });
        const html = response.ok ? await response.text() : '';
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const found: string[] = [];
        for (const script of doc.querySelectorAll('script[type="application/ld+json"]')) {
          try {
            found.push(...structuredLogo(JSON.parse(script.textContent || ''), response.url || jobUrl));
          } catch { /* A page can contain unrelated or malformed structured data. */ }
        }
        if (!controller.signal.aborted) setDiscovered(found);
      } catch {
        if (!controller.signal.aborted) setDiscovered([]);
      } finally {
        clearTimeout(timeout);
      }
    };

    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        observer.disconnect();
        void discover();
      }
    }, { rootMargin: '160px' });
    observer.observe(box.current);
    return () => {
      observer.disconnect();
      clearTimeout(timeout);
      controller.abort();
    };
  }, [source, jobUrl, discovered]);

  return (
    <div className="logo-box job-logo-box" ref={box}>
      {!showImage && <div className="logo-fallback" aria-hidden="true">?</div>}
      {source && (
        <img
          key={source}
          src={source}
          alt=""
          className="company-logo job-logo-image"
          style={{ opacity: showImage ? 1 : 0 }}
          loading="lazy"
          decoding="async"
          onLoad={event => {
            if (event.currentTarget.naturalWidth > 1) setLoadedSource(source);
            else setStage(stage + 1);
          }}
          onError={() => setStage(stage + 1)}
        />
      )}
    </div>
  );
}

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

  const category = job._normCategory || classifyJobCategory(job);
  const phoneDialog = useRef<HTMLDialogElement>(null);
  const phoneHeadingId = useId();
  const phoneNumbers = isWalkin ? String(job.contact_phone ?? '')
    .split(/[,;|/\n]+/)
    .map(number => number.trim())
    .filter(number => {
      const digits = number.replace(/\D/g, '');
      return digits.length >= 7 && digits.length <= 15;
    }) : [];
  const phone = phoneNumbers[0];
  const dialNumber = phone ? (phone.startsWith('+') ? '+' : '') + phone.replace(/\D/g, '') : '';
  const email = isWalkin ? job.contact_email : undefined;

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

      <div className="card-footer job-card-footer">
        <span className="card-role" title={category}>{category}</span>
        {(applyUrl || phone || email) && (
          <div className="job-card-actions">
            {phone && email && (
              <a className="contact-action contact-email job-email-icon" href={'mailto:' + email} aria-label="Email recruiter" title="Email recruiter">
                <Mail size={15} aria-hidden="true" />
              </a>
            )}
            {applyUrl ? (
              <a href={applyUrl} target="_blank" rel="noopener noreferrer" className="apply-btn job-action">
                <Send size={13} aria-hidden="true" /> Apply
              </a>
            ) : isWalkin && <span className="job-action-space" aria-hidden="true" />}
            {phone ? (
              <>
                <button type="button" className="contact-action contact-call job-action call-desktop" onClick={() => phoneDialog.current?.showModal()} aria-haspopup="dialog">
                  <Phone size={13} aria-hidden="true" /> Call
                </button>
                <a className="contact-action contact-call job-action call-mobile" href={'tel:' + dialNumber}>
                  <Phone size={13} aria-hidden="true" /> Call
                </a>
              </>
            ) : email ? (
              <a className="contact-action contact-email job-action" href={'mailto:' + email}>
                <Mail size={13} aria-hidden="true" /> Email
              </a>
            ) : isWalkin && <span className="job-action-space" aria-hidden="true" />}
          </div>
        )}
      </div>
      {phone && (
        <dialog className="job-phone-dialog" ref={phoneDialog} aria-labelledby={phoneHeadingId}>
          <h2 id={phoneHeadingId}>Walk-in contact</h2>
          <p>{companyName}</p>
          <ul>{phoneNumbers.map((number, index) => <li key={number + index}>{number}</li>)}</ul>
          <form method="dialog">
            <button type="submit" autoFocus>Close</button>
          </form>
        </dialog>
      )}
    </div>
  );
});
