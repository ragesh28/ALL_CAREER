/*
  clean_jobs.js
  Deletes jobs older than 30 days.
  Updates both 'jobs.json' (Database) and 'jobs_data.js' (Website).
*/

const fs = require('fs');

try {
    // 1. Load the jobs
    const jobs = require('./jobs.json');
    console.log(`Total jobs before cleanup: ${jobs.length}`);

    // 2. Calculate the cutoff date (30 days ago)
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);

    // 3. Filter the jobs
    const freshJobs = jobs.filter(job => {
        // Try to parse the date
        const jobDate = new Date(job.date);

        // If date is invalid (e.g. "Just Now", "Today"), KEEP IT to be safe
        if (isNaN(jobDate.getTime())) {
            return true;
        }

        // Keep job if it is NEWER than 30 days ago
        return jobDate >= thirtyDaysAgo;
    });

    const deletedCount = jobs.length - freshJobs.length;
    console.log(`Deleted ${deletedCount} old jobs.`);
    console.log(`Jobs remaining: ${freshJobs.length}`);

    // 4. Save back to JSON (Database)
    fs.writeFileSync('jobs.json', JSON.stringify(freshJobs, null, 2));
    console.log('Updated jobs.json');

    // 5. Save back to JS (Website)
    const jsContent = `const activeJobs = ${JSON.stringify(freshJobs, null, 2)};`;
    fs.writeFileSync('jobs_data.js', jsContent);
    console.log('Updated jobs_data.js');

} catch (error) {
    console.error("Error cleaning jobs:", error.message);
}