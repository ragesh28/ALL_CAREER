import { categoryLabels, postedDateOptions } from './jobFilterOptions';

export interface AllJobsFilters {
  searchTerm: string;
  selectedSources: Set<string>;
  selectedLocations: Set<string>;
  selectedDateFilter: string;
  selectedRoles: Set<string>;
  expValue: number;
  exactExp: boolean;
  selectedSkills: Set<string>;
  selectedCompanies: Set<string>;
  walkinOnly: boolean;
  selectedWalkinDates: Set<string>;
  selectedCategory: string;
  sortBy: string;
}

const route = '#all_jobs';
const postedDates = postedDateOptions.map(option => option.id);
const categories = Object.keys(categoryLabels);
const sortOptions = ['latest', 'oldest', 'company'];
const walkinDateLabel = /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (?:[1-9]|[12][0-9]|3[01])$/;

export function isAllJobsHash(hash: string): boolean {
  return hash.split('?', 1)[0] === route;
}

export function readAllJobsFilters(hash: string): AllJobsFilters {
  const params = new URLSearchParams(isAllJobsHash(hash) ? hash.slice(route.length) : '');
  const selection = (name: string) => new Set(params.getAll(name).map(value => value.trim()).filter(Boolean));
  const option = (name: string, options: string[]) => {
    const value = params.get(name) ?? '';
    return options.includes(value) ? value : options[0];
  };
  const experience = params.get('experience');
  const expValue = experience !== null && /^(?:[0-9]|10)$/.test(experience) ? Number(experience) : -1;

  return {
    searchTerm: params.get('q') ?? '',
    selectedSources: selection('source'),
    selectedLocations: selection('city'),
    selectedDateFilter: option('posted', postedDates),
    selectedRoles: selection('role'),
    expValue,
    exactExp: expValue >= 0 && params.get('exact') === '1',
    selectedSkills: selection('skill'),
    selectedCompanies: selection('company'),
    walkinOnly: params.get('walkin') === '1',
    selectedWalkinDates: new Set([...selection('interview')].filter(value => walkinDateLabel.test(value))),
    selectedCategory: option('category', categories),
    sortBy: option('sort', sortOptions),
  };
}

export function writeAllJobsHash(filters: AllJobsFilters): string {
  const params = new URLSearchParams();
  const append = (key: string, values: Set<string>) => {
    for (const value of values) params.append(key, value);
  };
  if (filters.searchTerm) params.set('q', filters.searchTerm);
  append('source', filters.selectedSources);
  append('city', filters.selectedLocations);
  if (filters.selectedDateFilter !== 'all') params.set('posted', filters.selectedDateFilter);
  append('role', filters.selectedRoles);
  if (filters.expValue >= 0) params.set('experience', String(filters.expValue));
  if (filters.expValue >= 0 && filters.exactExp) params.set('exact', '1');
  append('skill', filters.selectedSkills);
  append('company', filters.selectedCompanies);
  if (filters.walkinOnly) params.set('walkin', '1');
  append('interview', filters.selectedWalkinDates);
  if (filters.selectedCategory !== 'all') params.set('category', filters.selectedCategory);
  if (filters.sortBy !== 'latest') params.set('sort', filters.sortBy);
  const query = params.toString();
  return query ? route + '?' + query : route;
}
