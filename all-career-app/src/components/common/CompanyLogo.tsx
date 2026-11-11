import React, { useState } from 'react';
import { getCompanyLogoData } from '../../utils/companyLogos';

interface CompanyLogoProps {
  name: string;
  size?: 'sm' | 'md' | 'lg' | number;
  className?: string;
  style?: React.CSSProperties;
}


export const CompanyLogo: React.FC<CompanyLogoProps> = props => (
  <LogoImage key={props.name} {...props} />
);

const LogoImage: React.FC<CompanyLogoProps> = ({
  name,
  size = 'sm',
  className = '',
  style = {}
}) => {
  const logo = getCompanyLogoData(name);
  const sources = [...new Set([logo.local, logo.google, logo.duckduckgo, logo.unavatar].filter(Boolean))];
  const [stage, setStage] = useState(0);
  const [loadedSource, setLoadedSource] = useState<string>();
  const source = sources[stage];
  const showImage = Boolean(source && loadedSource === source);

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
      {!showImage && (
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
      {source && (
        <img
          key={source}
          src={source}
          alt=""
          aria-hidden="true"
          loading="lazy"
          decoding="async"
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain', padding: dim > 24 ? '3px' : '1px', opacity: showImage ? 1 : 0 }}
          onLoad={event => {
            if (event.currentTarget.naturalWidth > 1) setLoadedSource(source);
            else setStage(stage + 1);
          }}
          onError={() => setStage(stage + 1)}
        />
      )}
    </div>
  );
};
