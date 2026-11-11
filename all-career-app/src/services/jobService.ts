import { BrowserCatalog, CatalogSummary, CatalogFilters, CatalogPage, isBrowserCatalog, isCatalogSummary, isJobPage, matchesCatalogLocation, matchesCatalogSource } from './catalogTypes';
import { Job, ManifestData, SidebarCounts } from '../types/jobs';
import { isWalkinJob, parseExperience, classifyJobCategory, getJobWalkinDates, isOtherSource } from '../utils/filterUtils';
import { fetchCatalogJson, fetchJsonWithFallback, resolveAssetUrl } from '../utils/urlHelper';

export class JobService {
  private manifestData: ManifestData | null = null;
  private sidebarCounts: SidebarCounts | null = null;
  private allJobsMap = new Map<string, Job>();
  private loadedShards = new Set<string>();
  private failedShards = new Set<string>();
  private roleCategoriesDict: Record<string, string[]> = {
    technical: ['developer', 'engineer', 'frontend', 'backend', 'fullstack', 'react', 'python', 'java', 'devops', 'software', 'cloud', 'data'],
    non_technical: ['bpo', 'voice', 'customer', 'sales', 'telecaller', 'recruiter', 'hr', 'support', 'operations'],
    pharma: ['pharma', 'clinical', 'chemist', 'drug', 'healthcare', 'medical', 'hospital', 'lab'],
    others: []
  };

  private summary: CatalogSummary | null = null;
  private summaryRequest: Promise<CatalogSummary | null> | null = null;
  private browserCatalog: BrowserCatalog | null = null;

  refreshSummary(): Promise<CatalogSummary | null> {
    if (this.summaryRequest) return this.summaryRequest;
    this.summaryRequest = (async () => {
      const next = await fetchCatalogJson('data/web/summary.json', isCatalogSummary);
      if (!next) return null;

      const previous = this.summary;
      if (previous && Date.parse(next.generated_at) < Date.parse(previous.generated_at)) {
        // GitHub Pages and the fallback host can publish at different times.
        return previous;
      }
      if (previous && previous.manifest !== next.manifest) {
        this.allJobsMap.clear();
        this.loadedShards.clear();
        this.failedShards.clear();
        this.browserCatalog = null;
      }
      if (previous && previous.manifest === next.manifest &&
          previous.generated_at === next.generated_at && previous.total_jobs === next.total_jobs) return previous;
      this.summary = next;
      this.sidebarCounts = next;
      return next;
    })().finally(() => { this.summaryRequest = null; });
    return this.summaryRequest;
  }

  async loadPreview(): Promise<Job[]> {
    const rows = await fetchCatalogJson('data/web/latest.json', isJobPage);
    if (rows) this.ingestJobs(rows);
    return rows ?? [];
  }

  async initCatalog(
    onProgress?: (jobs: Job[]) => void,
    onCounts?: (counts: SidebarCounts | null, summary: CatalogSummary | null) => void
  ): Promise<{ previewJobs: Job[]; sidebarCounts: SidebarCounts | null }> {
    // Keep the first cards and catalog counts independent on startup.
    let previewRows: Job[] | null = null;
    const preview = this.loadPreview().then(rows => {
      previewRows = rows;
      onProgress?.(this.getAllJobs());
    });
    const counts = this.refreshSummary().then(summary => {
      if (summary && previewRows) this.ingestJobs(previewRows);
      onCounts?.(this.sidebarCounts, summary);
    });
    await Promise.all([preview, counts]);
    return { previewJobs: this.getAllJobs(), sidebarCounts: this.sidebarCounts };
  }

