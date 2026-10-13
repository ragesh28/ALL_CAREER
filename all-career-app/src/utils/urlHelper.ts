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

export const fetchJsonWithFallback = async <T = any>(
  primaryPath: string,
  fallbackPaths: string[] = []
): Promise<T | null> => {
  const allPaths = [primaryPath, ...fallbackPaths];

  for (const p of allPaths) {
    const candidates = [
      resolveAssetUrl(p),
      `./${p.replace(/^\/+/, '')}`,
      `/${p.replace(/^\/+/, '')}`
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
