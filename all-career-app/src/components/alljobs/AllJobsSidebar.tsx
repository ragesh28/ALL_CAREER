import React, { useState } from 'react';
import { BriefcaseBusiness, CalendarDays, ChevronDown, Globe2, MapPin, Route, Search, SlidersHorizontal, Tag } from 'lucide-react';
import { formatWalkinDate } from '../../utils/companyLogos';

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
  // Experience Moving Bar Slider (-1 = Everything, 0 to 30 Yrs)
  expValue: number;
  onExpChange: (val: number) => void;
  exactExp: boolean;
  onToggleExactExp: () => void;
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
  locationCounts?: Record<string, number>;
  roleCounts?: Record<string, number>;
  skillCounts?: Record<string, number>;
  walkinCount?: number;
  walkinDateCounts?: Record<string, number>;
  walkinDateOptions?: { id: string; label: string; count: number }[];
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
  expValue,
  onExpChange,
  exactExp,
  onToggleExactExp,
  selectedSkills,
  onToggleSkill,
  walkinOnly,
  onToggleWalkin,
  selectedWalkinDates,
  onToggleWalkinDate,
  sourceCounts,
  locationCounts,
  roleCounts,
  skillCounts,
  walkinCount,
  walkinDateCounts,
  walkinDateOptions
}) => {
  // Section toggle state matching original all_jobs.html (source, date, location open by default)
  const [openSections, setOpenSections] = useState({
    source: true,
    date: true,
    location: true,
    roles: false,
    exp: true,
    skills: false,
    walkin: true
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
    { id: 'google_images', label: 'Images', logo: '/logos/portals/google.svg', defaultCount: 3519 },
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

  // 4. Role Categories matching original all_jobs.html (all 87 roles)
  const allRolesList = [
    // --- Tech Roles (High Popularity) ---
    { id: 'Software Engineer', label: 'Software Engineer', count: 52547 },
    { id: 'Software Developer', label: 'Software Developer', count: 48230 },
    { id: 'Full Stack Developer', label: 'Full Stack Developer', count: 17170 },
    { id: 'Frontend Developer', label: 'Frontend Developer', count: 12154 },
    { id: 'Backend Developer', label: 'Backend Developer', count: 12132 },
    { id: 'React Developer', label: 'React Developer', count: 18450 },
    { id: 'Java Developer', label: 'Java Developer', count: 24680 },
    { id: 'Python Developer', label: 'Python Developer', count: 21390 },
    { id: 'Node.js Developer', label: 'Node.js Developer', count: 14210 },
    { id: 'Android Developer', label: 'Android Developer', count: 8420 },
    { id: 'iOS Developer', label: 'iOS Developer', count: 6890 },
    { id: 'Mobile App Developer', label: 'Mobile App Developer', count: 9483 },
    { id: 'Data Analyst', label: 'Data Analyst', count: 25964 },
    { id: 'Data Scientist', label: 'Data Scientist', count: 10849 },
    { id: 'Data Engineer', label: 'Data Engineer', count: 17003 },
    { id: 'DevOps Engineer', label: 'DevOps Engineer', count: 14153 },
    { id: 'UI UX Designer', label: 'UI UX Designer', count: 23346 },
    { id: 'QA Engineer', label: 'QA Engineer', count: 11896 },
    { id: 'QA Analyst', label: 'QA Analyst', count: 9450 },
    { id: 'QA Automation Engineer', label: 'QA Automation Engineer', count: 8720 },
    { id: 'Test Automation Engineer', label: 'Test Automation Engineer', count: 7640 },
    { id: 'SDET', label: 'SDET', count: 9714 },
    { id: 'AI Engineer', label: 'AI Engineer', count: 14372 },
    { id: 'Machine Learning Engineer', label: 'Machine Learning Engineer', count: 16831 },

    // --- Business & Management ---
    { id: 'Product Manager', label: 'Product Manager', count: 14973 },
    { id: 'Project Manager', label: 'Project Manager', count: 22357 },
    { id: 'Technical Project Manager', label: 'Technical Project Manager', count: 12480 },
    { id: 'Business Development Executive', label: 'Business Development Executive', count: 92937 },
    { id: 'Business Development Manager', label: 'Business Development Manager', count: 34510 },
    { id: 'Sales Executive', label: 'Sales Executive', count: 78420 },
    { id: 'Sales Manager', label: 'Sales Manager', count: 26890 },

    // --- Non-Tech, Marketing & Design ---
    { id: 'HR Executive', label: 'HR Executive', count: 21137 },
    { id: 'HR Manager', label: 'HR Manager', count: 14820 },
    { id: 'Technical Recruiter', label: 'Technical Recruiter', count: 22345 },
    { id: 'Talent Acquisition Specialist', label: 'Talent Acquisition Specialist', count: 16730 },
    { id: 'HR Business Partner', label: 'HR Business Partner', count: 12450 },
    { id: 'Customer Support Executive', label: 'Customer Support Executive', count: 18940 },
    { id: 'Customer Success Manager', label: 'Customer Success Manager', count: 13972 },
    { id: 'Digital Marketer', label: 'Digital Marketer', count: 36971 },
    { id: 'Digital Marketing Manager', label: 'Digital Marketing Manager', count: 12480 },
    { id: 'Product Marketing Manager', label: 'Product Marketing Manager', count: 8750 },
    { id: 'SEO Specialist', label: 'SEO Specialist', count: 9640 },
    { id: 'Content Writer', label: 'Content Writer', count: 11320 },
    { id: 'Graphic Designer', label: 'Graphic Designer', count: 14250 },

    // --- Cloud, Network & Security ---
    { id: 'Cloud Engineer', label: 'Cloud Engineer', count: 16149 },
    { id: 'Cloud Architect', label: 'Cloud Architect', count: 12380 },
    { id: 'AWS Engineer', label: 'AWS Engineer', count: 14260 },
    { id: 'Azure Engineer', label: 'Azure Engineer', count: 11850 },
    { id: 'Systems Administrator', label: 'Systems Administrator', count: 2080 },
    { id: 'System Administrator', label: 'System Administrator', count: 4820 },
    { id: 'Network Engineer', label: 'Network Engineer', count: 10821 },
    { id: 'Cybersecurity Analyst', label: 'Cybersecurity Analyst', count: 13739 },
    { id: 'Cybersecurity Engineer', label: 'Cybersecurity Engineer', count: 11450 },
    { id: 'Security Analyst', label: 'Security Analyst', count: 9870 },
    { id: 'Penetration Tester', label: 'Penetration Tester', count: 2438 },
    { id: 'Database Administrator', label: 'Database Administrator', count: 7575 },

    // --- Specialized Tech ---
    { id: 'Flutter Developer', label: 'Flutter Developer', count: 6840 },
    { id: 'React Native Developer', label: 'React Native Developer', count: 5920 },
    { id: 'Angular Developer', label: 'Angular Developer', count: 8430 },
    { id: 'Salesforce Developer', label: 'Salesforce Developer', count: 9850 },
    { id: 'SAP Consultant', label: 'SAP Consultant', count: 7640 },
    { id: 'Blockchain Developer', label: 'Blockchain Developer', count: 3420 },
    { id: 'Game Developer', label: 'Game Developer', count: 4150 },
    { id: 'Embedded Systems Engineer', label: 'Embedded Systems Engineer', count: 5680 },
    { id: 'VLSI Engineer', label: 'VLSI Engineer', count: 3890 },
    { id: 'Hardware Engineer', label: 'Hardware Engineer', count: 4720 },
    { id: 'ETL Developer', label: 'ETL Developer', count: 6340 },
    { id: 'Business Intelligence Analyst', label: 'Business Intelligence Analyst', count: 8920 },
    { id: 'Deep Learning Engineer', label: 'Deep Learning Engineer', count: 7850 },
    { id: 'NLP Engineer', label: 'NLP Engineer', count: 5430 },
    { id: 'Site Reliability Engineer', label: 'Site Reliability Engineer', count: 8620 },
    { id: 'Software Architect', label: 'Software Architect', count: 9335 },

    // --- Operations, Finance & Specialized Non-Tech ---
    { id: 'Operations Manager', label: 'Operations Manager', count: 18332 },
    { id: 'Financial Analyst', label: 'Financial Analyst', count: 45790 },
    { id: 'Accountant', label: 'Accountant', count: 18460 },
    { id: 'Finance Executive', label: 'Finance Executive', count: 14230 },
    { id: 'Supply Chain Analyst', label: 'Supply Chain Analyst', count: 6780 },
    { id: 'Supply Chain Manager', label: 'Supply Chain Manager', count: 7940 },
    { id: 'Logistics Executive', label: 'Logistics Executive', count: 8350 },
    { id: 'Legal Counsel', label: 'Legal Counsel', count: 7498 },
    { id: 'Scrum Master', label: 'Scrum Master', count: 4261 },
    { id: 'UX Researcher', label: 'UX Researcher', count: 3450 },
    { id: 'Technical Writer', label: 'Technical Writer', count: 11187 },
    { id: 'Video Editor', label: 'Video Editor', count: 6940 },
    { id: 'Social Media Manager', label: 'Social Media Manager', count: 11850 },
    { id: 'Pre-Sales Consultant', label: 'Pre-Sales Consultant', count: 8161 },
    { id: 'IT Support Specialist', label: 'IT Support Specialist', count: 5119 }
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

  // 6. Walk-in Dates matching Screenshot 1
  const WALKIN_DATES = [
    { id: 'Oct 5', label: '05 Oct 2026', count: 699 },
    { id: 'Oct 6', label: '06 Oct 2026', count: 682 },
    { id: 'Oct 7', label: '07 Oct 2026', count: 659 },
    { id: 'Oct 8', label: '08 Oct 2026', count: 598 },
    { id: 'Oct 9', label: '09 Oct 2026', count: 579 },
    { id: 'Oct 10', label: '10 Oct 2026', count: 556 },
    { id: 'Oct 11', label: '11 Oct 2026', count: 355 },
    { id: 'Oct 12', label: '12 Oct 2026', count: 342 },
    { id: 'Oct 13', label: '13 Oct 2026', count: 334 },
    { id: 'Oct 14', label: '14 Oct 2026', count: 295 },
    { id: 'Oct 15', label: '15 Oct 2026', count: 240 },
    { id: 'Oct 16', label: '16 Oct 2026', count: 190 }
  ];

  const displayWalkinDates = walkinDateOptions && walkinDateOptions.length > 0 
    ? walkinDateOptions 
    : WALKIN_DATES;

  const totalApplied =
    selectedSources.size +
    (selectedDateFilter !== 'all' ? 1 : 0) +
    selectedLocations.size +
    selectedRoles.size +
    (expValue >= 0 ? 1 : 0) +
    selectedSkills.size +
    (walkinOnly ? 1 : 0) +
    selectedWalkinDates.size;

  // Percentage for experience bubble position: -1 to 30 => 31 steps
  const expPercent = Math.min(100, Math.max(0, ((expValue + 1) / 31) * 100));

  return (
    <aside className="sidebar">
      {/* Sidebar Header */}
      <div className="sidebar-header">
        <span className="sidebar-title"><SlidersHorizontal size={15} aria-hidden="true" /> All Filters</span>
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
            <Tag size={14} aria-hidden="true" /> Source
            {selectedSources.size > 0 && (
              <span className="filter-count show">{selectedSources.size}</span>
            )}
          </span>
          <ChevronDown className="chevron" size={16} aria-hidden="true" />
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
                    <Globe2 className="meta-icon" size={14} aria-label="Other source" />
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
            <CalendarDays size={14} aria-hidden="true" /> Posted Date
            {selectedDateFilter !== 'all' && (
              <span className="filter-count show">1</span>
            )}
          </span>
          <ChevronDown className="chevron" size={16} aria-hidden="true" />
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
            <MapPin size={14} aria-hidden="true" /> Location
            {selectedLocations.size > 0 && (
              <span className="filter-count show">{selectedLocations.size}</span>
            )}
          </span>
          <ChevronDown className="chevron" size={16} aria-hidden="true" />
        </div>
        <div className="filter-body">
          <div className="filter-body-inner">
            <div id="location-options">
              {locationsList.map(item => {
                const isSelected = selectedLocations.has(item.id);
                const count = locationCounts ? (locationCounts[item.id] ?? 0) : item.count;
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
                    <span className="source-count">({count.toLocaleString()})</span>
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
            <BriefcaseBusiness size={14} aria-hidden="true" /> Role Category
            {selectedRoles.size > 0 && (
              <span className="filter-count show">{selectedRoles.size}</span>
            )}
          </span>
          <ChevronDown className="chevron" size={16} aria-hidden="true" />
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
                const count = roleCounts ? (roleCounts[item.id] ?? 0) : item.count;
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
                    <span className="source-count">({count.toLocaleString()})</span>
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

      {/* ── 5. Experience Moving Bar Format ── */}
      <div className={`filter-section ${openSections.exp ? 'open' : ''}`} id="sec-exp">
        <div className="filter-section-header" onClick={() => toggleSection('exp')}>
          <span className="filter-section-label">
            <BriefcaseBusiness size={14} aria-hidden="true" /> Experience
            {expValue >= 0 && (
              <span className="filter-count show">
                {exactExp ? `Exactly ${expValue} Yrs` : `${expValue} Yrs`}
              </span>
            )}
          </span>
          <ChevronDown className="chevron" size={16} aria-hidden="true" />
        </div>
        <div className="filter-body">
          <div className="filter-body-inner">
            <div className="exp-slider-wrap">
              {/* Floating Bubble Pin (Pill for 'Everything', Teardrop for numbers) */}
              <div
                className={`exp-slider-bubble ${expValue === -1 ? 'is-everything' : ''}`}
                style={{
                  left: `calc(${expPercent}% + ${(16 - expPercent * 0.32)}px)`
                }}
              >
                <span>{expValue === -1 ? 'Everything' : expValue}</span>
              </div>

              {/* Slider Track: starts at -1 (Everything), next step is 0, up to 30 */}
              <input
                type="range"
                min="-1"
                max="30"
                step="1"
                value={expValue}
                onChange={e => onExpChange(parseInt(e.target.value, 10))}
                className="exp-range-slider"
                aria-label="Experience slider in years"
              />

              {/* Labels below slider */}
              <div className="exp-slider-labels">
                <span>Everything</span>
                <span>30 Yrs</span>
              </div>

              {/* Small Checkbox: Disappears at 'Everything', appears at 0 or 1-30 */}
              {expValue >= 0 && (
                <div
                  className={`exp-exact-checkbox ${exactExp ? 'active' : ''}`}
                  onClick={onToggleExactExp}
                  id="expExactCheckboxWrap"
                >
                  <div className="custom-checkbox">
                    {exactExp && (
                      <svg width="10" height="10" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    )}
                  </div>
                  <span className="option-label">
                    {expValue === 0
                      ? 'Exactly 0 years only'
                      : `Exactly ${expValue} year${expValue === 1 ? '' : 's'} only`}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── 6. Skills (With Colorful Search Bar) ── */}
      <div className={`filter-section ${openSections.skills ? 'open' : ''}`} id="sec-skills">
        <div className="filter-section-header" onClick={() => toggleSection('skills')}>
          <span className="filter-section-label">
            <Tag size={14} aria-hidden="true" /> Skills
            {selectedSkills.size > 0 && (
              <span className="filter-count show">{selectedSkills.size}</span>
            )}
          </span>
          <ChevronDown className="chevron" size={16} aria-hidden="true" />
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
                const count = skillCounts ? (skillCounts[item.id] ?? 0) : item.count;
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
                    <span className="source-count">({count.toLocaleString()})</span>
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

      {/* ── 7. Walk-in Interview (Matching Screenshot 1) ── */}
      <div className={`filter-section ${openSections.walkin ? 'open' : ''}`} id="sec-walkin">
        <div className="filter-section-header" onClick={() => toggleSection('walkin')}>
          <span className="filter-section-label">
            <Route size={14} aria-hidden="true" /> Walk-in Interview
            {(walkinOnly || selectedWalkinDates.size > 0) && (
              <span className="filter-count show">
                {(walkinOnly ? 1 : 0) + selectedWalkinDates.size}
              </span>
            )}
          </span>
          <ChevronDown className="chevron" size={16} aria-hidden="true" />
        </div>
        <div className="filter-body">
          <div className="filter-body-inner">
            {/* Top Option: All Walk-ins with dynamic count */}
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
              <span className="option-label"><Route size={14} aria-hidden="true" /> All Walk-ins</span>
              <span className="source-count">({(walkinCount !== undefined ? walkinCount : 7365).toLocaleString()})</span>
            </div>

            {/* Subheader: INTERVIEW DATES matching Screenshot 1 */}
            <div
              style={{
                fontSize: '0.73rem',
                fontWeight: 700,
                color: '#64748b',
                margin: '14px 0 8px 4px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                paddingTop: '10px'
              }}
            >
              INTERVIEW DATES
            </div>

            {/* Scrollable list with authentic calendar dates dynamically populated */}
            <div id="walkin-dates-options" style={{ maxHeight: '240px', overflowY: 'auto' }}>
              {displayWalkinDates.map(item => {
                const isSelected = selectedWalkinDates.has(item.id);
                const count = walkinDateCounts ? (walkinDateCounts[item.id] ?? item.count) : item.count;
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
                    <span className="option-label">{formatWalkinDate(item.label || item.id)}</span>
                    <span className="source-count">({count.toLocaleString()})</span>
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
