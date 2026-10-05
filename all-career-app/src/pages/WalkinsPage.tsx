import React, { useState, useEffect, useMemo } from 'react';
import { Job } from '../types/jobs';
import { jobService } from '../services/jobService';
import { JobCard } from '../components/jobs/JobCard';
import { WalkinFilterBar } from '../components/walkins/WalkinFilterBar';
import { Footprints, AlertTriangle } from 'lucide-react';

export const WalkinsPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState('all');
  const [selectedCity, setSelectedCity] = useState('all');

  useEffect(() => {
    let isMounted = true;
    jobService.fetchWalkinJobs().then(all => {
      if (!isMounted) return;
      // Filter walkins
      const walkins = all.filter(j => 
        j.walkin_date || 
        (j.walkin_dates && j.walkin_dates.length > 0) || 
        (j.title && /walk-?in/i.test(j.title)) ||
        j.category === 'walkin'
      );
      setJobs(walkins);
      setLoading(false);
    });
    return () => {
      isMounted = false;
    };
  }, []);

  // Extract distinct dates
  const distinctDates = useMemo(() => {
    const dates = new Set<string>();
    for (const j of jobs) {
      if (j.walkin_dates && Array.isArray(j.walkin_dates)) {
        j.walkin_dates.forEach(d => dates.add(d));
      } else if (j.walkin_date) {
        dates.add(j.walkin_date);
      }
    }
    return Array.from(dates).slice(0, 10);
  }, [jobs]);

  // Extract distinct cities
  const distinctCities = useMemo(() => {
    const cities = new Set<string>();
    for (const j of jobs) {
      const loc = (j.location || '').split(',')[0].trim();
      if (loc && !['nan', 'none', 'null'].includes(loc.toLowerCase())) {
        cities.add(loc);
      }
    }
    return Array.from(cities).slice(0, 15);
  }, [jobs]);

  // Filtered jobs
  const filteredJobs = useMemo(() => {
    return jobs.filter(j => {
      if (selectedDate !== 'all') {
        const matchesDate = (j.walkin_dates && j.walkin_dates.includes(selectedDate)) || (j.walkin_date === selectedDate);
        if (!matchesDate) return false;
      }

      if (selectedCity !== 'all') {
        const loc = (j.location || '').toLowerCase();
        if (!loc.includes(selectedCity.toLowerCase())) return false;
      }

      return true;
    });
  }, [jobs, selectedDate, selectedCity]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Title & Description */}
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
          <Footprints className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-2xl sm:text-3xl font-heading font-extrabold text-white">
            Daily Verified Walk-in Drives
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">
            Real-time scraped direct walk-in interviews with venues, recruiter emails, and phone numbers.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <WalkinFilterBar
        dates={distinctDates}
        selectedDate={selectedDate}
        onSelectDate={setSelectedDate}
        selectedCity={selectedCity}
        onSelectCity={setSelectedCity}
        cities={distinctCities}
      />

      {/* Jobs Grid */}
      {loading ? (
        <div id="loading">Loading walk-in interview catalog...</div>
      ) : filteredJobs.length === 0 ? (
        <div className="text-center py-20 bg-[#0b1120]/50 rounded-2xl border border-white/5">
          <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto mb-2 opacity-80" />
          <p className="text-slate-400 text-sm mb-3">No walk-in drives matched the selected filter.</p>
          <button
            onClick={() => { setSelectedDate('all'); setSelectedCity('all'); }}
            className="px-4 py-2 text-xs font-bold rounded-xl bg-amber-400 text-black hover:opacity-90 transition-all"
          >
            Show All Walk-ins
          </button>
        </div>
      ) : (
        <div className="jobs-grid">
          {filteredJobs.map((job, idx) => (
            <JobCard key={`${job.id || job._id || idx}-walkin`} job={job} index={idx} />
          ))}
        </div>
      )}
    </div>
  );
};
