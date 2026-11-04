/**
 * Safe URL & Fetch Resolver for All Career
 * Ensures JSON data and assets load reliably across:
 * - Local Vite Dev Server (localhost:5173)
 * - Local Static Preview (file:// or static server)
 * - GitHub Pages (https://ragesh28.github.io/ALL_CAREER/)
 */

export const resolveAssetUrl = (path: string): string => {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:')) {
    return path;
  }

  const clean = path.replace(/^\/+/, '');
  const base = (((import.meta as any).env?.BASE_URL as string) || './').replace(/\/+$/, '');

  if (!base || base === '.' || base === './') {
    return `./${clean}`;
  }

  return `${base}/${clean}`;
};

// Catalog requests have one published location and one bounded fallback.
const catalogRequests = new Map<string, Promise<any>>();
export const fetchCatalogJson = <T,>(path: string): Promise<T | null> => {
  if (catalogRequests.has(path)) return catalogRequests.get(path)!;
  const task = (async () => {
    const clean = path.replace(/^\/+/, '');
    for (const url of [resolveAssetUrl(clean), `https://raw.githubusercontent.com/ragesh28/ALL_CAREER/main/${clean}`]) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);
      try {
        const res = await fetch(url, { signal: controller.signal });
        if (res.ok) {
          if (clean.endsWith('.gz')) {
            const buffer = await res.arrayBuffer();
            const bytes = new Uint8Array(buffer);
            // Some static hosts send Content-Encoding and the browser unwraps it.
            if (bytes[0] !== 31 || bytes[1] !== 139) return JSON.parse(new TextDecoder().decode(buffer)) as T;
            return await new Response(new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'))).json() as T;
          }
          return await res.json() as T;
        }
      } catch { /* A timeout or a failed host may use the fallback. */ }
      finally { clearTimeout(timeout); }
    }
    catalogRequests.delete(path);
    return null;
  })();
  catalogRequests.set(path, task);
  return task;
};

export const fetchJsonWithFallback = async <T = any>(
  primaryPath: string,
  fallbackPaths: string[] = []
): Promise<T | null> => {
  const allPaths = [primaryPath, ...fallbackPaths];

  for (const p of allPaths) {
    if (p.startsWith('http://') || p.startsWith('https://')) {
      try {
        const res = await fetch(p);
        if (res.ok) {
          const data = await res.json();
          if (data) return data as T;
        }
      } catch {}
      continue;
    }

    const clean = p.replace(/^\/+/, '');
    const candidates = [
      resolveAssetUrl(clean),
      `./${clean}`,
      `/ALL_CAREER/${clean}`,
      `/${clean}`,
      `all-career-app/public/${clean}`,
      `./all-career-app/public/${clean}`,
      `https://raw.githubusercontent.com/ragesh28/ALL_CAREER/main/all-career-app/public/${clean}`,
      `https://raw.githubusercontent.com/ragesh28/ALL_CAREER/main/${clean}`
    ];

    // Remove duplicates
    const uniqueCandidates = Array.from(new Set(candidates));

    for (const url of uniqueCandidates) {
      try {
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          if (data) return data as T;
        }
      } catch {
        // Continue to next candidate
      }
    }
  }

  return null;
};
