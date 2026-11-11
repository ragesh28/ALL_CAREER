import { getJobWalkinDates } from '../utils/filterUtils';
import { CatalogSummary, matchesCatalogLocation, matchesCatalogSource } from './catalogTypes';

export interface WalkinFacetInput {
  summary: CatalogSummary;
  locations: string[];
  sources: string[];
  dates: string[];
}

export interface WalkinFacets {
  dates: Record<string, number>;
  locations: Record<string, number>;
  sources: Record<string, number>;
}

export function calculateWalkinFacets(input: WalkinFacetInput): WalkinFacets {
  const { summary } = input;
  const dates: Record<string, number> = {};
  const locations: Record<string, number> = {};
  const sources: Record<string, number> = {};
  const selectedDates = new Set(input.dates);

  for (const group of summary.walkins.date_groups) {
    if (!Array.isArray(group)) continue;
    const [city, source, rawDates, reference, count] = group;
    if (typeof city !== 'string' || typeof source !== 'string' || !Number.isFinite(count)) continue;

    const matchesLocation = matchesCatalogLocation(city, input.locations);
    const matchesSource = matchesCatalogSource(source, input.sources);
    if (!matchesLocation && !matchesSource) continue;

    const labels = getJobWalkinDates({ is_walkin: true, walkin_dates: rawDates, date: reference });
    const matchesDate = !selectedDates.size || labels.some(label => selectedDates.has(label));
    if (matchesLocation && matchesDate) sources[source] = (sources[source] || 0) + count;
    if (matchesSource && matchesDate) locations[city] = (locations[city] || 0) + count;
    if (matchesLocation && matchesSource) {
      for (const label of labels) dates[label] = (dates[label] || 0) + count;
    }
  }
  return { dates, locations, sources };
}
