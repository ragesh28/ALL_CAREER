/*
  This is your main scraper script.
  It now loads the company list from a secure file
  or from GitHub Secrets.
*/

// --- THIS IS THE NEW CODE ---
// We use 'puppeteer-extra' instead of the normal 'puppeteer'
const puppeteer = require('puppeteer-extra');
// We add the 'stealth' plugin
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
// We tell puppeteer to use the plugin
puppeteer.use(StealthPlugin());
// --- END OF NEW CODE ---

const fs =require('fs').promises;

// --- THIS IS THE NEW, SECURE WAY TO LOAD COMPANIES ---
let COMPANIES = [];

if (process.env.COMPANIES_JSON) {
  // We are running on GitHub
  console.log("Loading companies from GitHub Secrets...");
  COMPANIES = JSON.parse(process.env.COMPANIES_JSON);
} else {
  // We are running on your local PC
  console.log("Loading companies from local 'companies.json' file...");
  // We use 'require' because it's easier
  COMPANIES = require('./companies.json');
}
// --- END OF NEW LOADING LOGIC ---


// --- THE HCLTECH FUNCTION IS NOW DELETED (it's in the JSON file) ---


// --- Helper function to read the old database ---
async function getExistingJobs() {
  try {
    const data = await fs.readFile('jobs.json', 'utf8');
    return JSON.parse(data);
  } catch (err) {
    console.log('No existing jobs.json found. Creating a new one.');
    return []; // Return an empty array if file doesn't exist
  }
}

// --- Main function to run the scraper (UPDATED) ---
async function scrapeJobs() {
  // 1. Read the old jobs from our file
  const oldJobs = await getExistingJobs();
  const oldJobUrls = new Set(oldJobs.map(job => job.url));
  
  let allScrapedJobs = []; // This will hold ALL jobs we find

  // 2. Scrape ALL companies from the list
  for (const company of COMPANIES) {
    let browser; 
    
    try {
      console.log(`Scraping ${company.name}...`);
      browser = await puppeteer.launch({
        headless: true, // 100% automated
        args: ['--no-sandbox', '--disable-setuid-sandbox']
      });

      const page = await browser.newPage();
      await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36');
      
      // --- FIX: Removed extra dot typos ---
      if (company.url.startsWith('https.')) {
        company.url = company.url.replace('https.://', 'https://');
      }
      // --- END OF FIX ---
      
      await page.goto(company.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      
      await page.waitForSelector(company.itemSelector, { timeout: 15000 });

      // Scrape data, including date and location
      let jobsOnPage = await page.evaluate((company) => {
        const jobItems = [];
        const elements = document.querySelectorAll(company.itemSelector);

        elements.forEach(item => {
          const titleEl = item.querySelector(company.titleSelector);
          const linkEl = item.querySelector(company.linkSelector);
          const dateEl = item.querySelector(company.dateSelector);
          const locationEl = item.querySelector(company.locationSelector);
          
          if (titleEl && linkEl) {
            jobItems.push({
              company: company.name,
              title: titleEl.innerText.trim(),
              url: linkEl.href,
              location: locationEl ? locationEl.innerText.trim() : 'Unknown',
              date: dateEl ? dateEl.innerText.trim().replace(/\s+/g, ' ') : new Date().toISOString()
            });
          }
        });
        return jobItems;
      }, company); // Pass in the full company config

      // --- THIS IS YOUR NEW FILTERING LOGIC ---
      if (company.filterLocations && company.filterLocations.length > 0) {
        console.log(`-- Found ${jobsOnPage.length} jobs. Filtering for: ${company.filterLocations.join(', ')}`);
        
        const filteredJobs = jobsOnPage.filter(job => {
          const locationText = job.location.toLowerCase();
          // Check if any of the filter words are in the location
          return company.filterLocations.some(filterLoc => locationText.includes(filterLoc));
        });
        
        allScrapedJobs.push(...filteredJobs); // Add only filtered jobs
        console.log(`Found ${filteredJobs.length} jobs at ${company.name} (after filtering).`);
      } else {
        // This is for Zoho and Freshworks (no filter)
        allScrapedJobs.push(...jobsOnPage); // Add all jobs
        console.log(`Found ${jobsOnPage.length} jobs at ${company.name}.`);
      }
      // --- END OF NEW FILTERING LOGIC ---

    } catch (error) {
      console.error(`Failed to scrape ${company.name}: ${error.message}`);
    } finally {
      if (browser) {
        await browser.close();
      }
    }
  }
  
  console.log('All scraping finished.');

  // 4. --- NEW, SAFER LOGIC (YOUR IDEA) ---
  
  // A. Check if scraping failed
  if (allScrapedJobs.length === 0) {
    console.log('--- Database Update ---');
    console.log('CRITICAL: Scrapers found 0 total jobs. This might be an error.');
    console.log('To protect your data, no changes will be made to jobs.json.');
    return; // STOP and do not delete anything
  }

  // B. Find only the new jobs
  const newJobs = allScrapedJobs.filter(job => !oldJobUrls.has(job.url));
  
  // C. Create the new list by ADDING new jobs to the OLD jobs
  const finalJobsList = [...newJobs, ...oldJobs];

  console.log('--- Database Update ---');
  console.log(`Found ${newJobs.length} new jobs.`);
  console.log('Added new jobs to the existing list.');
  console.log(`Total jobs in file: ${finalJobsList.length}`);
  
  // 5. Save the final, safe list to jobs.json
  try {
    await fs.writeFile('jobs.json', JSON.stringify(finalJobsList, null, 2));
    console.log('Successfully saved job data to jobs.json');
  } catch (err) {
    console.error('Error writing jobs.json file:', err);
  }
}

// Run the scraper
scrapeJobs();