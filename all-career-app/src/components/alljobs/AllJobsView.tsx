import React, { useState, useEffect, useMemo, startTransition } from 'react';
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

  // Compute category counts for breakdown
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {
      technical: 0,
      non_technical: 0,
      pharma: 0,
      others: 0
    };
    for (const j of jobs) {
      const cat = (j.category || classifyJobCategory(j)).toLowerCase().replace(/[^a-z0-9]/g, '_');
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

  // Helper function for faceted counting
  const checkJobMatchWithout = (
    j: Job,
    excludeDim: 'none' | 'location' | 'role' | 'source' | 'walkin' | 'skill',
    term: string
  ): boolean => {
    // 1. Search Query
    if (term) {
      const hay = [j.title, j.company, j.location, j.role_search, j.description]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      if (!hay.includes(term)) return false;
    }

    // 2. Source Filter
    if (excludeDim !== 'source' && selectedSources.size > 0) {
      const src = (j.source || '').toLowerCase().trim();
      const match = Array.from(selectedSources).some(s => {
        if (s === 'telegram') return src.includes('telegram');
        if (s === 'images' || s === 'google_images') return src.includes('google') || src.includes('image');
        return src.includes(s);
      });
      if (!match) return false;
    }

    // 3. Date Filter
    if (selectedDateFilter !== 'all') {
      const dateStr = (j.fetchedAt || j.date || '').slice(0, 10);
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

    // 4. Location Filter
    if (excludeDim !== 'location' && selectedLocations.size > 0) {
      const loc = (j.location || '').toLowerCase();
      const match = Array.from(selectedLocations).some(l => loc.includes(l.toLowerCase()));
      if (!match) return false;
    }

    // 5. Role Category Filter
    if (excludeDim !== 'role' && selectedRoles.size > 0) {
      const titleLow = (j.title || '').toLowerCase();
      const roleSearchLow = (j.role_search || '').toLowerCase();
      const match = Array.from(selectedRoles).some(roleId => {
        const kws = ROLE_KEYWORDS[roleId] || [roleId.toLowerCase()];
        return kws.some(kw => titleLow.includes(kw) || roleSearchLow.includes(kw));
      });
      if (!match) return false;
    }

    // 6. Experience Filter (Moving Bar: -1 = Everything, 0 to 10 Yrs)
    if (expValue >= 0) {
      const [minE, maxE] = parseExperience(j.experience);
      if (minE === null) return false;

      if (exactExp) {
        if (expValue === 0) {
          if (minE !== 0 || (maxE !== null && maxE !== 0)) return false;
        } else if (expValue >= 10) {
          // If 10+, show all above 10 year experience like 15 or 30 or more
          const has10Plus = (minE >= 10) || (maxE !== null && maxE >= 10);
          if (!has10Plus) return false;
        } else {
          if (minE !== expValue || (maxE !== null && maxE !== expValue)) return false;
        }
      } else {
        if (expValue === 0) {
          if (minE !== 0) return false;
        } else if (expValue >= 10) {
          // If 10+, show all above 10 year experience like 15 or 30 or more
          const has10Plus = (minE >= 10) || (maxE !== null && maxE >= 10);
          if (!has10Plus) return false;
        } else {
          if (minE > expValue) return false;
          if (maxE !== null && expValue > maxE) return false;
        }
      }
    }

    // 7. Skills Filter
    if (excludeDim !== 'skill' && selectedSkills.size > 0) {
      const skillsText = [
        Array.isArray(j.skills) ? j.skills.join(' ') : '',
        j.title || '',
        j.description || ''
      ].join(' ').toLowerCase();
      const match = Array.from(selectedSkills).some(s => skillsText.includes(s.toLowerCase()));
      if (!match) return false;
    }

    // 8. Company Filter
    if (selectedCompanies.size > 0) {
      const comp = (j.company || '').toLowerCase();
      const match = Array.from(selectedCompanies).some(c => comp.includes(c.toLowerCase()));
      if (!match) return false;
    }

    // 9. Walkin Filter
    if (excludeDim !== 'walkin' && (walkinOnly || selectedWalkinDates.size > 0)) {
      if (!isWalkinJob(j)) return false;
      if (selectedWalkinDates.size > 0) {
        const jDates = getJobWalkinDates(j);
        const matchDate = Array.from(selectedWalkinDates).some(d => {
          const normD = formatWalkinDate(d);
          return jDates.some(jd => formatWalkinDate(jd) === normD || jd === d);
        });
        if (!matchDate) return false;
      }
    }

    // 10. Top Category Pills filter
    if (selectedCategory !== 'all') {
      const cCat = classifyJobCategory(j);
      if (selectedCategory === 'sales' && cCat !== 'Sales & Marketing') return false;
      if (selectedCategory === 'technical' && cCat !== 'Technical') return false;
      if (selectedCategory === 'non_technical' && cCat !== 'Non-Technical') return false;
      if (selectedCategory === 'banking' && cCat !== 'Banking & Finance') return false;
      if (selectedCategory === 'hr' && cCat !== 'HR & Staffing') return false;
      if (selectedCategory === 'pharma' && cCat !== 'Pharma') return false;
    }

    return true;
  };

  // Filtered jobs matching all 8 filters + search
  const filteredJobs = useMemo(() => {
    const term = searchTerm.toLowerCase().trim();
    const list = jobs.filter(j => checkJobMatchWithout(j, 'none', term));
    if (sortBy === 'company') {
      return list.slice().sort((a, b) => (a.company || '').localeCompare(b.company || ''));
    } else if (sortBy === 'oldest') {
      return list.slice().sort((a, b) => {
        const da = a.fetchedAt || a.date || '';
        const db = b.fetchedAt || b.date || '';
        return da.localeCompare(db);
      });
    }
    return list;
  }, [
    jobs,
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
    currentJobs.forEach(j => {
      const cat = classifyJobCategory(j);
      if (cat === 'Sales & Marketing') sales++;
      else if (cat === 'Technical') technical++;
      else if (cat === 'Non-Technical') nonTechnical++;
      else if (cat === 'Banking & Finance') banking++;
      else if (cat === 'HR & Staffing') hr++;
      else if (cat === 'Pharma') pharma++;
      else others++;
    });

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

  // Dynamic Faceted Counts for real-time counts across filters
  const dynamicCounts = useMemo(() => {
    const term = searchTerm.toLowerCase().trim();
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

    // 1. Location dynamic counts (jobs matching all filters EXCEPT location)
    for (const j of jobs) {
      if (checkJobMatchWithout(j, 'location', term)) {
        const locLow = (j.location || '').toLowerCase();
        for (const c of cities) {
          if (locLow.includes(c.toLowerCase())) {
            locCounts[c] = (locCounts[c] || 0) + 1;
          }
        }
      }
    }

    // 2. Role Category dynamic counts (jobs matching all filters EXCEPT role)
    for (const j of jobs) {
      if (checkJobMatchWithout(j, 'role', term)) {
        const titleLow = (j.title || '').toLowerCase();
        const roleSearchLow = (j.role_search || '').toLowerCase();
        for (const r of roleKeys) {
          const kws = ROLE_KEYWORDS[r] || [r.toLowerCase()];
          if (kws.some(kw => titleLow.includes(kw) || roleSearchLow.includes(kw))) {
            roleCounts[r] = (roleCounts[r] || 0) + 1;
          }
        }
      }
    }

    // 3. Source dynamic counts (jobs matching all filters EXCEPT source)
    for (const j of jobs) {
      if (checkJobMatchWithout(j, 'source', term)) {
        let src = (j.source || '').toLowerCase().trim();
        if (src.includes('google') || j.flyer_image_url) src = 'google_images';
        else if (src.includes('telegram')) src = src.includes('post') ? 'telegram_post' : 'telegram_message';
        srcCounts[src] = (srcCounts[src] || 0) + 1;
      }
    }

    // 4. Skills dynamic counts
    for (const j of jobs) {
      if (checkJobMatchWithout(j, 'skill', term)) {
        const skillsText = [Array.isArray(j.skills) ? j.skills.join(' ') : '', j.title || '', j.description || ''].join(' ').toLowerCase();
        for (const s of skillsList) {
          if (skillsText.includes(s)) {
            skillCounts[s] = (skillCounts[s] || 0) + 1;
          }
        }
      }
    }

    // 5. Walk-in dynamic counts
    const walkinDateCounts: Record<string, number> = {};
    let walkinTotalCount = 0;

    for (const j of jobs) {
      if (checkJobMatchWithout(j, 'walkin', term)) {
        if (isWalkinJob(j)) {
          walkinTotalCount++;
          const dates = getJobWalkinDates(j);
          for (const d of dates) {
            const normD = formatWalkinDate(d);
            if (normD) {
              walkinDateCounts[normD] = (walkinDateCounts[normD] || 0) + 1;
            }
          }
        }
      }
    }

    // Sort walk-in dates by count descending, ensuring top dates with actual jobs (no year)
    const walkinDateOptions = Object.entries(walkinDateCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([label, count]) => ({ id: label, label, count }));

    // Ensure selected dates are always present in the list
    for (const selDate of selectedWalkinDates) {
      const normSel = formatWalkinDate(selDate);
      if (!walkinDateOptions.some(o => o.id === selDate || o.id === normSel)) {
        walkinDateOptions.push({ id: selDate, label: normSel || selDate, count: walkinDateCounts[normSel] || 0 });
      }
    }

    return { locCounts, roleCounts, srcCounts, skillCounts, walkinTotalCount, walkinDateCounts, walkinDateOptions };
  }, [
    jobs,
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
    selectedCategory
  ]);

  const hasActiveFilters =
    selectedSources.size > 0 ||
    selectedDateFilter !== 'all' ||
    selectedLocations.size > 0 ||
    selectedRoles.size > 0 ||
    expValue >= 0 ||
    selectedSkills.size > 0 ||
    walkinOnly ||
    selectedWalkinDates.size > 0 ||
    selectedCategory !== 'all' ||
    Boolean(searchTerm);

  const clearAllFilters = () => {
    setSelectedSources(new Set());
    setSelectedDateFilter('all');
    setSelectedLocations(new Set());
    setSelectedRoles(new Set());
    setExpValue(-1);
    setExactExp(false);
    setSelectedSkills(new Set());
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
