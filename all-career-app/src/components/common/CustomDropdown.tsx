import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Check, ChevronDown } from 'lucide-react';

export interface DropdownOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
}

export interface DropdownGroup {
  label: string;
  tone: string;
  options: DropdownOption[];
}

interface CustomDropdownProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  options: DropdownOption[];
  groups?: DropdownGroup[];
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
  groups,
  icon,
  prefix,
  ariaLabel,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [opensUp, setOpensUp] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  // Selected option
  const selectedOption = options.find(o => o.value === value) ??
    groups?.flatMap(group => group.options).find(o => o.value === value) ?? options[0];

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
    if (groups) {
      dropdownRef.current?.querySelector<HTMLButtonElement>('[aria-selected="true"]')?.focus();
    }

    const handlePointerDown = (e: MouseEvent | TouchEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
        if (groups && dropdownRef.current?.contains(document.activeElement)) triggerRef.current?.focus();
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
  }, [isOpen, groups]);

  const toggleOpen = useCallback(() => {
    if (groups && triggerRef.current) {
      const bounds = triggerRef.current.getBoundingClientRect();
      const below = window.innerHeight - bounds.bottom;
      const above = bounds.top;
      const openAbove = below < 300 && above > below;
      setOpensUp(openAbove);
      dropdownRef.current?.style.setProperty('--dropdown-space', `${Math.max(84, (openAbove ? above : below) - 24)}px`);
    }
    setIsOpen(prev => !prev);
  }, [groups]);

  const handleSelect = (val: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onChange(val);
    setIsOpen(false);
    if (groups) triggerRef.current?.focus();
  };

  const handleListKeys = (event: React.KeyboardEvent) => {
    if (!groups || !['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    const items = Array.from(dropdownRef.current?.querySelectorAll<HTMLButtonElement>('[role="option"]') ?? []);
    const current = items.indexOf(document.activeElement as HTMLButtonElement);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 :
      (current + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
    event.preventDefault();
    items[next]?.focus();
  };

  const renderOption = (opt: DropdownOption) => (
    <button key={opt.value} type="button" role="option" aria-selected={opt.value === value}
      className={`custom-dropdown-item ${opt.value === value ? 'is-selected' : ''}`}
      onClick={e => handleSelect(opt.value, e)}>
      <span className="custom-dropdown-item-content">
        {opt.icon && <span className="item-icon">{opt.icon}</span>}
        <span className="item-label">{opt.label}</span>
      </span>
      {opt.value === value && <span className="item-check" aria-hidden="true"><Check size={13} strokeWidth={2.5} /></span>}
    </button>
  );

  return (
    <div
      ref={dropdownRef}
      className={`custom-dropdown-container ${className} ${isOpen ? 'is-open' : ''} ${opensUp ? 'opens-up' : ''}`}
      id={id}
      onBlur={groups ? event => {
        if (!event.currentTarget.contains(event.relatedTarget)) setIsOpen(false);
      } : undefined}
    >
      {/* Trigger Pill Button */}
      <button
        ref={triggerRef}
        type="button"
        className="custom-dropdown-trigger"
        onClick={event => {
          event.preventDefault();
          event.stopPropagation();
          toggleOpen();
        }}
        onKeyDown={groups ? event => {
          if (!isOpen && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
            event.preventDefault();
            toggleOpen();
          }
        } : undefined}
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
          onKeyDown={handleListKeys}
        >
          <div className="custom-dropdown-menu-inner">
            {options.map(renderOption)}
            {groups?.map(group => (
              <div key={group.label} role="group" aria-label={group.label}
                className={`custom-dropdown-group tone-${group.tone}`}>
                <span className="custom-dropdown-group-label" aria-hidden="true">{group.label}</span>
                {group.options.map(renderOption)}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
