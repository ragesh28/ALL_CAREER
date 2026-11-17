import { isJobPage } from './catalogTypes';
import { JOBS_PER_PAGE } from '../data/preparedJobFilters';
import { type AllJobsFilters, writeAllJobsHash } from '../components/alljobs/allJobsFilters';
import { type Job } from '../types/jobs';

const FETCH_MS = 2500;

export const pilotSearchEndpoint: string | undefined =
  import.meta.env.DEV ? import.meta.env.VITE_PILOT_SEARCH_URL : undefined;

export function pilotSearchQuery(filters: AllJobsFilters, version: string | undefined): string {
  const groups = [
    filters.searchTerm.trim(), filters.selectedSources.size, filters.selectedLocations.size,
    filters.selectedDateFilter !== 'all', filters.selectedRoles.size, filters.expValue >= 0,
    filters.selectedSkills.size, filters.selectedCompanies.size,
    filters.walkinOnly || filters.selectedWalkinDates.size, filters.selectedCategory !== 'all',
  ];
  if (!version || !/^[0-9a-f]{64}$/.test(version) || groups.filter(Boolean).length < 2) return '';
  const params = new URLSearchParams(writeAllJobsHash(filters).split('?')[1]);
  params.set('version', version);
  if (filters.selectedDateFilter !== 'all') {
    const localMidnight = new Date();
    localMidnight.setHours(0, 0, 0, 0);
    params.set('as_of', localMidnight.toISOString().slice(0, 10));
  }
  return params.toString();
}

export interface PilotBatch {
  query: string;
  jobs: Job[];
  total: number;
  nextCursor: string | null;
}

export async function loadPilotJobs(
  endpoint: string,
  query: string,
  target: number,
  signal: AbortSignal,
  previous: PilotBatch | null
): Promise<PilotBatch> {
  const jobs = previous?.query === query ? previous.jobs.slice() : [];
  let nextCursor = previous?.query === query ? previous.nextCursor : null;
  let total = previous?.query === query ? previous.total : undefined;
  const params = new URLSearchParams(query);
  const version = params.get('version');
  const url = new URL('/jobs', endpoint);
  while (jobs.length < target && (total === undefined || nextCursor)) {
    if (nextCursor) params.set('cursor', nextCursor);
    const request = new AbortController();
    const abort = () => request.abort();
    signal.addEventListener('abort', abort, { once: true });
    const deadline = setTimeout(abort, FETCH_MS);
    try {
      signal.throwIfAborted();
      url.search = params.toString();
      const response = await fetch(url, { cache: 'no-store', credentials: 'omit', signal: request.signal });
      if (!response.ok) throw new Error('Pilot search unavailable');
      const data = await response.json();
      if (!data || data.catalog_version !== version || !Number.isSafeInteger(data.total) ||
          data.total < jobs.length || (total !== undefined && data.total !== total) ||
          !isJobPage(data.jobs) || data.jobs.length !== Math.min(JOBS_PER_PAGE, data.total - jobs.length)) {
        throw new Error('Pilot search returned incompatible results');
      }
      const hasMore = jobs.length + data.jobs.length < data.total;
      if (hasMore ? typeof data.next_cursor !== 'string' || !data.next_cursor || data.next_cursor === nextCursor
        : data.next_cursor !== null) {
        throw new Error('Pilot search returned an invalid page cursor');
      }
      jobs.push(...data.jobs);
      total = data.total;
      nextCursor = data.next_cursor;
    } finally {
      clearTimeout(deadline);
      signal.removeEventListener('abort', abort);
    }
  }
  return { query, jobs, total: total ?? 0, nextCursor };
}
