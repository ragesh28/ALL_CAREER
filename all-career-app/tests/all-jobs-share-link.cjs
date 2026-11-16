const assert = require('node:assert/strict');
const puppeteer = require('puppeteer');

const base = process.env.ALL_CAREER_TEST_URL || 'http://127.0.0.1:5187/';
const existingQuery = '?_release=fixture';
const firstSearch = '#all_jobs?source=naukri&city=Chennai&experience=0&category=software_technical';
const roleSearch = '#all_jobs?source=naukri&city=Chennai&role=Software+Engineer&experience=0';
const today = new Date().toISOString().slice(0, 10);
const nextDay = new Date(Date.now() + 86400000);
const interview = nextDay.toISOString().slice(0, 10);
const interviewLabel = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' }).format(nextDay);
const ranged = {
  title: 'Software Engineer · range', company: 'Example', location: 'Chennai', source: 'naukri',
  url: 'https://example.com/range', experience: '0–2 years', date_posted: today,
  _normCategory: 'Software Technical', _minExp: 0, _maxExp: 2,
};
const exact = {
  ...ranged, title: 'Software Engineer · exact', url: 'https://example.com/exact', experience: '0 years',
  _maxExp: 0, is_walkin: true, walkin_date: interview,
};
const summary = {
  schema: 1, total_jobs: 2, generated_at: today,
  manifest: 'data/web/manifest.json', filtered_catalog: 'data/web/prepared.json',
  sources: { naukri: 2 }, locations: { chennai: 2 }, source_locations: { naukri: { chennai: 2 } },
  walkins: {
    total: 1, sources: { naukri: 1 }, locations: { chennai: 1 },
    source_locations: { naukri: { chennai: 1 } }, date_groups: [['chennai', 'naukri', [interview], today, 1]],
  },
};
const descriptor = { path: 'data/web/jobs.json', count: 2, newest: today, sources: ['naukri'], locations: ['chennai'] };
const files = {
  'summary.json': summary,
  'latest.json': [ranged, exact],
  'jobs.json': [ranged, exact],
  'manifest.json': { pages: [descriptor], sources: { naukri: [descriptor] }, walkins: { chennai: [descriptor] } },
  'prepared.json': {
    schema: 1, page_size: 50, zero_year_roles: true, queries: {
      'naukri/chennai/software_technical/zero': { count: 2, pages: ['data/web/ranged.json'] },
      'naukri/chennai/software_technical/exact-zero': { count: 1, pages: ['data/web/exact.json'] },
      'naukri/chennai/role/Software%20Engineer/zero': { count: 2, pages: ['data/web/role-ranged.json'] },
      'naukri/chennai/role/Software%20Engineer/exact-zero': { count: 1, pages: ['data/web/role-exact.json'] },
    },
  },
  'ranged.json': [ranged, exact],
  'exact.json': [exact],
  'role-ranged.json': [ranged, exact],
  'role-exact.json': [exact],
};

async function configure(page, requests, errors, preview = files['latest.json']) {
  page.on('pageerror', error => errors.push(error.message));
  await page.setRequestInterception(true);
  page.on('request', async request => {
    const url = new URL(request.url());
    if (url.pathname.includes('/data/web/')) {
      const file = url.pathname.split('/').pop();
      requests.push(file);
      if (file === 'role-ranged.json') await new Promise(resolve => setTimeout(resolve, 250));
      return request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(file === 'latest.json' ? preview : files[file] ?? []) });
    }
    if (url.hostname === 'cdn.tailwindcss.com') {
      return request.respond({ status: 200, contentType: 'application/javascript', body: 'window.tailwind={};' });
    }
    if (url.origin === new URL(base).origin || url.protocol === 'data:') return request.continue();
    return request.abort();
  });
}

async function clickOption(page, selector, text) {
  const found = await page.$$eval(selector, (items, label) => {
    const option = items.find(item => item.querySelector('.option-label')?.textContent.trim() === label);
    option?.click();
    return Boolean(option);
  }, text);
  assert.equal(found, true, 'Filter option available for ' + text);
}

async function assertSelections(page, search) {
  await page.waitForFunction(() => document.querySelector('.topnav input') !== null);
  const state = await page.evaluate(() => ({
    search: document.querySelector('.topnav input').value,
    sources: [...document.querySelectorAll('#source-options .checked .option-label')].map(el => el.textContent.trim()),
    cities: [...document.querySelectorAll('#location-options .checked .option-label')].map(el => el.textContent.trim()),
    role: document.querySelector('#roles-options .checked .option-label')?.textContent.trim(),
    skill: document.querySelector('#skills-options .checked .option-label')?.textContent.trim(),
    posted: document.querySelector('#sec-date .selected .option-label')?.textContent.trim(),
    experience: document.querySelector('.exp-range-slider').value,
    walkin: document.querySelector('#walkinOpt').classList.contains('checked'),
    category: document.querySelector('.pill-tech').getAttribute('aria-pressed'),
  }));
  assert.deepEqual(state, {
    search, sources: ['Naukri', 'Indeed'], cities: ['Bangalore', 'Chennai'],
    role: 'Software Engineer', skill: 'JavaScript', posted: 'Last 7 Days',
    experience: '0', walkin: true, category: 'true',
  });
  await page.waitForFunction(label => {
    const date = document.querySelector('#walkin-dates-options .checked .option-label');
    return date?.textContent.trim() === label;
  }, {}, interviewLabel);
}

