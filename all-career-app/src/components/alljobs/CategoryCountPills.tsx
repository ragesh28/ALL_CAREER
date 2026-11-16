import React from 'react';
import { categoryLabels } from './jobFilterOptions';

interface CategoryCountPillsProps {
  pageCounts: {
    sales: number;
    softwareTechnical: number;
    nonTechnical: number;
    banking: number;
    hr: number;
    pharma: number;
    others: number;
  };
  totalOnPage: number;
  selectedCategory: string;
  onSelectCategory: (cat: string) => void;
}

export const CategoryCountPills: React.FC<CategoryCountPillsProps> = ({
  pageCounts,
  totalOnPage,
  selectedCategory,
  onSelectCategory
}) => {
  return (
    <div className="sort-category-bar">
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
          {categoryLabels.all}
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'sales'}
          onClick={() => onSelectCategory('sales')} 
          className="pill-tag pill-sales"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          {categoryLabels.sales} <strong>{pageCounts.sales}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'software_technical'}
          onClick={() => onSelectCategory('software_technical')}
          className="pill-tag pill-tech"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          {categoryLabels.software_technical} <strong>{pageCounts.softwareTechnical}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'non_technical'}
          onClick={() => onSelectCategory('non_technical')} 
          className="pill-tag pill-nontech"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          {categoryLabels.non_technical} <strong>{pageCounts.nonTechnical}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'banking'}
          onClick={() => onSelectCategory('banking')} 
          className="pill-tag pill-finance"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          {categoryLabels.banking} <strong>{pageCounts.banking}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'hr'}
          onClick={() => onSelectCategory('hr')} 
          className="pill-tag pill-hr"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          {categoryLabels.hr} <strong>{pageCounts.hr}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'pharma'}
          onClick={() => onSelectCategory('pharma')} 
          className="pill-tag pill-pharma"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          {categoryLabels.pharma} <strong>{pageCounts.pharma}</strong>
        </button>

        <button 
          type="button"
          aria-pressed={selectedCategory === 'others'}
          onClick={() => onSelectCategory('others')} 
          className="pill-tag pill-others"
          style={{ cursor: 'pointer' }}
        >
          <span className="category-mark" aria-hidden="true" />
          {categoryLabels.others} <strong>{pageCounts.others}</strong>
        </button>
      </div>
    </div>
  );
};
