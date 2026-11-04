# Static web catalog

Scrapers continue to own `data/jobs/` and `data/index/walkin_jobs.json`.
`Publish Fast Web Catalog` runs after scraper completions, hourly, or manually.
It publishes a separate browser projection in `data/web/` using Python's standard library.
No database service or paid backend is required. The temporary SQLite file only sorts
the source records inside the GitHub Actions runner.

## Browser loading

- Startup requests `data/web/latest.json` (50 newest records) and
  `data/web/summary.json` independently. Counts never wait for job records.
- The summary includes total, source, location, source/location intersections, and
  compact walk-in date groups. A Web Worker expands date groups for the rolling
  interview-date window.
- A content-addressed compressed manifest identifies browser pages. Each page
  contains at most 250 records and normally at most 240 KB before compression;
  an unusually large single record can exceed the byte limit. Pages stop at
  posting-date boundaries, keeping historical pages stable as new jobs arrive.
- The browser uses native gzip decompression for `.json.gz` pages. All Jobs shows
  50 records at a time and downloads another batch on request.
- Walk-in pages are additionally grouped by city. Selecting Chennai walk-ins
  requests relevant city pages, rather than the entire walk-in index.
- General source/location facets are computed from the full summary. Text,
  experience, skill, role and company filters currently filter loaded records;
  the UI offers more batches and identifies those counts as loaded matches.
  Exhaustive text search still requires loading the remaining candidate pages.
- The catalog fetcher tries the published site and one raw GitHub fallback, with
  an 8-second timeout per host. Failed pages remain retryable.
- Practice and Big Company route bundles load when opened. All Jobs does not
  download their bulk datasets at startup.

## Publishing and retention

Source files are never rewritten by the publisher. Records are deduplicated by
URL, title, company and normalized city, then ordered by posting date descending.
The summary and referenced pages are committed together. Content hashes prevent
mixing old cached pages with a new manifest. Pages that are no longer referenced
are retained for three days for open browser sessions. An unchanged source
fingerprint keeps the previous snapshot and avoids an unnecessary Pages rebuild.

The legacy `all_jobs.html` remains a separate implementation. The optimized client
is the React app served by root `index.html` and `#all_jobs`.

## Verification

Run from repository root:

```powershell
python -m unittest tests.test_web_catalog
```

Run from `all-career-app`:

```powershell
node tests/catalog-service.test.cjs
npm run build
```

For the browser integration check, start Vite on port 5187 and run
`node tests/catalog-browser.cjs` from `all-career-app`. The fixture intentionally
stalls the preview request and asserts that all three count sections are visible.
