import { SidebarCounts } from '../types/jobs';

export interface CatalogSummary extends SidebarCounts {
  schema: number;
  generated_at: string;
  manifest: string;
  source_locations: Record<string, Record<string, number>>;
  walkins: {
    total: number;
    locations: Record<string, number>;
    sources: Record<string, number>;
    source_locations: Record<string, Record<string, number>>;
    date_groups: [string, string, string[], string, number][];
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

export const catalogCity = (value: string) => {
  const city = value.toLowerCase().trim();
  return city === 'bengaluru' ? 'bangalore' : city === 'new delhi' ? 'delhi' : city;
};
