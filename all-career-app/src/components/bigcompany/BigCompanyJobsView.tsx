import React, { useState, useEffect, useMemo } from 'react';
import { BriefcaseBusiness, CalendarDays, History, Home, MapPin, RotateCcw, Search, Send, X } from 'lucide-react';
import { AuthenticLogoBox } from '../alljobs/JobCard';
import { ROLE_KEYWORDS } from '../../utils/filterUtils';
import { bridgeService } from '../../services/bridgeService';
import { resolveAssetUrl, fetchJsonWithFallback } from '../../utils/urlHelper';
import { STRING_THEORY_LOGO } from '../../utils/brandLogo';

interface BigCompanyJob {
  title: string;
  company: string;
  location: string;
  apply_url?: string;
  url?: string;
  posted?: string;
  fetched_at?: string;
  fetchedAt?: string;
  date?: string;
}

interface BigCompanyJobsViewProps {
  onGoHub: () => void;
}

// 39 Top Cities from big_company_jobs.html
const BIG_COMPANY_CITIES = [
  'Bangalore', 'Bengaluru', 'Chennai', 'Hyderabad', 'Mumbai', 'Delhi', 'Pune', 'Noida', 'Kolkata', 
  'Ahmedabad', 'Remote', 'Trivandrum', 'Kochi', 'Coimbatore', 'Jaipur', 'Lucknow', 'Indore', 
  'Nagpur', 'Bhubaneswar', 'Patna', 'Chandigarh', 'Guwahati', 'Visakhapatnam', 'Surat', 'Vadodara', 
  'Gurgaon', 'Ghaziabad', 'Faridabad', 'Thiruvananthapuram', 'Mangalore', 'Mysore', 'Trichy', 
  'Madurai', 'Bhopal', 'Nashik', 'Secunderabad', 'Guntur', 'Vijayawada', 'Warangal'
];

// Exact 84 Roles from big_company_jobs.html (Top 8 displayed initially + 76 more)
const BIG_COMPANY_ROLES = [
  // --- Technical Roles (IT & Engineering) ---
  'Software Engineer',
  'Software Developer',
  'Full Stack Developer',
  'Frontend Developer',
  'Backend Developer',
  'React Developer',
  'Java Developer',
  'Python Developer',
  'Node.js Developer',
  'Android Developer',
  'iOS Developer',
  'Mobile App Developer',
  'Data Analyst',
  'Data Scientist',
  'Data Engineer',
  'DevOps Engineer',
  'UI UX Designer',
  'QA Engineer',
  'QA Analyst',
  'QA Automation Engineer',
  'Test Automation Engineer',
  'SDET',
  'AI Engineer',
  'Machine Learning Engineer',
  'Cloud Engineer',
  'Cloud Architect',
  'AWS Engineer',
  'Azure Engineer',
  'Systems Administrator',
  'System Administrator',
  'Network Engineer',
  'Cybersecurity Analyst',
  'Cybersecurity Engineer',
  'Security Analyst',
  'Penetration Tester',
  'Database Administrator',
  'Flutter Developer',
  'React Native Developer',
  'Angular Developer',
  'Salesforce Developer',
  'SAP Consultant',
  'Blockchain Developer',
  'Game Developer',
  'Embedded Systems Engineer',
  'VLSI Engineer',
  'Hardware Engineer',
  'ETL Developer',
  'Business Intelligence Analyst',
  'Deep Learning Engineer',
  'NLP Engineer',
  'Site Reliability Engineer',
  'Software Architect',
  'Technical Lead',
  'Engineering Manager',

  // --- Business, Management & Product ---
  'Product Manager',
  'Project Manager',
  'Technical Project Manager',
  'Product Owner',
  'Scrum Master',
  'Business Analyst',
  'Business Development Executive',
  'Business Development Manager',
  'Sales Executive',
  'Sales Manager',

  // --- Non-Technical & HR ---
  'HR Executive',
  'HR Manager',
  'Technical Recruiter',
  'Talent Acquisition Specialist',
  'HR Business Partner',
  'Customer Support Executive',
  'Customer Success Manager',
  'Digital Marketer',
  'Digital Marketing Manager',
  'Product Marketing Manager',
  'SEO Specialist',
  'Content Writer',
  'Graphic Designer',
  'UX Researcher',
  'Technical Writer',
  'Operations Manager',
  'Video Editor',
  'Social Media Manager',
  'Pre-Sales Consultant',
  'IT Support Specialist'
];

