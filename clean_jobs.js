/*
  CLEAN_JOBS.JS

  This is a separate tool, as you requested.
  Its only job is to read 'jobs.json', remove jobs
  older than 30 days, and save the file.
*/

const fs = require('fs').promises;
const path = require('path');

const jobFilePath = path.join(__dirname, 'jobs.json');
const MAX_JOB_AGE_DAYS = 30; // We will remove jobs older than this

// Main function to run the cleanup
async function cleanOldJobs() {
  console.log(`--- Starting Job Cleanup ---`);
  
  // 1. Get the current date and calculate the "cutoff" date
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - MAX_JOB_AGE_DAYS);
  console.log(`Removing any jobs posted before: ${cutoffDate.toDateString()}`);

  let jobs;
  try {
    // 2. Read the jobs.json file
    const data = await fs.readFile(jobFilePath, 'utf8');
    jobs = JSON.parse(data);
  } catch (err) {
    console.error(`Error: Could not read jobs.json. ${err.message}`);
    return; // Stop if we can't read the file
  }

  const originalJobCount = jobs.length;

  // 3. Filter the jobs, keeping only the "fresh" ones
  const freshJobs = jobs.filter(job => {
    // If the job has no date, we can't check it, so we keep it.
    if (!job.date) {
      return true;
    }

    try {
      // Try to convert the job's date string into a real Date object
      const jobDate = new Date(job.date);

      // Check if the date is valid. If not, keep the job.
      if (isNaN(jobDate.getTime())) {
        return true; 
      }

      // This is the main check:
      // We keep the job if its date is *after* our cutoff date.
      return jobDate >= cutoffDate;

    } catch (error) {
      // If anything goes wrong with parsing, keep the job.
      return true;
    }
  });

  const removedJobCount = originalJobCount - freshJobs.length;

  // 4. Log the results
  console.log(`Original job count: ${originalJobCount}`);
  console.log(`Removed ${removedJobCount} old jobs.`);
  console.log(`Remaining jobs: ${freshJobs.length}`);

  // 5. Save the new, clean list back to jobs.json
  try {
    await fs.writeFile(jobFilePath, JSON.stringify(freshJobs, null, 2));
    console.log('Successfully saved cleaned jobs to jobs.json');
  } catch (err) {
    console.error(`Error writing cleaned jobs.json: ${err.message}`);
  }
}

// Run the cleanup script
cleanOldJobs();