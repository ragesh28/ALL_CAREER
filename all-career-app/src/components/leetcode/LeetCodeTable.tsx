import React, { useState } from 'react';
import { LeetCodeProblem } from '../../types/leetcode';
import { Search, ExternalLink, Flame, Building2, Tag, ChevronLeft, ChevronRight } from 'lucide-react';

interface LeetCodeTableProps {
  problems: LeetCodeProblem[];
}

export const LeetCodeTable: React.FC<LeetCodeTableProps> = ({ problems }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDifficulty, setSelectedDifficulty] = useState('all');
  const [selectedCompany, setSelectedCompany] = useState('all');
  const [selectedTopic, setSelectedTopic] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 50;

  const topCompanies = ['all', 'Google', 'Amazon', 'Meta', 'Microsoft', 'Apple', 'Uber', 'Bloomberg', 'TikTok', 'Adobe'];
  const topTopics = ['all', 'Array', 'String', 'Hash Table', 'Dynamic Programming', 'Math', 'Sorting', 'Depth-First Search', 'Binary Search', 'Tree', 'Graph'];

  const filtered = problems.filter(p => {
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const matchTitle = p.title.toLowerCase().includes(term);
      const matchId = String(p.id) === term;
      const matchTopic = p.topic_tags?.some(t => t.toLowerCase().includes(term));
      if (!matchTitle && !matchId && !matchTopic) return false;
    }

    if (selectedDifficulty !== 'all') {
      if (p.difficulty.toLowerCase() !== selectedDifficulty.toLowerCase()) return false;
    }

    if (selectedCompany !== 'all') {
      const hasComp = p.companies?.some(c => c.toLowerCase() === selectedCompany.toLowerCase());
      if (!hasComp) return false;
    }

    if (selectedTopic !== 'all') {
      const hasTopic = p.topic_tags?.some(t => t.toLowerCase() === selectedTopic.toLowerCase());
      if (!hasTopic) return false;
    }

    return true;
  });

  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  const currentProblems = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const getDiffBadge = (diff: string) => {
    const d = diff.toLowerCase();
    if (d === 'easy') {
      return <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Easy</span>;
    }
    if (d === 'hard') {
      return <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">Hard</span>;
    }
    return <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">Medium</span>;
  };

  return (
    <div className="bg-[#0b1120]/80 backdrop-blur-md rounded-2xl border border-white/5 p-4 sm:p-6 shadow-xl">
      {/* Controls Bar */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center mb-6">
        {/* Search */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search problem title, #ID, topic..."
            value={searchTerm}
            onChange={e => { setSearchTerm(e.target.value); setCurrentPage(1); }}
            className="w-full pl-9 pr-4 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/50"
          />
        </div>

        {/* Difficulty Selectors */}
        <div className="flex items-center gap-1.5 bg-white/5 p-1 rounded-xl border border-white/5">
          {['all', 'easy', 'medium', 'hard'].map(d => (
            <button
              key={d}
              onClick={() => { setSelectedDifficulty(d); setCurrentPage(1); }}
              className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize transition-all ${
                selectedDifficulty === d
                  ? 'bg-emerald-500 text-black font-bold shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Top Company Chips */}
      <div className="flex flex-wrap items-center gap-1.5 mb-4">
        <span className="text-[11px] font-bold text-slate-500 uppercase mr-1">Companies:</span>
        {topCompanies.map(c => (
          <button
            key={c}
            onClick={() => { setSelectedCompany(c); setCurrentPage(1); }}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              selectedCompany === c
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                : 'bg-white/5 text-slate-400 hover:text-slate-200 border border-white/5'
            }`}
          >
            {c === 'all' ? 'All Companies' : c}
          </button>
        ))}
      </div>

      {/* Top Topics Chips */}
      <div className="flex flex-wrap items-center gap-1.5 mb-6">
        <span className="text-[11px] font-bold text-slate-500 uppercase mr-1">Topics:</span>
        {topTopics.map(t => (
          <button
            key={t}
            onClick={() => { setSelectedTopic(t); setCurrentPage(1); }}
            className={`px-2.5 py-0.5 rounded-md text-[11px] font-medium transition-all ${
              selectedTopic === t
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
                : 'bg-white/[0.03] text-slate-500 hover:text-slate-300 border border-white/5'
            }`}
          >
            {t === 'all' ? 'All Topics' : t}
          </button>
        ))}
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between text-xs text-slate-400 pb-3 border-b border-white/10 mb-2 font-medium">
        <span>Showing <strong className="text-white">{filtered.length.toLocaleString()}</strong> problems</span>
        <span>Page {currentPage} of {totalPages}</span>
      </div>

      {/* Problems Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              <th className="py-3 px-3">#ID</th>
              <th className="py-3 px-3">Title</th>
              <th className="py-3 px-3">Difficulty</th>
              <th className="py-3 px-3">Frequency</th>
              <th className="py-3 px-3">Topics</th>
              <th className="py-3 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-sm">
            {currentProblems.map(p => {
              const problemSlug = p.slug || p.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
              const url = p.url || `https://leetcode.com/problems/${problemSlug}/`;
              const freq = p.max_frequency_pct ? `${p.max_frequency_pct}%` : 'High';

              return (
                <tr key={p.id} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="py-3 px-3 font-mono text-xs text-slate-400 font-bold">
                    {p.id}
                  </td>
                  <td className="py-3 px-3">
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-slate-200 group-hover:text-emerald-400 transition-colors flex items-center gap-1.5"
                    >
                      <span>{p.title}</span>
                      <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity text-emerald-400" />
                    </a>
                  </td>
                  <td className="py-3 px-3 whitespace-nowrap">
                    {getDiffBadge(p.difficulty)}
                  </td>
                  <td className="py-3 px-3 whitespace-nowrap">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
                      <Flame className="w-3.5 h-3.5" />
                      <span>{freq}</span>
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex flex-wrap gap-1 max-w-xs">
                      {(p.topic_tags || ['Algorithms']).slice(0, 3).map((topic, i) => (
                        <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-slate-400 border border-white/5">
                          {topic}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right whitespace-nowrap">
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-bold bg-emerald-500/10 hover:bg-emerald-500 text-emerald-400 hover:text-black transition-all border border-emerald-500/20"
                    >
                      Solve
                    </a>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-6 border-t border-white/5 mt-4">
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed text-slate-300"
          >
            <ChevronLeft className="w-4 h-4" /> Previous
          </button>
          <span className="text-xs text-slate-400 font-medium">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed text-slate-300"
          >
            Next <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};
