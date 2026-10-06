import React from 'react';

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
  sortBy: string;
  onSortChange: (sort: string) => void;
  selectedCategory: string;
  onSelectCategory: (cat: string) => void;
}

export const CategoryCountPills: React.FC<CategoryCountPillsProps> = ({
  pageCounts,
  totalOnPage,
  sortBy,
  onSortChange,
  selectedCategory,
  onSelectCategory
}) => {
  return (
    <div className="sort-category-bar">
      {/* Sort Select */}
      <div className="sort-select-box">
        <span>Sort by:</span>
        <select value={sortBy} onChange={e => onSortChange(e.target.value)}>
          <option value="latest">Latest First</option>
          <option value="oldest">Oldest First</option>
          <option value="company">Company Name</option>
        </select>
      </div>

      {/* This Page (100) and Category Pills */}
      <div className="page-category-pills">
        <span style={{ color: '#7c8db5', fontWeight: 600 }}>This Page ({totalOnPage}):</span>

        <button 
          onClick={() => onSelectCategory('all')} 
          className={`pill-tag ${selectedCategory === 'all' ? 'pill-others' : ''}`}
          style={{ cursor: 'pointer', background: selectedCategory === 'all' ? 'rgba(255,255,255,0.1)' : 'transparent', border: '1px solid rgba(255,255,255,0.1)' }}
        >
          All
        </button>

        <button 
          onClick={() => onSelectCategory('sales')} 
          className="pill-tag pill-sales"
          style={{ cursor: 'pointer', opacity: selectedCategory !== 'all' && selectedCategory !== 'sales' ? 0.5 : 1 }}
        >
          <span className="category-mark" aria-hidden="true" />
          Sales & Marketing <strong>{pageCounts.sales}</strong>
        </button>

        <button 
          onClick={() => onSelectCategory('technical')} 
          className="pill-tag pill-tech"
          style={{ cursor: 'pointer', opacity: selectedCategory !== 'all' && selectedCategory !== 'technical' ? 0.5 : 1 }}
        >
          <span className="category-mark" aria-hidden="true" />
          Technical <strong>{pageCounts.technical}</strong>
        </button>

        <button 
          onClick={() => onSelectCategory('non_technical')} 
          className="pill-tag pill-nontech"
          style={{ cursor: 'pointer', opacity: selectedCategory !== 'all' && selectedCategory !== 'non_technical' ? 0.5 : 1 }}
        >
          <span className="category-mark" aria-hidden="true" />
          Non-Technical <strong>{pageCounts.nonTechnical}</strong>
        </button>

        <button 
          onClick={() => onSelectCategory('banking')} 
          className="pill-tag pill-finance"
          style={{ cursor: 'pointer', opacity: selectedCategory !== 'all' && selectedCategory !== 'banking' ? 0.5 : 1 }}
        >
          <span className="category-mark" aria-hidden="true" />
          Banking & Finance <strong>{pageCounts.banking}</strong>
        </button>

        <button 
          onClick={() => onSelectCategory('hr')} 
          className="pill-tag pill-hr"
          style={{ cursor: 'pointer', opacity: selectedCategory !== 'all' && selectedCategory !== 'hr' ? 0.5 : 1 }}
        >
          <span className="category-mark" aria-hidden="true" />
          HR & Staffing <strong>{pageCounts.hr}</strong>
        </button>

        <button 
          onClick={() => onSelectCategory('pharma')} 
          className="pill-tag pill-pharma"
          style={{ cursor: 'pointer', opacity: selectedCategory !== 'all' && selectedCategory !== 'pharma' ? 0.5 : 1 }}
        >
          <span className="category-mark" aria-hidden="true" />
          Pharma <strong>{pageCounts.pharma}</strong>
        </button>

        <button 
          onClick={() => onSelectCategory('others')} 
          className="pill-tag pill-others"
          style={{ cursor: 'pointer', opacity: selectedCategory !== 'all' && selectedCategory !== 'others' ? 0.5 : 1 }}
        >
          <span className="category-mark" aria-hidden="true" />
          Others <strong>{pageCounts.others}</strong>
        </button>
      </div>
    </div>
  );
};
