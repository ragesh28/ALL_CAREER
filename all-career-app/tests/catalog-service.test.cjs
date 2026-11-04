const assert = require('node:assert/strict');
const { gzipSync } = require('node:zlib');
const esbuild = require('esbuild');

(async () => {
  const output = await esbuild.build({ entryPoints: ['src/services/jobService.ts'], bundle: true, platform: 'node', format: 'esm', write: false, define: { 'import.meta.env.BASE_URL': '"./"' } });
  const code = output.outputFiles[0].text;
  const requests = [];
  let releasePreview;
  const previewReady = new Promise(resolve => { releasePreview = resolve; });
  let failPage = true;
  const job = (title, date, url) => ({ title, date_posted: date, url, company: 'Company', location: 'Chennai', source: 'naukri' });
  const newest = job('Newest', '2026-11-04', 'https://example.com/new');
  const oldest = job('Oldest', '2025-01-01', 'https://example.com/old');
  const summary = { schema: 1, total_jobs: 10000, manifest: 'data/web/manifest.json', locations: { chennai: 9000 }, sources: { naukri: 10000 }, walkins: { total: 1000 } };
  const manifest = { pages: [{ path: 'data/web/page1.json.gz', locations: ['chennai'], sources: ['naukri'] }, { path: 'data/web/page2.json.gz', locations: ['chennai'], sources: ['naukri'] }], walkins: {} };
  manifest.sources = { apna: [1, 2, 3].map(n => ({ path: `data/web/rare${n}.json.gz`, newest: `2026-11-0${4 - n}`, sources: ['apna'], locations: ['chennai'] })) };
  manifest.walkins.chennai = manifest.sources.apna;
  global.fetch = async url => {
    requests.push(String(url));
    if (String(url).endsWith('latest.json')) { await previewReady; return Response.json([newest]); }
    if (String(url).endsWith('summary.json')) return Response.json(summary);
    if (String(url).endsWith('manifest.json')) return Response.json(manifest);
    const rare = String(url).match(/rare([123])\.json\.gz$/);
    if (rare) return new Response(gzipSync(JSON.stringify([{ ...job(`Rare ${rare[1]}`, `2026-11-0${4 - Number(rare[1])}`, `https://example.com/rare${rare[1]}`), source: 'apna', is_walkin: true }])));
    if (String(url).endsWith('page1.json.gz')) {
      if (failPage) return new Response('', { status: 503 });
      return new Response(gzipSync(JSON.stringify([newest, job('Middle', '2026-10-01', 'https://example.com/mid')])));
    }
    if (String(url).endsWith('page2.json.gz')) return new Response(gzipSync(JSON.stringify([oldest])));
    return new Response('', { status: 404 });
  };
  const { JobService } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
  const service = new JobService();
  let countReady = false, cardsReady = false;
  const startup = service.initCatalog(() => { cardsReady = true; }, counts => { assert.equal(counts.total_jobs, 10000); countReady = true; });
  await new Promise(resolve => setTimeout(resolve, 30));
  assert.equal(countReady, true, 'counts must not wait for preview');
  assert.equal(cardsReady, false);
  assert.equal(requests.length, 2, 'startup must request only preview and summary');
  releasePreview(); await startup;
  const filters = { sources: [], locations: [], walkin: false };
  assert.equal((await service.loadMore(filters)).error, true, 'failed page should be retryable');
  failPage = false;
  const first = await service.loadMore(filters);
  assert.equal(first.jobs.length, 2, 'preview job must not duplicate');
  assert.equal(first.hasMore, true);
  const second = await service.loadMore(filters);
  assert.deepEqual(second.jobs.map(j => j.title), ['Newest', 'Middle', 'Oldest']);
  assert.equal(second.hasMore, false);
  let progressCalls = 0;
  const rare = await service.loadUntil({ sources: ['apna'], locations: [], walkin: false }, j => j._normSource === 'apna', 50, () => { progressCalls++; });
  assert.equal(rare.jobs.filter(j => j._normSource === 'apna').length, 3, 'all three rare-source jobs must load automatically');
  assert.equal(rare.hasMore, false, 'no Load more should be needed for fewer than 50 matches');
  assert.equal(progressCalls, 3);
  const walkins = await service.loadUntil({ sources: ['apna'], locations: ['Chennai'], walkin: true }, j => j._isWalkinJob && j._normSource === 'apna', 50);
  assert.equal(walkins.jobs.filter(j => j._isWalkinJob && j._normSource === 'apna').length, 3);
  assert.equal(walkins.hasMore, false);
  summary.total_jobs = 10001;
  summary.manifest = 'data/web/manifest-v2.json';
  await service.initCatalog(undefined, counts => assert.equal(counts.total_jobs, 10001));
  assert.equal(service.getAllJobs().length, 1, 'a new catalog snapshot must not retain old filtered records');
  assert.equal(requests.filter(url => url.endsWith('summary.json')).length, 2, 'mutable summaries should revalidate on a later visit');
  assert.ok(requests.every(path => !/initial_jobs|big_company_jobs|walkin_jobs/.test(path)), 'no bulk startup files');
  console.log('Independent startup, gzip, retries, newest-first order and automatic loading of all small-source/walk-in results passed');
})().catch(error => { console.error(error); process.exit(1); });
