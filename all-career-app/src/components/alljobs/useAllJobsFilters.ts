import { useEffect, useRef, useState } from 'react';
import { AllJobsFilters, isAllJobsHash, readAllJobsFilters, writeAllJobsHash } from './allJobsFilters';

export function useAllJobsFilters() {
  const [filters, setFilters] = useState(() => readAllJobsFilters(window.location.hash));
  const snapshot = useRef({ hash: window.location.hash, filters });

  useEffect(() => {
    function syncFromUrl() {
      const hash = window.location.hash;
      if (hash === snapshot.current.hash || !isAllJobsHash(hash)) return;
      const next = readAllJobsFilters(hash);
      snapshot.current = { hash, filters: next };
      setFilters(next);
    }
    window.addEventListener('hashchange', syncFromUrl);
    syncFromUrl();
    return () => window.removeEventListener('hashchange', syncFromUrl);
  }, []);

  function updateFilters(update: (current: AllJobsFilters) => Partial<AllJobsFilters>) {
    const hash = window.location.hash;
    if (!isAllJobsHash(hash)) return;
    const current = snapshot.current.hash === hash ? snapshot.current.filters : readAllJobsFilters(hash);
    const next = { ...current, ...update(current) };
    const nextHash = writeAllJobsHash(next);
    if (nextHash !== hash) window.history.replaceState(window.history.state, '', nextHash);
    if (nextHash === snapshot.current.hash) return;
    snapshot.current = { hash: nextHash, filters: next };
    setFilters(next);
  }

  return [filters, updateFilters] as const;
}
