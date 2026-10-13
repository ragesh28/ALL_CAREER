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
  { name: 'Google', count: 2361 },
  { name: 'Amazon', count: 2045 },
  { name: 'Microsoft', count: 1423 },
  { name: 'Meta', count: 1420 },
  { name: 'Bloomberg', count: 1257 },
  { name: 'Apple', count: 890 },
  { name: 'Uber', count: 680 },
  { name: 'Adobe', count: 520 },
  { name: 'Goldman Sachs', count: 480 },
  { name: 'TCS', count: 320 },
  { name: 'Infosys', count: 290 },
  { name: 'Wipro', count: 210 },
  { name: 'Accenture', count: 310 },
  { name: 'Flipkart', count: 240 },
  { name: 'Oracle', count: 380 },
  { name: 'Cisco', count: 260 },
  { name: 'Atlassian', count: 190 },
  { name: 'LinkedIn', count: 340 }
];

export const PracticeView: React.FC<PracticeViewProps> = ({ onGoHub, onNavigateToJobs }) => {
  const [selectedMode, setSelectedMode] = useState<string>('all_questions');
  const [selectedCompany, setSelectedCompany] = useState<string>('');
  const [companies, setCompanies] = useState<CompanyEntry[]>(DEFAULT_COMPANIES);

  // Load complete deduplicated company list from JSON
  useEffect(() => {
    fetchJsonWithFallback<CompanyEntry[]>('data/leetcode_companies.json')
      .then((data) => {
        if (data && Array.isArray(data) && data.length > 0) {
          setCompanies(data);
        }
      })
      .catch(err => {
        console.warn('Could not load leetcode_companies.json, using default list:', err);
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
        />
      </div>
    </div>
  );
};
