const assert = require('node:assert/strict');
const puppeteer = require('puppeteer');

const app = new URL(process.env.ALL_CAREER_TEST_URL || 'http://127.0.0.1:5187/');
const pilot = new URL(process.env.VITE_PILOT_SEARCH_URL || 'http://127.0.0.1:18765/');
const version = 'a'.repeat(64);
const today = new Date().toISOString().slice(0, 10);
const listing = {
  title: 'Software Engineer Static', company: 'Example', location: 'Chennai', source: 'naukri',
  date_posted: today, url: 'https://example.test/static', experience: '0 years',
};
const preparedJob = {
  ...listing, title: 'Software Engineer Prepared', url: 'https://example.test/prepared',
  _minExp: 0, _maxExp: 0, _normCategory: 'Software Technical',
};
const summary = {
  schema: 1, generated_at: today, inputs_hash: version, total_jobs: 1,
  manifest: 'data/web/manifest.json', filtered_catalog: 'data/web/prepared.json',
  sources: { naukri: 1 }, locations: { chennai: 1 }, source_locations: { naukri: { chennai: 1 } },
  walkins: { total: 0, sources: {}, locations: {}, source_locations: {}, date_groups: [] },
};
const descriptor = { path: 'data/web/jobs.json', count: 1, newest: today, sources: ['naukri'], locations: ['chennai'] };
const files = {
  'summary.json': summary,
  'latest.json': [listing],
  'jobs.json': [listing],
  'manifest.json': { schema: 1, pages: [descriptor], sources: { naukri: [descriptor] }, walkins: {} },
  'prepared.json': {
    schema: 1, page_size: 50, queries: { 'naukri/chennai/software_technical/zero': { count: 1, pages: ['data/web/prepared-jobs.json'] } },
  },
  'prepared-jobs.json': [preparedJob],
};

async function main() {
  const browser = await puppeteer.launch({
    headless: true,
    executablePath: process.env.ALL_CAREER_TEST_BROWSER,
    args: ['--no-sandbox'],
  });
  let mode = 'late';
  const apiRequests = [];
  const browserErrors = [];
  try {
    const page = await browser.newPage();
    page.on('pageerror', error => browserErrors.push(error.message));
    await page.setRequestInterception(true);
    page.on('request', async request => {
      const url = new URL(request.url());
      const json = data => request.respond({
        status: 200, contentType: 'application/json',
        headers: { 'Access-Control-Allow-Origin': app.origin },
        body: JSON.stringify(data),
      });
      if (url.origin === pilot.origin) {
        apiRequests.push(Object.fromEntries(url.searchParams));
        if (mode === 'late') {
          await new Promise(resolve => setTimeout(resolve, 3500));
          await request.abort().catch(() => {});
          return;
        }
        const start = url.searchParams.has('cursor') ? 50 : 0;
        const jobs = Array.from({ length: start ? 1 : 50 }, (_, offset) => ({
          ...listing, title: 'Software Engineer Indexed ' + (start + offset),
          url: 'https://example.test/indexed/' + (start + offset),
        }));
        await json({ catalog_version: version, jobs, total: 51, next_cursor: start ? null : 'page-two' }).catch(() => {});
        return;
      }
      if (url.pathname.includes('/data/web/')) return json(files[url.pathname.split('/').pop()] ?? []);
      if (url.hostname === 'cdn.tailwindcss.com') {
        return request.respond({ status: 200, contentType: 'application/javascript', body: 'window.tailwind={};' });
      }
      return url.origin === app.origin || url.protocol === 'data:' ? request.continue() : request.abort();
    });

    const open = hash => page.goto(new URL(hash, app).href);
    const see = text => page.waitForFunction(label =>
      [...document.querySelectorAll('.job-title')].some(item => item.textContent === label), {}, text);
    const clickButton = async label => {
      const found = await page.$$eval('button', (buttons, text) => {
        const button = buttons.find(item => item.textContent.trim() === text && !item.disabled);
        button?.click();
        return Boolean(button);
      }, label);
      assert.ok(found, 'Expected button ' + label);
    };

    await open('#all_jobs?source=naukri&source=indeed');
    await see('Software Engineer Static');
    await page.waitForFunction(() => document.querySelector('main [role=status]')?.textContent.includes('matching jobs loaded'));
    assert.equal(apiRequests.length, 0, 'Two choices in one source group stay on static data');

    await open('#all_jobs?source=naukri&city=Chennai&experience=0&category=software_technical');
    await see('Software Engineer Prepared');
    assert.equal(apiRequests.length, 0, 'A covered combination stays on prepared pages');

    await open('#all_jobs?source=naukri&city=Chennai');
    const retry = 'Retry indexed search';
    await page.waitForFunction(text => [...document.querySelectorAll('button')].some(button => button.textContent === text), {}, retry);
    await see('Software Engineer Static');
    assert.equal(apiRequests.length, 1);
    assert.equal(apiRequests[0].version, version);

    mode = 'ready';
    await clickButton(retry);
    await see('Software Engineer Indexed 0');
    await clickButton('2');
    await see('Software Engineer Indexed 50');
    assert.equal(apiRequests.at(-1).cursor, 'page-two');
    await page.click('[aria-label="Remove Chennai filter"]');
    await page.waitForFunction(() => location.hash === '#all_jobs?source=naukri');
    await see('Software Engineer Static');
    assert.equal(apiRequests.length, 3);
    assert.deepEqual(browserErrors, []);
    console.log('Edge verified static routing, prepared routing, timeout fallback, retry, pagination and shared filter removal.');
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
