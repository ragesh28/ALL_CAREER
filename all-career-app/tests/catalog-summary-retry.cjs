const assert = require('node:assert/strict');
const puppeteer = require('puppeteer');

(async () => {
  const origin = 'http://127.0.0.1:5187/';
  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });
    const errors = [];
    const summaryRequests = [];
    const shardRequests = [];
    let oldManifestRequests = 0;
    let summaryPhase = 'unavailable';
    let shardAvailable = false;

    const posted = new Date();
    const tomorrow = new Date(posted);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const interview = tomorrow.toISOString().slice(0, 10);
    const city = 'chennai, tamil nadu';
    const source = 'google_images_(hasdata)';
    const descriptor = (name, newest) => ({
      path: 'data/web/' + name + '.json', count: 1, newest, sources: [source], locations: [city],
    });
    const pages = [descriptor('flaky', '2026-11-05'), descriptor('healthy', '2026-11-04')];
    const summary = (version, generatedAt) => ({
      schema: 1, total_jobs: 100, manifest: 'data/web/manifest-' + version + '.json', generated_at: generatedAt,
      sources: { [source]: 2, naukri: 98 }, locations: { [city]: 100 },
      source_locations: { [source]: { [city]: 2 }, naukri: { [city]: 98 } },
      walkins: {
        total: 2, locations: { [city]: 2 }, sources: { [source]: 2 },
        source_locations: { [source]: { [city]: 2 } },
        date_groups: [[city, source, [interview], posted.toISOString().slice(0, 10), 2]],
      },
    });
    const walkin = (title, date) => ({
      title, company: 'Fixture company', location: 'Chennai, Tamil Nadu',
      source, url: 'https://example.com/' + title.replaceAll(' ', '-'), date_posted: date,
      is_walkin: true, walkin_dates: [interview],
    });

    page.on('pageerror', error => errors.push(error.message));
    await page.evaluateOnNewDocument(() => {
      const NativeWorker = window.Worker;
      window.Worker = class extends NativeWorker {
        constructor(url, options) {
          if (String(url).includes('walkinSummary.worker')) throw new Error('Worker blocked in fixture');
          super(url, options);
        }
      };
    });
    await page.setRequestInterception(true);
    page.on('request', request => {
      const url = new URL(request.url());
      const respond = (body, status = 200) => request.respond({
        status,
        contentType: 'application/json',
        headers: { 'access-control-allow-origin': '*' },
        body: JSON.stringify(body),
      });
      if (url.pathname.endsWith('/data/web/summary.json')) {
        summaryRequests.push(url);
        if (summaryPhase === 'unavailable') return respond({}, 503);
        if (summaryPhase === 'malformed') return respond({ schema: 1, walkins: { total: 0 } });
        if (summaryPhase === 'old') return respond(summary('old', '2026-11-11T01:00:00Z'));
        return respond(summary('current', '2026-11-11T02:00:00Z'));
      }
      if (url.pathname.endsWith('/data/web/latest.json')) return respond([{
        title: 'Ordinary preview job', company: 'Fixture company', source: 'naukri',
        location: 'Chennai', url: 'https://example.com/preview',
      }]);
      if (url.pathname.endsWith('/data/web/manifest-old.json')) {
        oldManifestRequests++;
        return respond({}, 404);
      }
      if (url.pathname.endsWith('/data/web/manifest-current.json')) return respond({
        schema: 1, pages, walkins: { [city]: pages },
      });
      if (url.pathname.endsWith('/data/web/flaky.json')) {
        shardRequests.push(url);
        return shardAvailable ? respond([walkin('Recovered walk-in', pages[0].newest)]) : respond([]);
      }
      if (url.pathname.endsWith('/data/web/healthy.json')) return respond([walkin('Available walk-in', pages[1].newest)]);
      if (url.hostname === 'cdn.tailwindcss.com') return request.respond({
        status: 200, contentType: 'application/javascript', body: 'window.tailwind = {};',
      });
      if (!url.href.startsWith(origin) && url.protocol !== 'data:') return request.abort();
      return request.continue();
    });

    const waitForRetry = () => page.waitForFunction(() => {
      const button = document.querySelector('.walkin-retry-btn');
      return button && !button.disabled && button.textContent === 'Retry walk-ins';
    });
    const assertUnverifiedState = async () => {
      assert.doesNotMatch(await page.$eval('#sec-walkin', node => node.textContent), /\(0\)|No upcoming walk-in interview dates found/);
      assert.doesNotMatch(await page.$eval('main [role="status"]', node => node.textContent), /0 matching jobs loaded/);
    };

    await page.goto(origin + '#all_jobs', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.job-card');
    await page.click('#walkinOpt');
    await waitForRetry();
    await assertUnverifiedState();
    assert.equal(summaryRequests.length, 2, 'both summary hosts must be attempted');

    summaryPhase = 'malformed';
    await Promise.all([
      page.waitForResponse(response =>
        response.url().startsWith('https://raw.githubusercontent.com/') &&
        response.url().includes('/data/web/summary.json') && response.status() === 200),
      page.click('.walkin-retry-btn'),
    ]);
    await waitForRetry();
    await assertUnverifiedState();
    assert.equal(summaryRequests.length, 4, 'manual retry must reject invalid HTTP 200 data from both hosts');

    summaryPhase = 'old';
    await page.waitForFunction(() => document.querySelector('#walkinOpt .source-count')?.textContent === '(2)');
    await page.waitForSelector('#walkin-dates-options .filter-option');
    await waitForRetry();
    assert.ok(oldManifestRequests >= 2, 'missing manifest must be retried on the other host');
    await assertUnverifiedState();

    summaryPhase = 'current';
    await page.waitForFunction(() => document.querySelector('.job-card')?.textContent.includes('Available walk-in'));
    await waitForRetry();
    assert.ok(shardRequests.length >= 2, 'both hosts must reject an empty page declared to contain jobs');
    assert.equal(await page.$eval('#walkinOpt .source-count', node => node.textContent), '(2)');
    shardAvailable = true;

    await page.waitForFunction(() => document.querySelectorAll('.job-card').length === 2);
    await page.waitForFunction(() => document.querySelector('.walkin-retry-btn')?.textContent === 'Refresh walk-ins');
    assert.match(await page.$eval('.job-card', node => node.textContent), /Recovered walk-in/);
    assert.ok(summaryRequests.every(url => url.searchParams.has('_fresh')), 'mutable summaries must bypass browser cache');
    assert.ok(shardRequests.some(url => url.searchParams.has('_fresh')), 'retried pages must bypass cached failures');

    await page.click('#src-google_images');
    await page.evaluate(() => [...document.querySelectorAll('#location-options .filter-option')]
      .find(option => option.querySelector('.option-label')?.textContent === 'Chennai').click());
    await page.waitForSelector('#walkin-dates-options .filter-option');
    await page.click('#walkin-dates-options .filter-option');
    await page.waitForFunction(() => document.querySelectorAll('.job-card').length === 2);
    assert.equal(await page.$eval('#walkinOpt .source-count', node => node.textContent), '(2)');
    assert.deepEqual(errors, []);
    console.log('Passed: manual and automatic retry, valid counts without a worker, stale manifest recovery, partial page recovery, and Chennai Images date filtering');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
