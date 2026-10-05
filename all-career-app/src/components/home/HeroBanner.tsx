import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight, Zap, Flame, Code2, Footprints } from 'lucide-react';

interface HeroBannerProps {
  onNavigate: (tab: string) => void;
  totalJobsCount: number;
}

export const HeroBanner: React.FC<HeroBannerProps> = ({ onNavigate, totalJobsCount }) => {
  return (
    <div className="relative pt-12 pb-16 px-4 overflow-hidden">
      {/* Dynamic Glow Sphere in background */}
      <div className="hero-glow-bg" />

      <div className="max-w-5xl mx-auto text-center relative z-10">
        {/* Floating animated pill */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.05] border border-white/10 backdrop-blur-md text-xs font-semibold text-emerald-400 mb-8 shadow-inner"
        >
          <Sparkles className="w-3.5 h-3.5 animate-spin" style={{ animationDuration: '6s' }} />
          <span>Next-Generation Career Platform & Interview Intelligence</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
        </motion.div>

        {/* Headline with vibrant gradient */}
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight leading-[1.1] mb-6 text-white"
        >
          Land Your Dream Role with <br />
          <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
            Precision Job Intelligence
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="text-base sm:text-lg text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed font-normal"
        >
          Aggregating verified walk-ins, direct recruiter opportunities, and all{' '}
          <strong className="text-white font-semibold">4,073 LeetCode problems</strong> with actual interview frequency percentages across{' '}
          <strong className="text-white font-semibold">1,418 top tech companies</strong>.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="flex flex-wrap items-center justify-center gap-4"
        >
          <button
            onClick={() => onNavigate('all_jobs')}
            className="flex items-center gap-2.5 px-6 py-3.5 rounded-2xl bg-gradient-to-r from-emerald-400 to-cyan-400 text-black font-bold text-sm shadow-xl shadow-emerald-500/25 hover:shadow-emerald-500/40 hover:scale-[1.03] active:scale-[0.98] transition-all"
          >
            <span>Explore Jobs ({totalJobsCount.toLocaleString()}+)</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={() => onNavigate('leetcode')}
            className="flex items-center gap-2.5 px-6 py-3.5 rounded-2xl bg-[#0e1424] hover:bg-[#131b30] text-slate-200 border border-white/10 hover:border-cyan-500/40 font-bold text-sm hover:scale-[1.02] active:scale-[0.98] transition-all shadow-lg"
          >
            <Code2 className="w-4 h-4 text-cyan-400" />
            <span>LeetCode Frequency (4,073 Qs)</span>
          </button>

          <button
            onClick={() => onNavigate('walkins')}
            className="flex items-center gap-2.5 px-6 py-3.5 rounded-2xl bg-[#0e1424] hover:bg-[#131b30] text-slate-200 border border-white/10 hover:border-amber-500/40 font-bold text-sm hover:scale-[1.02] active:scale-[0.98] transition-all shadow-lg"
          >
            <Footprints className="w-4 h-4 text-amber-400" />
            <span>Walk-in Interviews</span>
          </button>
        </motion.div>
      </div>
    </div>
  );
};
