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

let refreshSequence = 0;

export function freshDataUrl(url: string): string {
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}_fresh=${Date.now()}-${++refreshSequence}`;
}

const catalogRequests = new Map<string, Promise<unknown>>();
const failedCatalogPaths = new Set<string>();

// Mutable pointers always come from the network. Retry failed immutable paths
// with a fresh URL too, since a host can cache a 404 during publication.
export function fetchCatalogJson<T>(path: string, accept: (value: unknown) => value is T): Promise<T | null> {
  const clean = path.replace(/^\/+/, '');
  const pending = catalogRequests.get(clean);
  if (pending) return pending as Promise<T | null>;

  const mutable = /(?:summary|latest|sidebar_counts|latest_preview_100)\.json$/.test(clean);
  const fresh = mutable || failedCatalogPaths.has(clean);
  const task = (async () => {
    const urls = [resolveAssetUrl(clean), `https://raw.githubusercontent.com/ragesh28/ALL_CAREER/main/${clean}`];
    for (const url of urls) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), clean.endsWith('/summary.json') ? 20000 : 10000);
      try {
        const response = await fetch(fresh ? freshDataUrl(url) : url, {
          signal: controller.signal,
          cache: fresh ? 'no-store' : 'default',
          credentials: 'omit',
        });
        if (!response.ok) continue;
        let data: unknown;
        if (clean.endsWith('.gz')) {
          const buffer = await response.arrayBuffer();
          const bytes = new Uint8Array(buffer);
          // Some hosts unwrap gzip through Content-Encoding.
          data = bytes[0] === 31 && bytes[1] === 139
            ? await new Response(new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'))).json()
            : JSON.parse(new TextDecoder().decode(buffer));
        } else {
          data = await response.json();
        }
        if (!accept(data)) continue;
        failedCatalogPaths.delete(clean);
        return data;
      } catch {
        // A timeout, invalid file, or network error can use the other host.
      } finally {
        clearTimeout(timeout);
      }
    }
    failedCatalogPaths.add(clean);
    return null;
  })().finally(() => catalogRequests.delete(clean));
  catalogRequests.set(clean, task);
  return task;
}

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
