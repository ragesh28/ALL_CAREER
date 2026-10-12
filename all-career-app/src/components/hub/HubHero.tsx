import React from 'react';

interface HubHeroProps {
  onScrollDown: () => void;
}

export const HubHero: React.FC<HubHeroProps> = ({ onScrollDown }) => {
  return (
    <section className="hero-panel" aria-label="All Career introduction">
      <h1>ALL_CAREER</h1>

      {/* Center-Bottom High-End Kinetic Scroll Indicator */}
      <div
        className="hero-scroll-cue"
        role="button"
        tabIndex={0}
        onClick={(e) => {
          e.stopPropagation();
          onScrollDown();
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onScrollDown();
          }
        }}
        aria-label="Scroll down to categories"
      >
        <div className="scroll-cue-ambient-glow" aria-hidden="true" />
        <div className="scroll-cue-pill">
          {/* Kinetic Photon Chamber */}
          <div className="scroll-photon-chamber" aria-hidden="true">
            <div className="scroll-photon-rail" />
            <div className="scroll-photon-laser" />
            <div className="scroll-photon-pulse-ring" />
          </div>

          {/* Shimmer Typography */}
          <div className="scroll-cue-label">
            <span className="scroll-cue-text">SCROLL TO EXPLORE</span>
          </div>

          {/* Button-in-Button Trailing Badge with Cascading Chevrons */}
          <div className="scroll-cue-badge" aria-hidden="true">
            <svg className="scroll-cue-chevron chevron-top" viewBox="0 0 16 16" width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 6l5 5 5-5" />
            </svg>
            <svg className="scroll-cue-chevron chevron-bottom" viewBox="0 0 16 16" width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 6l5 5 5-5" />
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
};
