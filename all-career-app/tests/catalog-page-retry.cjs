const puppeteer = require('puppeteer');
const assert = require('node:assert/strict');

(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage();
    const errors = [], fetched = []; let pageFailures = 0;
    page.on('pageerror', error => errors.push(error.message));
    const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
    const interview = tomorrow.toISOString().slice(0, 10);
    const descriptor = n => ({ path: `data/web/rare${n}.json`, count: 1, newest: `2026-11-0${4 - n}`, sources: ['apna'], locations: ['chennai'] });
    const pages = [1, 2, 3].map(descriptor);
    const summary = { schema: 1, total_jobs: 100, manifest: 'data/web/manifest.json', sources: { apna: 3, naukri: 97 }, locations: { chennai: 100 }, source_locations: { apna: { chennai: 3 }, naukri: { chennai: 97 } }, walkins: { total: 3, locations: { chennai: 3 }, sources: { apna: 3 }, source_locations: { apna: { chennai: 3 } }, date_groups: [['chennai', 'apna', [interview], '2026-11-04', 3]] } };
    await page.setRequestInterception(true);
    page.on('request', request => {
      const url = request.url().split('?')[0];
      if (url.includes('/data/web/')) {
        fetched.push(url);
        const rare = url.match(/rare([123])\.json$/);
        if (rare && rare[1] === '2' && pageFailures++ < 2) return request.respond({status: 503, body: 'temporary error'});
        const data = url.endsWith('summary.json') ? summary : url.endsWith('manifest.json') ? { pages: [], sources: { apna: pages }, walkins: { chennai: pages } } : rare ? [{ title: `Apna opening ${rare[1]}`, company: 'Fixture company', location: 'Chennai', source: 'apna', url: `https://example.com/${rare[1]}`, is_walkin: true, walkin_date: interview, date_posted: `2026-11-0${4 - Number(rare[1])}` }] : [];
        return request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(data) });
      }
      if (url.includes('cdn.tailwindcss.com')) return request.respond({ status: 200, contentType: 'application/javascript', body: 'window.tailwind={};' });
      if (!url.startsWith('http://127.0.0.1:5187/') && !url.startsWith('data:')) return request.abort();
      request.continue();
    });
    await page.goto('http://127.0.0.1:5187/#all_jobs', { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelector('.count-num')?.textContent === '100');
    await page.click('#src-apna');
    await page.waitForFunction(() => document.querySelector('main [role="status"]')?.textContent.includes('3 matching jobs loaded'));
    assert.ok(pageFailures >= 3, 'failed page should retry on both hosts and recover automatically');
    assert.equal(await page.evaluate(() => [...document.querySelectorAll('button')].some(button => /Load more matching jobs/.test(button.textContent))), false);
    await page.click('#walkinOpt');
    await page.waitForFunction(() => document.querySelector('#walkin-dates-options .filter-option'));
    await page.click('#walkin-dates-options .filter-option');
    await page.waitForFunction(() => document.querySelector('main [role="status"]')?.textContent.includes('3 matching jobs loaded'));
    assert.deepEqual(errors, []);
    console.log('Browser passed: automatic page retry, all 3 Apna jobs loaded automatically, no Load more, and walk-in date filter returns all 3');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
