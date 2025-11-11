/*
  This is your main scraper script.
  It uses Puppeteer to launch a headless Chrome browser
  and visit the sites you define.
*/

const puppeteer = require('puppeteer');
const fs = require('fs').promises;

// --- THIS IS THE PART YOU MUST CUSTOMIZE ---
/*
  This array holds the configuration for every company
  you want to scrape.
*/
const COMPANIES = [
  {
    name: 'Zoho',
    // This config is correct and working
    url: 'https.://www.zoho.com/careers/',
    listSelector: '#rec_job_listing_div',
    itemSelector: 'ul.rec-job-info',
    titleSelector: '.rec-job-title',
    linkSelector: '.rec-job-title a',
    isItemLink: false
  },
  {
    name: 'Freshworks',
    // This config is correct and working
    url: 'https://careers.smartrecruiters.com/Freshworks/',
    listSelector: 'ul.jobs-list', // The <ul> that holds all jobs
    itemSelector: 'li.job', // The <li> for a single job
    titleSelector: 'h4', // The <h4> tag is the title
    linkSelector: 'a', // The <a> tag is the link
    isItemLink: false // The link is *inside* the item
  }
  // ... Add more companies here using your find_selectors.js tool
  // We will scrape HCLTech in a special way below
];

// --- SPECIAL FUNCTION FOR HCLTECH ---
// This site is too complex, so it needs its own scraper function.
async function scrapeHCLTech(locationsToScrape) {
  let browser;
  const hclJobs = [];

  try {
    console.log(`Scraping HCLTech...`);
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.Example.com (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36');
    
    // Go to the main search page
    const url = 'https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=25667&siteid=5417#home';
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });

    // Wait for the search controls to be ready
    // We use the IDs from the HTML you sent
    await page.waitForSelector('#sidebarSearchbox_locationSearch_2785', { timeout: 15000 });
    await page.waitForSelector('#clearResumeJobsBtn', { timeout: 15000 });

    for (const location of locationsToScrape) {
      console.log(`-- Scraping HCLTech for location: ${location}`);

      // 1. Type the location into the box
      // We use page.type, which is like a real user typing
      await page.type('#sidebarSearchbox_locationSearch_2785', location);

      // 2. Click the search button
      // We use page.click
      await page.click('#clearResumeJobsBtn');

      // 3. Wait for the results to load
      // This is the hardest part. We wait for the "search-results" container to appear.
      // This is a common selector for Brassring sites.
      await page.waitForSelector('li.list-item', { timeout: 15000 });

      // 4. Scrape the data
      const jobs = await page.evaluate((companyName) => {
        const jobItems = [];
        // This is a common selector for Brassring job items
        const elements = document.querySelectorAll('li.list-item');

        elements.forEach(item => {
          // This is a common selector for the title/link
          const linkEl = item.querySelector('a[ng-if="job.JobTitle"]');
          
          if (linkEl) {
            jobItems.push({
              company: companyName,
              title: linkEl.innerText.trim(),
              url: linkEl.href
            });
          }
        });
        return jobItems;
      }, 'HCLTech'); // Pass in the company name

      hclJobs.push(...jobs);
      console.log(`-- Found ${jobs.length} jobs at HCLTech in ${location}.`);

      // 5. Go back to the search page to prepare for the next location
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForSelector('#sidebarSearchbox_locationSearch_2785', { timeout: 15000 });
    }

  } catch (error) {
    console.error(`Failed to scrape HCLTech: ${error.message}`);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
  return hclJobs; // Return all the HCL jobs we found
}


// --- Main function to run the scraper (UPDATED) ---
async function scrapeJobs() {
  let allJobs = [];

  // 1. Scrape the "normal" companies
  for (const company of COMPANIES) {
    let browser; 
    
    try {
      console.log(`Scraping ${company.name}...`);
      browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
      });

      const page = await browser.newPage();
      await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36');
      await page.goto(company.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForSelector(company.itemSelector, { timeout: 15000 });

      const jobs = await page.evaluate((company) => {
        const jobItems = [];
        const elements = document.querySelectorAll(company.itemSelector);

        elements.forEach(item => {
          const titleEl = item.querySelector(company.titleSelector);
          let linkEl;
          if (company.isItemLink) {
            linkEl = item;
          } else {
            linkEl = item.querySelector(company.linkSelector);
          }
          if (titleEl && linkEl) {
            jobItems.push({
              company: company.name,
              title: titleEl.innerText.trim(),
              url: linkEl.href
            });
          }
        });
        return jobItems;
      }, company); 

      allJobs.push(...jobs);
      console.log(`Found ${jobs.length} jobs at ${company.name}.`);

    } catch (error) {
      console.error(`Failed to scrape ${company.name}: ${error.message}`);
    } finally {
      if (browser) {
        await browser.close();
      }
    }
  }

  // 2. Scrape the special HCLTech company
  // We specify which locations we want to search for
  const hclJobs = await scrapeHCLTech(['Chennai', 'Bangalore']);
  allJobs.push(...hclJobs); // Add the HCL jobs to our main list

  console.log('All scraping finished.');

  // 3. Save all results to jobs.json
  try {
    await fs.writeFile('jobs.json', JSON.stringify(allJobs, null, 2));
    console.log('Successfully saved job data to jobs.json');
    console.log(`Total jobs found: ${allJobs.length}`);
  } catch (err) {
    console.error('Error writing jobs.json file:', err);
  }
}

// Run the scraper
scrapeJobs();