const DATE_RANGES = [
  { id: 'all', label: 'All Time' },
  { id: '24h', label: 'Last 24 Hours' },
  { id: '3d', label: 'Last 3 Days' },
  { id: '7d', label: 'Last 7 Days' },
  { id: '15d', label: 'Last 15 Days' }
];

function formatDate(dateStr?: string) {
  if (!dateStr) return '';
  const clean = dateStr.replace(/[^a-zA-Z0-9\s-:,]/g, '').trim();
  const d = new Date(clean);
  if (isNaN(d.getTime())) return clean;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays > 1 && diffDays <= 7) return `${diffDays} days ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export const BigCompanyJobsView: React.FC<BigCompanyJobsViewProps> = ({ onGoHub }) => {
  const [jobs, setJobs] = useState<BigCompanyJob[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters state (strictly: Date Posted, Location, and Role Category only)
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDateFilter, setSelectedDateFilter] = useState('all');
  const [selectedLocations, setSelectedLocations] = useState<Set<string>>(new Set());
  const [selectedRoles, setSelectedRoles] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<'date' | 'company'>('date');
  const [currentPage, setCurrentPage] = useState(1);
  const JOBS_PER_PAGE = 50;

  // Search inside filter sections
  const [locSearch, setLocSearch] = useState('');
  const [roleSearch, setRoleSearch] = useState('');

  // Expand / collapse "+ more" states
  const [showMoreLocs, setShowMoreLocs] = useState(false);
  const [showMoreRoles, setShowMoreRoles] = useState(false);

  // Section toggle state (Accordion)
  const [openSections, setOpenSections] = useState({
    date: true,
    location: true,
    roles: true
  });

  const toggleSection = (s: keyof typeof openSections) => {
    setOpenSections(prev => ({ ...prev, [s]: !prev[s] }));
  };

  // Load jobs from /data/big_company_jobs.json
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        const data = await fetchJsonWithFallback<BigCompanyJob[]>('data/big_company_jobs.json', [
          'data/big_company_jobs.json',
          'workday_scraper/big_company_jobs.json'
        ]);
        if (data && isMounted && Array.isArray(data)) {
          setJobs(data);
          setLoading(false);
          return;
        }
      } catch (err) {
        console.warn('Local big_company_jobs.json fetch failed, trying remote fallback...', err);
      }

      // Fallback to GitHub raw if local not fetched
      try {
        const fbRes = await fetch('https://raw.githubusercontent.com/ragesh28/ALL_CAREER/main/data/big_company_jobs.json');
        if (fbRes.ok) {
          const data = await fbRes.json();
          if (isMounted && Array.isArray(data)) {
            setJobs(data);
          }
        }
      } catch (e) {
        console.error('All big company jobs sources failed:', e);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  // Filtered sub-lists for sidebar
  const filteredLocs = useMemo(() => {
    if (!locSearch) return BIG_COMPANY_CITIES;
    return BIG_COMPANY_CITIES.filter(c => c.toLowerCase().includes(locSearch.toLowerCase()));
  }, [locSearch]);

  const visibleLocs = useMemo(() => {
    if (showMoreLocs || locSearch) return filteredLocs;
    return filteredLocs.slice(0, 8);
  }, [showMoreLocs, locSearch, filteredLocs]);

  const filteredRoles = useMemo(() => {
    if (!roleSearch) return BIG_COMPANY_ROLES;
    return BIG_COMPANY_ROLES.filter(r => r.toLowerCase().includes(roleSearch.toLowerCase()));
  }, [roleSearch]);

  const visibleRoles = useMemo(() => {
    if (showMoreRoles || roleSearch) return filteredRoles;
    return filteredRoles.slice(0, 8);
  }, [showMoreRoles, roleSearch, filteredRoles]);

  // Helper to check match excluding one dimension for dynamic faceted counting
  const checkJobMatchWithout = (
    j: BigCompanyJob,
    excludeDim: 'none' | 'location' | 'role' | 'date',
    term: string
  ): boolean => {
    // 1. Search Query
    if (term) {
      const hay = [j.title, j.company, j.location].filter(Boolean).join(' ').toLowerCase();
      if (!hay.includes(term)) return false;
    }

    // 2. Date Filter
    if (excludeDim !== 'date' && selectedDateFilter !== 'all') {
      const dateStr = (j.fetched_at || j.fetchedAt || j.date || '').slice(0, 10);
      if (dateStr) {
        const jd = new Date(dateStr);
        if (!isNaN(jd.getTime())) {
          const now = new Date();
          now.setHours(0, 0, 0, 0);
          const diffDays = Math.floor((now.getTime() - jd.getTime()) / 86400000);
          if (selectedDateFilter === '24h' && diffDays > 1) return false;
          if (selectedDateFilter === '3d' && diffDays > 3) return false;
          if (selectedDateFilter === '7d' && diffDays > 7) return false;
          if (selectedDateFilter === '15d' && diffDays > 15) return false;
        }
      }
    }

    // 3. Location Filter
    if (excludeDim !== 'location' && selectedLocations.size > 0) {
      const jLoc = (j.location || '').toLowerCase();
      let matchedLoc = false;
      for (const loc of selectedLocations) {
        if (jLoc.includes(loc.toLowerCase())) {
          matchedLoc = true;
          break;
        }
      }
      if (!matchedLoc) return false;
    }

    // 4. Role Filter (Exact regex word-boundary keyword matching from big_company_jobs.html)
    if (excludeDim !== 'role' && selectedRoles.size > 0) {
      const titleLow = (j.title || '').toLowerCase();
      let matchedRole = false;
      for (const role of selectedRoles) {
        const kws = ROLE_KEYWORDS[role] || [role.toLowerCase()];
        const match = kws.some(kw => {
          if (kw.endsWith(' ')) {
            return titleLow.includes(kw);
          }
          const esc_kw = kw.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
          const regex = new RegExp('(?:^|\\s|[\\-_/,])' + esc_kw + '(?:$|\\s|[\\-_/,])', 'i');
          return regex.test(titleLow);
        });
        if (match) {
          matchedRole = true;
          break;
        }
      }
      if (!matchedRole) return false;
    }

    return true;
  };

  // Main filtered jobs matching real web format
  const filteredJobs = useMemo(() => {
    const term = searchTerm.toLowerCase().trim();
    return jobs.filter(j => checkJobMatchWithout(j, 'none', term)).sort((a, b) => {
      if (sortBy === 'company') {
        return (a.company || '').localeCompare(b.company || '');
      }
      return (b.fetched_at || b.fetchedAt || b.date || '').localeCompare(a.fetched_at || a.fetchedAt || a.date || '');
    });
  }, [jobs, searchTerm, selectedDateFilter, selectedLocations, selectedRoles, sortBy]);

  // Dynamic Faceted Counts for real-time counts across filters
  const dynamicCounts = useMemo(() => {
    const term = searchTerm.toLowerCase().trim();
    const locCounts: Record<string, number> = {};
    const roleCounts: Record<string, number> = {};

    BIG_COMPANY_CITIES.forEach(c => { locCounts[c] = 0; });
    BIG_COMPANY_ROLES.forEach(r => { roleCounts[r] = 0; });

    // 1. Dynamic Location counts: for jobs matching all active filters EXCEPT location
    for (const j of jobs) {
      if (checkJobMatchWithout(j, 'location', term)) {
        const locLow = (j.location || '').toLowerCase();
        for (const c of BIG_COMPANY_CITIES) {
          if (locLow.includes(c.toLowerCase())) {
            locCounts[c] = (locCounts[c] || 0) + 1;
          }
        }
      }
    }

    // 2. Dynamic Role counts: for jobs matching all active filters EXCEPT role
    for (const j of jobs) {
      if (checkJobMatchWithout(j, 'role', term)) {
        const titleLow = (j.title || '').toLowerCase();
        for (const role of BIG_COMPANY_ROLES) {
          const kws = ROLE_KEYWORDS[role] || [role.toLowerCase()];
          const match = kws.some(kw => {
            if (kw.endsWith(' ')) return titleLow.includes(kw);
            const esc_kw = kw.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
            const regex = new RegExp('(?:^|\\s|[\\-_/,])' + esc_kw + '(?:$|\\s|[\\-_/,])', 'i');
            return regex.test(titleLow);
          });
          if (match) {
            roleCounts[role] = (roleCounts[role] || 0) + 1;
          }
        }
      }
    }

    return { locCounts, roleCounts };
  }, [jobs, searchTerm, selectedDateFilter, selectedLocations, selectedRoles]);

  // Pagination slice
  const totalPages = Math.max(1, Math.ceil(filteredJobs.length / JOBS_PER_PAGE));
  const pageJobs = useMemo(() => {
    const start = (currentPage - 1) * JOBS_PER_PAGE;
    return filteredJobs.slice(start, start + JOBS_PER_PAGE);
  }, [filteredJobs, currentPage]);

  const totalApplied = (selectedDateFilter !== 'all' ? 1 : 0) + selectedLocations.size + selectedRoles.size;
  const hasActiveFilters = totalApplied > 0 || Boolean(searchTerm);

  const clearAllFilters = () => {
    setSearchTerm('');
    setSelectedDateFilter('all');
    setSelectedLocations(new Set());
    setSelectedRoles(new Set());
    setCurrentPage(1);
  };

  const handleAutoApply = () => {
    const urls = pageJobs.map(j => j.apply_url || j.url).filter(Boolean) as string[];
    bridgeService.sendBatchJobsToExtension(urls);
    alert(`Dispatched ${urls.length} Big Company application URLs to Auto-Fill-V5 Extension!`);
  };

  const dateLabels: Record<string, string> = {
    '24h': 'Last 24 Hours',
    '3d': 'Last 3 Days',
    '7d': 'Last 7 Days',
    '15d': 'Last 15 Days'
  };

  return (
    <div className="bigcompany-jobs-page" style={{ minHeight: '100vh', background: '#06080f', color: '#f1f5f9' }}>
      {/* ══ TOP NAVBAR (Matching big_company_jobs.html) ══ */}
      <nav className="topnav">
        <div className="topnav-left">
          <div className="topnav-logo" onClick={onGoHub} style={{ cursor: 'pointer' }}>
            <img src={STRING_THEORY_LOGO} alt="ALL_CAREER" />
            <span>ALL_CAREER</span>
            <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '12px', background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', fontWeight: 700, marginLeft: '8px' }}>
              Big Company Jobs
            </span>
          </div>
        </div>

        <div className="topnav-center">
          <div className="topnav-search">
            <Search size={15} aria-hidden="true" />
            <input
              type="text"
              id="searchInput"
              placeholder="Search big company jobs..."
              value={searchTerm}
              onChange={e => { setSearchTerm(e.target.value); setCurrentPage(1); }}
            />
          </div>
        </div>

        <div className="topnav-right">
          {/* Auto Apply & History buttons */}
          <div className="topnav-auto-apply-group">
            <button
              className="auto-apply-nav-btn"
              onClick={handleAutoApply}
              title="Auto Apply to visible jobs on this page"
            >
              <Send className="auto-apply-icon" size={15} aria-hidden="true" />
              <span className="auto-apply-text">Auto Apply ({pageJobs.length})</span>
            </button>
            <button
              className="history-nav-btn"
              onClick={() => bridgeService.openHistory()}
              title="View Application History"
            >
              <History className="history-icon" size={15} aria-hidden="true" />
              <span className="history-text">History</span>
            </button>
          </div>

          <div className="topnav-count">
            Showing <span style={{ color: '#34d399', fontWeight: 800 }}>{filteredJobs.length.toLocaleString()}</span> jobs
          </div>
        </div>
      </nav>

      {/* ══ PAGE LAYOUT ══ */}
      <div className="page-layout">
        {/* ══ LEFT SIDEBAR FILTERS (ONLY Posted Date, Location, and Role Category) ══ */}
        <aside className="sidebar">
          <div className="sidebar-header">
            <span className="sidebar-title">All Filters</span>
            {totalApplied > 0 && (
              <span className="applied-badge visible">
                Applied ({totalApplied})
              </span>
            )}
          </div>

          {/* 1. Posted Date */}
          <div className={`filter-section ${openSections.date ? 'open' : ''}`} id="sec-date">
            <div className="filter-section-header" onClick={() => toggleSection('date')}>
              <span className="filter-section-label">
                <CalendarDays size={14} aria-hidden="true" /> Posted Date
                {selectedDateFilter !== 'all' && <span className="filter-count show">1</span>}
              </span>
              <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </div>
            <div className="filter-body">
              <div className="filter-body-inner">
                {DATE_RANGES.map(opt => (
                  <div
                    key={opt.id}
                    className={`filter-radio ${selectedDateFilter === opt.id ? 'selected' : ''}`}
                    onClick={() => { setSelectedDateFilter(opt.id); setCurrentPage(1); }}
                  >
                    <div className="custom-radio"><div className="radio-dot"></div></div>
                    <span className="option-label">{opt.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 2. Location */}
          <div className={`filter-section ${openSections.location ? 'open' : ''}`} id="sec-location">
            <div className="filter-section-header" onClick={() => toggleSection('location')}>
              <span className="filter-section-label">
                <MapPin size={14} aria-hidden="true" /> Location
                {selectedLocations.size > 0 && <span className="filter-count show">{selectedLocations.size}</span>}
              </span>
              <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </div>
            <div className="filter-body">
              <div className="filter-body-inner">
                <div className="filter-search colored-search">
                  <svg width="13" height="13" fill="none" stroke="#38bdf8" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="11" cy="11" r="8" />
                    <path d="m21 21-4.35-4.35" />
                  </svg>
                  <input
                    type="text"
                    id="locSearch"
                    placeholder="Search location..."
                    value={locSearch}
                    onChange={e => setLocSearch(e.target.value)}
                  />
                </div>
                <div id="location-options">
                  {visibleLocs.map(city => {
                    const isChecked = selectedLocations.has(city);
                    const count = dynamicCounts.locCounts[city] ?? 0;
                    return (
                      <div
                        key={city}
                        className={`filter-option ${isChecked ? 'checked' : ''}`}
                        onClick={() => {
                          setSelectedLocations(prev => {
                            const next = new Set(prev);
                            if (next.has(city)) next.delete(city);
                            else next.add(city);
                            return next;
                          });
                          setCurrentPage(1);
                        }}
                      >
                        <div className="custom-checkbox">
                          {isChecked && (
                            <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                              <path d="M20 6 9 17l-5-5" />
                            </svg>
                          )}
                        </div>
                        <span className="option-label">{city}</span>
                        <span className="source-count">({count.toLocaleString()})</span>
                      </div>
                    );
                  })}
                </div>
                {!locSearch && BIG_COMPANY_CITIES.length > 8 && (
                  <span className="show-more-btn" onClick={() => setShowMoreLocs(prev => !prev)}>
                    {showMoreLocs ? '− Show less' : `+ ${BIG_COMPANY_CITIES.length - 8} more`}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* 3. Role Category */}
          <div className={`filter-section ${openSections.roles ? 'open' : ''}`} id="sec-roles">
            <div className="filter-section-header" onClick={() => toggleSection('roles')}>
              <span className="filter-section-label">
                <BriefcaseBusiness size={14} aria-hidden="true" /> Role Category
                {selectedRoles.size > 0 && <span className="filter-count show">{selectedRoles.size}</span>}
              </span>
              <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </div>
            <div className="filter-body">
              <div className="filter-body-inner">
                <div className="filter-search colored-search">
                  <svg width="13" height="13" fill="none" stroke="#38bdf8" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="11" cy="11" r="8" />
                    <path d="m21 21-4.35-4.35" />
                  </svg>
                  <input
                    type="text"
                    id="roleSearch"
                    placeholder="Search roles..."
                    value={roleSearch}
                    onChange={e => setRoleSearch(e.target.value)}
                  />
                </div>
                <div id="roles-options">
                  {visibleRoles.map(role => {
                    const isChecked = selectedRoles.has(role);
                    const count = dynamicCounts.roleCounts[role] ?? 0;
                    return (
                      <div
                        key={role}
                        className={`filter-option ${isChecked ? 'checked' : ''}`}
                        onClick={() => {
                          setSelectedRoles(prev => {
                            const next = new Set(prev);
                            if (next.has(role)) next.delete(role);
                            else next.add(role);
                            return next;
                          });
                          setCurrentPage(1);
                        }}
                      >
                        <div className="custom-checkbox">
                          {isChecked && (
                            <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                              <path d="M20 6 9 17l-5-5" />
                            </svg>
                          )}
                        </div>
                        <span className="option-label">{role}</span>
                        <span className="source-count">({count.toLocaleString()})</span>
                      </div>
                    );
                  })}
                </div>
                {!roleSearch && BIG_COMPANY_ROLES.length > 8 && (
                  <span className="show-more-btn" onClick={() => setShowMoreRoles(prev => !prev)}>
                    {showMoreRoles ? '− Show less' : `+ ${BIG_COMPANY_ROLES.length - 8} more`}
                  </span>
                )}
              </div>
            </div>
          </div>
        </aside>

        {/* ══ MAIN CONTENT ══ */}
        <main className="main-content" style={{ flex: 1, padding: '24px 32px', minWidth: 0 }}>
          {/* Reset Button (replaces Sort dropdown, shown only when any filter is active) */}
          {hasActiveFilters && (
            <div className="filter-reset-bar" style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
              <button
                type="button"
                className="premium-reset-btn"
                onClick={clearAllFilters}
                title="Reset all active filters"
              >
                <span className="reset-icon-halo">
                  <RotateCcw size={13} className="reset-spin-icon" aria-hidden="true" />
                </span>
                <span className="reset-btn-label">Reset Filters</span>
                {((selectedDateFilter !== 'all' ? 1 : 0) + selectedLocations.size + selectedRoles.size + (searchTerm ? 1 : 0)) > 0 && (
                  <span className="reset-count-badge">
                    {(selectedDateFilter !== 'all' ? 1 : 0) + selectedLocations.size + selectedRoles.size + (searchTerm ? 1 : 0)}
                  </span>
                )}
              </button>
            </div>
          )}

          {/* Active Filter Chips */}
          {hasActiveFilters && (
            <div className="active-chips" id="activeChips" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
              {selectedDateFilter !== 'all' && (
                <div className="chip">
                  <CalendarDays size={13} aria-hidden="true" /><span>{dateLabels[selectedDateFilter] || selectedDateFilter}</span>
                  <span className="chip-x" onClick={() => setSelectedDateFilter('all')}><X size={13} aria-label="Remove date filter" /></span>
                </div>
              )}
              {Array.from(selectedLocations).map(loc => (
                <div key={loc} className="chip">
                  <MapPin size={13} aria-hidden="true" /><span>{loc}</span>
                  <span className="chip-x" onClick={() => setSelectedLocations(prev => { const n = new Set(prev); n.delete(loc); return n; })}><X size={13} aria-label={`Remove ${loc} filter`} /></span>
                </div>
              ))}
              {Array.from(selectedRoles).map(role => (
                <div key={role} className="chip">
                  <BriefcaseBusiness size={13} aria-hidden="true" /><span>{role}</span>
                  <span className="chip-x" onClick={() => setSelectedRoles(prev => { const n = new Set(prev); n.delete(role); return n; })}><X size={13} aria-label={`Remove ${role} filter`} /></span>
                </div>
              ))}
              {searchTerm && (
                <div className="chip">
                  <Search size={13} aria-hidden="true" /><span>"{searchTerm}"</span>
                  <span className="chip-x" onClick={() => setSearchTerm('')}><X size={13} aria-label="Clear search" /></span>
                </div>
              )}
            </div>
          )}

          {/* Loading Indicator */}
          {loading && (
            <div id="loading" style={{ textAlign: 'center', padding: '80px 20px', color: '#94a3b8' }}>
              <div className="hub-loader" style={{ margin: '0 auto 16px' }}></div>
              <p>Loading real big company jobs...</p>
            </div>
          )}

          {/* No results */}
          {!loading && filteredJobs.length === 0 && (
            <div id="noResults" style={{ textAlign: 'center', padding: '80px 20px', color: '#94a3b8', fontStyle: 'italic' }}>
              No big company jobs found matching your filters.
            </div>
          )}

          {/* Jobs Grid (Real Big Company Jobs) */}
          {!loading && pageJobs.length > 0 && (
            <div className="jobs-grid" id="jobsGrid">
              {pageJobs.map((job, idx) => {
                const date = formatDate(job.date || job.fetched_at || job.fetchedAt);
                const applyUrl = job.apply_url || job.url || '';
                const rawLoc = job.location && job.location !== 'nan' && job.location !== 'None' ? job.location : 'India';
                const cityLoc = rawLoc.split(',')[0].trim();

                return (
                  <div key={`${job.company}-${job.title}-${idx}`} className="job-card" style={{ animationDelay: `${(idx % 30) * 0.03}s` }}>
                    <div className="card-top">
                      <AuthenticLogoBox company={job.company} />
                      <div className="card-info">
                        <div className="company-name">{job.company}</div>
                        <div className="job-title" title={job.title}>{job.title || 'Open Position'}</div>
                      </div>
                    </div>

                    <div className="job-meta">
                      <div className="meta-row">
                        <div className="meta-badge loc"><MapPin size={13} aria-hidden="true" />{cityLoc}</div>
                      </div>
                      <div className="meta-row">
                        {date && <div className="meta-badge date"><CalendarDays size={13} aria-hidden="true" />{date}</div>}
                        <div className="meta-badge" style={{ color: 'var(--text-main)', borderColor: 'var(--border)' }}>
                          Direct Apply
                        </div>
                      </div>
                    </div>

                    <div className="card-footer">
                      <span className="card-role" title={job.title}>
                        {job.title}
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
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {!loading && totalPages > 1 && (
            <div id="pagination" className="pagination-container" style={{ marginTop: '36px', display: 'flex', justifyContent: 'center', gap: '6px' }}>
              <button
                className="page-btn nav-btn"
                disabled={currentPage === 1}
                onClick={() => { setCurrentPage(prev => Math.max(1, prev - 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              >
                ←
              </button>

              {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                let pageNum = i + 1;
                if (totalPages > 7) {
                  if (currentPage > 4) {
                    pageNum = currentPage - 3 + i;
                    if (pageNum > totalPages) pageNum = totalPages - (6 - i);
                  }
                }
                return (
                  <button
                    key={pageNum}
                    className={`page-btn ${currentPage === pageNum ? 'active' : ''}`}
                    onClick={() => { setCurrentPage(pageNum); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                  >
                    {pageNum}
                  </button>
                );
              })}

              <button
                className="page-btn nav-btn"
                disabled={currentPage === totalPages}
                onClick={() => { setCurrentPage(prev => Math.min(totalPages, prev + 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              >
                →
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
