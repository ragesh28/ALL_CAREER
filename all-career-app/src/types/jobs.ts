export interface Job {
  id?: number | string;
  _id?: number;
  title?: string;
  role?: string;
  company?: string;
  location?: string;
  experience?: string;
  date?: string;
  fetchedAt?: string;
  source?: string;
  url?: string;
  contact_email?: string;
  contact_phone?: string;
  telegram_url?: string;
  flyer_image_url?: string;
  raw_flyer_src?: string;
  walkin_date?: string;
  walkin_dates?: string[];
  role_search?: string;
  category?: string;
  job_type?: string;
  description?: string;
  skills?: string[];
  venue?: string;
  other_details?: string;
  is_walkin?: boolean;

  // Pre-indexed fast search & filter properties (0ms instantaneous lookup)
  _searchHay?: string;
  _minExp?: number | null;
  _maxExp?: number | null;
  _normSource?: string;
  _normCategory?: string;
  _dateDaysAgo?: number | null;
  _isWalkinJob?: boolean;
  _walkinDatesList?: string[];
}

export interface RoleCategory {
  name: string;
  count: number;
}

export interface SidebarCounts {
  portals?: Record<string, number>;
  sources?: Record<string, number>;
  locations?: Record<string, number>;
  roles?: Record<string, number>;
  total_jobs?: number;
}

export interface ManifestData {
  total_jobs?: number;
  roles?: Record<string, {
    name?: string;
    sources?: Record<string, {
      locs?: Record<string, number>;
    }>;
  }>;
}

export interface FilterState {
  searchTerm: string;
  selectedPortals: Set<string>;
  selectedLocations: Set<string>;
  selectedRoles: Set<string>;
  selectedCategories: Set<string>;
  selectedWalkinDates: Set<string>;
  experienceFilter: string;
}
