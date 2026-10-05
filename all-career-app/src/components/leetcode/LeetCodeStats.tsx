import React from 'react';
import { LeetCodeStatsData } from '../../types/leetcode';
import { Code2, Building2, CheckCircle2, AlertCircle, Award } from 'lucide-react';

interface LeetCodeStatsProps {
  stats: LeetCodeStatsData;
}

export const LeetCodeStats: React.FC<LeetCodeStatsProps> = ({ stats }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 mb-8">
      {/* 1. Official Total Problems */}
      <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-500/10 to-teal-500/5 border border-emerald-500/30 flex items-center gap-3 shadow-md">
        <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center text-emerald-400">
          <Award className="w-5 h-5" />
        </div>
        <div>
          <div className="text-xl font-extrabold text-white">
            {stats.totalOfficialCount.toLocaleString()}
          </div>
          <div className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wide">
            Official Catalog Total
          </div>
        </div>
      </div>

      {/* 2. Company Interview Tagged */}
      <div className="p-4 rounded-xl bg-[#0b1120]/80 border border-cyan-500/20 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center text-cyan-400">
          <Code2 className="w-5 h-5" />
        </div>
        <div>
          <div className="text-xl font-extrabold text-cyan-400">
            {stats.totalCompanyTaggedCount.toLocaleString()}
          </div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            Company-Tagged Qs
          </div>
        </div>
      </div>

      {/* 3. Easy Problems */}
      <div className="p-4 rounded-xl bg-[#0b1120]/80 border border-white/5 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
          <CheckCircle2 className="w-5 h-5" />
        </div>
        <div>
          <div className="text-xl font-extrabold text-emerald-400">
            {stats.easyCount.toLocaleString()}
          </div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            Easy Problems
          </div>
        </div>
      </div>

      {/* 4. Medium Problems */}
      <div className="p-4 rounded-xl bg-[#0b1120]/80 border border-white/5 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400">
          <AlertCircle className="w-5 h-5" />
        </div>
        <div>
          <div className="text-xl font-extrabold text-amber-400">
            {stats.mediumCount.toLocaleString()}
          </div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            Medium Problems
          </div>
        </div>
      </div>

      {/* 5. Hard Problems */}
      <div className="p-4 rounded-xl bg-[#0b1120]/80 border border-white/5 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-400">
          <Building2 className="w-5 h-5" />
        </div>
        <div>
          <div className="text-xl font-extrabold text-rose-400">
            {stats.hardCount.toLocaleString()}
          </div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            Hard Problems
          </div>
        </div>
      </div>
    </div>
  );
};
