import { MobileFilters } from '../common/MobileFilters';
import React, { useState, useEffect, useMemo, useRef, useDeferredValue, startTransition } from 'react';
import { LoaderCircle } from 'lucide-react';
import { Job } from '../../types/jobs';
import { jobService } from '../../services/jobService';
import { AllJobsTopNav } from './AllJobsTopNav';
import { AllJobsSidebar } from './AllJobsSidebar';
import { CategoryCountPills } from './CategoryCountPills';
import { JobCard } from './JobCard';
import { bridgeService } from '../../services/bridgeService';
import { isWalkinJob, parseExperience, ROLE_KEYWORDS, classifyJobCategory, getJobWalkinDates, isOtherSource, MONTH_SHORT, SOFTWARE_TECHNICAL } from '../../utils/filterUtils';
import { formatWalkinDate } from '../../utils/companyLogos';
import { CatalogSummary, matchesCatalogLocation, matchesCatalogSource } from '../../services/catalogTypes';
import { calculateWalkinFacets, WalkinFacetInput, WalkinFacets } from '../../services/walkinFacets';

interface AllJobsViewProps {
  onGoHub: () => void;
  initialSearch?: string;
}

export const AllJobsView: React.FC<AllJobsViewProps> = ({ onGoHub, initialSearch }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState(false);
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [summary, setSummary] = useState<CatalogSummary | null>(null);
  const summaryRef = useRef<CatalogSummary | null>(null);
  const [facetResult, setFacetResult] = useState<{ input: WalkinFacetInput; facets: WalkinFacets } | null>(null);
  const [batchLoading, setBatchLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [batchError, setBatchError] = useState(false);
  const batchFailures = useRef(0);
  const batchTarget = useRef(50);
  const lastCatalogCheck = useRef(0);

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

  const applySummary = (next: CatalogSummary) => {
    if (summaryRef.current !== next) {
      summaryRef.current = next;
      setSummary(next);
      setJobs(jobService.getAllJobs());
    }
    setCatalogError(false);
    setCatalogLoading(false);
  };

  useEffect(() => {
    let mounted = true;
    void jobService.loadPreview().catch(() => {}).finally(() => {
      if (!mounted) return;
      setJobs(jobService.getAllJobs());
    });
    return () => { mounted = false; };
  }, []);

  // Retry only the unavailable summary. The preview can render independently.
  useEffect(() => {
    let mounted = true;
    let failures = 0;
    let retry: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => {
      lastCatalogCheck.current = Date.now();
      setCatalogLoading(true);
      const next = await jobService.refreshSummary();
      if (!mounted) return;
      if (next) {
        applySummary(next);
        return;
      }
      setCatalogLoading(false);
      setCatalogError(true);
      retry = setTimeout(refresh, Math.min(30000, 4000 * 2 ** failures++));
    };
    void refresh();
    return () => {
      mounted = false;
      clearTimeout(retry);
    };
  }, [catalogAttempt]);

  useEffect(() => {
    const refresh = () => setCatalogAttempt(value => value + 1);
    const restored = (event: PageTransitionEvent) => { if (event.persisted) refresh(); };
    const visible = () => {
      if (document.visibilityState === 'visible' && Date.now() - lastCatalogCheck.current >= 60000) refresh();
    };
    window.addEventListener('online', refresh);
    window.addEventListener('pageshow', restored);
    document.addEventListener('visibilitychange', visible);
    return () => {
      window.removeEventListener('online', refresh);
      window.removeEventListener('pageshow', restored);
      document.removeEventListener('visibilitychange', visible);
    };
  }, []);

  const facetInput = useMemo<WalkinFacetInput | null>(() => summary ? {
    summary,
    locations: [...selectedLocations],
    sources: [...selectedSources],
    dates: [...selectedWalkinDates],
  } : null, [summary, selectedLocations, selectedSources, selectedWalkinDates]);
  const summaryFacets = facetResult && facetResult.input === facetInput ? facetResult.facets : null;

  // A failed or blocked worker can calculate the same dates from the summary
  // on the main thread. A late response from an old filter is ignored.
  useEffect(() => {
    if (!facetInput) return;
    let worker: Worker | undefined;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    let finished = false;
    const finish = (facets?: WalkinFacets) => {
      if (finished) return;
      finished = true;
      clearTimeout(timeout);
      worker?.terminate();
      setFacetResult({ input: facetInput, facets: facets ?? calculateWalkinFacets(facetInput) });
    };
    try {
      worker = new Worker(new URL('../../services/walkinSummary.worker.ts', import.meta.url), { type: 'module' });
      worker.onmessage = ({ data }: MessageEvent<WalkinFacets>) => finish(data);
      worker.onerror = event => { event.preventDefault(); finish(); };
      worker.onmessageerror = () => finish();
      timeout = setTimeout(() => finish(), 6000);
      worker.postMessage(facetInput);
    } catch {
      finish();
    }
    return () => {
      finished = true;
      clearTimeout(timeout);
      worker?.terminate();
    };
  }, [facetInput]);

  const loadController = useRef<AbortController | null>(null);
  const requestBatch = async (target: number, refreshCatalog = false) => {
    loadController.current?.abort();
    const controller = new AbortController();
    loadController.current = controller;
    batchTarget.current = target;
    setBatchLoading(true);

    try {
      if (refreshCatalog) {
        const latest = await jobService.refreshSummary();
        if (controller.signal.aborted) return null;
        if (latest) {
          const changed = latest.manifest !== summaryRef.current?.manifest;
          applySummary(latest);
          if (changed) return null; // The new snapshot starts its own batch.
        }
      }
      const result = await jobService.loadUntil(
        { sources: [...deferredSources], locations: [...deferredLocations], walkin: deferredWalkinOnly || deferredWalkinDates.size > 0, postedDays: ({ '24h': 1, '3d': 3, '7d': 7, '15d': 15 } as Record<string, number>)[deferredDateFilter] },
        job => checkJobMatchWithout(job, 'none', deferredSearchTerm.toLowerCase().trim()),
        target,
        incoming => { if (!controller.signal.aborted) setJobs(incoming); },
        controller.signal
      );
      if (controller.signal.aborted) return null;
      setJobs(result.jobs);
      setHasMore(result.hasMore);
      setBatchError(result.error);
      batchFailures.current = result.error ? batchFailures.current + 1 : 0;
      return result;
    } catch {
      if (!controller.signal.aborted) {
        batchFailures.current++;
        setHasMore(true);
        setBatchError(true);
      }
      return null;
    } finally {
      if (!controller.signal.aborted) setBatchLoading(false);
    }
  };

  const retryBatch = () => { void requestBatch(batchTarget.current, true); };
  useEffect(() => {
    if (!batchError || batchLoading || !summary) return;
    const delay = Math.min(30000, 4000 * 2 ** Math.max(0, batchFailures.current - 1));
    const retry = setTimeout(retryBatch, delay);
    return () => clearTimeout(retry);
  }, [batchError, batchLoading, summary, deferredSources, deferredLocations, deferredWalkinOnly, deferredWalkinDates, deferredSearchTerm, deferredRoles, deferredSkills, deferredCompanies, deferredDateFilter, deferredExpValue, deferredExactExp, deferredCategory]);

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
      const cat = j._normCategory || classifyJobCategory(j);
      if (cat === SOFTWARE_TECHNICAL) counts.technical++;
      else if (cat === 'Pharma') counts.pharma++;
      else if (cat === 'Non-Technical') counts.non_technical++;
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

    // 2. Use the same source aliases as the catalog page lookup.
    if (excludeDim !== 'source' && !matchesCatalogSource(j._normSource || (j.source || '').toLowerCase().trim(), sources)) return false;

    // 3. Date Filter (Precomputed days difference)
    if (dateFilter !== 'all') {
      const diffDays = j._dateDaysAgo;
      if (diffDays === null || diffDays === undefined) return false;
      if (diffDays !== null && diffDays !== undefined) {
        if (dateFilter === '24h' && diffDays > 1) return false;
        if (dateFilter === '3d' && diffDays > 3) return false;
        if (dateFilter === '7d' && diffDays > 7) return false;
        if (dateFilter === '15d' && diffDays > 15) return false;
      }
    }

    // 4. Use the same location matching as the catalog page lookup.
    if (excludeDim !== 'location' && !matchesCatalogLocation(j.location || '', locations)) return false;

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
        const jDates = j._walkinDatesList || getJobWalkinDates(j);
        let matchDate = false;
        for (const d of walkinD) {
          if (jDates.includes(d)) {
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
      if (cat === 'software_technical' && cCat !== SOFTWARE_TECHNICAL) return false;
      if (cat === 'non_technical' && cCat !== 'Non-Technical') return false;
      if (cat === 'banking' && cCat !== 'Banking & Finance') return false;
      if (cat === 'hr' && cCat !== 'HR & Staffing') return false;
      if (cat === 'pharma' && cCat !== 'Pharma') return false;
      if (cat === 'others' && cCat !== 'Others' && cCat !== 'Electrical') return false;
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

  useEffect(() => {
    if (!summary) return;
    loadController.current?.abort();
    batchFailures.current = 0;
    setBatchLoading(true);
    setBatchError(false);
    const timer = setTimeout(() => { void requestBatch(JOBS_PER_PAGE); }, 150);
    return () => {
      clearTimeout(timer);
      loadController.current?.abort();
    };
  }, [summary, deferredSources, deferredLocations, deferredWalkinOnly, deferredWalkinDates, deferredSearchTerm, deferredRoles, deferredSkills, deferredCompanies, deferredDateFilter, deferredExpValue, deferredExactExp, deferredCategory]);

  // Pagination calculation: 50 jobs per page
  const totalPages = Math.max(1, Math.ceil(filteredJobs.length / JOBS_PER_PAGE));
  const safePage = Math.min(currentPage, totalPages);
  const availablePages = Math.max(totalPages, hasMore && filteredJobs.length >= currentPage * JOBS_PER_PAGE ? currentPage + 1 : totalPages);
  const goToPage = async (page: number) => {
    if (batchLoading || page < 1 || page > availablePages) return;
    if (hasMore && filteredJobs.length < page * JOBS_PER_PAGE) {
      const result = await requestBatch(page * JOBS_PER_PAGE);
      if (!result || result.error || result.jobs.filter(job => checkJobMatchWithout(job, 'none', deferredSearchTerm.toLowerCase().trim())).length <= (page - 1) * JOBS_PER_PAGE) return;
    }
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const startIdx = (safePage - 1) * JOBS_PER_PAGE;
  const currentJobs = useMemo(() => {
    return filteredJobs.slice(startIdx, startIdx + JOBS_PER_PAGE);
  }, [filteredJobs, startIdx]);

  // Compute breakdown for "This Page (50)"
  const pageCategoryCounts = useMemo(() => {
    let sales = 0, softwareTechnical = 0, nonTechnical = 0, banking = 0, hr = 0, pharma = 0, others = 0;
    for (let i = 0; i < currentJobs.length; i++) {
      const j = currentJobs[i];
      const cat = j._normCategory || classifyJobCategory(j);
      if (cat === 'Sales & Marketing') sales++;
      else if (cat === SOFTWARE_TECHNICAL) softwareTechnical++;
      else if (cat === 'Non-Technical') nonTechnical++;
      else if (cat === 'Banking & Finance') banking++;
      else if (cat === 'HR & Staffing') hr++;
      else if (cat === 'Pharma') pharma++;
      else others++;
    }

    return {
      sales,
      softwareTechnical,
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
    const targetPool = jobs;

    for (let i = 0; i < targetPool.length; i++) {
      const j = targetPool[i];
      // Source count
      let src = j._normSource || (j.source || '').toLowerCase().trim();
      srcCounts[src] = (srcCounts[src] || 0) + 1;
      if (src !== 'other' && isOtherSource(src)) {
        srcCounts['other'] = (srcCounts['other'] || 0) + 1;
      }

      // Location count
      if (checkJobMatchWithout(j, 'location', term)) {
        const locLow = (j.location || '').toLowerCase();
        for (const c of cities) {
          if (locLow.includes(c.toLowerCase()) || (c === 'Bangalore' && locLow.includes('bengaluru'))) {
            locCounts[c] = (locCounts[c] || 0) + 1;
          }
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

    return { locCounts, roleCounts, srcCounts, skillCounts };
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
  const canUseWalkinSummary = !!summary && !searchTerm.trim() && selectedRoles.size === 0 && selectedSkills.size === 0 && selectedCompanies.size === 0 && selectedDateFilter === 'all' && expValue < 0 && selectedCategory === 'all';
  const catalogFacets = useMemo(() => {
    const locations: Record<string, number> = {}, sources: Record<string, number> = {};
    for (const [source, locs] of Object.entries(summary?.source_locations || {})) {
      const sourceMatch = matchesCatalogSource(source, selectedSources);
      for (const [city, count] of Object.entries(locs)) {
        if (sourceMatch) locations[city] = (locations[city] || 0) + count;
        if (matchesCatalogLocation(city, selectedLocations)) sources[source] = (sources[source] || 0) + count;
      }
    }
    return { locations, sources };
  }, [summary, selectedLocations, selectedSources]);
  const useWalkinFacets = canUseWalkinSummary && (walkinOnly || selectedWalkinDates.size > 0);
  const displayedSources = canUseWalkinSummary ? (useWalkinFacets ? summaryFacets?.sources || {} : catalogFacets.sources) : dynamicCounts.srcCounts;
  const sourceFacets = { ...displayedSources };
  sourceFacets.telegram = Object.entries(displayedSources).filter(([s]) => s.includes('telegram')).reduce((sum, [, n]) => sum + n, 0);
  if (canUseWalkinSummary) sourceFacets.other = Object.entries(displayedSources).filter(([s]) => s === 'other' || isOtherSource(s)).reduce((sum, [, n]) => sum + n, 0);
  const walkinDateOptions = useMemo(() => {
    if (!summaryFacets) return [];
    const dates = { ...summaryFacets.dates };
    for (const selected of selectedWalkinDates) dates[selected] ??= 0;
    const today = new Date();
    const offset = today.getMonth() * 31 + today.getDate();
    const dateOrder = (label: string) => {
      const [month, day] = label.split(' ');
      return (MONTH_SHORT.indexOf(month) * 31 + Number(day) - offset + 372) % 372;
    };
    return Object.entries(dates).map(([label, count]) => ({ id: label, label, count }))
      .sort((a, b) => dateOrder(a.id) - dateOrder(b.id));
  }, [summaryFacets, selectedWalkinDates]);
  const walkinLocations = summaryFacets?.locations ?? summary?.walkins.locations;
  const walkinActive = walkinOnly || selectedWalkinDates.size > 0;
  const walkinCount = useMemo(() => {
    if (!summary) return undefined;
    if (!selectedLocations.size && !selectedSources.size) return summary.walkins.total;
    let count = 0;
    for (const [source, locations] of Object.entries(summary.walkins.source_locations)) {
      if (!matchesCatalogSource(source, selectedSources)) continue;
      for (const [city, total] of Object.entries(locations)) {
        if (matchesCatalogLocation(city, selectedLocations)) count += total;
      }
    }
    return count;
  }, [summary, selectedLocations, selectedSources]);
  const walkinRetrying = catalogError || (walkinActive && batchError);
  const retryWalkins = () => {
    if (summary && walkinActive) retryBatch();
    else setCatalogAttempt(value => value + 1);
  };
  const reconnecting = catalogError || batchError;
  const waitingForJobs = !summary || batchLoading ||
    walkinOnly !== deferredWalkinOnly || selectedWalkinDates !== deferredWalkinDates;

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
    const jobsToApply = (filteredJobs && filteredJobs.length > 0 ? filteredJobs : jobs)
      .filter(j => (j.url || (j as any).apply_url))
      .slice(0, 30);
    bridgeService.startBatchAutoApply(jobsToApply);
  };

  return (
    <div className="alljobs-page">
      {/* Top Navigation from Screenshot 3 */}
      <AllJobsTopNav
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        totalJobsCount={summary?.total_jobs ?? null}
        catalogLoading={catalogLoading || !summary}
        categoryCounts={categoryCounts}
        onGoHub={onGoHub}
        onAutoApply={handleAutoApply}
        onClearAll={clearAllFilters}
        hasActiveFilters={hasActiveFilters}
      />

      {/* Main Layout: Sidebar + Grid */}
      <div className="alljobs-layout">
        {/* Left Filter Sidebar with dynamic counts & independent scroll */}
        <MobileFilters><AllJobsSidebar
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
          sourceCounts={sourceFacets}
          sourceCountsAreCatalog={canUseWalkinSummary}
          locationCounts={useWalkinFacets ? walkinLocations : canUseWalkinSummary ? catalogFacets.locations : hasActiveFilters ? dynamicCounts.locCounts : summary?.locations}
          locationCountsAreCatalog={!hasActiveFilters || canUseWalkinSummary}
          roleCounts={dynamicCounts.roleCounts}
          skillCounts={dynamicCounts.skillCounts}
          walkinCount={walkinCount}
          walkinSummaryLoading={!summaryFacets}
          walkinRetrying={walkinRetrying}
          walkinRetryBusy={catalogLoading || (walkinActive && Boolean(summary) && batchLoading)}
          onRetryWalkins={retryWalkins}
          walkinDateOptions={walkinDateOptions}
          sidebarCounts={summary}
        /></MobileFilters>

        {/* Right Main Grid */}
        <main className="alljobs-main">
          <p role="status" style={{ color: '#94a3b8', fontSize: '0.8rem', margin: '0 0 12px' }}>
            {filteredJobs.length > 0 || (!waitingForJobs && !reconnecting)
              ? filteredJobs.length.toLocaleString() + ' matching jobs loaded · Newest first · More jobs load in small batches'
              : reconnecting ? 'Retrying job downloads…' : walkinActive ? 'Loading walk-in jobs…' : 'Loading jobs…'}
          </p>
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
          {waitingForJobs && !filteredJobs.length && !reconnecting ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#7c8db5' }}>
              <div style={{ display: 'inline-block', width: '38px', height: '38px', border: '3px solid rgba(56,189,248,0.2)', borderTopColor: '#38bdf8', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }}></div>
              <p style={{ color: '#94a3b8', marginTop: '14px', fontSize: '15px', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: '8px' }}><LoaderCircle size={16} aria-hidden="true" /> Loading matching jobs...</p>
            </div>
          ) : filteredJobs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#7c8db5' }}>
              {reconnecting ? 'Some job data could not load. Retrying automatically…' : 'No jobs found matching your criteria.'}
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

              {availablePages > 1 && (
                <div className="pagination-container" role="navigation" aria-label="Pagination">
                  <button className="page-btn" disabled={safePage === 1 || batchLoading} onClick={() => void goToPage(safePage - 1)} aria-label="Previous Page">←</button>
                  {Array.from({ length: Math.min(7, Math.min(availablePages, safePage + 1)) }, (_, i) => {
                    const end = Math.min(availablePages, safePage + 1);
                    const page = Math.max(1, end - 6) + i;
                    return <button key={page} className={`page-btn ${page === safePage ? 'active' : ''}`} aria-current={page === safePage ? 'page' : undefined} disabled={batchLoading} onClick={() => void goToPage(page)}>{page}</button>;
                  })}
                  <button className="page-btn" disabled={safePage >= availablePages || batchLoading} onClick={() => void goToPage(safePage + 1)} aria-label="Next Page">→</button>
                </div>
              )}
            </>
          )}
          <div style={{ display: 'flex', justifyContent: 'center', padding: '20px 0' }}>
            {batchError && <button type="button" className="page-btn" disabled={batchLoading} onClick={retryBatch} style={{ minWidth: 210, padding: '12px 20px' }}>
              {batchLoading ? 'Loading jobs…' : 'Retry loading jobs'}
            </button>}
          </div>
        </main>
      </div>
    </div>
  );
};
