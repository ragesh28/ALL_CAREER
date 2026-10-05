import React, { useState } from 'react';
import { Layers, ChevronDown } from 'lucide-react';

interface CategoryBarProps {
  selectedCategory: string;
  onSelectCategory: (category: string) => void;
  categoryCounts: Record<string, number>;
  totalJobsCount: number;
}

export const CategoryBar: React.FC<CategoryBarProps> = ({
  selectedCategory,
  onSelectCategory,
  categoryCounts,
  totalJobsCount
}) => {
  const [showPopover, setShowPopover] = useState(false);

  const categories = [
    { id: 'all', label: 'All Jobs', count: totalJobsCount },
    { id: 'technical', label: 'Technical', count: categoryCounts.technical || 0 },
    { id: 'non_technical', label: 'Non-Technical', count: categoryCounts.non_technical || 0 },
    { id: 'pharma', label: 'Pharma', count: categoryCounts.pharma || 0 },
    { id: 'others', label: 'Others', count: categoryCounts.others || 0 }
  ];

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 mb-6 bg-[#0b1120]/70 backdrop-blur-md p-3 rounded-2xl border border-white/5 shadow-sm">
      {/* Category Pills */}
      <div className="flex flex-wrap items-center gap-2">
        {categories.map(cat => {
          const isSelected = selectedCategory === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => onSelectCategory(cat.id)}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                isSelected
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-sm'
                  : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-white/5'
              }`}
            >
              <span>{cat.label}</span>
              <span className={`px-1.5 py-0.2 rounded-md text-[10px] font-bold ${
                isSelected ? 'bg-emerald-400 text-black' : 'bg-white/10 text-slate-400'
              }`}>
                {cat.count.toLocaleString()}
              </span>
            </button>
          );
        })}
      </div>

      {/* Showing count with popover */}
      <div 
        className="relative"
        onMouseEnter={() => setShowPopover(true)}
        onMouseLeave={() => setShowPopover(false)}
      >
        <button className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition-all">
          <Layers className="w-3.5 h-3.5 text-emerald-400" />
          <span>Showing <strong className="text-emerald-400">{totalJobsCount.toLocaleString()}</strong> jobs</span>
          <ChevronDown className="w-3 h-3 text-slate-400" />
        </button>

        {showPopover && (
          <div className="absolute right-0 top-full mt-2 w-64 bg-[#0f172a]/95 backdrop-blur-xl border border-cyan-500/30 rounded-xl p-3 shadow-2xl z-30 animate-fadeIn">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider pb-2 border-b border-white/10 mb-2 flex items-center justify-between">
              <span>Category Breakdown</span>
              <span className="text-emerald-400">{totalJobsCount.toLocaleString()}</span>
            </div>
            <div className="space-y-1.5">
              {categories.filter(c => c.id !== 'all').map(c => (
                <div 
                  key={c.id} 
                  onClick={() => { onSelectCategory(c.id); setShowPopover(false); }}
                  className="flex items-center justify-between text-xs py-1 px-2 rounded-lg hover:bg-white/10 cursor-pointer text-slate-300"
                >
                  <span>{c.label}</span>
                  <span className="font-semibold text-emerald-400">{c.count.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
