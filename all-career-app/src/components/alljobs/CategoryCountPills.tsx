import React from 'react';
import { RotateCcw } from 'lucide-react';

interface CategoryCountPillsProps {
  pageCounts: {
    sales: number;
    technical: number;
    nonTechnical: number;
    banking: number;
    hr: number;
    pharma: number;
    others: number;
  };
  totalOnPage: number;
  selectedCategory: string;
  onSelectCategory: (cat: string) => void;
  hasActiveFilters?: boolean;
  activeFilterCount?: number;
  onClearAll?: () => void;
}

export const CategoryCountPills: React.FC<CategoryCountPillsProps> = ({
  pageCounts,
  totalOnPage,
  selectedCategory,
  onSelectCategory,
  hasActiveFilters,
  activeFilterCount = 0,
  onClearAll
}) => {
  return (
    <div className="sort-category-bar">
      {/* Premium Redesigned Reset Button (sleek obsidian glass with micro-counter) */}
      {hasActiveFilters && onClearAll ? (
        <button
          type="button"
          className="premium-reset-btn"
          onClick={onClearAll}
          title="Reset all active filters"
        >
          <span className="reset-icon-halo">
            <RotateCcw size={13} className="reset-spin-icon" aria-hidden="true" />
          </span>
          <span className="reset-btn-label">Reset Filters</span>
          {activeFilterCount > 0 && (
            <span className="reset-count-badge">{activeFilterCount}</span>
          )}
        </button>
      ) : (
        <div style={{ minWidth: 0 }} />
      )}

      {/* This Page (50) and Category Pills */}
      <div className="page-category-pills">
        <span style={{ color: '#7c8db5', fontWeight: 600 }}>This Page ({totalOnPage}):</span>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'all'}
          onClick={() => onSelectCategory('all')} 
          className={`pill-tag ${selectedCategory === 'all' ? 'pill-others' : ''}`}
          style={{ cursor: 'pointer' }}
        >
          All
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'sales'}
          onClick={() => onSelectCategory('sales')} 
          className="pill-tag pill-sales"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          Sales & Marketing <strong>{pageCounts.sales}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'technical'}
          onClick={() => onSelectCategory('technical')} 
          className="pill-tag pill-tech"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          Technical <strong>{pageCounts.technical}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'non_technical'}
          onClick={() => onSelectCategory('non_technical')} 
          className="pill-tag pill-nontech"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          Non-Technical <strong>{pageCounts.nonTechnical}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'banking'}
          onClick={() => onSelectCategory('banking')} 
          className="pill-tag pill-finance"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          Banking & Finance <strong>{pageCounts.banking}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'hr'}
          onClick={() => onSelectCategory('hr')} 
          className="pill-tag pill-hr"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          HR & Staffing <strong>{pageCounts.hr}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'pharma'}
          onClick={() => onSelectCategory('pharma')} 
          className="pill-tag pill-pharma"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          Pharma <strong>{pageCounts.pharma}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'others'}
          onClick={() => onSelectCategory('others')} 
          className="pill-tag pill-others"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          Others <strong>{pageCounts.others}</strong>
        </button>
      </div>
    </div>
  );
};
