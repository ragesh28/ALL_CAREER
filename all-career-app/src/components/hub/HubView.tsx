import React from 'react';
import { GlobalLogoPill } from '../common/GlobalLogoPill';
import { HubHero } from './HubHero';
import { HubCategoryGrid } from './HubCategoryGrid';

interface HubViewProps {
  onNavigate: (view: 'career_explorer' | 'big_company_jobs' | 'all_jobs' | 'practice') => void;
}

export const HubView: React.FC<HubViewProps> = ({ onNavigate }) => {
  const scrollToCategories = () => {
    const el = document.getElementById('categoryGrid');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="hub-container">
      {/* Top-left Global Logo Pill */}
      <GlobalLogoPill onGoHome={() => window.scrollTo({ top: 0, behavior: 'smooth' })} />

      <main className="career-stage">
        {/* Screenshot 1: Hero Section */}
        <HubHero onScrollDown={scrollToCategories} />

        {/* Screenshot 2: Category Grid */}
        <HubCategoryGrid onNavigate={onNavigate} />
      </main>
    </div>
  );
};
