import React from 'react';
import { Calendar, MapPin } from 'lucide-react';

interface WalkinFilterBarProps {
  dates: string[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
  selectedCity: string;
  onSelectCity: (city: string) => void;
  cities: string[];
}

export const WalkinFilterBar: React.FC<WalkinFilterBarProps> = ({
  dates,
  selectedDate,
  onSelectDate,
  selectedCity,
  onSelectCity,
  cities
}) => {
  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-[#0b1120]/80 backdrop-blur-md border border-white/5 mb-8 shadow-sm">
      {/* Date Filter Pills */}
      <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
        <div className="flex items-center gap-1.5 text-xs font-bold text-amber-400 mr-2 flex-shrink-0">
          <Calendar className="w-4 h-4" />
          <span>Walk-in Date:</span>
        </div>
        <button
          onClick={() => onSelectDate('all')}
          className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
            selectedDate === 'all'
              ? 'bg-amber-400 text-black font-bold shadow-sm'
              : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-white/5'
          }`}
        >
          All Dates
        </button>
        {dates.map(date => (
          <button
            key={date}
            onClick={() => onSelectDate(date)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              selectedDate === date
                ? 'bg-amber-400 text-black font-bold shadow-sm'
                : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-white/5'
            }`}
          >
            {date}
          </button>
        ))}
      </div>

      {/* City Dropdown */}
      <div className="flex items-center gap-2 w-full sm:w-auto">
        <MapPin className="w-4 h-4 text-cyan-400 flex-shrink-0" />
        <select
          value={selectedCity}
          onChange={e => onSelectCity(e.target.value)}
          className="w-full sm:w-auto px-3 py-1.5 bg-[#0e1424] border border-white/10 rounded-xl text-xs font-semibold text-slate-200 focus:outline-none focus:border-cyan-500/50 cursor-pointer"
        >
          <option value="all">All Locations</option>
          {cities.map(city => (
            <option key={city} value={city.toLowerCase()}>
              {city}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};
