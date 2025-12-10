/*
  This is your main scraper script.
  It includes:
  1. Stealth mode to bypass bot detection.
  2. Logic to save 'jobs_data.js' for the website (Fixes the loading error).
  3. Logic to save 'jobs.json' for the database (Remembers old jobs).
  4. Fix for Accenture (waiting for text to load).
*/

const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());
const fs = require('fs').promises;

// --- 1. SETUP: LOAD COMPANIES ---
let COMPANIES = [];
try {
  if (process.env.COMPANIES_JSON) {
    console.log("Loading companies from GitHub Secrets...");
    COMPANIES = JSON.parse(process.env.COMPANIES_JSON);
  } else {
    console.log("Loading companies from local 'companies.json' file...");
    COMPANIES = require('./companies.json');
  }
} catch (error) {
  console.error("Error loading companies:", error.message);
  process.exit(1);
}

// --- 2. CONFIGURATION: TEST MODE ---
// Set this to a company name (e.g. "Accenture") to test only that company.
// Leave as "" to run ALL companies.
const TEST_ONLY_COMPANY = ""; 

async function getExistingJobs() {
  try {
    const data = await fs.readFile('jobs.json', 'utf8');
    return JSON.parse(data);
  } catch (err) {
    return [];
  }
}

async function scrapeJobs() {
  const oldJobs = await getExistingJobs();
  const oldJobUrls = new Set(oldJobs.map(job => job.url));
  let allScrapedJobs = [];

  for (const company of COMPANIES) {
    // Isolation Logic
    if (TEST_ONLY_COMPANY && company.name !== TEST_ONLY_COMPANY) {
      continue; 
    }

    let browser;
    try {
      console.log(`Scraping ${company.name}...`);
      browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
      });

      const page = await browser.newPage();
      await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36');
      
      // Automatic Typo Fixer for URLs
      if (company.url.startsWith('https.')) {
        company.url = company.url.replace('https.://', 'https://');
      }

      await page.goto(company.url, { waitUntil: 'domcontentloaded', timeout: 60000 });

      try {
        await page.waitForSelector(company.itemSelector, { timeout: 15000 });
        
        // --- ACCENTURE FIX: WAIT FOR SKELETON LOADING ---
        if (company.name === "Accenture") {
             console.log(`-- Accenture detected. Waiting 5 seconds for text to appear...`);
             await new Promise(r => setTimeout(r, 5000)); 
        }
        // ------------------------------------------------

      } catch(e) {
        console.log(`-- Warning: Could not find items for ${company.name}.`);
        if (browser) await browser.close();
        continue;
      }

      const jobsOnPage = await page.evaluate((company) => {
        const jobItems = [];
        const elements = document.querySelectorAll(company.itemSelector);

        elements.forEach(item => {
          const titleEl = company.titleSelector ? item.querySelector(company.titleSelector) : null;
          let linkEl;
          if (company.isItemLink) {
            linkEl = item;
          } else {
            linkEl = company.linkSelector ? item.querySelector(company.linkSelector) : null;
          }
          
          const dateEl = company.dateSelector ? item.querySelector(company.dateSelector) : null;
          const locationEl = company.locationSelector ? item.querySelector(company.locationSelector) : null;
          
          if (titleEl) {
            // Use textContent to get text even if hidden
            let locText = locationEl ? locationEl.textContent.trim() : 'Unknown';
            locText = locText.replace(/\s+/g, ' ');

            let titleText = titleEl.textContent.trim();

            if (titleText.length > 0) {
                jobItems.push({
                company: company.name,
                title: titleText,
                // Fallback to company URL if specific link is missing (TCS fix)
                url: linkEl ? linkEl.href : company.url,
                location: locText,
                date: dateEl ? dateEl.textContent.trim().replace(/\s+/g, ' ') : new Date().toISOString()
                });
            }
          }
        });
        return jobItems;
      }, company);

      // Filter Logic
      if (company.filterLocations && company.filterLocations.length > 0) {
        console.log(`-- Found ${jobsOnPage.length} raw jobs. Filtering...`);
        
        const filteredJobs = jobsOnPage.filter(job => {
          const locationText = job.location.toLowerCase();
          return company.filterLocations.some(filterLoc => locationText.includes(filterLoc));
        });
        
        allScrapedJobs.push(...filteredJobs);
        console.log(`Found ${filteredJobs.length} jobs at ${company.name} (after filtering).`);
      } else {
        allScrapedJobs.push(...jobsOnPage);
        console.log(`Found ${jobsOnPage.length} jobs at ${company.name}.`);
      }

    } catch (error) {
      console.error(`Failed to scrape ${company.name}: ${error.message}`);
    } finally {
      if (browser) await browser.close();
    }
  }
  
  console.log('All scraping finished.');

  if (allScrapedJobs.length === 0) {
    console.log('--- Database Update ---');
    console.log('No jobs found (or scraping failed). No changes made to data files.');
    return;
  }

  const newJobs = allScrapedJobs.filter(job => !oldJobUrls.has(job.url));
  const finalJobsList = [...newJobs, ...oldJobs];

  console.log('--- Database Update ---');
  console.log(`Found ${newJobs.length} new jobs.`);
  console.log(`Total jobs in database: ${finalJobsList.length}`);
  
  try {
    // 1. Save JSON (The Database)
    await fs.writeFile('jobs.json', JSON.stringify(finalJobsList, null, 2));
    console.log('Saved jobs.json (Database)');

    // 2. Save JS (For the Website)
    const jsContent = `const activeJobs = ${JSON.stringify(finalJobsList, null, 2)};`;
    await fs.writeFile('jobs_data.js', jsContent);
    console.log('Saved jobs_data.js (Website Data)');

  } catch (err) {
    console.error('Error writing files:', err);
  }
}

scrapeJobs();