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

  async initCatalog(): Promise<{ previewJobs: Job[]; sidebarCounts: SidebarCounts | null }> {
    try {
      const [mRes, scRes, prevRes, rcRes] = await Promise.allSettled([
        fetch('/data/index/manifest.json'),
        fetch('/data/index/sidebar_counts.json'),
        fetch('/data/index/latest_preview_100.json'),
        fetch('/data/index/role_categories.json')
      ]);

      if (mRes.status === 'fulfilled' && mRes.value.ok) {
        this.manifestData = await mRes.value.json();
      }
      if (scRes.status === 'fulfilled' && scRes.value.ok) {
        this.sidebarCounts = await scRes.value.json();
      }
      if (rcRes.status === 'fulfilled' && rcRes.value.ok) {
        try {
          const dict = await rcRes.value.json();
          if (dict && typeof dict === 'object') this.roleCategoriesDict = dict;
        } catch {}
      }

      let previewList: Job[] = [];
      if (prevRes.status === 'fulfilled' && prevRes.value.ok) {
        const rows: Job[] = await prevRes.value.json();
        this.ingestJobs(rows);
        previewList = rows;
      }

      // Also fetch walkins in parallel
      this.fetchWalkinJobs();

      return { previewJobs: this.getAllJobs(), sidebarCounts: this.sidebarCounts };
    } catch (err) {
      console.warn('Error loading initial job preview:', err);
      return { previewJobs: [], sidebarCounts: null };
    }
  }

  async fetchWalkinJobs(): Promise<Job[]> {
    try {
      const res = await fetch('/data/index/walkin_jobs.json?t=' + Date.now()).catch(() =>
        fetch('/scraped_image_walkin_jobs.json?t=' + Date.now())
      );
      if (res.ok) {
        const walkins: Job[] = await res.json();
        this.ingestJobs(walkins);
      }
    } catch (e) {
      console.warn('Walk-ins load note:', e);
    }
    return this.getAllJobs();
  }

  ingestJobs(rows: Job[]): number {
    let added = 0;
    for (const r of rows) {
      const key = `${(r.title || '').trim().toLowerCase()}|${(r.company || '').trim().toLowerCase()}|${(r.location || '').trim().toLowerCase()}`;
      if (!this.allJobsMap.has(key)) {
        r.category = this.classifyRoleCategory(r.title || r.role || '');
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
    const t = title.toLowerCase();
    for (const [cat, keywords] of Object.entries(this.roleCategoriesDict)) {
      if (cat === 'others') continue;
      for (const kw of keywords) {
        if (t.includes(kw.toLowerCase())) return cat;
      }
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
