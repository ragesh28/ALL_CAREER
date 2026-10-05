import React, { useState } from 'react';

interface AllJobsSidebarProps {
  // Source
  selectedSources: Set<string>;
  onToggleSource: (source: string) => void;
  // Date
  selectedDateFilter: string;
  onSelectDateFilter: (filter: string) => void;
  // Location
  selectedLocations: Set<string>;
  onToggleLocation: (location: string) => void;
  // Role
  selectedRoles: Set<string>;
  onToggleRole: (role: string) => void;
  // Experience
  minExp: string;
  onMinExpChange: (exp: string) => void;
  zeroExpOnly: boolean;
  onToggleZeroExp: () => void;
  // Skills
  selectedSkills: Set<string>;
  onToggleSkill: (skill: string) => void;
  // Walkin
  walkinOnly: boolean;
  onToggleWalkin: () => void;
  selectedWalkinDates: Set<string>;
  onToggleWalkinDate: (date: string) => void;
  // Dynamic counts
  sourceCounts: Record<string, number>;
}

export const AllJobsSidebar: React.FC<AllJobsSidebarProps> = ({
  selectedSources,
  onToggleSource,
  selectedDateFilter,
  onSelectDateFilter,
  selectedLocations,
  onToggleLocation,
  selectedRoles,
  onToggleRole,
  minExp,
  onMinExpChange,
  zeroExpOnly,
  onToggleZeroExp,
  selectedSkills,
  onToggleSkill,
  walkinOnly,
  onToggleWalkin,
  selectedWalkinDates,
  onToggleWalkinDate,
  sourceCounts
}) => {
  // Section toggle state matching original all_jobs.html (source, date, location open by default)
  const [openSections, setOpenSections] = useState({
    source: true,
    date: true,
    location: true,
    roles: false,
    exp: false,
    skills: false,
    walkin: false
  });

  const toggleSection = (section: keyof typeof openSections) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Search inside filters (Only Role and Skills have search bars as requested!)
  const [roleSearch, setRoleSearch] = useState('');
  const [skillSearch, setSkillSearch] = useState('');

  // Show more toggles
  const [showMoreRoles, setShowMoreRoles] = useState(false);
  const [showMoreSkills, setShowMoreSkills] = useState(false);

  // 1. Sources List with authentic logos from logos/portals/
  const PORTALS = [
    { id: 'linkedin', label: 'LinkedIn', logo: '/logos/portals/linkedin.png', defaultCount: 221380 },
    { id: 'naukri', label: 'Naukri', logo: '/logos/portals/naukri.png', defaultCount: 322160 },
    { id: 'indeed', label: 'Indeed', logo: '/logos/portals/indeed.png', defaultCount: 78407 },
    { id: 'internshala', label: 'Internshala', logo: '/logos/portals/internshala.png', defaultCount: 83161 },
    { id: 'glassdoor', label: 'Glassdoor', logo: '/logos/portals/glassdoor.ico', defaultCount: 4786 },
    { id: 'shine', label: 'Shine', logo: '/logos/portals/shine.ico', defaultCount: 47436 },
    { id: 'timesjobs', label: 'TimesJobs', logo: '/logos/portals/timesjobs.svg', defaultCount: 101057 },
    { id: 'hirist', label: 'Hirist', logo: '/logos/portals/hirist.ico', defaultCount: 10355 },
    { id: 'workindia', label: 'WorkIndia', logo: '/logos/portals/workindia.png', defaultCount: 15876 },
    { id: 'foundit', label: 'Foundit', logo: '/logos/portals/foundit.png', defaultCount: 20644 },
    { id: 'apna', label: 'Apna', logo: '/logos/portals/apna.png', defaultCount: 7409 },
    { id: 'freshersworld', label: 'FreshersWorld', logo: '/logos/portals/freshersworld.ico', defaultCount: 4065 },
    { id: 'telegram_message', label: 'Messages', logo: '/logos/portals/telegram.svg', defaultCount: 681 },
    { id: 'telegram_post', label: 'Post', logo: '/logos/portals/telegram.svg', defaultCount: 540 },
    { id: 'google_images', label: 'Images', logo: 'https://www.google.com/favicon.ico', defaultCount: 120 },
    { id: 'other', label: 'Other Sources', logo: '', defaultCount: 0 }
  ];

  // 2. Date Options matching original all_jobs.html
  const dateOptions = [
    { id: 'all', label: 'All Time' },
    { id: '24h', label: 'Last 24 Hours' },
    { id: '3d', label: 'Last 3 Days' },
    { id: '7d', label: 'Last 7 Days' },
    { id: '15d', label: 'Last 15 Days' }
  ];

  // 3. Locations List with real counts (NO search bar as requested)
  const locationsList = [
    { id: 'Bangalore', label: 'Bangalore', count: 32450 },
    { id: 'Chennai', label: 'Chennai', count: 14280 },
    { id: 'Hyderabad', label: 'Hyderabad', count: 21120 },
    { id: 'Mumbai', label: 'Mumbai', count: 19450 },
    { id: 'Delhi', label: 'Delhi', count: 28900 },
    { id: 'Pune', label: 'Pune', count: 16480 },
    { id: 'Noida', label: 'Noida', count: 8950 },
    { id: 'Kolkata', label: 'Kolkata', count: 6240 },
    { id: 'Ahmedabad', label: 'Ahmedabad', count: 4820 },
    { id: 'Remote', label: 'Remote', count: 13400 }
  ];

  // 4. Role Categories matching original all_jobs.html
  const allRolesList = [
    { id: 'software-engineer', label: 'Software Engineer', count: 4520 },
    { id: 'software-developer', label: 'Software Developer', count: 3890 },
    { id: 'full-stack', label: 'Full Stack Developer', count: 2810 },
    { id: 'frontend', label: 'Frontend Developer', count: 1940 },
    { id: 'backend', label: 'Backend Developer', count: 2150 },
    { id: 'react-developer', label: 'React Developer', count: 1230 },
    { id: 'java', label: 'Java Developer', count: 2240 },
    { id: 'python', label: 'Python Developer', count: 1630 },
    { id: 'node-developer', label: 'Node.js Developer', count: 980 },
    { id: 'android-developer', label: 'Android Developer', count: 640 },
    { id: 'ios-developer', label: 'iOS Developer', count: 580 },
    { id: 'devops', label: 'DevOps Engineer', count: 980 },
    { id: 'data-analyst', label: 'Data Analyst', count: 1840 },
    { id: 'data-science', label: 'Data Scientist', count: 1420 },
    { id: 'sales-marketing', label: 'Sales Executive', count: 3200 },
    { id: 'customer-support', label: 'Customer Support', count: 2100 },
    { id: 'hr', label: 'HR Executive', count: 890 },
    { id: 'qa-tester', label: 'QA Engineer', count: 1120 }
  ];

  const filteredRoles = allRolesList.filter(r =>
    r.label.toLowerCase().includes(roleSearch.toLowerCase())
  );
  const visibleRoles = showMoreRoles || roleSearch ? filteredRoles : filteredRoles.slice(0, 8);

  // 5. Skills List matching original all_jobs.html
  const allSkillsList = [
    { id: 'python', label: 'Python', count: 3420 },
    { id: 'react', label: 'React.js', count: 2810 },
    { id: 'java', label: 'Java', count: 2950 },
    { id: 'sql', label: 'SQL', count: 2640 },
    { id: 'javascript', label: 'JavaScript', count: 3800 },
    { id: 'node', label: 'Node.js', count: 1920 },
    { id: 'aws', label: 'AWS / Cloud', count: 2100 },
    { id: 'docker', label: 'Docker / Kubernetes', count: 1140 },
    { id: 'machine-learning', label: 'Machine Learning', count: 1230 },
    { id: 'cpp', label: 'C++ / C', count: 1450 },
    { id: 'html-css', label: 'HTML/CSS', count: 2400 },
    { id: 'git', label: 'Git', count: 1850 },
    { id: 'mongodb', label: 'MongoDB', count: 920 },
    { id: 'spring-boot', label: 'Spring Boot', count: 840 }
  ];

  const filteredSkills = allSkillsList.filter(s =>
    s.label.toLowerCase().includes(skillSearch.toLowerCase())
  );
  const visibleSkills = showMoreSkills || skillSearch ? filteredSkills : filteredSkills.slice(0, 8);

  // 6. Walk-in Dates
  const walkinDates = [
    { id: 'today', label: 'Today (Live Drive)', count: 42 },
    { id: 'tomorrow', label: 'Tomorrow', count: 38 },
    { id: 'this-week', label: 'This Week', count: 124 },
    { id: 'upcoming', label: 'Upcoming Weekend', count: 86 }
  ];

  const totalApplied =
    selectedSources.size +
    (selectedDateFilter !== 'all' ? 1 : 0) +
    selectedLocations.size +
    selectedRoles.size +
    (minExp || zeroExpOnly ? 1 : 0) +
    selectedSkills.size +
    (walkinOnly ? 1 : 0) +
    selectedWalkinDates.size;

  return (
    <aside className="sidebar">
      {/* Sidebar Header */}
      <div className="sidebar-header">
        <span className="sidebar-title">All Filters</span>
        {totalApplied > 0 && (
          <span className="applied-badge visible">
            Applied ({totalApplied})
          </span>
        )}
      </div>

      {/* ── 1. Source ── */}
      <div className={`filter-section ${openSections.source ? 'open' : ''}`} id="sec-source">
        <div className="filter-section-header" onClick={() => toggleSection('source')}>
          <span className="filter-section-label">
            Source
            {selectedSources.size > 0 && (
              <span className="filter-count show">{selectedSources.size}</span>
            )}
          </span>
          <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        <div className="filter-body">
          <div className="filter-body-inner" id="source-options">
            {PORTALS.map(item => {
              const isSelected = selectedSources.has(item.id);
              const count = sourceCounts[item.id] ?? item.defaultCount;
              return (
                <div
                  key={item.id}
                  className={`filter-option ${isSelected ? 'checked' : ''}`}
                  id={`src-${item.id}`}
                  onClick={() => onToggleSource(item.id)}
                >
                  <div className="custom-checkbox">
                    <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                  </div>
                  {item.logo ? (
                    <img
                      src={item.logo}
                      className="option-img"
                      alt={item.label}
                      onError={e => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                  ) : (
                    <span className="meta-icon" style={{ fontSize: '13px' }}>🌐</span>
                  )}
                  <span className="option-label">{item.label}</span>
                  <span className="source-count" id={`cnt-src-${item.id}`}>
                    ({count.toLocaleString()})
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── 2. Posted Date ── */}
      <div className={`filter-section ${openSections.date ? 'open' : ''}`} id="sec-date">
        <div className="filter-section-header" onClick={() => toggleSection('date')}>
          <span className="filter-section-label">
            Posted Date
            {selectedDateFilter !== 'all' && (
              <span className="filter-count show">1</span>
            )}
          </span>
          <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        <div className="filter-body">
          <div className="filter-body-inner">
            {dateOptions.map(item => {
              const isSelected = selectedDateFilter === item.id;
              return (
                <div
                  key={item.id}
                  className={`filter-radio ${isSelected ? 'selected' : ''}`}
                  data-range={item.id}
                  onClick={() => onSelectDateFilter(item.id)}
                >
                  <div className="custom-radio">
                    <div className="radio-dot"></div>
                  </div>
                  <span className="option-label">{item.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── 3. Location (NO SEARCH BAR as requested, with count) ── */}
      <div className={`filter-section ${openSections.location ? 'open' : ''}`} id="sec-location">
        <div className="filter-section-header" onClick={() => toggleSection('location')}>
          <span className="filter-section-label">
            Location
            {selectedLocations.size > 0 && (
              <span className="filter-count show">{selectedLocations.size}</span>
            )}
          </span>
          <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        <div className="filter-body">
          <div className="filter-body-inner">
            <div id="location-options">
              {locationsList.map(item => {
                const isSelected = selectedLocations.has(item.id);
                return (
                  <div
                    key={item.id}
                    className={`filter-option ${isSelected ? 'checked' : ''}`}
                    onClick={() => onToggleLocation(item.id)}
                  >
                    <div className="custom-checkbox">
                      <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                    <span className="option-label">{item.label}</span>
                    <span className="source-count">({item.count.toLocaleString()})</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* ── 4. Role Category (With Colorful Search Bar) ── */}
      <div className={`filter-section ${openSections.roles ? 'open' : ''}`} id="sec-roles">
        <div className="filter-section-header" onClick={() => toggleSection('roles')}>
          <span className="filter-section-label">
            Role Category
            {selectedRoles.size > 0 && (
              <span className="filter-count show">{selectedRoles.size}</span>
            )}
          </span>
          <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        <div className="filter-body">
          <div className="filter-body-inner">
            {/* Colorful Search Bar */}
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
              {visibleRoles.map(item => {
                const isSelected = selectedRoles.has(item.id);
                return (
                  <div
                    key={item.id}
                    className={`filter-option ${isSelected ? 'checked' : ''}`}
                    onClick={() => onToggleRole(item.id)}
                  >
                    <div className="custom-checkbox">
                      <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                    <span className="option-label">{item.label}</span>
                    <span className="source-count">({item.count.toLocaleString()})</span>
                  </div>
                );
              })}
            </div>
            {!roleSearch && (
              <span className="show-more-btn" onClick={() => setShowMoreRoles(prev => !prev)}>
                {showMoreRoles ? '− Show less' : `+ ${allRolesList.length - 8} more`}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── 5. Experience (Min Year) ── */}
      <div className={`filter-section ${openSections.exp ? 'open' : ''}`} id="sec-exp">
        <div className="filter-section-header" onClick={() => toggleSection('exp')}>
          <span className="filter-section-label">
            Experience
            {(minExp || zeroExpOnly) && <span className="filter-count show">1</span>}
          </span>
          <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        <div className="filter-body">
          <div className="filter-body-inner" style={{ padding: '16px 4px 20px 4px' }}>
            <div className="exp-input-container">
              <label htmlFor="expMinInput">Min Year</label>
              <input
                type="number"
                min="0"
                max="30"
                value={minExp}
                placeholder="None"
                className="exp-input"
                id="expMinInput"
                onChange={e => onMinExpChange(e.target.value)}
              />
              <span className="exp-input-suffix">Yrs</span>
            </div>
            <div
              className={`exp-zero-checkbox ${zeroExpOnly ? 'active' : ''}`}
              id="expZeroCheckboxWrap"
              style={{ display: 'flex' }}
              onClick={onToggleZeroExp}
            >
              <input
                type="checkbox"
                id="expExactlyZero"
                checked={zeroExpOnly}
                onChange={onToggleZeroExp}
              />
              <label htmlFor="expExactlyZero">Exactly 0 years only</label>
            </div>
          </div>
        </div>
      </div>

      {/* ── 6. Skills (With Colorful Search Bar) ── */}
      <div className={`filter-section ${openSections.skills ? 'open' : ''}`} id="sec-skills">
        <div className="filter-section-header" onClick={() => toggleSection('skills')}>
          <span className="filter-section-label">
            Skills
            {selectedSkills.size > 0 && (
              <span className="filter-count show">{selectedSkills.size}</span>
            )}
          </span>
          <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        <div className="filter-body">
          <div className="filter-body-inner">
            {/* Colorful Search Bar */}
            <div className="filter-search colored-search">
              <svg width="13" height="13" fill="none" stroke="#22d3ee" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
              <input
                type="text"
                id="skillSearch"
                placeholder="Search skills..."
                value={skillSearch}
                onChange={e => setSkillSearch(e.target.value)}
              />
            </div>
            <div id="skills-options">
              {visibleSkills.map(item => {
                const isSelected = selectedSkills.has(item.id);
                return (
                  <div
                    key={item.id}
                    className={`filter-option ${isSelected ? 'checked' : ''}`}
                    onClick={() => onToggleSkill(item.id)}
                  >
                    <div className="custom-checkbox">
                      <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                    <span className="option-label">{item.label}</span>
                    <span className="source-count">({item.count.toLocaleString()})</span>
                  </div>
                );
              })}
            </div>
            {!skillSearch && (
              <span className="show-more-btn" onClick={() => setShowMoreSkills(prev => !prev)}>
                {showMoreSkills ? '− Show less' : `+ ${allSkillsList.length - 8} more`}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── 7. Walk-in Interview ── */}
      <div className={`filter-section ${openSections.walkin ? 'open' : ''}`} id="sec-walkin">
        <div className="filter-section-header" onClick={() => toggleSection('walkin')}>
          <span className="filter-section-label">
            Walk-in Interview
            {(walkinOnly || selectedWalkinDates.size > 0) && (
              <span className="filter-count show">
                {(walkinOnly ? 1 : 0) + selectedWalkinDates.size}
              </span>
            )}
          </span>
          <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        <div className="filter-body">
          <div className="filter-body-inner">
            <div
              className={`filter-option ${walkinOnly ? 'checked' : ''}`}
              id="walkinOpt"
              onClick={onToggleWalkin}
            >
              <div className="custom-checkbox">
                <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path d="M20 6 9 17l-5-5" />
                </svg>
              </div>
              <span className="option-label">🚶 All Walk-ins</span>
              <span className="source-count">(290)</span>
            </div>
            <div
              style={{
                fontSize: '0.73rem',
                fontWeight: 700,
                color: 'var(--text-dim)',
                margin: '12px 0 6px 4px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                borderTop: '1px solid var(--border)',
                paddingTop: '10px'
              }}
            >
              Interview Dates
            </div>
            <div id="walkin-dates-options">
              {walkinDates.map(item => {
                const isSelected = selectedWalkinDates.has(item.id);
                return (
                  <div
                    key={item.id}
                    className={`filter-option ${isSelected ? 'checked' : ''}`}
                    onClick={() => onToggleWalkinDate(item.id)}
                  >
                    <div className="custom-checkbox">
                      <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                    <span className="option-label">{item.label}</span>
                    <span className="source-count">({item.count})</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
