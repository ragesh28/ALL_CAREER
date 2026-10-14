import React, { useState, useEffect } from 'react';
import { GlobalLogoPill } from '../common/GlobalLogoPill';
import { PracticeSidebar } from './PracticeSidebar';
import { PracticeContent } from './PracticeContent';
import { fetchJsonWithFallback } from '../../utils/urlHelper';

interface CompanyEntry {
  name: string;
  count: number;
}

interface PracticeViewProps {
  onGoHub: () => void;
  onNavigateToJobs?: (company: string) => void;
}

const DEFAULT_COMPANIES: CompanyEntry[] = [
  { name: 'Accenture', count: 310 },
  { name: 'Adobe', count: 520 },
  { name: 'Amazon', count: 2045 },
  { name: 'Apple', count: 890 },
  { name: 'Atlassian', count: 190 },
  { name: 'Bloomberg', count: 1257 },
  { name: 'Cisco', count: 260 },
  { name: 'Flipkart', count: 240 },
  { name: 'Goldman Sachs', count: 480 },
  { name: 'Google', count: 2361 },
  { name: 'Infosys', count: 290 },
  { name: 'LinkedIn', count: 340 },
  { name: 'Meta', count: 1420 },
  { name: 'Microsoft', count: 1423 },
  { name: 'Oracle', count: 380 },
  { name: 'TCS', count: 320 },
  { name: 'Uber', count: 597 },
  { name: 'Wipro', count: 210 }
];

export const PracticeView: React.FC<PracticeViewProps> = ({ onGoHub, onNavigateToJobs }) => {
  const [selectedMode, setSelectedMode] = useState<string>('all_questions');
  const [selectedCompany, setSelectedCompany] = useState<string>('');
  const [companies, setCompanies] = useState<CompanyEntry[]>(DEFAULT_COMPANIES);

  // Load complete deduplicated company list from JSON
  useEffect(() => {
    // Fetch companies: try workers API first, then local json fallbacks
    fetch('https://leetcode-api.lragesh28.workers.dev/api/companies')
      .then(res => res.json())
      .then((data: any[]) => {
        if (Array.isArray(data) && data.length > 0) {
          // Normalize names to Title Case, deduplicate and sort A-Z
          const compMap = new Map<string, number>();
          data.forEach(item => {
            const raw = typeof item === 'string' ? item : item.name;
            const cnt = typeof item === 'object' && item.count ? item.count : 0;
            if (!raw) return;
            const norm = raw.trim().replace(/\b\w/g, (l: string) => l.toUpperCase());
            compMap.set(norm, Math.max(compMap.get(norm) || 0, cnt));
          });
          const list: CompanyEntry[] = Array.from(compMap.entries()).map(([name, count]) => ({
            name,
            count: count || (name.toLowerCase() === 'uber' ? 597 : 100)
          }));
          list.sort((a, b) => a.name.localeCompare(b.name));
          setCompanies(list);
          return;
        }
        throw new Error('Empty from worker API');
      })
      .catch(() => {
        fetchJsonWithFallback<CompanyEntry[]>('data/leetcode_companies.json', [
          'all-career-app/public/data/leetcode_companies.json',
          './data/leetcode_companies.json'
        ]).then(data => {
          if (data && Array.isArray(data) && data.length > 0) {
            const sorted = data.slice().sort((a, b) => a.name.localeCompare(b.name));
            setCompanies(sorted);
          }
        }).catch(err => {
          console.warn('Could not load leetcode_companies.json, using default list:', err);
        });
      });
  }, []);

  const handleSelectMode = (mode: string) => {
    setSelectedMode(mode);
    setSelectedCompany('');
  };

  const handleSelectCompany = (comp: string) => {
    setSelectedMode('company');
    setSelectedCompany(comp);
  };

  const handleCompanyCountUpdate = (compName: string, count: number) => {
    setCompanies(prev => prev.map(c => {
      if (c.name.toLowerCase() === compName.toLowerCase()) {
        return { ...c, count };
      }
      return c;
    }));
  };

  return (
    <div className="practice-page">
      {/* Top-left Global Logo Pill */}
      <GlobalLogoPill onGoHome={onGoHub} />

      <div className="practice-layout">
        <PracticeSidebar
          selectedMode={selectedMode}
          onSelectMode={handleSelectMode}
          selectedCompany={selectedCompany}
          onSelectCompany={handleSelectCompany}
          companiesList={companies}
        />

        <PracticeContent
          selectedMode={selectedMode}
          selectedCompany={selectedCompany}
          onNavigateToJobs={onNavigateToJobs}
          onCompanyCountUpdate={handleCompanyCountUpdate}
        />
      </div>
    </div>
  );
};
