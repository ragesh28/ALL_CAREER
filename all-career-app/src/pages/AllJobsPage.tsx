import React, { useState, useEffect, useMemo } from 'react';
import { Job, SidebarCounts } from '../types/jobs';
import { jobService } from '../services/jobService';
import { JobCard } from '../components/jobs/JobCard';
import { CategoryBar } from '../components/jobs/CategoryBar';
import { FilterSidebar } from '../components/jobs/FilterSidebar';
import { Pagination } from '../components/jobs/Pagination';
import { Search, Sparkles, Send } from 'lucide-react';
import { bridgeService } from '../services/bridgeService';

export const AllJobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sidebarCounts, setSidebarCounts] = useState<SidebarCounts | null>(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedPortals, setSelectedPortals] = useState<Set<string>>(new Set());
  const [selectedLocations, setSelectedLocations] = useState<Set<string>>(new Set());
  const [selectedExperience, setSelectedExperience] = useState('all');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 30;

  // Ultra-fast <60ms catalog initialization
  useEffect(() => {
    let isMounted = true;
    jobService.initCatalog().then(data => {
      if (!isMounted) return;
      setJobs(data.previewJobs);
      setSidebarCounts(data.sidebarCounts);
      setLoading(false);
    });
    return () => {
      isMounted = false;
    };
  }, []);

  // On demand shard fetching when filters change
  useEffect(() => {
    if (selectedPortals.size > 0 || selectedLocations.size > 0 || searchTerm) {
      jobService.loadShardsForFilters(
        Array.from(selectedPortals),
        Array.from(selectedLocations),
        [],
        searchTerm
      ).then(updatedJobs => {
        setJobs([...updatedJobs]);
      });
    }
  }, [selectedPortals, selectedLocations, searchTerm]);

  // Compute category counts
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {
      technical: 0,
      non_technical: 0,
      pharma: 0,
      others: 0
    };
    for (const j of jobs) {
      const cat = j.category || 'others';
      if (counts[cat] !== undefined) counts[cat]++;
      else counts.others++;
    }
    return counts;
  }, [jobs]);

  // Toggle helpers
  const handleTogglePortal = (portal: string) => {
    setSelectedPortals(prev => {
      const next = new Set(prev);
      if (next.has(portal)) next.delete(portal);
      else next.add(portal);
      return next;
    });
    setCurrentPage(1);
  };

  const handleToggleLocation = (loc: string) => {
    setSelectedLocations(prev => {
      const next = new Set(prev);
      if (next.has(loc)) next.delete(loc);
      else next.add(loc);
      return next;
    });
    setCurrentPage(1);
  };

  const handleResetFilters = () => {
    setSelectedPortals(new Set());
    setSelectedLocations(new Set());
    setSelectedExperience('all');
    setSelectedCategory('all');
    setSearchTerm('');
    setCurrentPage(1);
  };

  // Filtered jobs
  const filteredJobs = useMemo(() => {
    const term = searchTerm.toLowerCase().trim();
    return jobs.filter(j => {
      if (term) {
        const titleMatch = (j.title || '').toLowerCase().includes(term);
        const compMatch = (j.company || '').toLowerCase().includes(term);
        const locMatch = (j.location || '').toLowerCase().includes(term);
        const roleMatch = (j.role_search || '').toLowerCase().includes(term);
        if (!titleMatch && !compMatch && !locMatch && !roleMatch) return false;
      }

      if (selectedCategory !== 'all') {
        if (j.category !== selectedCategory) return false;
      }

      if (selectedPortals.size > 0) {
        const src = (j.source || '').toLowerCase();
        if (!selectedPortals.has(src)) return false;
      }

      if (selectedLocations.size > 0) {
        const loc = (j.location || '').toLowerCase();
        const matched = Array.from(selectedLocations).some(l => loc.includes(l.toLowerCase()));
        if (!matched) return false;
      }

      if (selectedExperience !== 'all') {
        const expStr = (j.experience || '').toLowerCase();
        if (selectedExperience === 'fresher' && !expStr.includes('0') && !expStr.includes('fresher')) return false;
        if (selectedExperience === '1-3' && !expStr.includes('1') && !expStr.includes('2') && !expStr.includes('3')) return false;
        if (selectedExperience === '3-5' && !expStr.includes('3') && !expStr.includes('4') && !expStr.includes('5')) return false;
      }

      return true;
    });
  }, [jobs, searchTerm, selectedCategory, selectedPortals, selectedLocations, selectedExperience]);

  const totalPages = Math.ceil(filteredJobs.length / pageSize) || 1;
  const currentJobs = filteredJobs.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  // Trigger batch auto apply to Auto-Fill-V5 extension
  const handleBatchAutoApply = () => {
    const urls = currentJobs.map(j => j.url).filter(Boolean) as string[];
    bridgeService.sendBatchJobsToExtension(urls);
    alert(`Dispatched ${urls.length} application URLs to Auto-Fill-V5 Extension!`);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Search & Batch Apply Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
        <div className="relative w-full sm:max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search by job title, company, skills, or city..."
            value={searchTerm}
            onChange={e => { setSearchTerm(e.target.value); setCurrentPage(1); }}
            className="w-full pl-10 pr-4 py-2.5 bg-[#0b1120] border border-white/10 rounded-xl text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/50 shadow-inner"
          />
        </div>

        <button
          onClick={handleBatchAutoApply}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 text-black hover:opacity-95 shadow-md shadow-emerald-500/20 hover:scale-[1.02] active:scale-[0.98] transition-all whitespace-nowrap"
        >
          <Send className="w-3.5 h-3.5" />
          Start Batch Auto-Apply ({Math.min(currentJobs.length, 30)})
        </button>
      </div>

      {/* Category Pills Bar */}
      <CategoryBar
        selectedCategory={selectedCategory}
        onSelectCategory={cat => { setSelectedCategory(cat); setCurrentPage(1); }}
        categoryCounts={categoryCounts}
        totalJobsCount={sidebarCounts?.total_jobs || jobs.length}
      />

      {/* Main Content Layout */}
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* Left Filter Sidebar */}
        <FilterSidebar
          sidebarCounts={sidebarCounts}
          selectedPortals={selectedPortals}
          onTogglePortal={handleTogglePortal}
          selectedLocations={selectedLocations}
          onToggleLocation={handleToggleLocation}
          selectedExperience={selectedExperience}
          onSelectExperience={exp => { setSelectedExperience(exp); setCurrentPage(1); }}
          onResetFilters={handleResetFilters}
        />

        {/* Right Job Cards Grid */}
        <div className="flex-1 w-full min-w-0">
          {loading ? (
            <div id="loading">Loading instant job catalog...</div>
          ) : filteredJobs.length === 0 ? (
            <div className="text-center py-20 bg-[#0b1120]/50 rounded-2xl border border-white/5">
              <p className="text-slate-400 text-sm mb-3">No jobs matched your active filters.</p>
              <button
                onClick={handleResetFilters}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-white/10 hover:bg-white/15 text-white transition-all"
              >
                Clear all filters
              </button>
            </div>
          ) : (
            <>
              <div className="jobs-grid">
                {currentJobs.map((job, idx) => (
                  <JobCard key={`${job.id || job._id || idx}-${job.title}`} job={job} index={idx} />
                ))}
              </div>

              {/* Pagination */}
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={page => {
                  setCurrentPage(page);
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
};
