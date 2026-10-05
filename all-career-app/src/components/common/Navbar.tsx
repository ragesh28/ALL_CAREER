import React from 'react';
import { Briefcase, Building2, Code2, Sparkles, Footprints } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  totalJobsCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, totalJobsCount = 10000 }) => {
  const navItems = [
    { id: 'home', label: 'Home', icon: Sparkles },
    { id: 'all_jobs', label: 'All Jobs', icon: Briefcase, count: totalJobsCount },
    { id: 'walkins', label: 'Walk-ins', icon: Footprints, badge: 'Daily' },
    { id: 'leetcode', label: 'LeetCode Explorer', icon: Code2, badge: '4,073 Qs' }
  ];

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-[#06080f]/85 border-b border-white/10 px-4 lg:px-8 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand */}
        <div 
          onClick={() => setActiveTab('home')}
          className="flex items-center gap-3 cursor-pointer group select-none"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 p-0.5 shadow-lg shadow-emerald-500/20 group-hover:scale-105 transition-transform">
            <div className="w-full h-full bg-[#0b1120] rounded-[10px] flex items-center justify-center overflow-hidden">
              <img src="/String_Theory.png" alt="All Career" className="w-7 h-7 object-contain" onError={(e) => {
                (e.target as HTMLElement).style.display = 'none';
              }} />
              <span className="text-emerald-400 font-bold text-lg">AC</span>
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-heading font-extrabold text-xl tracking-tight text-white group-hover:text-emerald-400 transition-colors">
                ALL CAREER
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
                Next-Gen
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Job Ecosystem & Interview Analytics</p>
          </div>
        </div>

        {/* Navigation links */}
        <nav className="hidden md:flex items-center gap-1.5 bg-[#0e1424]/80 p-1.5 rounded-2xl border border-white/5">
          {navItems.map(item => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`relative flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                  isActive 
                    ? 'text-white bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 border border-emerald-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
                {item.badge && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase ${
                    isActive ? 'bg-emerald-500 text-black' : 'bg-white/10 text-slate-300'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Action Button */}
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setActiveTab('leetcode')}
            className="hidden sm:flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl bg-gradient-to-r from-emerald-400 to-cyan-400 text-black hover:opacity-95 shadow-md shadow-emerald-500/20 hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <Code2 className="w-3.5 h-3.5" />
            LeetCode 4,073
          </button>
        </div>
      </div>
    </header>
  );
};
