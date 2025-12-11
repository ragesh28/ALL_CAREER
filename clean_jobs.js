/*
  clean_jobs.js
  Strictly deletes jobs based on the 'fetchedAt' timestamp.
  Ignores the text date from the website.
  Ensures jobs older than 30 days are removed from both the database and the website file.
*/

const fs = require('fs');

try {
    // 1. Load the current database
    const jobs = require('./jobs.json');
    console.log(`Total jobs before cleanup: ${jobs.length}`);
    
    // 2. Set the Cutoff Date (Today - 30 Days)
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30); 
    
    console.log(`Removing jobs fetched before: ${thirtyDaysAgo.toISOString().split('T')[0]}`);

    // 3. Filter the list
    const freshJobs = jobs.filter(job => {
        // If a job has no 'fetchedAt' (from old version of scraper), keep it safe for now.
        if (!job.fetchedAt) return true; 

        const fetchDate = new Date(job.fetchedAt);
        
        // Return TRUE to keep the job if it is newer than the cutoff
        return fetchDate >= thirtyDaysAgo;
    });

    const deletedCount = jobs.length - freshJobs.length;
    console.log(`Deleted ${deletedCount} expired jobs.`);
    console.log(`Jobs remaining: ${freshJobs.length}`);

    // 4. Save to Database (jobs.json)
    fs.writeFileSync('jobs.json', JSON.stringify(freshJobs, null, 2));
    console.log('Updated jobs.json');
    
    // 5. Save to Website Data (jobs_data.js)
    const jsContent = `const activeJobs = ${JSON.stringify(freshJobs, null, 2)};`;
    fs.writeFileSync('jobs_data.js', jsContent);
    console.log('Updated jobs_data.js');

} catch (error) {
    console.error("Cleanup Error:", error.message);
}