import React from 'react';
import { HeroBanner } from '../components/home/HeroBanner';
import { StatsCounter } from '../components/home/StatsCounter';
import { FeatureCards } from '../components/home/FeatureCards';

interface HomePageProps {
  onNavigate: (tab: string) => void;
  totalJobsCount: number;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate, totalJobsCount }) => {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero section */}
      <HeroBanner onNavigate={onNavigate} totalJobsCount={totalJobsCount} />

      {/* Global Stats counter */}
      <StatsCounter totalJobs={totalJobsCount} />

      {/* Platform Features */}
      <FeatureCards onNavigate={onNavigate} />
    </div>
  );
};
