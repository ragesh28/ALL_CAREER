import React from 'react';

interface GlobalLogoPillProps {
  onGoHome: () => void;
}

export const GlobalLogoPill: React.FC<GlobalLogoPillProps> = ({ onGoHome }) => {
  return (
    <div 
      className="global-logo-pill" 
      onClick={onGoHome}
      title="All Career Hub"
    >
      <img src="/String_Theory.png" alt="Logo" />
      <span>ALL_CAREER</span>
    </div>
  );
};
