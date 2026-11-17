// Index using the same role, experience, and walk-in rules as All Jobs.
import { createInterface } from 'node:readline';
import {
  catalogCity, isOtherSource, isWalkinJob, getJobWalkinDates,
  parseExperience, classifyJobCategory, jobRoleText, matchesJobRole, ROLE_KEYWORDS,
} from '../all-career-app/src/utils/filterUtils.ts';

const roles = Object.keys(ROLE_KEYWORDS);
process.stdout.write(JSON.stringify(roles) + '\n');
const aliases = { apna_jobs: 'apna', work_india: 'workindia', freshers_world: 'freshersworld' };
for await (const line of createInterface({ input: process.stdin, crlfDelay: Infinity })) {
  const indexed = JSON.parse(line).map(job => {
    const title = String(job.title || 'Position');
    const company = typeof job.company === 'string' ? job.company
      : String(job.company?.name || job.company || 'DIRECT RECRUITER');
    const location = typeof job.location === 'string' ? job.location
      : String(job.location?.city || job.location?.name || 'India');
    let source = String(job.source || job.platform || '').toLowerCase().trim().replace(/\s+/g, '_');
    source = Object.hasOwn(aliases, source) ? aliases[source] : source;
    const url = String(job.url || job.apply_url || job.telegram_url || '').toLowerCase();
    if (source === 'other' || !source) {
      if (job.telegram_url || url.includes('t.me/')) source = 'telegram_message';
      else if (job.flyer_image_url || job.raw_flyer_src) source = 'google_images';
    }

    const date = String(job.date_posted || job.fetchedAt || job.fetched_at || job.date || '').slice(0, 10);
    const parsed = Date.parse(date);
    const posted = date && Number.isFinite(parsed) ? new Date(parsed).toISOString().slice(0, 10) : '';
    const normalized = { ...job, company, title, location, source, date };
    const [titleText, roleText] = jobRoleText(normalized);
    const walkin = isWalkinJob(normalized);
    const [min, max] = parseExperience(job.experience);
    return {
      source, other: isOtherSource(source), city: catalogCity(location),
      company: company.toLowerCase(), date, posted,
      category: classifyJobCategory(normalized), min, max,
      title: titleText, role: roleText,
      roles: roles.filter(role => matchesJobRole([titleText, roleText], role)),
      search: [title, company, location, job.role_search, job.walkin_date, job.description, job.venue]
        .filter(Boolean).join(' ').toLowerCase(),
      skills: [Array.isArray(job.skills) ? job.skills.join(' ') : '', title, job.description || '']
        .join(' ').toLowerCase(),
      walkin, interviews: walkin ? getJobWalkinDates(normalized) : [],
    };
  });
  if (!process.stdout.write(JSON.stringify(indexed) + '\n')) {
    await new Promise(resolve => process.stdout.once('drain', resolve));
  }
}
