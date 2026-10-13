import React from 'react';
import { STRING_THEORY_LOGO } from '../../utils/brandLogo';

interface AllCareerLogoProps {
  onGoHome?: () => void;
  position?: 'top-right' | 'inline';
  className?: string;
  subtitle?: string;
}

export const AllCareerLogo: React.FC<AllCareerLogoProps> = ({
  onGoHome,
  position = 'top-right',
  className = '',
  subtitle
}) => {
  const logoSrc = STRING_THEORY_LOGO;

  return (
    <div
      className={`all-career-brand-badge ${position === 'top-right' ? 'top-right-corner' : 'inline-badge'} ${className}`}
      onClick={onGoHome}
      role="button"
      tabIndex={0}
      title="ALL_CAREER Home"
      aria-label="ALL_CAREER Home"
    >
      <div className="brand-logo-icon-wrapper">
        <img
          src={logoSrc}
          alt="ALL_CAREER"
          className="brand-logo-img"
          onError={(e) => {
            // Fallback to text monogram if image is unavailable
            (e.target as HTMLElement).style.display = 'none';
          }}
        />
      </div>
      <div className="brand-logo-text-group">
        <span className="brand-logo-title">ALL_CAREER</span>
        {subtitle && <span className="brand-logo-subtitle">{subtitle}</span>}
      </div>
    </div>
  );
};
