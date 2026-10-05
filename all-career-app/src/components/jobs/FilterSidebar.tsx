import React, { useState } from 'react';
import { Filter, Search, RotateCcw, ChevronDown, Check } from 'lucide-react';
import { SidebarCounts } from '../../types/jobs';

interface FilterSidebarProps {
  sidebarCounts: SidebarCounts | null;
  selectedPortals: Set<string>;
  onTogglePortal: (portal: string) => void;
  selectedLocations: Set<string>;
  onToggleLocation: (location: string) => void;
  selectedExperience: string;
  onSelectExperience: (exp: string) => void;
  onResetFilters: () => void;
}

export const FilterSidebar: React.FC<FilterSidebarProps> = ({
  sidebarCounts,
  selectedPortals,
  onTogglePortal,
  selectedLocations,
  onToggleLocation,
  selectedExperience,
  onSelectExperience,
  onResetFilters
}) => {
  const [portalSearch, setPortalSearch] = useState('');
  const [locationSearch, setLocationSearch] = useState('');
  const [openSections, setOpenSections] = useState({
    portals: true,
    locations: true,
    experience: true
  });

  const toggleSection = (section: 'portals' | 'locations' | 'experience') => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const portalEntries = Object.entries(sidebarCounts?.portals || {
    naukri: 2450,
    indeed: 1890,
    linkedin: 1420,
    foundit: 980,
    telegram: 850,
    walkin: 620
  }).filter(([name]) => name.toLowerCase().includes(portalSearch.toLowerCase()));

  const locationEntries = Object.entries(sidebarCounts?.locations || {
    bangalore: 3200,
    hyderabad: 2100,
    pune: 1450,
    chennai: 1100,
    mumbai: 980,
    delhi: 890,
    remote: 1250
  }).filter(([name]) => name.toLowerCase().includes(locationSearch.toLowerCase()));

  const expOptions = [
    { id: 'all', label: 'All Experience' },
    { id: 'fresher', label: 'Fresher (0–1 yrs)' },
    { id: '1-3', label: '1–3 Years' },
    { id: '3-5', label: '3–5 Years' },
    { id: '5+', label: '5+ Years' }
  ];

  const totalActiveFilters = selectedPortals.size + selectedLocations.size + (selectedExperience !== 'all' ? 1 : 0);

  return (
    <aside className="w-full lg:w-64 bg-[#0b1120]/90 backdrop-blur-md rounded-2xl border border-white/5 p-4 flex flex-col gap-5 h-fit shadow-md">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-emerald-400" />
          <span className="font-heading font-bold text-sm text-white">Filters</span>
          {totalActiveFilters > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-400 text-black font-bold">
              {totalActiveFilters}
            </span>
          )}
        </div>
        {totalActiveFilters > 0 && (
          <button
            onClick={onResetFilters}
            className="flex items-center gap-1 text-[11px] font-semibold text-slate-400 hover:text-rose-400 transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            Reset
          </button>
        )}
      </div>

      {/* Portals Section */}
      <div className="border-b border-white/5 pb-4">
        <button
          onClick={() => toggleSection('portals')}
          className="flex items-center justify-between w-full text-xs font-bold text-slate-300 mb-2.5"
        >
          <span>Job Portals</span>
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${openSections.portals ? 'rotate-180' : ''}`} />
        </button>
        {openSections.portals && (
          <div className="space-y-2">
            <div className="relative">
              <Search className="w-3 h-3 absolute left-2.5 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search portals..."
                value={portalSearch}
                onChange={e => setPortalSearch(e.target.value)}
                className="w-full pl-7 pr-3 py-1.5 text-xs bg-white/5 border border-white/5 rounded-lg text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <div className="max-h-40 overflow-y-auto pr-1 space-y-1">
              {portalEntries.map(([portal, count]) => {
                const checked = selectedPortals.has(portal);
                return (
                  <div
                    key={portal}
                    onClick={() => onTogglePortal(portal)}
                    className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-white/5 cursor-pointer text-xs transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <div className={`w-3.5 h-3.5 rounded flex items-center justify-center border ${
                        checked ? 'bg-emerald-500 border-emerald-500' : 'border-slate-600 bg-white/5'
                      }`}>
                        {checked && <Check className="w-2.5 h-2.5 text-black stroke-[3]" />}
                      </div>
                      <span className="capitalize text-slate-300 font-medium">{portal}</span>
                    </div>
                    <span className="text-[11px] text-slate-500 font-semibold">{count.toLocaleString()}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Locations Section */}
      <div className="border-b border-white/5 pb-4">
        <button
          onClick={() => toggleSection('locations')}
          className="flex items-center justify-between w-full text-xs font-bold text-slate-300 mb-2.5"
        >
          <span>Top Locations</span>
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${openSections.locations ? 'rotate-180' : ''}`} />
        </button>
        {openSections.locations && (
          <div className="space-y-2">
            <div className="relative">
              <Search className="w-3 h-3 absolute left-2.5 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search locations..."
                value={locationSearch}
                onChange={e => setLocationSearch(e.target.value)}
                className="w-full pl-7 pr-3 py-1.5 text-xs bg-white/5 border border-white/5 rounded-lg text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <div className="max-h-40 overflow-y-auto pr-1 space-y-1">
              {locationEntries.map(([loc, count]) => {
                const checked = selectedLocations.has(loc);
                return (
                  <div
                    key={loc}
                    onClick={() => onToggleLocation(loc)}
                    className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-white/5 cursor-pointer text-xs transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <div className={`w-3.5 h-3.5 rounded flex items-center justify-center border ${
                        checked ? 'bg-cyan-500 border-cyan-500' : 'border-slate-600 bg-white/5'
                      }`}>
                        {checked && <Check className="w-2.5 h-2.5 text-black stroke-[3]" />}
                      </div>
                      <span className="capitalize text-slate-300 font-medium">{loc}</span>
                    </div>
                    <span className="text-[11px] text-slate-500 font-semibold">{count.toLocaleString()}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Experience Section */}
      <div>
        <button
          onClick={() => toggleSection('experience')}
          className="flex items-center justify-between w-full text-xs font-bold text-slate-300 mb-2.5"
        >
          <span>Experience Level</span>
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${openSections.experience ? 'rotate-180' : ''}`} />
        </button>
        {openSections.experience && (
          <div className="space-y-1">
            {expOptions.map(opt => {
              const selected = selectedExperience === opt.id;
              return (
                <div
                  key={opt.id}
                  onClick={() => onSelectExperience(opt.id)}
                  className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 cursor-pointer text-xs transition-colors"
                >
                  <div className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${
                    selected ? 'border-amber-400' : 'border-slate-600'
                  }`}>
                    {selected && <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
                  </div>
                  <span className={`font-medium ${selected ? 'text-amber-300' : 'text-slate-300'}`}>
                    {opt.label}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
};
