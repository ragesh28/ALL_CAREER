import { freshDataUrl } from './urlHelper';

export function checkPublishedRelease(moduleUrl: string) {
  const current = new URL(moduleUrl);
  const assets = new URL('./', current);
  const index = new URL('../index.html', current);
  let checking = false;
  let lastCheck = 0;

  const check = async () => {
    if (checking || !navigator.onLine) return;
    checking = true;
    lastCheck = Date.now();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch(freshDataUrl(index.href), {
        cache: 'no-store',
        credentials: 'omit',
        signal: controller.signal,
      });
      if (!response.ok) return;
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      const entry = page.querySelector('script[type="module"][src]')?.getAttribute('src');
      if (!entry) return;

      const latest = new URL(entry, index);
      if (latest.origin !== current.origin || !latest.pathname.startsWith(assets.pathname) ||
          !latest.pathname.endsWith('.js') || latest.pathname === current.pathname) return;

      const next = new URL(window.location.href);
      const release = latest.pathname.slice(assets.pathname.length);
      // A published release is attempted once per navigation, even if a CDN
      // temporarily serves the older document to the next request.
      if (next.searchParams.get('_release') === release) return;
      next.searchParams.set('_release', release);
      next.searchParams.delete('_fresh');
      const destination = new URL(freshDataUrl(next.origin + next.pathname + next.search));
      destination.hash = next.hash;
      window.location.replace(destination.href);
    } catch {
      // Keep the open page usable during a connection problem.
    } finally {
      clearTimeout(timeout);
      checking = false;
    }
  };

  void check();
  window.addEventListener('online', check);
  window.addEventListener('pageshow', event => {
    if (event.persisted) void check();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && Date.now() - lastCheck >= 60000) void check();
  });
}
