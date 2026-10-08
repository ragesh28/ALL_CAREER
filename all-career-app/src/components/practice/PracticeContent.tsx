import React, { useState, useEffect, useMemo } from 'react';
import { ArrowUpDown, BriefcaseBusiness, Layers3, Search, Star, X } from 'lucide-react';
import { CustomDropdown } from '../common/CustomDropdown';
import { top150Data, Top150Problem } from '../../data/top150Data';
import { CompanyLogo } from '../common/CompanyLogo';

export interface LeetCodeMasterProblem {
  id: number;
  title: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  url: string;
  slug?: string;
  topics?: string[];
  companies?: string[];
  company_count?: number;
  acceptance?: string;
  frequency?: number;
}

interface PracticeContentProps {
  selectedMode: string;
  selectedCompany: string;
  onNavigateToJobs?: (company: string) => void;
}

const ITEMS_PER_PAGE = 100;

const topicTone = (topic: string) => {
  const value = topic.toLowerCase();
  if (value.includes('dynamic') || value.includes('backtracking')) return 'topic-tag tone-rose';
  if (value.includes('graph') || value.includes('tree')) return 'topic-tag tone-violet';
  if (value.includes('array') || value.includes('hash')) return 'topic-tag tone-emerald';
  if (value.includes('string') || value.includes('sliding')) return 'topic-tag tone-cyan';
  if (value.includes('math') || value.includes('bit')) return 'topic-tag tone-amber';
  return 'topic-tag tone-slate';
};

const acceptanceTone = (value?: string) => {
  const rate = parseFloat((value || '').replace('%', ''));
  if (Number.isNaN(rate)) return 'acceptance-rate tone-slate';
  if (rate < 30) return 'acceptance-rate tone-rose';
  if (rate < 50) return 'acceptance-rate tone-amber';
  if (rate < 70) return 'acceptance-rate tone-cyan';
  if (rate < 90) return 'acceptance-rate tone-emerald';
  return 'acceptance-rate tone-positive';
};

