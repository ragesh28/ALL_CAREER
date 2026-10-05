import React from 'react';
import { Heart, Sparkles, Database, Layers } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-white/5 bg-[#06080f] py-10 px-4 mt-20 text-slate-500 text-xs">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-xs">
            AC
          </div>
          <span className="font-semibold text-slate-300">All Career Platform</span>
          <span>© 2026. Built with React + Vite + Cloudflare D1.</span>
        </div>

        <div className="flex items-center gap-6 text-slate-400">
          <div className="flex items-center gap-1.5 hover:text-emerald-400 transition-colors">
            <Database className="w-3.5 h-3.5" />
            <span>Cloudflare D1 Native</span>
          </div>
          <div className="flex items-center gap-1.5 hover:text-cyan-400 transition-colors">
            <Layers className="w-3.5 h-3.5" />
            <span>JSON Sharding</span>
          </div>
          <div className="flex items-center gap-1.5 hover:text-purple-400 transition-colors">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Modular Architecture</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
