import React, { useState, useEffect } from 'react';
import { getCompanyLogoData } from '../../utils/companyLogos';

interface CompanyLogoProps {
  name: string;
  size?: 'sm' | 'md' | 'lg' | number;
  className?: string;
  style?: React.CSSProperties;
}

const logoStageCache = new Map<string, number>();

export const CompanyLogo: React.FC<CompanyLogoProps> = ({
  name,
  size = 'sm',
  className = '',
  style = {}
}) => {
  const logo = getCompanyLogoData(name);
  // Stage 0: Unavatar -> Stage 1: DuckDuckGo -> Stage 2: Google -> Stage 3: Clearbit -> Stage 4: Monogram
  const [stage, setStage] = useState<number>(() => logoStageCache.get(name) ?? 0);

  // Sync stage if name prop changes
  useEffect(() => {
    setStage(logoStageCache.get(name) ?? 0);
  }, [name]);

  const handleStageError = (nextStage: number) => {
    logoStageCache.set(name, nextStage);
    setStage(nextStage);
  };

  // Compute pixel dimensions
  let dim = 20;
  if (typeof size === 'number') dim = size;
  else if (size === 'md') dim = 36;
  else if (size === 'lg') dim = 48;

  const letterGradients = [
    'linear-gradient(135deg, #0d9488, #14b8a6)',
    'linear-gradient(135deg, #0284c7, #38bdf8)',
    'linear-gradient(135deg, #3b82f6, #6366f1)',
    'linear-gradient(135deg, #8b5cf6, #d946ef)',
    'linear-gradient(135deg, #f59e0b, #ef4444)',
    'linear-gradient(135deg, #10b981, #06b6d4)'
  ];
  const charCode = (name.charCodeAt(0) || 67) % letterGradients.length;
  const gradient = letterGradients[charCode];

  return (
    <div
      className={`company-logo-container ${className}`}
      style={{
        position: 'relative',
        width: `${dim}px`,
        height: `${dim}px`,
        borderRadius: dim > 24 ? '8px' : '4px',
        background: '#ffffff',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
        verticalAlign: 'middle',
        ...style
      }}
    >
      {logo.local ? (
        <img
          src={logo.local}
          alt={name}
          loading="lazy"
          decoding="async"
          style={{ width: '100%', height: '100%', objectFit: 'contain', padding: dim > 24 ? '3px' : '1px' }}
          onError={() => handleStageError(4)}
        />
      ) : stage === 0 ? (
        <img
          src={logo.unavatar}
          alt={name}
          loading="lazy"
          decoding="async"
          style={{ width: '100%', height: '100%', objectFit: 'contain', padding: dim > 24 ? '3px' : '1px' }}
          onError={() => handleStageError(1)}
        />
      ) : stage === 1 ? (
        <img
          src={logo.duckduckgo}
          alt={name}
          loading="lazy"
          decoding="async"
          style={{ width: '100%', height: '100%', objectFit: 'contain', padding: dim > 24 ? '2px' : '1px' }}
          onError={() => handleStageError(2)}
        />
      ) : stage === 2 ? (
        <img
          src={logo.google}
          alt={name}
          loading="lazy"
          decoding="async"
          style={{ width: '100%', height: '100%', objectFit: 'contain', padding: dim > 24 ? '2px' : '1px' }}
          onError={() => handleStageError(3)}
        />
      ) : stage === 3 ? (
        <img
          src={logo.clearbit}
          alt={name}
          loading="lazy"
          decoding="async"
          style={{ width: '100%', height: '100%', objectFit: 'contain', padding: dim > 24 ? '3px' : '1px' }}
          onError={() => handleStageError(4)}
        />
      ) : (
        <div
          style={{
            width: '100%',
            height: '100%',
            background: gradient,
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            fontSize: `${Math.max(10, Math.floor(dim * 0.45))}px`,
            fontFamily: 'Outfit, sans-serif'
          }}
        >
          {logo.initial}
        </div>
      )}
    </div>
  );
};
