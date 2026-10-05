import React from 'react';
import { top150Data, Top150Problem } from '../../data/top150Data';

interface PracticeContentProps {
  selectedMode: string;
  selectedCompany: string;
  companyProblems?: Top150Problem[];
}

export const PracticeContent: React.FC<PracticeContentProps> = ({
  selectedMode,
  selectedCompany,
  companyProblems
}) => {
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

  // 2. Top 150 Interview Questions
  if (selectedMode === 'top150') {
    // Group by topic
    const grouped: Record<string, Top150Problem[]> = {};
    top150Data.forEach(p => {
      if (!grouped[p.topic]) grouped[p.topic] = [];
      grouped[p.topic].push(p);
    });

    return (
      <main className="practice-content">
        <div style={{ marginBottom: '24px' }}>
          <h2 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>★</span> Top 150 Interview Questions
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.88rem' }}>
            Must-solve foundational DSA problems selected by top tech interviewers.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {Object.entries(grouped).map(([topic, problems]) => (
            <div key={topic} style={{ background: 'rgba(15, 23, 42, 0.4)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '8px' }}>
                {topic} <span style={{ fontSize: '0.8rem', color: '#64748b' }}>({problems.length})</span>
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {problems.map(p => (
                  <div key={p.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px', borderRadius: '8px', background: 'rgba(255,255,255,0.02)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ color: '#64748b', fontSize: '0.78rem', width: '36px', fontFamily: 'monospace' }}>#{p.id}</span>
                      <a 
                        href={p.url} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        style={{ color: '#f1f5f9', textDecoration: 'none', fontWeight: 600, fontSize: '0.88rem' }}
                        onMouseOver={(e) => (e.currentTarget.style.color = '#38bdf8')}
                        onMouseOut={(e) => (e.currentTarget.style.color = '#f1f5f9')}
                      >
                        {p.title}
                      </a>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span className={`diff-tag diff-${p.difficulty}`}>{p.difficulty}</span>
                      <a 
                        href={p.url} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        style={{ padding: '4px 10px', borderRadius: '6px', background: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa', textDecoration: 'none', fontSize: '0.75rem', fontWeight: 700 }}
                      >
                        Solve ↗
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </main>
    );
  }

  // 3. Selected Company View
  const list = companyProblems || top150Data.slice(0, 25);
  return (
    <main className="practice-content">
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#38bdf8' }}>
          {selectedCompany} Interview Questions
        </h2>
        <p style={{ color: '#94a3b8', fontSize: '0.88rem' }}>
          Recent question frequency asked at {selectedCompany} interviews.
        </p>
      </div>

      <div style={{ background: 'rgba(15, 23, 42, 0.4)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '16px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {list.map((p, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', borderRadius: '8px', background: 'rgba(255,255,255,0.02)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ color: '#64748b', fontSize: '0.78rem', width: '36px', fontFamily: 'monospace' }}>#{p.id || idx + 1}</span>
                <a 
                  href={p.url || `https://leetcode.com/problems/${p.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}/`} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  style={{ color: '#f1f5f9', textDecoration: 'none', fontWeight: 600, fontSize: '0.9rem' }}
                >
                  {p.title}
                </a>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span className={`diff-tag diff-${p.difficulty || 'Medium'}`}>{p.difficulty || 'Medium'}</span>
                <a 
                  href={p.url || `https://leetcode.com/problems/${p.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}/`} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  style={{ padding: '4px 10px', borderRadius: '6px', background: 'rgba(52, 211, 153, 0.1)', color: '#34d399', textDecoration: 'none', fontSize: '0.75rem', fontWeight: 700 }}
                >
                  Solve ↗
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
};
