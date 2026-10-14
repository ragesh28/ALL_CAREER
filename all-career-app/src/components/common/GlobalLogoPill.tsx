import React from 'react';
import { STRING_THEORY_LOGO } from '../../utils/brandLogo';

interface GlobalLogoPillProps {
  onGoHome: () => void;
}

export const GlobalLogoPill: React.FC<GlobalLogoPillProps> = ({ onGoHome }) => {
  const logoSrc = STRING_THEORY_LOGO;

  return (
    <div 
      className="global-logo-pill" 
      style={{ position: 'absolute', top: 18, left: 24, right: 'auto', zIndex: 1000 }}
      onClick={onGoHome}
      title="ALL_CAREER Home"
      role="button"
      tabIndex={0}
      aria-label="ALL_CAREER Home"
    >
      <img src={logoSrc} alt="ALL_CAREER Logo" />
      <span>ALL_CAREER</span>
    </div>
  );
};

