/**
 * clean_big_jobs.js
 * Removes big company jobs older than 10 days from big_jobs.json and big_jobs_data.js
 */
const fs = require('fs');
const path = require('path');

const BIG_JOBS_FILE = path.join(__dirname, 'big_jobs.json');
const BIG_JOBS_DATA_FILE = path.join(__dirname, 'big_jobs_data.js');
const KEEP_DAYS = 10;

function main() {
    if (!fs.existsSync(BIG_JOBS_FILE)) {
        console.log('No big_jobs.json found. Nothing to clean.');
        return;
    }

    let jobs;
    try {
        jobs = JSON.parse(fs.readFileSync(BIG_JOBS_FILE, 'utf8'));
    } catch (e) {
        console.log('big_jobs.json is invalid or empty. Skipping.');
        return;
    }

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - KEEP_DAYS);

    const before = jobs.length;
    const fresh = jobs.filter(job => {
        if (!job.fetchedAt) return true; // keep if no date
        const fetched = new Date(job.fetchedAt);
        return fetched >= cutoff;
    });
    const removed = before - fresh.length;

    console.log(`🧹 Big jobs cleanup: removed ${removed} jobs older than ${KEEP_DAYS} days. ${fresh.length} jobs remaining.`);

    fs.writeFileSync(BIG_JOBS_FILE, JSON.stringify(fresh, null, 2), 'utf8');
    fs.writeFileSync(BIG_JOBS_DATA_FILE, `const bigJobs = ${JSON.stringify(fresh, null, 2)};`, 'utf8');
    console.log('✅ big_jobs.json and big_jobs_data.js updated.');
}

main();