  private async candidatePages(filters: CatalogFilters, snapshot: CatalogSummary | null): Promise<CatalogPage[] | null> {
    if (!snapshot) return null;
    const needsWalkins = filters.walkin && snapshot.walkins.total > 0;
    const hasWalkins = (catalog: BrowserCatalog) => Object.values(catalog.walkins).some(rows => rows.length > 0);
    const catalog = this.browserCatalog && (!needsWalkins || hasWalkins(this.browserCatalog))
      ? this.browserCatalog
      : await fetchCatalogJson(snapshot.manifest, (value): value is BrowserCatalog =>
        isBrowserCatalog(value) && (!needsWalkins || hasWalkins(value)));
    if (!catalog || snapshot.manifest !== this.summary?.manifest) return null;
    this.browserCatalog = catalog;

    const matchesCity = (location: string) => matchesCatalogLocation(location, filters.locations);
    const matchesSource = (source: string) => matchesCatalogSource(source, filters.sources);
    const walkinPages = Object.entries(catalog.walkins);
    let pages: CatalogPage[] = filters.walkin
      ? walkinPages.filter(([city]) => matchesCity(city)).flatMap(([, rows]) => rows)
      : catalog.pages;
    if (!filters.walkin && filters.sources.length && filters.sources.every(source => !!catalog.sources?.[source])) {
      pages = filters.sources.flatMap(source => catalog.sources![source]);
    }
    const minimumDate = filters.postedDays === undefined ? '' : new Date(Date.now() - (filters.postedDays + 1) * 86400000).toISOString().slice(0, 10);
    pages = pages.filter(page => (!minimumDate || (page.newest || '') >= minimumDate) &&
      (!filters.locations.length || page.locations.some(matchesCity)) &&
      (!filters.sources.length || page.sources.some(matchesSource)));
    const unique = [...new Map(pages.map(page => [page.path, page])).values()];
    return unique.sort((a, b) => (b.newest || '').localeCompare(a.newest || ''));
  }

  private async loadPage(page: CatalogPage, snapshot: CatalogSummary | null, signal?: AbortSignal): Promise<boolean> {
    const rows = await fetchCatalogJson(page.path, (value): value is Job[] =>
      isJobPage(value) && (!page.count || value.length > 0));
    if (signal?.aborted || snapshot?.manifest !== this.summary?.manifest) return false;
    if (!rows) {
      this.failedShards.add(page.path);
      return false;
    }
    this.ingestJobs(rows);
    this.failedShards.delete(page.path);
    this.loadedShards.add(page.path);
    return true;
  }

  async loadMore(filters: CatalogFilters): Promise<{ jobs: Job[]; hasMore: boolean; error: boolean }> {
    const snapshot = this.summary;
    const pages = await this.candidatePages(filters, snapshot);
    if (!pages) return { jobs: this.getAllJobs(), hasMore: true, error: true };
    const pending = pages.filter(page => !this.loadedShards.has(page.path));
    if (!pending.length) return { jobs: this.getAllJobs(), hasMore: false, error: false };
    const loaded = await this.loadPage(pending[0], snapshot);
    return { jobs: this.getAllJobs(), hasMore: !loaded || pending.length > 1, error: !loaded };
  }

  async loadUntil(
    filters: CatalogFilters,
    matches: (job: Job) => boolean,
    target = 50,
    onProgress?: (jobs: Job[]) => void,
    signal?: AbortSignal
  ): Promise<{ jobs: Job[]; hasMore: boolean; error: boolean }> {
    const snapshot = this.summary;
    const pages = await this.candidatePages(filters, snapshot);
    let jobs = this.getAllJobs();
    if (!pages) return { jobs, hasMore: true, error: true };

    let failures = 0;
    let count = jobs.filter(matches).length;
    for (const page of pages) {
      if (signal?.aborted) break;
      if (count >= target && !this.failedShards.has(page.path)) continue;
      if (snapshot?.manifest !== this.summary?.manifest) {
        return { jobs: this.getAllJobs(), hasMore: true, error: true };
      }
      if (this.loadedShards.has(page.path)) continue;
      if (!await this.loadPage(page, snapshot, signal)) {
        if (signal?.aborted) break;
        if (snapshot?.manifest !== this.summary?.manifest) {
          return { jobs: this.getAllJobs(), hasMore: true, error: true };
        }
        failures++;
        // One missing walk-in file should not hide the healthy files behind it.
        if (!filters.walkin || failures >= 2) break;
        continue;
      }
      jobs = this.getAllJobs();
      count = jobs.filter(matches).length;
      onProgress?.(jobs);
    }
    return { jobs, hasMore: pages.some(page => !this.loadedShards.has(page.path)), error: failures > 0 };
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

      let srcStr = String(r.source || (r as any).platform || '').toLowerCase().trim().replace(/\s+/g, '_');
      const aliases: Record<string, string> = { apna_jobs: 'apna', work_india: 'workindia', freshers_world: 'freshersworld' };
      srcStr = aliases[srcStr] || srcStr;
      const uStr = String(r.url || (r as any).apply_url || (r as any).telegram_url || '').toLowerCase();
      if (!srcStr || srcStr === 'other') {
        if ((r as any).telegram_url || uStr.includes('t.me/')) srcStr = 'telegram_message';
        else if ((r as any).flyer_image_url || (r as any).raw_flyer_src) srcStr = 'google_images';
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
