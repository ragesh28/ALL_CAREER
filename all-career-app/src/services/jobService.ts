import { BrowserCatalog, CatalogSummary, CatalogFilters, CatalogPage, catalogCity } from './catalogTypes';
import { Job, ManifestData, SidebarCounts } from '../types/jobs';
import { isWalkinJob, parseExperience, classifyJobCategory, getJobWalkinDates, isOtherSource } from '../utils/filterUtils';
import { formatWalkinDate } from '../utils/companyLogos';
import { fetchCatalogJson, fetchJsonWithFallback, resolveAssetUrl } from '../utils/urlHelper';

export class JobService {
  private manifestData: ManifestData | null = null;
  private sidebarCounts: SidebarCounts | null = null;
  private allJobsMap = new Map<string, Job>();
  private loadedShards = new Set<string>();
  private roleCategoriesDict: Record<string, string[]> = {
    technical: ['developer', 'engineer', 'frontend', 'backend', 'fullstack', 'react', 'python', 'java', 'devops', 'software', 'cloud', 'data'],
    non_technical: ['bpo', 'voice', 'customer', 'sales', 'telecaller', 'recruiter', 'hr', 'support', 'operations'],
    pharma: ['pharma', 'clinical', 'chemist', 'drug', 'healthcare', 'medical', 'hospital', 'lab'],
    others: []
  };

  private summary: CatalogSummary | null = null;
  private browserCatalog: BrowserCatalog | null = null;
  private batchLoading = false;

  async initCatalog(
    onProgress?: (jobs: Job[]) => void,
    onCounts?: (counts: SidebarCounts | null, summary: CatalogSummary | null) => void
  ): Promise<{ previewJobs: Job[]; sidebarCounts: SidebarCounts | null }> {
    // These tasks publish independently: a slow preview cannot hide counts, and
    // counts never wait for walk-in records, manifests, categories or ATS dumps.
    const previewTask = (async () => {
      const rows = await fetchCatalogJson<Job[]>('data/web/latest.json')
        ?? await fetchCatalogJson<Job[]>('data/index/latest_preview_100.json');
      if (Array.isArray(rows)) this.ingestJobs(rows);
      onProgress?.(this.getAllJobs());
    })();
    const countsTask = (async () => {
      const summary = await fetchCatalogJson<CatalogSummary>('data/web/summary.json');
      if (summary?.schema === 1 && summary.walkins) {
        this.summary = summary;
        this.sidebarCounts = summary;
      } else {
        this.sidebarCounts = await fetchCatalogJson<SidebarCounts>('data/index/sidebar_counts.json');
      }
      onCounts?.(this.sidebarCounts, this.summary);
    })();
    await Promise.allSettled([previewTask, countsTask]);
    return { previewJobs: this.getAllJobs(), sidebarCounts: this.sidebarCounts };
  }

  private async catalog(): Promise<BrowserCatalog | null> {
    if (!this.browserCatalog && this.summary?.manifest) {
      this.browserCatalog = await fetchCatalogJson<BrowserCatalog>(this.summary.manifest);
    }
    return this.browserCatalog;
  }

  async loadMore(filters: CatalogFilters): Promise<{ jobs: Job[]; hasMore: boolean; error: boolean }> {
    this.batchLoading = true;
    try {
      const catalog = await this.catalog();
      if (!catalog) return { jobs: this.getAllJobs(), hasMore: false, error: true };
      const cities = filters.locations.map(catalogCity);
      let pages: CatalogPage[] = filters.walkin
        ? Object.entries(catalog.walkins).filter(([city]) => !cities.length || cities.includes(city)).flatMap(([, rows]) => rows)
        : catalog.pages;
      pages = pages.filter(page => (!cities.length || page.locations.some(city => cities.includes(city))) &&
        (!filters.sources.length || page.sources.some(source => filters.sources.some(s => s === source || (s === 'telegram' && source.includes('telegram')) || (s === 'other' && isOtherSource(source))))));
      if (filters.walkin) pages = pages.slice().sort((a, b) => b.newest.localeCompare(a.newest));
      const pending = pages.filter(page => !this.loadedShards.has(page.path));
      const page = pending[0];
      if (!page) return { jobs: this.getAllJobs(), hasMore: false, error: false };
      const rows = await fetchCatalogJson<Job[]>(page.path);
      if (!Array.isArray(rows)) return { jobs: this.getAllJobs(), hasMore: true, error: true };
      this.ingestJobs(rows);
      // Failed pages remain retryable.
      this.loadedShards.add(page.path);
      return { jobs: this.getAllJobs(), hasMore: pending.length > 1, error: false };
    } finally { this.batchLoading = false; }
  }

  async fetchWalkinJobs(): Promise<Job[]> {
    try {
      const walkins = await fetchJsonWithFallback<Job[]>('data/index/walkin_jobs.json', [
        'data/walkin_jobs.json',
        'data/scraped_image_walkin_jobs.json',
        'all-career-app/public/data/walkin_jobs.json',
        'all-career-app/public/data/scraped_image_walkin_jobs.json'
      ]);
      if (Array.isArray(walkins) && walkins.length > 0) {
        this.ingestJobs(walkins);
      }
    } catch (e) {
      console.warn('Walk-ins load note:', e);
    }
    return this.getAllJobs();
  }

