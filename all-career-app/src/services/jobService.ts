import { Job, ManifestData, SidebarCounts } from '../types/jobs';

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
      const [mRes, scRes, prevRes, rcRes] = await Promise.allSettled([
        fetch('/data/index/manifest.json'),
        fetch('/data/index/sidebar_counts.json'),
        fetch('/data/index/latest_preview_100.json'),
        fetch('/data/index/role_categories.json')
      ]);

      if (mRes.status === 'fulfilled' && mRes.value.ok) {
        try { this.manifestData = await mRes.value.json(); } catch {}
      }
      if (scRes.status === 'fulfilled' && scRes.value.ok) {
        try { this.sidebarCounts = await scRes.value.json(); } catch {}
      }
      if (rcRes.status === 'fulfilled' && rcRes.value.ok) {
        try {
          const dict = await rcRes.value.json();
          if (dict && typeof dict === 'object') this.roleCategoriesDict = dict;
        } catch {}
      }

      if (prevRes.status === 'fulfilled' && prevRes.value.ok) {
        try {
          const rows: Job[] = await prevRes.value.json();
          this.ingestJobs(rows);
          if (onProgress) onProgress(this.getAllJobs());
        } catch {}
      }

      // Load walk-ins immediately
      await this.fetchWalkinJobs();
      if (onProgress) onProgress(this.getAllJobs());

      // Stream full initial_jobs in background without blocking initial render
      fetch('/data/initial_jobs.json')
        .then(res => res.ok ? res.json() : [])
        .then((fullRows: Job[]) => {
          if (Array.isArray(fullRows) && fullRows.length > 0) {
            this.ingestJobs(fullRows);
            if (onProgress) onProgress(this.getAllJobs());
          }
        })
        .catch(err => console.warn('initial_jobs load note:', err));

      return { previewJobs: this.getAllJobs(), sidebarCounts: this.sidebarCounts };
    } catch (err) {
      console.warn('Error loading initial job preview:', err);
      return { previewJobs: this.getAllJobs(), sidebarCounts: this.sidebarCounts };
    }
  }

  async fetchWalkinJobs(): Promise<Job[]> {
    try {
      let res = await fetch('/data/walkin_jobs.json?t=' + Date.now()).catch(() => null);
      if (!res || !res.ok) {
        res = await fetch('/data/index/walkin_jobs.json?t=' + Date.now()).catch(() => null);
      }
      if (!res || !res.ok) {
        res = await fetch('/data/scraped_image_walkin_jobs.json?t=' + Date.now()).catch(() => null);
      }
      if (res && res.ok) {
        const walkins: Job[] = await res.json();
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

      const targetSources = activePortals.length > 0
        ? activePortals.filter(s => roleObj.sources[s])
        : Object.keys(roleObj.sources);

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
          const res = await fetch(path);
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
