import React, { useState, useEffect } from 'react';
import { HubView } from './components/hub/HubView';
import { AllJobsView } from './components/alljobs/AllJobsView';
import { PracticeView } from './components/practice/PracticeView';
import { BigCompanyView } from './components/bigcompany/BigCompanyView';
import './styles/all_career_theme.css';

export type ViewType = 'hub' | 'all_jobs' | 'practice' | 'big_company_jobs' | 'career_explorer';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewType>('hub');

  // Handle URL hash navigation if user refreshes or shares URL
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as ViewType;
      if (['hub', 'all_jobs', 'practice', 'big_company_jobs', 'career_explorer'].includes(hash)) {
        setCurrentView(hash);
      }
    };
    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateTo = (view: ViewType) => {
    setCurrentView(view);
    window.location.hash = view;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="all-career-root">
      {/* 1. Hub / Landing Scene (Screenshots 1 & 2) */}
      {currentView === 'hub' && (
        <HubView onNavigate={navigateTo} />
      )}

      {/* 2. All Jobs Portal (Screenshot 3) */}
      {currentView === 'all_jobs' && (
        <AllJobsView onGoHub={() => navigateTo('hub')} />
      )}

      {/* 3. Learn Coding / Practice (Screenshot 4) */}
      {currentView === 'practice' && (
        <PracticeView onGoHub={() => navigateTo('hub')} />
      )}

      {/* 4. Big Company Jobs / Name List (Screenshot 5) */}
      {(currentView === 'big_company_jobs' || currentView === 'career_explorer') && (
        <BigCompanyView onGoHub={() => navigateTo('hub')} />
      )}
    </div>
  );
};

export default App;
