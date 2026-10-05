import React from 'react';

interface HubHeroProps {
  onScrollDown: () => void;
}

export const HubHero: React.FC<HubHeroProps> = ({ onScrollDown }) => {
  return (
    <section className="hero-panel" aria-label="All Career introduction">
      <h1>ALL_CAREER</h1>
      <p className="scroll-cue" onClick={onScrollDown}>
        Scroll to explore or click
      </p>
    </section>
  );
};