(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
  try {
    const errors = [], requests = [];
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });
    await configure(page, requests, errors);
    await page.goto(base + existingQuery + firstSearch, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelector('main [role="status"]')?.textContent === '2 matching jobs · Newest first');
    assert.ok(requests.includes('ranged.json'), 'The shared link uses prepared pages');
    assert.ok(!requests.includes('jobs.json'), 'The shared link does not scan general job pages');
    await page.click('#expExactCheckboxWrap');
    await page.waitForFunction(() => location.hash.includes('exact=1'));
    await page.waitForFunction(() => document.querySelector('main [role="status"]')?.textContent === '1 matching jobs · Newest first');
    assert.ok(requests.includes('exact.json'));
    await page.click('#expExactCheckboxWrap');
    await page.click('#src-indeed');
    await clickOption(page, '#location-options .filter-option', 'Bangalore');
    await clickOption(page, '#sec-date .filter-radio', 'Last 7 Days');
    await clickOption(page, '#roles-options .filter-option', 'Software Engineer');
    await clickOption(page, '#skills-options .filter-option', 'JavaScript');
    await page.click('#walkinOpt');
    await page.waitForSelector('#walkin-dates-options .filter-option');
    await clickOption(page, '#walkin-dates-options .filter-option', interviewLabel);
    await page.click('.pill-tech');
    const search = 'C++ & café # remote';
    await page.type('.topnav input', search);
    const shared = new URL(page.url());
    assert.equal(shared.search, existingQuery);
    const params = new URLSearchParams(shared.hash.split('?')[1]);
    assert.deepEqual(Object.fromEntries(params), {
      q: search, source: 'indeed', city: 'Bangalore', posted: '7d', role: 'Software Engineer',
      experience: '0', skill: 'javascript', walkin: '1', interview: interviewLabel, category: 'software_technical',
    });
    assert.deepEqual(params.getAll('source'), ['naukri', 'indeed']);
    assert.deepEqual(params.getAll('city'), ['Chennai', 'Bangalore']);

    const opened = await browser.newPage();
    await configure(opened, [], errors);
    await opened.goto(shared.href, { waitUntil: 'domcontentloaded' });
    await assertSelections(opened, search);
    await opened.reload({ waitUntil: 'domcontentloaded' });
    await assertSelections(opened, search);
    await opened.click('.topnav-logo');
    await opened.waitForSelector('.hub-about-link');
    await opened.goBack();
    await assertSelections(opened, search);
    await opened.click('.premium-reset-btn');
    await opened.waitForFunction(() => location.hash === '#all_jobs' && document.querySelector('.topnav input').value === '');
    assert.equal(new URL(opened.url()).search, existingQuery);
    const rolePage = await browser.newPage();
    await rolePage.setViewport({ width: 1440, height: 900 });
    const roleRequests = [];
    await configure(rolePage, roleRequests, errors, []);
    await rolePage.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'no-preference' }]);
    await rolePage.goto(base + roleSearch, { waitUntil: 'domcontentloaded' });
    await rolePage.waitForFunction(() => {
      const spinner = document.querySelector('.alljobs-search-spinner');
      return spinner?.getAnimations().some(animation => animation.playState === 'running');
    });
    await rolePage.waitForFunction(() => document.querySelector('main [role="status"]')?.textContent === '2 matching jobs · Newest first');
    assert.ok(roleRequests.includes('role-ranged.json'));
    assert.ok(!roleRequests.includes('manifest.json'), 'sidebar roles must not scan the general catalog');
    await rolePage.click('#expExactCheckboxWrap');
    await rolePage.waitForFunction(() => document.querySelector('main [role="status"]')?.textContent === '1 matching jobs · Newest first');
    assert.ok(roleRequests.includes('role-exact.json'));
    const unmatched = roleSearch.replace('Software+Engineer', 'Accountant');
    await rolePage.goto(base + unmatched, { waitUntil: 'domcontentloaded' });
    await rolePage.waitForFunction(() => document.querySelector('main [role="status"]')?.textContent === '0 matching jobs · Newest first');
    assert.ok(!roleRequests.includes('manifest.json'), 'an indexed combination with no matches must finish without scanning');

    await rolePage.goto(base + roleSearch, { waitUntil: 'domcontentloaded' });
    const remove = label => rolePage.click('[aria-label="Remove ' + label + ' filter"]');
    const currentParams = () => new URLSearchParams(new URL(rolePage.url()).hash.split('?')[1]);
    await rolePage.waitForSelector('[aria-label="Remove Software Engineer filter"]');
    assert.deepEqual(await rolePage.$$eval('.alljobs-filter-chip span', nodes => nodes.map(node => node.textContent)),
      ['Naukri', 'Chennai', 'Software Engineer', '0 years']);
    await remove('Software Engineer');
    assert.deepEqual(Object.fromEntries(currentParams()), { source: 'naukri', city: 'Chennai', experience: '0' });
    assert.equal(await rolePage.$('[aria-label="Remove Software Engineer filter"]'), null);
    await remove('Naukri');
    assert.deepEqual(Object.fromEntries(currentParams()), { city: 'Chennai', experience: '0' });
    assert.equal(await rolePage.$('[aria-label="Remove Naukri filter"]'), null);
    assert.deepEqual(errors, []);
    console.log('Shared filters passed, including prepared sidebar roles, exact zero, empty results, spinner motion, and independent chip removal.');
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
