import React from 'react';
import { motion } from 'framer-motion';
import { Briefcase, Footprints, Code2, Cpu, ArrowUpRight } from 'lucide-react';

interface FeatureCardsProps {
  onNavigate: (tab: string) => void;
}

export const FeatureCards: React.FC<FeatureCardsProps> = ({ onNavigate }) => {
  const cards = [
    {
      id: 'all_jobs',
      title: 'Unified Multi-Portal Jobs',
      description: 'Aggregating thousands of verified job postings from Naukri, Indeed, LinkedIn, Foundit, and company ATS portals with granular JSON sharding.',
      tag: 'Real-Time Shards',
      icon: Briefcase,
      color: 'from-emerald-500/10 to-emerald-500/0',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    },
    {
      id: 'walkins',
      title: 'Daily Walk-in Interviews',
      description: 'Never miss an in-person drive. Extracted verified walk-in dates, contact phones, email addresses, and venue details categorized by date.',
      tag: 'Verified Walk-ins',
      icon: Footprints,
      color: 'from-amber-500/10 to-amber-500/0',
      badgeColor: 'text-amber-400 bg-amber-500/10 border-amber-500/20'
    },
    {
      id: 'leetcode',
      title: 'LeetCode Company Frequency (4,073 Qs)',
      description: 'Prepare effectively with real interview frequencies across 1,418 companies. See which questions were asked 10x, 20x, or 40+ times in actual rounds.',
      tag: 'Cloudflare D1 Live',
      icon: Code2,
      color: 'from-cyan-500/10 to-cyan-500/0',
      badgeColor: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20'
    },
    {
      id: 'extension',
      title: 'AI Auto-Fill & Batch Dispatch',
      description: 'Integrated with the Auto-Fill-V5 browser extension. Batch dispatch job applications directly from the browser with adaptive AI fallback.',
      tag: 'Chrome V3 Ready',
      icon: Cpu,
      color: 'from-purple-500/10 to-purple-500/0',
      badgeColor: 'text-purple-400 bg-purple-500/10 border-purple-500/20'
    }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      <div className="flex flex-col items-center text-center mb-10">
        <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight mb-3">
          Explore The Career Ecosystem
        </h2>
        <p className="text-slate-400 text-sm max-w-xl">
          Everything you need to discover opportunities, prepare for technical rounds, and automate applications in one unified platform.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {cards.map((c, i) => {
          const Icon = c.icon;
          return (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              onClick={() => {
                if (c.id === 'extension') {
                  onNavigate('all_jobs');
                } else {
                  onNavigate(c.id);
                }
              }}
              className="p-8 rounded-3xl bg-[#0b1120]/80 backdrop-blur-md border border-white/5 hover:border-white/20 transition-all cursor-pointer group relative overflow-hidden shadow-xl"
            >
              <div className={`absolute inset-0 bg-gradient-to-b ${c.color} pointer-events-none opacity-50 group-hover:opacity-100 transition-opacity`} />
              
              <div className="flex items-center justify-between mb-6 relative z-10">
                <span className={`text-[11px] font-bold uppercase tracking-wider px-3 py-1 rounded-full border ${c.badgeColor}`}>
                  {c.tag}
                </span>
                <div className="w-10 h-10 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-white group-hover:scale-110 transition-transform">
                  <ArrowUpRight className="w-5 h-5 text-slate-300 group-hover:text-emerald-400 transition-colors" />
                </div>
              </div>

              <div className="flex items-start gap-4 relative z-10 mb-4">
                <div className="p-3 rounded-2xl bg-white/5 text-emerald-400 border border-white/10">
                  <Icon className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white group-hover:text-emerald-400 transition-colors">
                    {c.title}
                  </h3>
                  <p className="text-slate-400 text-sm mt-2 leading-relaxed">
                    {c.description}
                  </p>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
