import React from 'react';
import { motion } from 'framer-motion';
import { Briefcase, Building2, Code2, Zap } from 'lucide-react';

interface StatsCounterProps {
  totalJobs: number;
}

export const StatsCounter: React.FC<StatsCounterProps> = ({ totalJobs }) => {
  const stats = [
    {
      label: 'Verified Live Jobs',
      value: `${totalJobs.toLocaleString()}+`,
      subtext: 'Naukri, Indeed, Walk-ins, ATS',
      icon: Briefcase,
      color: 'from-emerald-400 to-teal-400',
      border: 'border-emerald-500/20'
    },
    {
      label: 'Official LeetCode Catalog',
      value: '4,073',
      subtext: '3,474 with company frequency',
      icon: Code2,
      color: 'from-cyan-400 to-blue-400',
      border: 'border-cyan-500/20'
    },
    {
      label: 'Top Tech Companies',
      value: '1,418',
      subtext: 'Google, Amazon, Meta, Microsoft...',
      icon: Building2,
      color: 'from-purple-400 to-indigo-400',
      border: 'border-purple-500/20'
    },
    {
      label: 'Ultra-Fast Sharding',
      value: '< 60ms',
      subtext: 'Instant in-memory catalog loading',
      icon: Zap,
      color: 'from-amber-400 to-orange-400',
      border: 'border-amber-500/20'
    }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s, idx) => {
          const Icon = s.icon;
          return (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: idx * 0.1 }}
              className={`p-6 rounded-2xl bg-[#0b1120]/80 backdrop-blur-md border ${s.border} relative overflow-hidden group hover:border-white/20 transition-all shadow-lg`}
            >
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{s.label}</span>
                <div className="w-8 h-8 rounded-xl bg-white/5 flex items-center justify-center text-slate-300 group-hover:scale-110 transition-transform">
                  <Icon className="w-4 h-4 text-emerald-400" />
                </div>
              </div>
              <div className={`text-3xl font-extrabold bg-gradient-to-r ${s.color} bg-clip-text text-transparent mb-1`}>
                {s.value}
              </div>
              <p className="text-xs text-slate-400 font-medium">{s.subtext}</p>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
