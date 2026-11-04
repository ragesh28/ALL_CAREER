const puppeteer = require('puppeteer');
const assert = require('node:assert/strict');

(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
  try {
    const page = await browser.newPage();
    const errors = [], requested = [], pending = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.setRequestInterception(true);
    const now = new Date(), tomorrow = new Date(now);
    tomorrow.setDate(now.getDate() + 1);
    const date = now.toISOString().slice(0, 10), interview = tomorrow.toISOString().slice(0, 10);
    const job = { title: 'Latest engineer', company: 'Fixture Company', location: 'Chennai', source: 'naukri', url: 'https://example.com/job', date_posted: date, is_walkin: true, walkin_date: interview };
    const descriptor = { path: 'data/web/testpage.json', count: 1, newest: date, sources: ['naukri'], locations: ['chennai'] };
    const summary = { schema: 1, total_jobs: 10000, manifest: 'data/web/testmanifest.json', sources: { naukri: 10000 }, locations: { chennai: 9000 }, source_locations: { naukri: { chennai: 9000 } }, walkins: { total: 1000, locations: { chennai: 1000 }, sources: { naukri: 1000 }, source_locations: { naukri: { chennai: 1000 } }, date_groups: [['chennai', 'naukri', [interview], date, 1000]] } };
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/data/web/')) {
        requested.push(url);
        if (url.endsWith('latest.json')) { pending.push(request); return; }
        const data = url.endsWith('summary.json') ? summary : url.endsWith('testmanifest.json') ? { pages: [descriptor], walkins: { chennai: [descriptor] } } : [job];
        return request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(data) });
      }
      // Isolate external CDN availability from this loading test.
      if (url.includes('cdn.tailwindcss.com')) return request.respond({ status: 200, contentType: 'application/javascript', body: 'window.tailwind = {};' });
      if (!url.startsWith('http://127.0.0.1:5187/') && !url.startsWith('data:')) return request.abort();
      request.continue();
    });
    await page.goto('http://127.0.0.1:5187/#all_jobs', { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelector('.count-num')?.textContent === '10,000');
    await page.waitForFunction(() => document.querySelector('#walkinOpt')?.textContent.includes('1,000'));
    assert.ok((await page.$eval('#location-options', element => element.textContent)).includes('9,000'));
    assert.ok(pending.length > 0, 'preview should still be stalled while all three counts are visible');
    for (const request of pending) await request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify([job]) });
    await page.waitForFunction(() => document.body.textContent.includes('Latest engineer'));
    await page.click('#walkinOpt');
    await page.waitForFunction(() => document.querySelector('#location-options')?.textContent.includes('1,000'));
    assert.deepEqual(errors, []);
    assert.ok(requested.every(url => !/initial_jobs|walkin_jobs|big_company_jobs/.test(url)));
    console.log('Browser passed: independent counts, summary worker, walk-in location facet, cards, and no app errors');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
