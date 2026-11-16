import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { gzipSync } from 'node:zlib';
import { JOBS_PER_PAGE, PREPARED_CITIES, PREPARED_SOURCES, preparedJobFilterKey, preparedRoleFilterKey } from '../all-career-app/src/data/preparedJobFilters.ts';
import { catalogCity, catalogJobKey, classifyJobCategory, jobRoleText, matchesJobRole, parseExperience, ROLE_KEYWORDS, SOFTWARE_TECHNICAL } from '../all-career-app/src/utils/filterUtils.ts';

const [databasePath, output] = process.argv.slice(2);
mkdirSync(join(output, 'pages'), { recursive: true });
const paths = new Set();

function publish(directory, prefix, value) {
  const compressed = gzipSync(JSON.stringify(value), { level: 9 });
  const hash = createHash('sha256').update(compressed).digest('hex').slice(0, 24);
  const filename = prefix + hash + '.json.gz';
  const target = join(output, directory, filename);
  const path = ['data/web', directory, filename].filter(Boolean).join('/');
  if (!existsSync(target)) writeFileSync(target, compressed);
  paths.add(path);
  return path;
}

const groups = new Map();
const roleNames = Object.keys(ROLE_KEYWORDS);
for (const source of PREPARED_SOURCES) {
  for (const city of PREPARED_CITIES) {
    for (const exactZero of [false, true]) {
      groups.set(preparedJobFilterKey(source, city, exactZero), { count: 0, pages: [], pending: [] });
    }
  }
}

function flush(group) {
  group.pages.push(publish('pages', '', group.pending));
  group.pending = [];
}

function add(key, job) {
  let group = groups.get(key);
  if (!group) {
    group = { count: 0, pages: [], pending: [] };
    groups.set(key, group);
  }
  group.count++;
  group.pending.push(job);
  if (group.pending.length === JOBS_PER_PAGE) flush(group);
}

const db = new DatabaseSync(databasePath, { readOnly: true });
const seen = new Set();
try {
  const placeholders = PREPARED_SOURCES.map(() => '?').join(',');
  // The catalog writer has already resolved archive duplicates and posting dates.
  const rows = db.prepare('SELECT payload FROM jobs WHERE source IN (' + placeholders + ') ORDER BY date DESC, id');
  for (const { payload } of rows.iterate(...PREPARED_SOURCES)) {
    const job = JSON.parse(payload);
    const [min, max] = parseExperience(job.experience);
    if (min !== 0) continue;

    const location = String(job.location || '');
    const city = catalogCity(location);
    const cityNames = PREPARED_CITIES.filter(name => city.includes(name));
    if (!cityNames.length) continue;

    const company = typeof job.company === 'string' ? job.company : String(job.company?.name || job.company || 'DIRECT RECRUITER');
    const identity = job.source + '|' + catalogJobKey({ ...job, company, location });
    if (seen.has(identity)) continue;
    seen.add(identity);

    const category = classifyJobCategory(job);
    const text = jobRoleText(job);
    const roles = roleNames.filter(role => matchesJobRole(text, role));
    const prepared = { ...job, _minExp: min, _maxExp: max, _normCategory: category };
    const experienceModes = max === 0 || max === null ? [false, true] : [false];
    for (const name of cityNames) {
      for (const exactZero of experienceModes) {
        if (category === SOFTWARE_TECHNICAL) add(preparedJobFilterKey(job.source, name, exactZero), prepared);
        for (const role of roles) add(preparedRoleFilterKey(job.source, name, role, exactZero), prepared);
      }
    }
  }
} finally {
  db.close();
}

const queries = {};
for (const [key, group] of groups) {
  if (group.pending.length) flush(group);
  queries[key] = { count: group.count, pages: group.pages };
}
const index = publish('', 'filtered-', { schema: 1, page_size: JOBS_PER_PAGE, zero_year_roles: true, queries });
process.stdout.write(JSON.stringify({ index, paths: [...paths] }));
