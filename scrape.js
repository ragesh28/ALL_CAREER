/*
  scrape.js
  - Scrapes jobs from the COMPANIES list.
  - Adds a 'fetchedAt' date stamp using LOCAL TIME (Fixes the wrong date issue).
  - Saves to 'jobs.json' and 'jobs_data.js'.
*/

const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());
const fs = require('fs').promises;

// --- 1. SETUP: LOAD COMPANIES ---
let COMPANIES = [];
try {
  if (process.env.COMPANIES_JSON) {
    COMPANIES = JSON.parse(process.env.COMPANIES_JSON);
  } else {
    COMPANIES = require('./companies.json');
  }
} catch (error) {
  process.exit(1);
}

// --- 2. CONFIGURATION ---
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

  // --- FIX: GENERATE LOCAL DATE STAMP (YYYY-MM-DD) ---
  // This uses your computer's local time, not UTC.
  // If it is Dec 11 for you, it will be Dec 11 here.
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  const dateStamp = `${year}-${month}-${day}`; 

  console.log(`Job Fetch Date Stamp: ${dateStamp}`);

  for (const company of COMPANIES) {
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
      
      if (company.url.startsWith('https.')) {
        company.url = company.url.replace('https.://', 'https://');
      }

      await page.goto(company.url, { waitUntil: 'domcontentloaded', timeout: 60000 });

      try {
        await page.waitForSelector(company.itemSelector, { timeout: 15000 });
        if (company.name === "Accenture") {
             console.log(`-- Accenture detected. Waiting 5 seconds...`);
             await new Promise(r => setTimeout(r, 5000)); 
        }
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
          if (company.isItemLink) linkEl = item;
          else linkEl = company.linkSelector ? item.querySelector(company.linkSelector) : null;
          
          const dateEl = company.dateSelector ? item.querySelector(company.dateSelector) : null;
          const locationEl = company.locationSelector ? item.querySelector(company.locationSelector) : null;
          
          if (titleEl) {
            let locText = locationEl ? locationEl.textContent.trim() : 'Unknown';
            locText = locText.replace(/\s+/g, ' ');
            let titleText = titleEl.textContent.trim();
            
            let jobUrl = company.url;
            if (linkEl && linkEl.href) jobUrl = linkEl.href;

            if (titleText.length > 0) {
                jobItems.push({
                    company: company.name,
                    title: titleText,
                    url: jobUrl,
                    location: locText,
                    // Store website date for display, but rely on fetchedAt for filtering
                    date: dateEl ? dateEl.textContent.trim().replace(/\s+/g, ' ') : 'Check Link'
                });
            }
          }
        });
        return jobItems;
      }, company);

      // Add the LOCAL 'fetchedAt' stamp
      const stampedJobs = jobsOnPage.map(j => ({
          ...j,
          fetchedAt: dateStamp 
      }));

      if (company.filterLocations && company.filterLocations.length > 0) {
        const filteredJobs = stampedJobs.filter(job => {
          const locationText = job.location.toLowerCase();
          return company.filterLocations.some(filterLoc => locationText.includes(filterLoc));
        });
        allScrapedJobs.push(...filteredJobs);
      } else {
        allScrapedJobs.push(...stampedJobs);
      }

    } catch (error) {
      console.error(`Failed to scrape ${company.name}: ${error.message}`);
    } finally {
      if (browser) await browser.close();
    }
  }
  
  // Deduplication & Saving
  const newJobs = allScrapedJobs.filter(job => !oldJobUrls.has(job.url));
  const finalJobsList = [...newJobs, ...oldJobs];

  console.log(`Found ${newJobs.length} new jobs.`);
  console.log(`Total jobs in database: ${finalJobsList.length}`);
  
  try {
    await fs.writeFile('jobs.json', JSON.stringify(finalJobsList, null, 2));
    const jsContent = `const activeJobs = ${JSON.stringify(finalJobsList, null, 2)};`;
    await fs.writeFile('jobs_data.js', jsContent);
    console.log('Database updated successfully.');
  } catch (err) {
    console.error('Error writing files:', err);
  }
}

scrapeJobs();