export const PracticeContent: React.FC<PracticeContentProps> = ({
  selectedMode,
  selectedCompany,
  onNavigateToJobs
}) => {
  // Master catalog state for "All Questions"
  const [allProblems, setAllProblems] = useState<LeetCodeMasterProblem[]>([]);
  const [loadingMaster, setLoadingMaster] = useState<boolean>(false);
  const [currentTopic, setCurrentTopic] = useState<string>('All');
  const [topicsExpanded, setTopicsExpanded] = useState<boolean>(false);
  const [searchAll, setSearchAll] = useState<string>('');
  const [diffAll, setDiffAll] = useState<string>('All');
  const [sortAll, setSortAll] = useState<string>('id');
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Company questions state
  const [companyProblems, setCompanyProblems] = useState<LeetCodeMasterProblem[]>([]);
  const [loadingCompany, setLoadingCompany] = useState<boolean>(false);
  const [companySearch, setCompanySearch] = useState<string>('');
  const [companyDiff, setCompanyDiff] = useState<string>('All');
  const [companySort, setCompanySort] = useState<string>('freq');

  // Load master catalog once if "all_questions" or company fallback needed
  useEffect(() => {
    if (allProblems.length === 0) {
      setLoadingMaster(true);
      fetch('/data/leetcode_master.json')
        .then(res => res.json())
        .then((data: LeetCodeMasterProblem[]) => {
          if (Array.isArray(data)) {
            // Ensure strict sort by ID ascending
            data.sort((a, b) => Number(a.id) - Number(b.id));
            setAllProblems(data);
          }
          setLoadingMaster(false);
        })
        .catch(err => {
          console.warn('Failed to load leetcode_master.json:', err);
          setLoadingMaster(false);
        });
    }
  }, [allProblems.length]);

  // Load company questions when selectedCompany changes
  useEffect(() => {
    if (selectedMode === 'company' && selectedCompany) {
      setLoadingCompany(true);
      const compClean = selectedCompany.toLowerCase().trim();

      // 1. Try fetching from Cloudflare worker API (like practice.html)
      fetch(`https://leetcode-api.lragesh28.workers.dev/api/company?name=${encodeURIComponent(selectedCompany)}`)
        .then(res => {
          if (!res.ok) throw new Error('API response not ok');
          return res.json();
        })
        .then((data: LeetCodeMasterProblem[]) => {
          if (Array.isArray(data) && data.length > 0) {
            setCompanyProblems(data);
            setLoadingCompany(false);
          } else {
            throw new Error('Empty from worker, using local fallback');
          }
        })
        .catch(() => {
          // 2. Seamless local fallback filtering leetcode_master.json
          fetch('/data/leetcode_master.json')
            .then(res => res.json())
            .then((master: LeetCodeMasterProblem[]) => {
              const matched = master.filter(p =>
                Array.isArray(p.companies) &&
                p.companies.some(c => c.toLowerCase() === compClean || c.toLowerCase().includes(compClean))
              );
              // Fallback to top150 slice if no specific company matches
              if (matched.length > 0) {
                setCompanyProblems(matched);
              } else {
                setCompanyProblems(master.slice(0, 30));
              }
              setLoadingCompany(false);
            })
            .catch(() => {
              setCompanyProblems(top150Data.slice(0, 25) as unknown as LeetCodeMasterProblem[]);
              setLoadingCompany(false);
            });
        });
    }
  }, [selectedMode, selectedCompany]);

  // Dynamic unique topics map with counts
  const uniqueTopics = useMemo(() => {
    const counts = new Map<string, number>();
    allProblems.forEach(p => {
      if (Array.isArray(p.topics)) {
        p.topics.forEach(t => {
          counts.set(t, (counts.get(t) || 0) + 1);
        });
      }
    });
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [allProblems]);

  // Filtered list for "All Questions"
  const filteredAllQuestions = useMemo(() => {
    const s = searchAll.toLowerCase().trim();
    let list = allProblems.filter(p => {
      // Search
      if (s) {
        const matchTitle = (p.title || '').toLowerCase().includes(s);
        const matchId = String(p.id).includes(s);
        if (!matchTitle && !matchId) return false;
      }
      // Difficulty
      if (diffAll !== 'All' && p.difficulty !== diffAll) return false;
      // Topic
      if (currentTopic !== 'All') {
        if (!Array.isArray(p.topics) || !p.topics.includes(currentTopic)) return false;
      }
      return true;
    });

    // Sorting
    if (sortAll === 'id') {
      list.sort((a, b) => Number(a.id) - Number(b.id));
    } else if (sortAll === 'freq') {
      list.sort((a, b) => (b.frequency || 0) - (a.frequency || 0));
    } else if (sortAll === 'accept') {
      const getVal = (str?: string) => parseFloat((str || '0').replace('%', ''));
      list.sort((a, b) => getVal(b.acceptance) - getVal(a.acceptance));
    }

    return list;
  }, [allProblems, searchAll, diffAll, currentTopic, sortAll]);

  // Filtered list for "Company View"
  const filteredCompanyQuestions = useMemo(() => {
    const s = companySearch.toLowerCase().trim();
    let list = companyProblems.filter(p => {
      if (s && !(p.title || '').toLowerCase().includes(s)) return false;
      if (companyDiff !== 'All' && p.difficulty !== companyDiff) return false;
      return true;
    });

    if (companySort === 'freq') {
      list.sort((a, b) => (b.frequency || 0) - (a.frequency || 0));
    } else if (companySort === 'accept') {
      const getVal = (str?: string) => parseFloat((str || '0').replace('%', ''));
      list.sort((a, b) => getVal(b.acceptance) - getVal(a.acceptance));
    } else {
      list.sort((a, b) => Number(a.id) - Number(b.id));
    }

    return list;
  }, [companyProblems, companySearch, companyDiff, companySort]);

  // 1. Default Welcome Screen (Screenshot 4)
  if (!selectedMode || selectedMode === 'welcome') {
    return (
      <main className="practice-content">
        <div className="practice-welcome">
          <h2>Select a category or company to start</h2>
          <p>Data sourced from LeetCode frequency lists</p>
        </div>
      </main>
    );
  }

  // 2. Top 150 Interview Questions (Yellow Star)
  if (selectedMode === 'top150') {
    const grouped: Record<string, Top150Problem[]> = {};
    const topicOrder = [
      'Arrays & Hashing', 'Two Pointers', 'Sliding Window', 'Stack',
      'Binary Search', 'Linked List', 'Trees', 'Tries', 'Heap',
      'Backtracking', 'Graphs', 'Advanced Graphs',
      '1-D Dynamic Programming', '2-D Dynamic Programming',
      'Greedy', 'Intervals', 'Math & Geometry', 'Bit Manipulation'
    ];

    top150Data.forEach(p => {
      if (!grouped[p.topic]) grouped[p.topic] = [];
      grouped[p.topic].push(p);
    });

    return (
      <main className="practice-content">
        <div className="company-header-bar" style={{ background: 'rgba(251, 191, 36, 0.1)', borderColor: 'rgba(251, 191, 36, 0.2)' }}>
          <div className="company-title-row">
            <div style={{ width: '32px', height: '32px', background: '#fbbf24', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'black', fontWeight: 'bold', fontSize: '1.1rem' }}>
              <Star size={17} aria-hidden="true" />
            </div>
            <div className="company-name-large" style={{ color: '#fbbf24' }}>
              Must Do Questions <span style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 500 }}>(Top 150 LeetCode)</span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {topicOrder.map(topic => {
            const problems = grouped[topic];
            if (!problems) return null;
            return (
              <div key={topic} className="practice-table-container">
                <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '12px 20px', fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="18" height="18"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                  {topic} <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 500 }}>({problems.length})</span>
                </div>

                <table className="problem-table">
                  <thead>
                    <tr>
                      <th style={{ width: '60px' }}>ID</th>
                      <th>Problem Name</th>
                      <th style={{ width: '120px' }}>Difficulty</th>
                      <th style={{ width: '100px' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {problems.map(p => (
                      <tr key={p.id}>
                        <td style={{ color: '#64748b', fontFamily: 'monospace' }}>#{p.id}</td>
                        <td>
                          <a href={p.url} target="_blank" rel="noopener noreferrer" className="problem-link">
                            {p.title}
                          </a>
                        </td>
                        <td><span className={`diff-tag diff-${p.difficulty}`}>{p.difficulty}</span></td>
                        <td>
                          <a href={p.url} target="_blank" rel="noopener noreferrer" style={{ color: '#38bdf8', fontWeight: 600, fontSize: '0.85rem', textDecoration: 'none' }}>
                            Solve &gt;
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          })}
        </div>
      </main>
    );
  }

  // 3. All Questions (Master List)
  if (selectedMode === 'all_questions') {
    const total = filteredAllQuestions.length;
    const totalPages = Math.ceil(total / ITEMS_PER_PAGE);
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = Math.min(startIndex + ITEMS_PER_PAGE, total);
    const pageItems = filteredAllQuestions.slice(startIndex, endIndex);

    const handleTopicClick = (t: string) => {
      setCurrentTopic(t);
      setCurrentPage(1);
    };

    const handlePageChange = (p: number) => {
      setCurrentPage(p);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    // Pagination numbers generator matching all_questions.html
    const pagesToShow: (number | string)[] = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pagesToShow.push(i);
    } else {
      if (currentPage <= 4) {
        pagesToShow.push(1, 2, 3, 4, 5, '...', totalPages);
      } else if (currentPage >= totalPages - 3) {
        pagesToShow.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
      } else {
        pagesToShow.push(1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages);
      }
    }

    return (
      <main className="practice-content">
        {/* TOPIC FILTER BAR */}
        <div className="topic-wrapper">
          <div className="topic-header-row">
            <span className="topic-label"><Layers3 size={15} aria-hidden="true" /> Filter by Topic</span>
            <button
              className="toggle-btn"
              onClick={() => setTopicsExpanded(prev => !prev)}
            >
              {topicsExpanded ? 'Show Less ▲' : 'Show All Topics ▼'}
            </button>
          </div>
          <div className={`topic-grid ${topicsExpanded ? 'expanded' : ''}`}>
            <button
              className={`topic-btn ${currentTopic === 'All' ? 'active' : ''}`}
              onClick={() => handleTopicClick('All')}
            >
              All Topics ({allProblems.length})
            </button>
            {uniqueTopics.map(([topic, count]) => (
              <button
                key={topic}
                className={`topic-btn ${currentTopic === topic ? 'active' : ''}`}
                onClick={() => handleTopicClick(topic)}
              >
                {topic} ({count})
              </button>
            ))}
          </div>
        </div>

        {/* STICKY FILTER BAR */}
        <div className="company-header-bar">
          <div className="practice-list-title">
            All questions
          </div>

          <div className="toolbar">
            <div className="practice-search-input-wrapper">
              <Search size={15} className="practice-search-icon" aria-hidden="true" />
              <input
                type="text"
                className="practice-search-input"
                placeholder="Search ID or Name..."
                value={searchAll}
                onChange={e => {
                  setSearchAll(e.target.value);
                  setCurrentPage(1);
                }}
                autoComplete="off"
                spellCheck={false}
              />
              {searchAll && (
                <button
                  type="button"
                  className="practice-search-clear"
                  onClick={() => {
                    setSearchAll('');
                    setCurrentPage(1);
                  }}
                  aria-label="Clear search"
                >
                  <X size={13} aria-hidden="true" />
                </button>
              )}
            </div>

            <div className="difficulty-filter-set" aria-label="Filter by difficulty">
              {(['All', 'Easy', 'Medium', 'Hard'] as const).map(difficulty => (
                <button
                  key={difficulty}
                  type="button"
                  className={`difficulty-filter difficulty-${difficulty.toLowerCase()} ${diffAll === difficulty ? 'active' : ''}`}
                  onClick={() => { setDiffAll(difficulty); setCurrentPage(1); }}
                >
                  {difficulty === 'All' ? 'All difficulty' : difficulty}
                </button>
              ))}
            </div>

            <CustomDropdown
              id="practice-sort-all"
              value={sortAll}
              onChange={val => {
                setSortAll(val);
                setCurrentPage(1);
              }}
              options={[
                { value: 'id', label: 'ID (1-3422)' },
                { value: 'freq', label: 'Frequency (High-Low)' },
                { value: 'accept', label: 'Acceptance (High-Low)' }
              ]}
              icon={<ArrowUpDown size={14} className="control-icon" aria-hidden="true" />}
              prefix="Sort"
              ariaLabel="Sort practice problems"
              className="practice-sort-custom"
            />

            <div style={{ color: '#94a3b8', fontSize: '0.85rem', fontWeight: 600 }}>
              Showing <span style={{ color: '#38bdf8' }}>{total > 0 ? `${startIndex + 1}-${endIndex}` : '0'}</span> of {total} problems
            </div>
          </div>
        </div>

        {/* MASTER PROBLEMS TABLE */}
        <div className="practice-table-container">
          {loadingMaster ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#94a3b8' }}>
              <div style={{ display: 'inline-block', width: '32px', height: '32px', border: '3px solid rgba(56,189,248,0.2)', borderTopColor: '#38bdf8', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }}></div>
              <p style={{ marginTop: '12px' }}>Loading 3,400+ LeetCode problems...</p>
            </div>
          ) : total === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#94a3b8' }}>
              No problems found matching your filters.
            </div>
          ) : (
            <table className="problem-table">
              <thead>
                <tr>
                  <th style={{ width: '70px' }}>ID</th>
                  <th>Problem Name</th>
                  <th style={{ width: '280px' }}>Topics</th>
                  <th style={{ width: '110px' }}>Acceptance</th>
                  <th style={{ width: '100px' }}>Difficulty</th>
                  <th style={{ width: '120px' }}>Frequency</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map(p => {
                  const freq = p.frequency || (p.company_count ? Math.min(100, Math.floor((p.company_count / 250) * 100)) : 15);
                  let barColor = freq > 70 ? '#2cbb5d' : (freq > 40 ? '#fbbf24' : '#94a3b8');
                  const topicList = Array.isArray(p.topics) ? p.topics : [];
                  const compList = Array.isArray(p.companies) ? p.companies : [];

                  return (
                    <tr key={p.id}>
                      <td style={{ color: '#64748b', fontFamily: 'monospace', fontWeight: 600 }}>#{p.id}</td>
                      <td>
                        <a href={p.url} target="_blank" rel="noopener noreferrer" className="problem-link">
                          {p.title}
                        </a>
                      </td>
                      <td>
                        {topicList.slice(0, 4).map(t => (
                          <span key={t} className={topicTone(t)}>{t}</span>
                        ))}
                        {topicList.length > 4 && (
                          <span className="topic-tag" style={{ opacity: 0.6 }}>+{topicList.length - 4}</span>
                        )}
                      </td>
                      <td><span className={acceptanceTone(p.acceptance)}>{p.acceptance || 'N/A'}</span></td>
                      <td><span className={`diff-tag diff-${p.difficulty}`}>{p.difficulty}</span></td>
                      <td>
                      <div className={`frequency-rate ${freq > 70 ? 'tone-emerald' : freq > 40 ? 'tone-amber' : 'tone-slate'}`}>{freq}%</div>
                        <div className="freq-bar-container">
                          <div className="freq-bar-fill" style={{ width: `${freq}%`, background: barColor }}></div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* PAGINATION CONTROLS */}
        {totalPages > 1 && (
          <div className="pagination-container">
            <button
              className="page-btn"
              disabled={currentPage === 1}
              onClick={() => handlePageChange(currentPage - 1)}
            >
              ←
            </button>

            {pagesToShow.map((page, idx) => {
              if (page === '...') {
                return (
                  <span key={`dots-${idx}`} style={{ color: '#64748b', padding: '0 6px', userSelect: 'none' }}>
                    ...
                  </span>
                );
              }
              const pNum = Number(page);
              return (
                <button
                  key={pNum}
                  className={`page-btn ${currentPage === pNum ? 'active' : ''}`}
                  onClick={() => handlePageChange(pNum)}
                >
                  {pNum}
                </button>
              );
            })}

            <button
              className="page-btn"
              disabled={currentPage === totalPages}
              onClick={() => handlePageChange(currentPage + 1)}
            >
              →
            </button>
          </div>
        )}
      </main>
    );
  }

  // 4. Selected Company View
  return (
    <main className="practice-content">
      {/* COMPANY HEADER BAR */}
      <div className="company-header-bar">
        <div className="company-title-row">
          <CompanyLogo name={selectedCompany} size="md" />
          <div className="company-name-large">
            <span>{selectedCompany}</span>
            <span style={{ fontSize: '0.85rem', fontWeight: 500, color: '#fbbf24' }}>
              ({companyProblems.length} questions)
            </span>
          </div>

          {/* Action button: Direct link to view company jobs in All Jobs */}
          {onNavigateToJobs && (
            <button
              className="btn-view-company-jobs"
              onClick={() => onNavigateToJobs(selectedCompany)}
              title={`View active job openings for ${selectedCompany}`}
            >
              <BriefcaseBusiness size={15} aria-hidden="true" /> <span>View Open Jobs for {selectedCompany}</span>
            </button>
          )}
        </div>

        {/* TOOLBAR */}
        <div className="toolbar">
          <div className="practice-search-input-wrapper">
            <Search size={15} className="practice-search-icon" aria-hidden="true" />
            <input
              type="text"
              className="practice-search-input"
              placeholder="Search problems..."
              value={companySearch}
              onChange={e => setCompanySearch(e.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
            {companySearch && (
              <button
                type="button"
                className="practice-search-clear"
                onClick={() => setCompanySearch('')}
                aria-label="Clear search"
              >
                <X size={13} aria-hidden="true" />
              </button>
            )}
          </div>

            <div className="difficulty-filter-set" aria-label="Filter company questions by difficulty">
              {(['All', 'Easy', 'Medium', 'Hard'] as const).map(difficulty => (
                <button
                  key={difficulty}
                  type="button"
                  className={`difficulty-filter difficulty-${difficulty.toLowerCase()} ${companyDiff === difficulty ? 'active' : ''}`}
                  onClick={() => setCompanyDiff(difficulty)}
                >
                  {difficulty === 'All' ? 'All difficulty' : difficulty}
                </button>
              ))}
            </div>

          <CustomDropdown
            id="practice-sort-company"
            value={companySort}
            onChange={val => setCompanySort(val)}
            options={[
              { value: 'freq', label: 'Frequency' },
              { value: 'accept', label: 'Acceptance' },
              { value: 'id', label: 'ID' }
            ]}
            icon={<ArrowUpDown size={14} className="control-icon" aria-hidden="true" />}
            prefix="Sort"
            ariaLabel="Sort company questions"
            className="practice-sort-custom"
          />
        </div>
      </div>

      {/* PROBLEMS TABLE */}
      <div className="practice-table-container">
        {loadingCompany ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#94a3b8' }}>
            <div style={{ display: 'inline-block', width: '32px', height: '32px', border: '3px solid rgba(56,189,248,0.2)', borderTopColor: '#38bdf8', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }}></div>
            <p style={{ marginTop: '12px' }}>Loading {selectedCompany} interview questions...</p>
          </div>
        ) : filteredCompanyQuestions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#94a3b8' }}>
            No questions found for {selectedCompany} matching your filter.
          </div>
        ) : (
          <table className="problem-table">
            <thead>
              <tr>
                <th style={{ width: '50px' }}>#</th>
                <th>Title</th>
                <th style={{ width: '120px' }}>Acceptance</th>
                <th style={{ width: '100px' }}>Difficulty</th>
                <th style={{ width: '140px' }}>Frequency</th>
              </tr>
            </thead>
            <tbody>
              {filteredCompanyQuestions.map((p, idx) => {
                const freq = p.frequency || (p.company_count ? Math.min(100, Math.floor((p.company_count / 250) * 100)) : 40);
                let barColor = freq > 70 ? '#2cbb5d' : (freq > 40 ? '#fbbf24' : '#94a3b8');

                return (
                  <tr key={p.id || idx}>
                    <td style={{ color: '#64748b', fontFamily: 'monospace' }}>{idx + 1}</td>
                    <td>
                      <a href={p.url || `https://leetcode.com/problems/${p.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}/`} target="_blank" rel="noopener noreferrer" className="problem-link">
                        {p.title}
                      </a>
                    </td>
                    <td><span className={acceptanceTone(p.acceptance)}>{p.acceptance || 'N/A'}</span></td>
                    <td><span className={`diff-tag diff-${p.difficulty || 'Medium'}`}>{p.difficulty || 'Medium'}</span></td>
                    <td>
                      <div className="freq-bar-container">
                        <div className="freq-bar-fill" style={{ width: `${freq}%`, background: barColor }}></div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
};
