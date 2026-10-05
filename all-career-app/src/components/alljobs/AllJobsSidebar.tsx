import React, { useState } from 'react';

interface AllJobsSidebarProps {
  selectedSources: Set<string>;
  onToggleSource: (source: string) => void;
  selectedDateFilter: string;
  onSelectDateFilter: (filter: string) => void;
  sourceCounts: Record<string, number>;
}

export const AllJobsSidebar: React.FC<AllJobsSidebarProps> = ({
  selectedSources,
  onToggleSource,
  selectedDateFilter,
  onSelectDateFilter,
  sourceCounts
}) => {
  const [sourcesOpen, setSourcesOpen] = useState(true);
  const [dateOpen, setDateOpen] = useState(true);

  // Exact sources list from Screenshot 3
  const sourcesList = [
    { id: 'linkedin', label: 'LinkedIn', icon: '💼', count: sourceCounts.linkedin ?? 221380 },
    { id: 'naukri', label: 'Naukri', icon: '🌐', count: sourceCounts.naukri ?? 322160 },
    { id: 'indeed', label: 'Indeed', icon: '🔍', count: sourceCounts.indeed ?? 78407 },
    { id: 'internshala', label: 'Internshala', icon: 'IS', count: sourceCounts.internshala ?? 83161 },
    { id: 'glassdoor', label: 'Glassdoor', icon: '🟢', count: sourceCounts.glassdoor ?? 4786 },
    { id: 'shine', label: 'Shine', icon: '⭐', count: sourceCounts.shine ?? 47436 },
    { id: 'timesjobs', label: 'TimesJobs', icon: '⏳', count: sourceCounts.timesjobs ?? 101057 },
    { id: 'hirist', label: 'Hirist', icon: 'h', count: sourceCounts.hirist ?? 10355 },
    { id: 'workindia', label: 'WorkIndia', icon: 'W', count: sourceCounts.workindia ?? 15876 },
    { id: 'foundit', label: 'Foundit', icon: '🎯', count: sourceCounts.foundit ?? 20644 },
    { id: 'apna', label: 'Apna', icon: 'A', count: sourceCounts.apna ?? 7409 },
    { id: 'freshersworld', label: 'FreshersWorld', icon: 'FW', count: sourceCounts.freshersworld ?? 4065 },
    { id: 'telegram', label: 'Messages', icon: '✉️', count: sourceCounts.telegram ?? 681 },
    { id: 'post', label: 'Post', icon: '📌', count: sourceCounts.post ?? 540 },
    { id: 'images', label: 'Images', icon: '🖼️', count: 0 },
    { id: 'others', label: 'Other Sources', icon: '⚙️', count: 0 }
  ];

  const dateOptions = [
    { id: 'all', label: 'All Time' },
    { id: 'today', label: 'Today' },
    { id: '3d', label: 'Last 3 Days' },
    { id: '7d', label: 'Last 7 Days' },
    { id: '30d', label: 'Last 30 Days' }
  ];

  return (
    <aside className="alljobs-sidebar">
      <div className="sidebar-title">All Filters</div>

      {/* Source Section */}
      <div>
        <div 
          className="filter-section-header"
          onClick={() => setSourcesOpen(!sourcesOpen)}
        >
          <span>Source</span>
          <span style={{ fontSize: '0.8rem', color: '#7c8db5' }}>{sourcesOpen ? '▲' : '▼'}</span>
        </div>

        {sourcesOpen && (
          <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '2px', maxHeight: '350px', overflowY: 'auto' }}>
            {sourcesList.map(item => {
              const isSelected = selectedSources.has(item.id);
              return (
                <div
                  key={item.id}
                  className={`filter-option ${isSelected ? 'selected' : ''}`}
                  onClick={() => onToggleSource(item.id)}
                >
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span className="custom-checkbox">
                      {isSelected && '✓'}
                    </span>
                    <span style={{ marginRight: '6px' }}>{item.icon}</span>
                    <span>{item.label}</span>
                  </div>
                  <span style={{ fontSize: '0.72rem', color: '#475775' }}>
                    ({item.count.toLocaleString()})
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Posted Date Section */}
      <div>
        <div 
          className="filter-section-header"
          onClick={() => setDateOpen(!dateOpen)}
        >
          <span>Posted Date</span>
          <span style={{ fontSize: '0.8rem', color: '#7c8db5' }}>{dateOpen ? '▲' : '▼'}</span>
        </div>

        {dateOpen && (
          <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {dateOptions.map(opt => {
              const isSelected = selectedDateFilter === opt.id;
              return (
                <div
                  key={opt.id}
                  className={`filter-option ${isSelected ? 'selected' : ''}`}
                  onClick={() => onSelectDateFilter(opt.id)}
                  style={{ justifyContent: 'flex-start', gap: '8px' }}
                >
                  <span style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    border: '1.5px solid ' + (isSelected ? '#34d399' : '#475775'),
                    background: isSelected ? '#34d399' : 'transparent',
                    display: 'inline-block'
                  }}></span>
                  <span>{opt.label}</span>
                </div>
              );
            })}

            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: '#38bdf8', padding: '6px 8px', borderRadius: '8px', background: 'rgba(56, 189, 248, 0.08)', marginTop: '6px' }}>
              <span>⚡</span>
              <span>Loading matching jobs...</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
