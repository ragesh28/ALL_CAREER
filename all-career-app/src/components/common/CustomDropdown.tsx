import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Check, ChevronDown } from 'lucide-react';

export interface DropdownOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
}

interface CustomDropdownProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  options: DropdownOption[];
  icon?: React.ReactNode;
  prefix?: string;
  ariaLabel: string;
  className?: string;
}

export const CustomDropdown: React.FC<CustomDropdownProps> = ({
  id,
  value,
  onChange,
  options,
  icon,
  prefix,
  ariaLabel,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Selected option
  const selectedOption = options.find(o => o.value === value) || options[0];

  // Compute trigger label
  let displayLabel = selectedOption?.label || '';
  if (prefix) {
    if (selectedOption.value === 'all') {
      displayLabel = `${prefix}: All`;
    } else if (selectedOption.value === 'default') {
      displayLabel = `${prefix}: Default`;
    } else {
      const cleanLabel = selectedOption.label
        .replace(new RegExp(`^(${prefix}|All)\\s*:?\\s*`, 'i'), '')
        .replace(/^Salary:\s*/i, '');
      displayLabel = `${prefix}: ${cleanLabel}`;
    }
  }

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (e: MouseEvent | TouchEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('touchstart', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('touchstart', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const toggleOpen = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsOpen(prev => !prev);
  }, []);

  const handleSelect = (val: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onChange(val);
    setIsOpen(false);
  };

  return (
    <div
      ref={dropdownRef}
      className={`custom-dropdown-container ${className} ${isOpen ? 'is-open' : ''}`}
      id={id}
    >
      {/* Trigger Pill Button */}
      <button
        type="button"
        className="custom-dropdown-trigger"
        onClick={toggleOpen}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={ariaLabel}
      >
        {icon && <span className="custom-dropdown-icon">{icon}</span>}
        <span className="custom-dropdown-label">{displayLabel}</span>
        <ChevronDown
          size={14}
          className={`custom-dropdown-chevron ${isOpen ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {/* Styled Curved Dropdown Popover */}
      {isOpen && (
        <div
          className="custom-dropdown-menu"
          role="listbox"
          aria-label={ariaLabel}
        >
          <div className="custom-dropdown-menu-inner">
            {options.map(opt => {
              const isSelected = opt.value === value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  className={`custom-dropdown-item ${isSelected ? 'is-selected' : ''}`}
                  onClick={e => handleSelect(opt.value, e)}
                >
                  <div className="custom-dropdown-item-content">
                    {opt.icon && <span className="item-icon">{opt.icon}</span>}
                    <span className="item-label">{opt.label}</span>
                  </div>
                  {isSelected && (
                    <span className="item-check" aria-hidden="true">
                      <Check size={13} strokeWidth={2.5} />
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
