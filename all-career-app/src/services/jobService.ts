import { Job, ManifestData, SidebarCounts } from '../types/jobs';
import { isWalkinJob, parseExperience, classifyJobCategory, getJobWalkinDates, isOtherSource } from '../utils/filterUtils';
import { formatWalkinDate } from '../utils/companyLogos';
import { fetchJsonWithFallback, resolveAssetUrl } from '../utils/urlHelper';

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

  async initCatalog(onProgress?: (jobs: Job[]) => void): Promise<{ previewJobs: Job[]; sidebarCounts: SidebarCounts | null }> {
    try {
      const [manifest, counts, previewRows, roleCategories] = await Promise.all([
        fetchJsonWithFallback<ManifestData>('data/index/manifest.json', ['all-career-app/public/data/index/manifest.json']),
        fetchJsonWithFallback<SidebarCounts>('data/index/sidebar_counts.json', ['all-career-app/public/data/index/sidebar_counts.json']),
        fetchJsonWithFallback<Job[]>('data/index/latest_preview_100.json', [
          'all-career-app/public/data/index/latest_preview_100.json',
          'latest_jobs_100.json',
          'all-career-app/public/latest_jobs_100.json',
          './latest_jobs_100.json'
        ]),
        fetchJsonWithFallback<Record<string, string[]>>('data/index/role_categories.json', ['all-career-app/public/data/index/role_categories.json'])
      ]);

      if (manifest) this.manifestData = manifest;
      if (counts) this.sidebarCounts = counts;
      if (roleCategories && typeof roleCategories === 'object') this.roleCategoriesDict = roleCategories;

      if (Array.isArray(previewRows) && previewRows.length > 0) {
        this.ingestJobs(previewRows);
        if (onProgress) onProgress(this.getAllJobs());
      }

      // Load walk-ins immediately
      await this.fetchWalkinJobs();
      if (onProgress) onProgress(this.getAllJobs());

      // Stream full initial_jobs in background without blocking initial render
      fetchJsonWithFallback<Job[]>('data/initial_jobs.json', [
        'all-career-app/public/data/initial_jobs.json',
        './data/initial_jobs.json',
        '/ALL_CAREER/data/initial_jobs.json',
        'https://raw.githubusercontent.com/ragesh28/ALL_CAREER/main/data/initial_jobs.json'
      ])
        .then((fullRows) => {
          if (Array.isArray(fullRows) && fullRows.length > 0) {
            this.ingestJobs(fullRows);
            if (onProgress) onProgress(this.getAllJobs());
          }
        })
        .catch(err => console.warn('initial_jobs load note:', err));

      // Stream big_company_jobs in background for direct ATS opportunities (Greenhouse, Lever, Workday)
      fetchJsonWithFallback<Job[]>('data/big_company_jobs.json', [
        'all-career-app/public/data/big_company_jobs.json',
        './data/big_company_jobs.json',
        'workday_scraper/big_company_jobs.json',
        'https://raw.githubusercontent.com/ragesh28/ALL_CAREER/main/data/big_company_jobs.json'
      ])
        .then((bigCompanyRows) => {
          if (Array.isArray(bigCompanyRows) && bigCompanyRows.length > 0) {
            const mapped = bigCompanyRows.map(bj => ({
              ...bj,
              url: (bj as any).apply_url || bj.url || '#',
              source: bj.source || 'other'
            }));
            this.ingestJobs(mapped);
            if (onProgress) onProgress(this.getAllJobs());
          }
        })
        .catch(err => console.warn('big_company_jobs load note:', err));

      return { previewJobs: this.getAllJobs(), sidebarCounts: this.sidebarCounts };
    } catch (err) {
      console.warn('Error loading initial job preview:', err);
      return { previewJobs: this.getAllJobs(), sidebarCounts: this.sidebarCounts };
    }
  }

  async fetchWalkinJobs(): Promise<Job[]> {
    try {
      const walkins = await fetchJsonWithFallback<Job[]>('data/walkin_jobs.json', [
        'data/index/walkin_jobs.json',
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
      const locStr = typeof r.location === 'string' ? r.location : (r.location ? String(r.location) : 'India');

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

      const key = `${titleStr.trim().toLowerCase()}|${compStr.trim().toLowerCase()}|${locStr.trim().toLowerCase()}`;
      if (!this.allJobsMap.has(key)) {
        r.category = this.classifyRoleCategory(titleStr || r.role || '');

        // Precompute high-speed indexed properties for 0ms filtering & search
        const dateStr = (r.fetchedAt || r.date || '').slice(0, 10);
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
      const da = a.fetchedAt || a.date || '';
      const db = b.fetchedAt || b.date || '';
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
