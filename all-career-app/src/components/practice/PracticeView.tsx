import React, { useState } from 'react';
import { GlobalLogoPill } from '../common/GlobalLogoPill';
import { PracticeSidebar } from './PracticeSidebar';
import { PracticeContent } from './PracticeContent';

interface PracticeViewProps {
  onGoHub: () => void;
}

export const PracticeView: React.FC<PracticeViewProps> = ({ onGoHub }) => {
  const [selectedMode, setSelectedMode] = useState<string>('welcome');
  const [selectedCompany, setSelectedCompany] = useState<string>('');

  // Sample company list matching Screenshot 4
  const sampleCompanies = [
    { name: '1kosmos', count: 1 },
    { name: '1Kosmos', count: 1 },
    { name: '6sense', count: 7 },
    { name: 'Accelya', count: 1 },
    { name: 'Accenture', count: 169 },
    { name: 'Accenture (India)', count: 156 },
    { name: 'Accolite', count: 23 },
    { name: 'Acko', count: 4 },
    { name: 'Adobe', count: 142 },
    { name: 'Amazon', count: 412 },
    { name: 'Apple', count: 185 },
    { name: 'Atlassian', count: 94 },
    { name: 'Cisco', count: 68 },
    { name: 'Flipkart', count: 86 },
    { name: 'Google', count: 520 },
    { name: 'Goldman Sachs', count: 112 },
    { name: 'Microsoft', count: 390 },
    { name: 'Oracle', count: 88 },
    { name: 'Uber', count: 154 }
  ];

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

      {/* Hub button at top-right */}
      <div style={{ position: 'absolute', top: '20px', right: '30px', zIndex: 1000 }}>
        <button 
          onClick={onGoHub}
          className="btn-hub-nav"
          style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa', borderColor: 'rgba(59, 130, 246, 0.3)' }}
        >
          🏠 Hub
        </button>
      </div>

      <div className="practice-layout">
        {/* Screenshot 4 Sidebar */}
        <PracticeSidebar
          selectedMode={selectedMode}
          onSelectMode={handleSelectMode}
          selectedCompany={selectedCompany}
          onSelectCompany={handleSelectCompany}
          companiesList={sampleCompanies}
        />

        {/* Screenshot 4 Content */}
        <PracticeContent
          selectedMode={selectedMode}
          selectedCompany={selectedCompany}
        />
      </div>
    </div>
  );
};