  ingestJobs(rows: Job[]): number {
    if (!Array.isArray(rows)) return 0;
    let added = 0;
    for (const r of rows) {
      if (!r) continue;
      const compStr = typeof r.company === 'string' ? r.company : (r.company ? String((r.company as any).name || r.company) : 'DIRECT RECRUITER');
      const titleStr = typeof r.title === 'string' ? r.title : (r.title ? String(r.title) : 'Position');
      const locStr = typeof r.location === 'string' ? r.location : (r.location ? String((r.location as any).city || (r.location as any).name || 'India') : 'India');

      r.company = compStr;
      r.title = titleStr;
      r.location = locStr;

      let srcStr = String(r.source || (r as any).platform || '').toLowerCase().trim();
      const uStr = String(r.url || (r as any).apply_url || (r as any).telegram_url || '').toLowerCase();
      if (srcStr.includes('google') || (r as any).flyer_image_url || (r as any).raw_flyer_src || uStr.includes('google.com')) {
        srcStr = 'google_images';
      } else if (srcStr.includes('telegram') || (r as any).telegram_url || uStr.includes('t.me/')) {
        srcStr = srcStr.includes('post') ? 'telegram_post' : 'telegram_message';
      }
      if (srcStr) r.source = srcStr;

      const identityUrl = String(r.url || (r as any).apply_url || (r as any).telegram_url || (r as any).flyer_image_url || '').trim();
      const detailsKey = `${titleStr.trim().toLowerCase()}|${compStr.trim().toLowerCase()}|${locStr.trim().toLowerCase()}`;
      const key = identityUrl && identityUrl !== '#' ? `url:${identityUrl.toLowerCase()}|${detailsKey}` : detailsKey;
      if (!this.allJobsMap.has(key)) {
        r.category = this.classifyRoleCategory(titleStr || r.role || '');

        // Precompute high-speed indexed properties for 0ms filtering & search
        r.date = String((r as any).date_posted || r.fetchedAt || (r as any).fetched_at || r.date || '');
        const dateStr = r.date.slice(0, 10);
        let daysAgo: number | null = null;
        if (dateStr) {
          const jd = new Date(dateStr);
          if (!isNaN(jd.getTime())) {
            const now = new Date();
            now.setHours(0, 0, 0, 0);
            daysAgo = Math.floor((now.getTime() - jd.getTime()) / 86400000);
          }
        }
        r._dateDaysAgo = daysAgo;

        const [minE, maxE] = parseExperience(r.experience);
        r._minExp = minE;
        r._maxExp = maxE;
        r._normSource = srcStr;
        r._isWalkinJob = isWalkinJob(r);
        r._normCategory = classifyJobCategory(r);

        const hay = [
          titleStr,
          compStr,
          locStr,
          r.role_search || '',
          r.walkin_date || '',
          r.description || '',
          (r as any).venue || ''
        ].filter(Boolean).join(' ').toLowerCase();
        r._searchHay = hay;

        if (r._isWalkinJob) {
          r._walkinDatesList = getJobWalkinDates(r);
        } else {
          r._walkinDatesList = [];
        }

        this.allJobsMap.set(key, r);
        added++;
      }
    }
    return added;
  }

  getAllJobs(): Job[] {
    const list = Array.from(this.allJobsMap.values());
    list.sort((a, b) => {
      const da = String((a as any).date_posted || a.fetchedAt || a.date || '');
      const db = String((b as any).date_posted || b.fetchedAt || b.date || '');
      if (da !== db) return db.localeCompare(da);
      return (Number(b._id || b.id || 0)) - (Number(a._id || a.id || 0));
    });
    return list;
  }

  classifyRoleCategory(title: string): string {
    const t = String(title || '').toLowerCase();
    for (const [cat, keywords] of Object.entries(this.roleCategoriesDict)) {
      if (cat === 'others') continue;
      if (keywords.some(k => t.includes(k))) return cat;
    }
    return 'others';
  }

  async loadShardsForFilters(
    activePortals: string[],
    activeLocations: string[],
    activeRoles: string[],
    searchTerm: string = ''
  ): Promise<Job[]> {
    if (!this.manifestData || !this.manifestData.roles) return this.getAllJobs();

    const targetRoles = activeRoles.length > 0 ? activeRoles : Object.keys(this.manifestData.roles);
    const pathsToFetch: string[] = [];

    for (const rSlug of targetRoles) {
      const roleObj = this.manifestData.roles[rSlug];
      if (!roleObj || !roleObj.sources) continue;

      let targetSources: string[] = [];
      if (activePortals.length > 0) {
        const includeOther = activePortals.includes('other');
        targetSources = Object.keys(roleObj.sources).filter(s => {
          if (activePortals.includes(s)) return true;
          if (includeOther && isOtherSource(s)) return true;
          return false;
        });
      } else {
        targetSources = Object.keys(roleObj.sources);
      }

      for (const sSlug of targetSources) {
        const srcObj = roleObj.sources[sSlug];
        if (!srcObj || !srcObj.locs) continue;

        if (activeLocations.length > 0) {
          for (const lSlug of activeLocations) {
            if (srcObj.locs[lSlug]) {
              pathsToFetch.push(`/data/jobs/${rSlug}/${sSlug}_${lSlug}.json`);
            }
          }
        } else {
          const topLocs = Object.entries(srcObj.locs).sort((a, b) => b[1] - a[1]).slice(0, 4);
          for (const [lSlug] of topLocs) {
            pathsToFetch.push(`/data/jobs/${rSlug}/${sSlug}_${lSlug}.json`);
          }
        }
      }
    }

    const unfechedPaths = pathsToFetch.filter(p => !this.loadedShards.has(p)).slice(0, 25);
    await Promise.allSettled(
      unfechedPaths.map(async path => {
        try {
          this.loadedShards.add(path);
          const safeUrl = resolveAssetUrl(path);
          const res = await fetch(safeUrl);
          if (res.ok) {
            const jobs: Job[] = await res.json();
            this.ingestJobs(jobs);
          }
        } catch {}
      })
    );

    return this.getAllJobs();
  }
}

export const jobService = new JobService();
