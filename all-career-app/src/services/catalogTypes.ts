import { Job, SidebarCounts } from '../types/jobs';
import { JOBS_PER_PAGE } from '../data/preparedJobFilters';
import { catalogCity, isOtherSource } from '../utils/filterUtils';

export { catalogCity };

export interface CatalogSummary extends SidebarCounts {
  schema: number;
  generated_at: string;
  manifest: string;
  filtered_catalog?: string;
  source_locations: Record<string, Record<string, number>>;
  walkins: {
    total: number;
    locations: Record<string, number>;
    sources: Record<string, number>;
    source_locations: Record<string, Record<string, number>>;
    date_groups: [string, string, string[] | string, string, number][];
  };
}

export interface CatalogPage {
  path: string;
  count: number;
  newest: string;
  sources: string[];
  locations: string[];
}

export interface BrowserCatalog {
  schema: number;
  pages: CatalogPage[];
  walkins: Record<string, CatalogPage[]>;
  sources?: Record<string, CatalogPage[]>;
}

export interface CatalogFilters {
  sources: string[];
  locations: string[];
  walkin: boolean;
  postedDays?: number;
}

export interface CatalogBatch {
  jobs: Job[];
  hasMore: boolean;
  error: boolean;
  total?: number;
  searchIncomplete?: boolean;
}

export interface PreparedJobCatalog {
  schema: 1;
  page_size: number;
  zero_year_roles?: boolean;
  queries: Record<string, { count: number; pages: string[] }>;
}

export function matchesCatalogLocation(location: string, selections: Iterable<string>): boolean {
  const actual = catalogCity(location);
  let hasSelection = false;
  for (const city of selections) {
    hasSelection = true;
    if (actual.includes(catalogCity(city))) return true;
  }
  return !hasSelection;
}

export function matchesCatalogSource(source: string, selections: Iterable<string>): boolean {
  let hasSelection = false;
  for (const selected of selections) {
    hasSelection = true;
    if (source === selected || (selected === 'telegram' && source.includes('telegram')) ||
      (selected === 'other' && isOtherSource(source)) ||
      ((selected === 'images' || selected === 'google_images') && /google|image/.test(source))) return true;
  }
  return !hasSelection;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isCatalogPath(path: unknown): path is string {
  return typeof path === 'string' && /^data\/web\/(?:pages\/)?[a-zA-Z0-9_.-]+\.json(?:\.gz)?$/.test(path);
}

function isCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

function isCountMap(value: unknown): boolean {
  return isRecord(value) && Object.values(value).every(isCount);
}

function isCountMatrix(value: unknown): boolean {
  return isRecord(value) && Object.values(value).every(isCountMap);
}

export function isCatalogSummary(value: unknown): value is CatalogSummary {
  if (!isRecord(value) || value.schema !== 1 || !isCatalogPath(value.manifest)) return false;
  if (value.filtered_catalog !== undefined && !isCatalogPath(value.filtered_catalog)) return false;
  const walkins = value.walkins;
  return isCount(value.total_jobs) &&
    isCountMap(value.sources) && isCountMap(value.locations) && isCountMatrix(value.source_locations) &&
    isRecord(walkins) && isCount(walkins.total) && walkins.total <= value.total_jobs &&
    isCountMap(walkins.locations) && isCountMap(walkins.sources) && isCountMatrix(walkins.source_locations) &&
    Array.isArray(walkins.date_groups) && (walkins.total === 0 || walkins.date_groups.length > 0) &&
    walkins.date_groups.every(group => Array.isArray(group) && group.length === 5 &&
      typeof group[0] === 'string' && typeof group[1] === 'string' &&
      (Array.isArray(group[2]) || typeof group[2] === 'string') &&
      typeof group[3] === 'string' && isCount(group[4]));
}

function isPageList(value: unknown): value is CatalogPage[] {
  return Array.isArray(value) && value.every(page =>
    isRecord(page) && isCatalogPath(page.path) &&
    Array.isArray(page.locations) && page.locations.every(location => typeof location === 'string') &&
    Array.isArray(page.sources) && page.sources.every(source => typeof source === 'string'));
}

export function isBrowserCatalog(value: unknown): value is BrowserCatalog {
  return isRecord(value) && (value.schema === undefined || value.schema === 1) &&
    isPageList(value.pages) && isRecord(value.walkins) && Object.values(value.walkins).every(isPageList) &&
    (value.sources === undefined || (isRecord(value.sources) && Object.values(value.sources).every(isPageList)));
}

export function isJobPage(value: unknown): value is Job[] {
  return Array.isArray(value) && value.every(row =>
    isRecord(row) && (typeof row.title === 'string' || typeof row.role === 'string'));
}

export function isPreparedJobCatalog(value: unknown): value is PreparedJobCatalog {
  return isRecord(value) && value.schema === 1 && value.page_size === JOBS_PER_PAGE &&
    (value.zero_year_roles === undefined || typeof value.zero_year_roles === 'boolean') &&
    isRecord(value.queries) && Object.values(value.queries).every(query =>
      isRecord(query) && isCount(query.count) && Array.isArray(query.pages) &&
      query.pages.length === Math.ceil(query.count / JOBS_PER_PAGE) &&
      query.pages.every(isCatalogPath));
}
