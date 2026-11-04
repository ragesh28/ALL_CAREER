import React, { Suspense, lazy, useState, useEffect } from 'react';
import { HubView } from './components/hub/HubView';
import { AllJobsView } from './components/alljobs/AllJobsView';
import { AutoApplyHUD } from './components/common/AutoApplyHUD';
import './styles/all_career_theme.css';

const PracticeView = lazy(() => import('./components/practice/PracticeView').then(m => ({ default: m.PracticeView })));
const BigCompanyView = lazy(() => import('./components/bigcompany/BigCompanyView').then(m => ({ default: m.BigCompanyView })));
const BigCompanyJobsView = lazy(() => import('./components/bigcompany/BigCompanyJobsView').then(m => ({ default: m.BigCompanyJobsView })));

export type ViewType = 'hub' | 'all_jobs' | 'practice' | 'big_company_jobs' | 'career_explorer';

const getInitialView = (): ViewType => {
  if (typeof window !== 'undefined') {
    const hash = window.location.hash.replace('#', '') as ViewType;
    if (['hub', 'all_jobs', 'practice', 'big_company_jobs', 'career_explorer'].includes(hash)) {
      return hash;
    }
  }
  return 'hub';
};

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewType>(getInitialView);
  const [allJobsSearch, setAllJobsSearch] = useState<string>('');

  // Handle URL hash navigation if user refreshes or shares URL
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as ViewType;
      if (['hub', 'all_jobs', 'practice', 'big_company_jobs', 'career_explorer'].includes(hash)) {
        setCurrentView(hash);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateTo = (view: ViewType) => {
    setCurrentView(view);
    window.location.hash = view;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNavigateToCompanyJobs = (companyName: string) => {
    setAllJobsSearch(companyName);
    navigateTo('all_jobs');
  };

  return (
    <div className="all-career-root">
      <Suspense fallback={<div role="status" style={{ padding: 32, color: '#94a3b8' }}>Loading section…</div>}>
      {/* 1. Hub / Landing Scene (Screenshots 1 & 2) */}
      {currentView === 'hub' && (
        <HubView onNavigate={navigateTo} />
      )}

      {/* 2. All Jobs Portal (Screenshot 3) */}
      {currentView === 'all_jobs' && (
        <AllJobsView
          onGoHub={() => {
            setAllJobsSearch('');
            navigateTo('hub');
          }}
          initialSearch={allJobsSearch}
        />
      )}

      {/* 3. Learn Coding / Practice (Screenshot 4) */}
      {currentView === 'practice' && (
        <PracticeView
          onGoHub={() => navigateTo('hub')}
          onNavigateToJobs={handleNavigateToCompanyJobs}
        />
      )}

      {/* 4. Big Company Name List (Card 1: 150+ Companies Directory) */}
      {currentView === 'career_explorer' && (
        <BigCompanyView
          onGoHub={() => navigateTo('hub')}
          title="Big Company Name List"
        />
      )}

      {/* 5. Big Company Jobs (Card 2: Real Jobs from 180+ Big Companies) */}
      {currentView === 'big_company_jobs' && (
        <BigCompanyJobsView
          onGoHub={() => navigateTo('hub')}
        />
      )}

      {/* Global Auto Apply Real-Time HUD & Extension Modals */}
      </Suspense>
      <AutoApplyHUD />
    </div>
  );
};

export default App;
