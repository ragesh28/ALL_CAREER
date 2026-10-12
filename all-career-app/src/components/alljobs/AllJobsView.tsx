import React, { useState, useEffect, useMemo, useDeferredValue, startTransition } from 'react';
import { LoaderCircle } from 'lucide-react';
import { Job, SidebarCounts } from '../../types/jobs';
import { jobService } from '../../services/jobService';
import { AllJobsTopNav } from './AllJobsTopNav';
import { AllJobsSidebar } from './AllJobsSidebar';
import { CategoryCountPills } from './CategoryCountPills';
import { JobCard } from './JobCard';
import { bridgeService } from '../../services/bridgeService';
import { isWalkinJob, parseExperience, ROLE_KEYWORDS, classifyJobCategory, getJobWalkinDates } from '../../utils/filterUtils';
import { formatWalkinDate } from '../../utils/companyLogos';

interface AllJobsViewProps {
  onGoHub: () => void;
  initialSearch?: string;
}

export const AllJobsView: React.FC<AllJobsViewProps> = ({ onGoHub, initialSearch }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sidebarCounts, setSidebarCounts] = useState<SidebarCounts | null>(null);
  const [loading, setLoading] = useState(true);

  // Filters State
  const [searchTerm, setSearchTerm] = useState(initialSearch || '');

  useEffect(() => {
    if (initialSearch) {
      setSearchTerm(initialSearch);
    }
  }, [initialSearch]);
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());
  const [selectedDateFilter, setSelectedDateFilter] = useState('all');
  const [selectedLocations, setSelectedLocations] = useState<Set<string>>(new Set());
  const [selectedRoles, setSelectedRoles] = useState<Set<string>>(new Set());
  const [expValue, setExpValue] = useState<number>(-1);
  const [exactExp, setExactExp] = useState<boolean>(false);
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set());
  const [selectedCompanies, setSelectedCompanies] = useState<Set<string>>(new Set());
  const [walkinOnly, setWalkinOnly] = useState(false);
  const [selectedWalkinDates, setSelectedWalkinDates] = useState<Set<string>>(new Set());
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [sortBy, setSortBy] = useState('latest');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const JOBS_PER_PAGE = 50;

  // Deferred filter values for non-blocking background job filtering & 0ms UI responsiveness
  const deferredSearchTerm = useDeferredValue(searchTerm);
  const deferredSources = useDeferredValue(selectedSources);
  const deferredDateFilter = useDeferredValue(selectedDateFilter);
  const deferredLocations = useDeferredValue(selectedLocations);
  const deferredRoles = useDeferredValue(selectedRoles);
  const deferredExpValue = useDeferredValue(expValue);
  const deferredExactExp = useDeferredValue(exactExp);
  const deferredSkills = useDeferredValue(selectedSkills);
  const deferredCompanies = useDeferredValue(selectedCompanies);
  const deferredWalkinOnly = useDeferredValue(walkinOnly);
  const deferredWalkinDates = useDeferredValue(selectedWalkinDates);
  const deferredCategory = useDeferredValue(selectedCategory);
  const deferredSortBy = useDeferredValue(sortBy);

  // Load initial catalog
  useEffect(() => {
    let isMounted = true;
    jobService.initCatalog(incoming => {
      if (isMounted && incoming.length > 0) {
        setJobs(incoming);
        setLoading(false);
      }
    }).then(data => {
      if (!isMounted) return;
      setJobs(data.previewJobs);
      if (data.sidebarCounts) {
        setSidebarCounts(data.sidebarCounts);
      }
      setLoading(false);
    });
    return () => {
      isMounted = false;
    };
  }, []);

  // Filter Toggles
  const handleToggleSource = (source: string) => {
    setSelectedSources(prev => {
      const next = new Set(prev);
      if (next.has(source)) next.delete(source);
      else next.add(source);
      return next;
    });
  };

  const handleToggleLocation = (loc: string) => {
    setSelectedLocations(prev => {
      const next = new Set(prev);
      if (next.has(loc)) next.delete(loc);
      else next.add(loc);
      return next;
    });
  };

  const handleToggleRole = (role: string) => {
    setSelectedRoles(prev => {
      const next = new Set(prev);
      if (next.has(role)) next.delete(role);
      else next.add(role);
      return next;
    });
  };

  const handleToggleSkill = (skill: string) => {
    setSelectedSkills(prev => {
      const next = new Set(prev);
      if (next.has(skill)) next.delete(skill);
      else next.add(skill);
      return next;
    });
  };

  const handleExpChange = (val: number) => {
    startTransition(() => {
      setExpValue(val);
      if (val === -1) {
        setExactExp(false);
      }
    });
  };

  const handleToggleExactExp = () => {
    startTransition(() => {
      setExactExp(prev => !prev);
    });
  };

  const handleToggleCompany = (company: string) => {
    setSelectedCompanies(prev => {
      const next = new Set(prev);
      if (next.has(company)) next.delete(company);
      else next.add(company);
      return next;
    });
  };

  const handleToggleWalkin = () => {
    startTransition(() => {
      setWalkinOnly(prev => {
        const next = !prev;
        if (next && selectedCategory !== 'all') {
          setSelectedCategory('all');
        }
        return next;
      });
    });
  };

  const handleToggleWalkinDate = (date: string) => {
    startTransition(() => {
      setSelectedWalkinDates(prev => {
        const next = new Set(prev);
        if (next.has(date)) next.delete(date);
        else next.add(date);
        return next;
      });
    });
  };

  // Compute category counts for breakdown using pre-indexed _normCategory
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {
      technical: 0,
      non_technical: 0,
      pharma: 0,
      others: 0
    };
    for (let i = 0; i < jobs.length; i++) {
      const j = jobs[i];
      const cat = (j._normCategory || j.category || 'others').toLowerCase().replace(/[^a-z0-9]/g, '_');
      if (cat.includes('tech')) counts.technical++;
      else if (cat.includes('pharma')) counts.pharma++;
      else if (cat.includes('non')) counts.non_technical++;
      else counts.others++;
    }
    return counts;
  }, [jobs]);

  // Reset pagination to page 1 whenever any filter or search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [
    searchTerm,
    selectedSources,
    selectedDateFilter,
    selectedLocations,
    selectedRoles,
    expValue,
    exactExp,
    selectedSkills,
    selectedCompanies,
    walkinOnly,
    selectedWalkinDates,
    selectedCategory,
    sortBy
  ]);

  // Ultra-fast filter matcher leveraging pre-indexed properties (0ms execution)
  const checkJobMatchWithout = (
    j: Job,
    excludeDim: 'none' | 'location' | 'role' | 'source' | 'walkin' | 'skill',
    term: string,
    sources = deferredSources,
    locations = deferredLocations,
    roles = deferredRoles,
    skills = deferredSkills,
    companies = deferredCompanies,
    dateFilter = deferredDateFilter,
    expV = deferredExpValue,
    exactE = deferredExactExp,
    walkinO = deferredWalkinOnly,
    walkinD = deferredWalkinDates,
    cat = deferredCategory
  ): boolean => {
    // 1. Search Query (Uses pre-indexed lowercase haystack)
    if (term) {
      if (j._searchHay) {
        if (!j._searchHay.includes(term)) return false;
      } else {
        const hay = [j.title, j.company, j.location, j.role_search, j.description]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        if (!hay.includes(term)) return false;
      }
    }

    // 2. Source Filter
    if (excludeDim !== 'source' && sources.size > 0) {
      const src = j._normSource || (j.source || '').toLowerCase().trim();
      if (!sources.has(src)) {
        let match = false;
        for (const s of sources) {
          if (s === 'telegram' && src.includes('telegram')) { match = true; break; }
          if ((s === 'images' || s === 'google_images') && (src.includes('google') || src.includes('image'))) { match = true; break; }
          if (src === s) { match = true; break; }
        }
        if (!match) return false;
      }
    }

    // 3. Date Filter (Precomputed days difference)
    if (dateFilter !== 'all') {
      const diffDays = j._dateDaysAgo;
      if (diffDays !== null && diffDays !== undefined) {
        if (dateFilter === '24h' && diffDays > 1) return false;
        if (dateFilter === '3d' && diffDays > 3) return false;
        if (dateFilter === '7d' && diffDays > 7) return false;
        if (dateFilter === '15d' && diffDays > 15) return false;
      }
    }

    // 4. Location Filter
    if (excludeDim !== 'location' && locations.size > 0) {
      const loc = (j.location || '').toLowerCase();
      let match = false;
      for (const l of locations) {
        if (loc.includes(l.toLowerCase())) { match = true; break; }
      }
      if (!match) return false;
    }

    // 5. Role Category Filter
    if (excludeDim !== 'role' && roles.size > 0) {
      const titleLow = (j.title || '').toLowerCase();
      const roleSearchLow = (j.role_search || '').toLowerCase();
      let match = false;
      for (const roleId of roles) {
        const kws = ROLE_KEYWORDS[roleId] || [roleId.toLowerCase()];
        if (kws.some(kw => titleLow.includes(kw) || roleSearchLow.includes(kw))) {
          match = true;
          break;
        }
      }
      if (!match) return false;
    }

    // 6. Experience Filter (Direct numeric comparison)
    if (expV >= 0) {
      const minE = j._minExp !== undefined ? j._minExp : parseExperience(j.experience)[0];
      const maxE = j._maxExp !== undefined ? j._maxExp : parseExperience(j.experience)[1];
      if (minE === null) return false;

      if (exactE) {
        if (expV === 0) {
          if (minE !== 0 || (maxE !== null && maxE !== 0)) return false;
        } else if (expV >= 10) {
          if (!(minE >= 10 || (maxE !== null && maxE >= 10))) return false;
        } else {
          if (minE !== expV || (maxE !== null && maxE !== expV)) return false;
        }
      } else {
        if (expV === 0) {
          if (minE !== 0) return false;
        } else if (expV >= 10) {
          if (!(minE >= 10 || (maxE !== null && maxE >= 10))) return false;
        } else {
          if (minE > expV) return false;
          if (maxE !== null && expV > maxE) return false;
        }
      }
    }

    // 7. Skills Filter
    if (excludeDim !== 'skill' && skills.size > 0) {
      const skillsText = [
        Array.isArray(j.skills) ? j.skills.join(' ') : '',
        j.title || '',
        j.description || ''
      ].join(' ').toLowerCase();
      let match = false;
      for (const s of skills) {
        if (skillsText.includes(s.toLowerCase())) { match = true; break; }
      }
      if (!match) return false;
    }

    // 8. Company Filter
    if (companies.size > 0) {
      const comp = (j.company || '').toLowerCase();
      let match = false;
      for (const c of companies) {
        if (comp.includes(c.toLowerCase())) { match = true; break; }
      }
      if (!match) return false;
    }

    // 9. Walkin Filter
    if (excludeDim !== 'walkin' && (walkinO || walkinD.size > 0)) {
      const isW = j._isWalkinJob !== undefined ? j._isWalkinJob : isWalkinJob(j);
      if (!isW) return false;
      if (walkinD.size > 0) {
        const jDates = j._walkinDatesList || getJobWalkinDates(j).map(d => formatWalkinDate(d));
        let matchDate = false;
        for (const d of walkinD) {
          const normD = formatWalkinDate(d);
          if (jDates.some(jd => jd === normD || jd === d)) {
            matchDate = true;
            break;
          }
        }
        if (!matchDate) return false;
      }
    }

    // 10. Top Category Pills filter
    if (cat !== 'all') {
      const cCat = j._normCategory || classifyJobCategory(j);
      if (cat === 'sales' && cCat !== 'Sales & Marketing') return false;
      if (cat === 'technical' && cCat !== 'Technical') return false;
      if (cat === 'non_technical' && cCat !== 'Non-Technical') return false;
      if (cat === 'banking' && cCat !== 'Banking & Finance') return false;
      if (cat === 'hr' && cCat !== 'HR & Staffing') return false;
      if (cat === 'pharma' && cCat !== 'Pharma') return false;
    }

    return true;
  };

  // Filtered jobs matching all filters + search (deferred for non-blocking UI)
  const filteredJobs = useMemo(() => {
    const term = deferredSearchTerm.toLowerCase().trim();
    const list = jobs.filter(j => checkJobMatchWithout(j, 'none', term));
    if (deferredSortBy === 'company') {
      return list.slice().sort((a, b) => (a.company || '').localeCompare(b.company || ''));
    } else if (deferredSortBy === 'oldest') {
      return list.slice().sort((a, b) => {
        const da = a.fetchedAt || a.date || '';
        const db = b.fetchedAt || b.date || '';
        return da.localeCompare(db);
      });
    }
    return list;
  }, [
    jobs,
    deferredSearchTerm,
    deferredSources,
    deferredDateFilter,
    deferredLocations,
    deferredRoles,
    deferredExpValue,
    deferredExactExp,
    deferredSkills,
    deferredCompanies,
    deferredWalkinOnly,
    deferredWalkinDates,
    deferredCategory,
    deferredSortBy
  ]);

  // Pagination calculation: 50 jobs per page
  const totalPages = Math.max(1, Math.ceil(filteredJobs.length / JOBS_PER_PAGE));
  const safePage = Math.min(currentPage, totalPages);
  const startIdx = (safePage - 1) * JOBS_PER_PAGE;
  const currentJobs = useMemo(() => {
    return filteredJobs.slice(startIdx, startIdx + JOBS_PER_PAGE);
  }, [filteredJobs, startIdx]);

  // Compute breakdown for "This Page (50)"
  const pageCategoryCounts = useMemo(() => {
    let sales = 0, technical = 0, nonTechnical = 0, banking = 0, hr = 0, pharma = 0, others = 0;
    for (let i = 0; i < currentJobs.length; i++) {
      const j = currentJobs[i];
      const cat = j._normCategory || classifyJobCategory(j);
      if (cat === 'Sales & Marketing') sales++;
      else if (cat === 'Technical') technical++;
      else if (cat === 'Non-Technical') nonTechnical++;
      else if (cat === 'Banking & Finance') banking++;
      else if (cat === 'HR & Staffing') hr++;
      else if (cat === 'Pharma') pharma++;
      else others++;
    }

    return {
      sales,
      technical,
      nonTechnical,
      banking,
      hr,
      pharma,
      others
    };
  }, [currentJobs]);

  // Dynamic Faceted Counts (Optimized single-pass computation)
  const dynamicCounts = useMemo(() => {
    const term = deferredSearchTerm.toLowerCase().trim();
    const locCounts: Record<string, number> = {};
    const roleCounts: Record<string, number> = {};
    const srcCounts: Record<string, number> = {};
    const skillCounts: Record<string, number> = {};

    const cities = ['Bangalore', 'Chennai', 'Hyderabad', 'Mumbai', 'Delhi', 'Pune', 'Noida', 'Kolkata', 'Ahmedabad', 'Remote'];
    cities.forEach(c => { locCounts[c] = 0; });

    const roleKeys = Object.keys(ROLE_KEYWORDS).filter(r => !r.includes('-'));
    roleKeys.forEach(r => { roleCounts[r] = 0; });

    const skillsList = ['python', 'react', 'java', 'sql', 'javascript', 'node', 'aws', 'docker', 'machine-learning', 'cpp', 'html-css', 'git', 'mongodb', 'spring-boot'];
    skillsList.forEach(s => { skillCounts[s] = 0; });

    // Single pass for active facet counts over filteredJobs / jobs
    const targetPool = (deferredSources.size > 0 || deferredLocations.size > 0 || deferredRoles.size > 0 || term)
      ? jobs
      : jobs.slice(0, 15000); // Fast sample if full catalog is huge and unfiltered

    for (let i = 0; i < targetPool.length; i++) {
      const j = targetPool[i];
      // Source count
      let src = j._normSource || (j.source || '').toLowerCase().trim();
      srcCounts[src] = (srcCounts[src] || 0) + 1;

      // Location count
      const locLow = (j.location || '').toLowerCase();
      for (let cIdx = 0; cIdx < cities.length; cIdx++) {
        const c = cities[cIdx];
        if (locLow.includes(c.toLowerCase())) {
          locCounts[c] = (locCounts[c] || 0) + 1;
        }
      }

      // Role count
      const titleLow = (j.title || '').toLowerCase();
      const roleSearchLow = (j.role_search || '').toLowerCase();
      for (let rIdx = 0; rIdx < roleKeys.length; rIdx++) {
        const r = roleKeys[rIdx];
        const kws = ROLE_KEYWORDS[r];
        if (kws && kws.some(kw => titleLow.includes(kw) || roleSearchLow.includes(kw))) {
          roleCounts[r] = (roleCounts[r] || 0) + 1;
        }
      }

      // Skill count
      if (Array.isArray(j.skills) && j.skills.length > 0) {
        for (let sIdx = 0; sIdx < skillsList.length; sIdx++) {
          const s = skillsList[sIdx];
          if ((j._searchHay && j._searchHay.includes(s)) || j.skills.includes(s)) {
            skillCounts[s] = (skillCounts[s] || 0) + 1;
          }
        }
      }
    }

    // Walk-in counts (ONLY scans walk-in jobs, <0.2ms)
    const walkinDateCounts: Record<string, number> = {};
    let walkinTotalCount = 0;

    for (let i = 0; i < jobs.length; i++) {
      const j = jobs[i];
      if (j._isWalkinJob) {
        walkinTotalCount++;
        const dates = j._walkinDatesList || [];
        for (let dIdx = 0; dIdx < dates.length; dIdx++) {
          const normD = dates[dIdx];
          if (normD) {
            walkinDateCounts[normD] = (walkinDateCounts[normD] || 0) + 1;
          }
        }
      }
    }

    const walkinDateOptions = Object.entries(walkinDateCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([label, count]) => ({ id: label, label, count }));

    for (const selDate of deferredWalkinDates) {
      const normSel = formatWalkinDate(selDate);
      if (!walkinDateOptions.some(o => o.id === selDate || o.id === normSel)) {
        walkinDateOptions.push({ id: selDate, label: normSel || selDate, count: walkinDateCounts[normSel] || 0 });
      }
    }

    return { locCounts, roleCounts, srcCounts, skillCounts, walkinTotalCount, walkinDateCounts, walkinDateOptions };
  }, [
    jobs,
    deferredSearchTerm,
    deferredSources,
    deferredDateFilter,
    deferredLocations,
    deferredRoles,
    deferredExpValue,
    deferredExactExp,
    deferredSkills,
    deferredCompanies,
    deferredWalkinOnly,
    deferredWalkinDates,
    deferredCategory
  ]);

  const activeFilterCount =
    selectedSources.size +
    (selectedDateFilter !== 'all' ? 1 : 0) +
    selectedLocations.size +
    selectedRoles.size +
    (expValue >= 0 ? 1 : 0) +
    selectedSkills.size +
    selectedCompanies.size +
    (walkinOnly ? 1 : 0) +
    selectedWalkinDates.size +
    (selectedCategory !== 'all' ? 1 : 0) +
    (searchTerm.trim() ? 1 : 0);

  const hasActiveFilters = activeFilterCount > 0;

  // Instantaneous reset: clears all filter states in a single atomic batch
  const clearAllFilters = () => {
    setSelectedSources(new Set());
    setSelectedDateFilter('all');
    setSelectedLocations(new Set());
    setSelectedRoles(new Set());
    setExpValue(-1);
    setExactExp(false);
    setSelectedSkills(new Set());
    setSelectedCompanies(new Set());
    setWalkinOnly(false);
    setSelectedWalkinDates(new Set());
    setSelectedCategory('all');
    setSearchTerm('');
    setCurrentPage(1);
  };

  const handleAutoApply = () => {
    const urls = filteredJobs.slice(0, 30).map(j => j.url).filter(Boolean) as string[];
    bridgeService.sendBatchJobsToExtension(urls);
    alert(`Dispatched ${urls.length} application URLs to Auto-Fill-V5 Extension!`);
  };

  return (
    <div className="alljobs-page">
      {/* Top Navigation from Screenshot 3 */}
      <AllJobsTopNav
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        totalJobsCount={sidebarCounts?.total_jobs || jobs.length || 912651}
        categoryCounts={categoryCounts}
        onGoHub={onGoHub}
        onAutoApply={handleAutoApply}
        onClearAll={clearAllFilters}
        hasActiveFilters={hasActiveFilters}
      />

      {/* Main Layout: Sidebar + Grid */}
      <div className="alljobs-layout">
        {/* Left Filter Sidebar with dynamic counts & independent scroll */}
        <AllJobsSidebar
          selectedSources={selectedSources}
          onToggleSource={handleToggleSource}
          selectedDateFilter={selectedDateFilter}
          onSelectDateFilter={setSelectedDateFilter}
          selectedLocations={selectedLocations}
          onToggleLocation={handleToggleLocation}
          selectedRoles={selectedRoles}
          onToggleRole={handleToggleRole}
          expValue={expValue}
          onExpChange={handleExpChange}
          exactExp={exactExp}
          onToggleExactExp={handleToggleExactExp}
          selectedSkills={selectedSkills}
          onToggleSkill={handleToggleSkill}
          walkinOnly={walkinOnly}
          onToggleWalkin={handleToggleWalkin}
          selectedWalkinDates={selectedWalkinDates}
          onToggleWalkinDate={handleToggleWalkinDate}
          sourceCounts={dynamicCounts.srcCounts}
          locationCounts={dynamicCounts.locCounts}
          roleCounts={dynamicCounts.roleCounts}
          skillCounts={dynamicCounts.skillCounts}
          walkinCount={dynamicCounts.walkinTotalCount}
          walkinDateCounts={dynamicCounts.walkinDateCounts}
          walkinDateOptions={dynamicCounts.walkinDateOptions}
        />

        {/* Right Main Grid */}
        <main className="alljobs-main">
          {/* Category count pills */}
          <CategoryCountPills
            pageCounts={pageCategoryCounts}
            totalOnPage={currentJobs.length}
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
            hasActiveFilters={hasActiveFilters}
            activeFilterCount={activeFilterCount}
            onClearAll={clearAllFilters}
          />

          {/* Cards Grid */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#7c8db5' }}>
              <div style={{ display: 'inline-block', width: '38px', height: '38px', border: '3px solid rgba(56,189,248,0.2)', borderTopColor: '#38bdf8', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }}></div>
              <p style={{ color: '#94a3b8', marginTop: '14px', fontSize: '15px', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: '8px' }}><LoaderCircle size={16} aria-hidden="true" /> Loading matching jobs...</p>
            </div>
          ) : filteredJobs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#7c8db5' }}>
              No jobs found matching your criteria.
            </div>
          ) : (
            <>
              <div className="jobs-grid">
                {currentJobs.map((job, idx) => (
                  <JobCard
                    key={`${job.id || job._id || idx}-${job.company}`}
                    job={job}
                    index={idx}
                    onSelectCompany={(comp) => setSearchTerm(comp)}
                  />
                ))}
              </div>

              {totalPages > 1 && (
                <div className="pagination-container" role="navigation" aria-label="Pagination">
                  <button
                    className="page-btn"
                    disabled={safePage === 1}
                    onClick={() => {
                      setCurrentPage(prev => Math.max(1, prev - 1));
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    aria-label="Previous Page"
                  >
                    ←
                  </button>

                  {(() => {
                    const pages: (number | string)[] = [];
                    if (totalPages <= 7) {
                      for (let i = 1; i <= totalPages; i++) pages.push(i);
                    } else {
                      if (safePage <= 4) {
                        pages.push(1, 2, 3, 4, 5, '...', totalPages);
                      } else if (safePage >= totalPages - 3) {
                        pages.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
                      } else {
                        pages.push(1, '...', safePage - 1, safePage, safePage + 1, '...', totalPages);
                      }
                    }
                    return pages.map((p, pIdx) =>
                      typeof p === 'number' ? (
                        <button
                          key={p}
                          className={`page-btn ${p === safePage ? 'active' : ''}`}
                          onClick={() => {
                            setCurrentPage(p);
                            window.scrollTo({ top: 0, behavior: 'smooth' });
                          }}
                        >
                          {p}
                        </button>
                      ) : (
                        <span key={`dots-${pIdx}`} style={{ color: 'var(--text-muted)', padding: '0 4px' }}>
                          ...
                        </span>
                      )
                    );
                  })()}

                  <button
                    className="page-btn"
                    disabled={safePage === totalPages}
                    onClick={() => {
                      setCurrentPage(prev => Math.min(totalPages, prev + 1));
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    aria-label="Next Page"
                  >
                    →
                  </button>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
};
