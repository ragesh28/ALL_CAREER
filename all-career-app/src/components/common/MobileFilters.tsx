import React, { useId, useState } from 'react';
import { SlidersHorizontal, X } from 'lucide-react';
export function MobileFilters({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return <div className={`responsive-filters ${open ? 'filters-open' : ''}`}>
    <button type="button" className="mobile-filter-toggle" aria-expanded={open} aria-controls={id} aria-label={open ? 'Close filters' : 'Open filters'} onClick={() => setOpen(!open)}>{open ? <X size={18}/> : <><SlidersHorizontal size={18}/><span>Filter</span></>}</button>
    {open && <button className="mobile-filter-backdrop" aria-label="Close filters" onClick={() => setOpen(false)} />}
    <div id={id} className="responsive-filter-content">{children}</div>
  </div>;
}
