import React from 'react';
import { RotateCcw, X } from 'lucide-react';
import { AllJobsFilters } from './allJobsFilters';
import { categoryLabels, postedDateOptions, skillOptions, sourceOptions } from './jobFilterOptions';

type RemoveFilter = (current: AllJobsFilters) => Partial<AllJobsFilters>;
type SetFilter = 'selectedSources' | 'selectedLocations' | 'selectedRoles' | 'selectedSkills' | 'selectedCompanies' | 'selectedWalkinDates';

interface FilterChip {
  id: string;
  label: string;
  remove: RemoveFilter;
}

function findLabel(options: { id: string; label: string }[], id: string): string {
  return options.find(option => option.id === id)?.label ?? id;
}

export function activeJobFilters(filters: AllJobsFilters): FilterChip[] {
  const active: FilterChip[] = [];
  function addSet(field: SetFilter, label: (value: string) => string = value => value) {
    for (const value of filters[field]) {
      active.push({
        id: field + '/' + value,
        label: label(value),
        remove: current => {
          const remaining = new Set(current[field]);
          remaining.delete(value);
          return { [field]: remaining };
        },
      });
    }
  }

  addSet('selectedSources', source => findLabel(sourceOptions, source));
  addSet('selectedLocations');
  addSet('selectedRoles');
  if (filters.expValue >= 0) {
    const years = filters.expValue === 10 ? '10+ years' : filters.expValue === 1 ? '1 year' : filters.expValue + ' years';
    active.push({
      id: 'experience',
      label: filters.exactExp && filters.expValue < 10 ? 'Exactly ' + years : years,
      remove: () => ({ expValue: -1, exactExp: false }),
    });
  }
  if (filters.selectedDateFilter !== 'all') {
    active.push({ id: 'posted', label: findLabel(postedDateOptions, filters.selectedDateFilter), remove: () => ({ selectedDateFilter: 'all' }) });
  }
  if (filters.selectedCategory !== 'all') {
    active.push({ id: 'category', label: categoryLabels[filters.selectedCategory], remove: () => ({ selectedCategory: 'all' }) });
  }
  addSet('selectedSkills', skill => findLabel(skillOptions, skill));
  addSet('selectedCompanies');
  if (filters.walkinOnly) {
    active.push({ id: 'walkin', label: 'All Walk-ins', remove: () => ({ walkinOnly: false }) });
  }
  addSet('selectedWalkinDates', date => 'Interview ' + date);
  if (filters.searchTerm.trim()) {
    active.push({ id: 'search', label: 'Search “' + filters.searchTerm.trim() + '”', remove: () => ({ searchTerm: '' }) });
  }
  if (filters.sortBy !== 'latest') {
    active.push({ id: 'sort', label: filters.sortBy === 'company' ? 'By company' : 'Oldest first', remove: () => ({ sortBy: 'latest' }) });
  }
  return active;
}

export function ActiveJobFilters({ active, onRemove, onReset }: {
  active: FilterChip[];
  onRemove: (remove: RemoveFilter) => void;
  onReset: () => void;
}) {
  if (!active.length) return null;

  return (
    <div className="alljobs-active-filters">
      <button type="button" className="premium-reset-btn" onClick={onReset} title="Reset all active filters">
        <span className="reset-icon-halo">
          <RotateCcw size={13} className="reset-spin-icon" aria-hidden="true" />
        </span>
        <span className="reset-btn-label">Reset Filters</span>
        <span className="reset-count-badge">{active.length}</span>
      </button>
      <ul className="alljobs-active-filter-list" aria-label="Active filters">
        {active.map(({ id, label, remove }) => (
          <li key={id}>
            <button type="button" className="alljobs-filter-chip" aria-label={'Remove ' + label + ' filter'} title={label} onClick={() => onRemove(remove)}>
              <span>{label}</span>
              <X size={15} aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
