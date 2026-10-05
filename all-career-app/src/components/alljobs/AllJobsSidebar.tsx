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
  // Company
  selectedCompanies: Set<string>;
  onToggleCompany: (company: string) => void;
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
  selectedCompanies,
  onToggleCompany,
  walkinOnly,
  onToggleWalkin,
  selectedWalkinDates,
  onToggleWalkinDate,
  sourceCounts
}) => {
  // Section toggle state (Source and Date open by default)
  const [openSections, setOpenSections] = useState({
    source: true,
    date: true,
    location: true,
    roles: false,
    exp: false,
    skills: false,
    company: false,
    walkin: false
  });

  const toggleSection = (section: keyof typeof openSections) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Search inside filters
  const [locSearch, setLocSearch] = useState('');
  const [roleSearch, setRoleSearch] = useState('');
  const [skillSearch, setSkillSearch] = useState('');
  const [compSearch, setCompSearch] = useState('');

  // 1. Sources List
  const sourcesList = [
    { id: 'linkedin', label: 'LinkedIn', icon: '💼', count: sourceCounts.linkedin ?? 221380 },
    { id: 'naukri', label: 'Naukri', icon: '🌐', count: sourceCounts.naukri ?? 322160 },
    { id: 'indeed', label: 'Indeed', icon: '🔍', count: sourceCounts.indeed ?? 78407 },
    { id: 'internshala', label: 'Internshala', icon: 'IS', count: sourceCounts.internshala ?? 83161 },
    { id: 'glassdoor', label: 'Glassdoor', icon: '🟢', count: sourceCounts.glassdoor ?? 4786 },
    { id: 'shine', label: 'Shine', icon: '⭐', count: sourceCounts.shine ?? 47436 },
    { id: 'timesjobs', label: 'TimesJobs', icon: '⏳', count: sourceCounts.timesjobs ?? 101057 },
    { id: 'hirist', label: 'Hirist', icon: 'h', count: sourceCounts.hirist ?? 10355 },
    { id: 'workindia', label: 'WorkIndia', icon: 'W', count: sourceCounts.workindia ?? 15876 },
    { id: 'foundit', label: 'Foundit', icon: '🎯', count: sourceCounts.foundit ?? 20644 },
    { id: 'apna', label: 'Apna', icon: 'A', count: sourceCounts.apna ?? 7409 },
    { id: 'freshersworld', label: 'FreshersWorld', icon: 'FW', count: sourceCounts.freshersworld ?? 4065 },
    { id: 'telegram', label: 'Messages', icon: '✉️', count: sourceCounts.telegram ?? 681 },
    { id: 'post', label: 'Post', icon: '📌', count: sourceCounts.post ?? 540 },
    { id: 'images', label: 'Images', icon: '🖼️', count: 0 },
    { id: 'others', label: 'Other Sources', icon: '⚙️', count: 0 }
  ];

  // 2. Date Options
  const dateOptions = [
    { id: 'all', label: 'All Time' },
    { id: '24h', label: 'Last 24 Hours' },
    { id: '3d', label: 'Last 3 Days' },
    { id: '7d', label: 'Last 7 Days' },
    { id: '15d', label: 'Last 15 Days' }
  ];

  // 3. Locations List
  const locationsList = [
    { id: 'bengaluru', label: 'Bengaluru', count: 3240 },
    { id: 'delhi', label: 'Delhi / NCR', count: 2890 },
    { id: 'mumbai', label: 'Mumbai', count: 1950 },
    { id: 'hyderabad', label: 'Hyderabad', count: 2120 },
    { id: 'pune', label: 'Pune', count: 1480 },
    { id: 'chennai', label: 'Chennai', count: 1150 },
    { id: 'noida', label: 'Noida', count: 890 },
    { id: 'gurgaon', label: 'Gurgaon', count: 950 },
    { id: 'kolkata', label: 'Kolkata', count: 620 },
    { id: 'ahmedabad', label: 'Ahmedabad', count: 480 },
    { id: 'remote', label: 'Remote', count: 1340 }
  ].filter(l => l.label.toLowerCase().includes(locSearch.toLowerCase()));

  // 4. Role Categories
  const rolesList = [
    { id: 'software-engineer', label: 'Software Engineer', count: 4520 },
    { id: 'full-stack', label: 'Full Stack Developer', count: 2810 },
    { id: 'frontend', label: 'Frontend Developer', count: 1940 },
    { id: 'backend', label: 'Backend Developer', count: 2150 },
    { id: 'python', label: 'Python Developer', count: 1630 },
    { id: 'java', label: 'Java Developer', count: 2240 },
    { id: 'devops', label: 'DevOps Engineer', count: 980 },
    { id: 'data-science', label: 'Data Scientist / AI', count: 1420 },
    { id: 'sales-marketing', label: 'Sales & Marketing', count: 3200 },
    { id: 'customer-support', label: 'Customer Support / BPO', count: 2100 },
    { id: 'hr', label: 'Human Resources (HR)', count: 890 },
    { id: 'qa-tester', label: 'QA / Test Engineer', count: 1120 }
  ].filter(r => r.label.toLowerCase().includes(roleSearch.toLowerCase()));

  // 6. Skills List
  const skillsList = [
    { id: 'python', label: 'Python', count: 3420 },
    { id: 'react', label: 'React.js', count: 2810 },
    { id: 'java', label: 'Java', count: 2950 },
    { id: 'sql', label: 'SQL', count: 2640 },
    { id: 'javascript', label: 'JavaScript', count: 3800 },
    { id: 'node', label: 'Node.js', count: 1920 },
    { id: 'aws', label: 'AWS / Cloud', count: 2100 },
    { id: 'docker', label: 'Docker / Kubernetes', count: 1140 },
    { id: 'ml', label: 'Machine Learning', count: 1230 },
    { id: 'cpp', label: 'C++ / C', count: 1450 },
    { id: 'html-css', label: 'HTML/CSS', count: 2400 }
  ].filter(s => s.label.toLowerCase().includes(skillSearch.toLowerCase()));

  // 7. Companies List
  const companiesList = [
    { id: 'amazon', label: 'Amazon', count: 420 },
    { id: 'google', label: 'Google', count: 310 },
    { id: 'microsoft', label: 'Microsoft', count: 380 },
    { id: 'tcs', label: 'TCS', count: 680 },
    { id: 'infosys', label: 'Infosys', count: 590 },
    { id: 'wipro', label: 'Wipro', count: 510 },
    { id: 'cognizant', label: 'Cognizant', count: 470 },
    { id: 'accenture', label: 'Accenture', count: 620 },
    { id: 'capgemini', label: 'Capgemini', count: 430 },
    { id: 'flipkart', label: 'Flipkart', count: 210 },
    { id: 'swiggy', label: 'Swiggy', count: 180 },
    { id: 'zomato', label: 'Zomato', count: 190 },
    { id: 'zoho', label: 'Zoho', count: 240 }
  ].filter(c => c.label.toLowerCase().includes(compSearch.toLowerCase()));

  // 8. Walkin Dates
  const walkinDates = [
    { id: 'today', label: 'Today (Live Drive)', count: 42 },
    { id: 'tomorrow', label: 'Tomorrow', count: 38 },
    { id: 'this-week', label: 'This Week', count: 124 },
    { id: 'upcoming', label: 'Upcoming Weekend', count: 86 }
  ];

  const totalApplied = selectedSources.size + (selectedDateFilter !== 'all' ? 1 : 0) + selectedLocations.size + selectedRoles.size + (minExp || zeroExpOnly ? 1 : 0) + selectedSkills.size + selectedCompanies.size + (walkinOnly ? 1 : 0);

  return (
    <aside className="sidebar">
      {/* Sidebar Header */}
      <div className="sidebar-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--border)' }}>
        <span className="sidebar-title">All Filters</span>
        {totalApplied > 0 && (
          <span className="applied-badge visible" style={{ display: 'inline-block' }}>
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
          <div className="filter-body-inner">
            {sourcesList.map(item => {
              const isSelected = selectedSources.has(item.id);
              return (
                <div
                  key={item.id}
                  className={`filter-option ${isSelected ? 'checked' : ''}`}
                  onClick={() => onToggleSource(item.id)}
                >
                  <div className="custom-checkbox">
                    {isSelected && (
                      <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    )}
                  </div>
                  <span className="option-label">{item.icon} {item.label}</span>
                  <span className="source-count">({item.count.toLocaleString()})</span>
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
            {dateOptions.map(opt => {
              const isSelected = selectedDateFilter === opt.id;
              return (
                <div
                  key={opt.id}
                  className={`filter-radio ${isSelected ? 'selected' : ''}`}
                  onClick={() => onSelectDateFilter(opt.id)}
                >
                  <div className="custom-radio">
                    <div className="radio-dot"></div>
                  </div>
                  <span className="option-label">{opt.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── 3. Location ── */}
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
            <div className="filter-search">
              <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
              <input
                type="text"
                placeholder="Search location..."
                value={locSearch}
                onChange={e => setLocSearch(e.target.value)}
              />
            </div>
            <div id="location-options">
              {locationsList.map(loc => {
                const isSelected = selectedLocations.has(loc.id);
                return (
                  <div
                    key={loc.id}
                    className={`filter-option ${isSelected ? 'checked' : ''}`}
                    onClick={() => onToggleLocation(loc.id)}
                  >
                    <div className="custom-checkbox">
                      {isSelected && (
                        <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      )}
                    </div>
                    <span className="option-label">{loc.label}</span>
                    <span className="source-count">({loc.count.toLocaleString()})</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* ── 4. Role Category ── */}
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
            <div className="filter-search">
              <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
              <input
                type="text"
                placeholder="Search roles..."
                value={roleSearch}
                onChange={e => setRoleSearch(e.target.value)}
              />
            </div>
            <div id="roles-options">
              {rolesList.map(r => {
                const isSelected = selectedRoles.has(r.id);
                return (
                  <div
                    key={r.id}
                    className={`filter-option ${isSelected ? 'checked' : ''}`}
                    onClick={() => onToggleRole(r.id)}
                  >
                    <div className="custom-checkbox">
                      {isSelected && (
                        <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      )}
                    </div>
                    <span className="option-label">{r.label}</span>
                    <span className="source-count">({r.count.toLocaleString()})</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* ── 5. Experience (Min Year) ── */}
      <div className={`filter-section ${openSections.exp ? 'open' : ''}`} id="sec-exp">
        <div className="filter-section-header" onClick={() => toggleSection('exp')}>
          <span className="filter-section-label">
            Experience
            {(minExp || zeroExpOnly) && (
              <span className="filter-count show">1</span>
            )}
          </span>
          <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        <div className="filter-body">
          <div className="filter-body-inner" style={{ padding: '16px 4px 24px 4px' }}>
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
              <span className="exp-input-suffix" style={{ fontSize: '13px', color: '#94a3b8' }}>Yrs</span>
            </div>
            <div className="exp-zero-checkbox" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '10px', fontSize: '0.82rem', color: '#94a3b8' }}>
              <input
                type="checkbox"
                id="expExactlyZero"
                checked={zeroExpOnly}
                onChange={onToggleZeroExp}
              />
              <label htmlFor="expExactlyZero" style={{ cursor: 'pointer' }}>Exactly 0 years only (Freshers)</label>
            </div>
          </div>
        </div>
      </div>

      {/* ── 6. Skills ── */}
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
            <div className="filter-search">
              <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
              <input
                type="text"
                placeholder="Search skills..."
                value={skillSearch}
                onChange={e => setSkillSearch(e.target.value)}
              />
            </div>
            <div id="skills-options">
              {skillsList.map(s => {
                const isSelected = selectedSkills.has(s.id);
                return (
                  <div
                    key={s.id}
                    className={`filter-option ${isSelected ? 'checked' : ''}`}
                    onClick={() => onToggleSkill(s.id)}
                  >
                    <div className="custom-checkbox">
                      {isSelected && (
                        <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      )}
                    </div>
                    <span className="option-label">{s.label}</span>
                    <span className="source-count">({s.count.toLocaleString()})</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* ── 7. Company ── */}
      <div className={`filter-section ${openSections.company ? 'open' : ''}`} id="sec-company">
        <div className="filter-section-header" onClick={() => toggleSection('company')}>
          <span className="filter-section-label">
            Company
            {selectedCompanies.size > 0 && (
              <span className="filter-count show">{selectedCompanies.size}</span>
            )}
          </span>
          <svg className="chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
        <div className="filter-body">
          <div className="filter-body-inner">
            <div className="filter-search">
              <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
              <input
                type="text"
                placeholder="Search company..."
                value={compSearch}
                onChange={e => setCompSearch(e.target.value)}
              />
            </div>
            <div id="company-options">
              {companiesList.map(comp => {
                const isSelected = selectedCompanies.has(comp.id);
                return (
                  <div
                    key={comp.id}
                    className={`filter-option ${isSelected ? 'checked' : ''}`}
                    onClick={() => onToggleCompany(comp.id)}
                  >
                    <div className="custom-checkbox">
                      {isSelected && (
                        <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      )}
                    </div>
                    <span className="option-label">{comp.label}</span>
                    <span className="source-count">({comp.count.toLocaleString()})</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* ── 8. Walk-in Interview ── */}
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
              onClick={onToggleWalkin}
            >
              <div className="custom-checkbox">
                {walkinOnly && (
                  <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                )}
              </div>
              <span className="option-label">🚶 All Walk-ins</span>
              <span className="source-count">(620)</span>
            </div>

            <div style={{ fontSize: '0.73rem', fontWeight: 700, color: 'var(--text-dim)', margin: '12px 0 6px 4px', textTransform: 'uppercase', letterSpacing: '0.5px', borderTop: '1px solid var(--border)', paddingTop: '10px' }}>
              Interview Dates
            </div>

            <div id="walkin-dates-options">
              {walkinDates.map(d => {
                const isSelected = selectedWalkinDates.has(d.id);
                return (
                  <div
                    key={d.id}
                    className={`filter-option ${isSelected ? 'checked' : ''}`}
                    onClick={() => onToggleWalkinDate(d.id)}
                  >
                    <div className="custom-checkbox">
                      {isSelected && (
                        <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      )}
                    </div>
                    <span className="option-label">{d.label}</span>
                    <span className="source-count">({d.count})</span>
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
