import { getJobWalkinDates, isOtherSource } from '../utils/filterUtils';
import { CatalogSummary, catalogCity } from './catalogTypes';

let summary: CatalogSummary | null = null;
self.onmessage = ({ data }) => {
  if (data.summary) summary = data.summary;
  if (!summary) return;
  const cities: string[] = data.locations.map(catalogCity);
  const selectedSources: string[] = data.sources;
  const selectedDates: string[] = data.dates;
  const dates: Record<string, number> = {};
  const locations: Record<string, number> = {};
  const sources: Record<string, number> = {};
  let total = 0;
  for (const [city, source, rawDates, reference, count] of summary.walkins.date_groups) {
    const matchesSource = !selectedSources.length || selectedSources.some(s => s === source || (s === 'telegram' && source.includes('telegram')) || (s === 'other' && isOtherSource(source)));
    const labels = getJobWalkinDates({ is_walkin: true, walkin_dates: rawDates, date: reference });
    if ((!cities.length || cities.includes(city)) && (!selectedDates.length || labels.some(label => selectedDates.includes(label)))) sources[source] = (sources[source] || 0) + count;
    if (!matchesSource) continue;
    if (!selectedDates.length || labels.some(label => selectedDates.includes(label))) locations[city] = (locations[city] || 0) + count;
    if (cities.length && !cities.includes(city)) continue;
    total += count;
    for (const label of labels) dates[label] = (dates[label] || 0) + count;
  }
  self.postMessage({ id: data.id, total, dates, locations, sources });
};
