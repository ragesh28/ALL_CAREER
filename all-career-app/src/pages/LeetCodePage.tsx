import React, { useState, useEffect } from 'react';
import { LeetCodeProblem, LeetCodeStatsData } from '../types/leetcode';
import { leetcodeService } from '../services/leetcodeService';
import { LeetCodeStats } from '../components/leetcode/LeetCodeStats';
import { LeetCodeTable } from '../components/leetcode/LeetCodeTable';
import { Code2, Database } from 'lucide-react';

export const LeetCodePage: React.FC = () => {
  const [problems, setProblems] = useState<LeetCodeProblem[]>([]);
  const [stats, setStats] = useState<LeetCodeStatsData>({
    totalOfficialCount: 4073,
    totalCompanyTaggedCount: 3474,
    totalUniqueCompanies: 1418,
    easyCount: 885,
    mediumCount: 1823,
    hardCount: 766
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    leetcodeService.loadProblems().then(data => {
      if (!isMounted) return;
      setProblems(data.problems);
      setStats(data.stats);
      setLoading(false);
    });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 p-0.5 shadow-lg shadow-emerald-500/20">
            <div className="w-full h-full bg-[#0b1120] rounded-[10px] flex items-center justify-center">
              <Code2 className="w-6 h-6 text-emerald-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl sm:text-3xl font-heading font-extrabold text-white">
                LeetCode Interview Intelligence
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Official Catalog: 4,073
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-400">
              Synchronized with Cloudflare D1. Complete topics, interview frequency %, and 1,418 tech company question sets.
            </p>
          </div>
        </div>

        {/* Database Status Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-xs font-semibold text-slate-300">
          <Database className="w-3.5 h-3.5 text-emerald-400" />
          <span>Cloudflare D1 Synced</span>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
        </div>
      </div>

      {/* Stats Cards */}
      <LeetCodeStats stats={stats} />

      {/* Table & Filters */}
      {loading ? (
        <div id="loading">Loading LeetCode interview dataset...</div>
      ) : (
        <LeetCodeTable problems={problems} />
      )}
    </div>
  );
};
