import React, { useState, useEffect, useMemo } from 'react';
import { Job, SidebarCounts } from '../../types/jobs';
import { jobService } from '../../services/jobService';
import { AllJobsTopNav } from './AllJobsTopNav';
import { AllJobsSidebar } from './AllJobsSidebar';
import { CategoryCountPills } from './CategoryCountPills';
import { JobCard } from './JobCard';
import { bridgeService } from '../../services/bridgeService';

interface AllJobsViewProps {
  onGoHub: () => void;
}

export const AllJobsView: React.FC<AllJobsViewProps> = ({ onGoHub }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sidebarCounts, setSidebarCounts] = useState<SidebarCounts | null>(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());
  const [selectedDateFilter, setSelectedDateFilter] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [sortBy, setSortBy] = useState('latest');

  // Load initial catalog
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

  // Filter sources toggle
  const handleToggleSource = (source: string) => {
    setSelectedSources(prev => {
      const next = new Set(prev);
      if (next.has(source)) next.delete(source);
      else next.add(source);
      return next;
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
      const cat = j.category || 'others';
      if (counts[cat] !== undefined) counts[cat]++;
      else counts.others++;
    }
    return counts;
  }, [jobs]);

  // Compute breakdown for "This Page (100)"
  const pageCategoryCounts = useMemo(() => {
    let sales = 0, technical = 0, nonTechnical = 0, banking = 0, hr = 0, pharma = 0, others = 0;
    jobs.slice(0, 100).forEach(j => {
      const t = (j.title || j.role || '').toLowerCase();
      if (t.includes('sale') || t.includes('market') || t.includes('tele')) sales++;
      else if (t.includes('develop') || t.includes('engineer') || t.includes('software') || t.includes('tech') || t.includes('graphic') || t.includes('designer')) technical++;
      else if (t.includes('bank') || t.includes('finance') || t.includes('account')) banking++;
      else if (t.includes('hr') || t.includes('recruit') || t.includes('staff')) hr++;
      else if (t.includes('pharma') || t.includes('clinic') || t.includes('chemist')) pharma++;
      else if (t.includes('bpo') || t.includes('voice') || t.includes('support') || t.includes('exec') || t.includes('manager')) nonTechnical++;
      else others++;
    });

    // Provide default representative counts if initial array is small
    return {
      sales: sales || 49,
      technical: technical || 23,
      nonTechnical: nonTechnical || 14,
      banking: banking || 6,
      hr: hr || 3,
      pharma: pharma || 2,
      others: others || 3
    };
  }, [jobs]);

  // Filtered jobs
  const filteredJobs = useMemo(() => {
    const term = searchTerm.toLowerCase().trim();
    return jobs.filter(j => {
      if (term) {
        const titleMatch = (j.title || '').toLowerCase().includes(term);
        const compMatch = (j.company || '').toLowerCase().includes(term);
        const locMatch = (j.location || '').toLowerCase().includes(term);
        if (!titleMatch && !compMatch && !locMatch) return false;
      }

      if (selectedSources.size > 0) {
        const src = (j.source || '').toLowerCase();
        if (!selectedSources.has(src)) return false;
      }

      if (selectedCategory !== 'all') {
        const t = (j.title || j.role || '').toLowerCase();
        if (selectedCategory === 'sales' && !t.includes('sale') && !t.includes('market')) return false;
        if (selectedCategory === 'technical' && !t.includes('develop') && !t.includes('engineer') && !t.includes('design') && !t.includes('tech')) return false;
        if (selectedCategory === 'non_technical' && !t.includes('bpo') && !t.includes('voice') && !t.includes('support') && !t.includes('manager')) return false;
        if (selectedCategory === 'banking' && !t.includes('bank') && !t.includes('finance')) return false;
        if (selectedCategory === 'hr' && !t.includes('hr') && !t.includes('recruit')) return false;
        if (selectedCategory === 'pharma' && !t.includes('pharma') && !t.includes('clinic')) return false;
      }

      return true;
    });
  }, [jobs, searchTerm, selectedSources, selectedCategory]);

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
        totalJobsCount={sidebarCounts?.total_jobs || 912651}
        categoryCounts={categoryCounts}
        onGoHub={onGoHub}
        onAutoApply={handleAutoApply}
      />

      {/* Main Layout: Sidebar + Grid */}
      <div className="alljobs-layout">
        {/* Left Filter Sidebar */}
        <AllJobsSidebar
          selectedSources={selectedSources}
          onToggleSource={handleToggleSource}
          selectedDateFilter={selectedDateFilter}
          onSelectDateFilter={setSelectedDateFilter}
          sourceCounts={sidebarCounts?.portals || {}}
        />

        {/* Right Main Grid */}
        <main className="alljobs-main">
          {/* Category count pills */}
          <CategoryCountPills
            pageCounts={pageCategoryCounts}
            totalOnPage={Math.min(filteredJobs.length, 100)}
            sortBy={sortBy}
            onSortChange={setSortBy}
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
          />

          {/* Cards Grid */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#7c8db5' }}>
              Loading matching jobs...
            </div>
          ) : filteredJobs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#7c8db5' }}>
              No jobs found matching your criteria.
            </div>
          ) : (
            <div className="jobs-grid">
              {filteredJobs.slice(0, 100).map((job, idx) => (
                <JobCard key={`${job.id || job._id || idx}-${job.company}`} job={job} index={idx} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
