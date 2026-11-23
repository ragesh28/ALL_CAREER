# Company investigation checklist

Started 23 November 2026. Baseline includes 244 company/source entries across three scraper engines. Employer names overlap between engines.

- [x] Preserve the previous audit and code in Git before investigation.
- [x] Inventory existing scraper engines, career URLs, saved samples and provider secret names.
- [x] Research browser network monitoring and public ATS posting/detail APIs.
- [ ] Build the persistent company inventory with previous working and failing states.
- [ ] Test configured proxy providers and record authentication, credit and connectivity results.
- [ ] Open each company career page in an isolated browser and capture public job-related network responses.
- [ ] Check direct HTML, structured data, rendered HTML and observed public APIs for linked jobs.
- [ ] Check each recovered posting for a description, experience, salary and posted date.
- [ ] Try healthy configured proxy transports for blocked requests.
- [ ] Diagnose sources that previously worked using saved samples and their current official pages.
- [ ] Implement verified parser, URL, API and description fixes in the production scraper entry points.
- [ ] Compare corrected samples locally and on GitHub Actions.
- [ ] Write a final row for every company/source with successful methods and remaining failures.
- [ ] Commit the code and reports and update PR #2.

## Recorded evidence

`company-investigation-monitor.json` and its Markdown view record the company, source engine, career URL, prior result, method attempts, observed status codes, job samples and description coverage. Each company is checkpointed individually. A later run can resume unfinished companies. Provider credentials remain in environment variables or GitHub Secrets.

## Completion rules

A successful posting needs a job title and a usable individual posting URL. An available description must belong to that posting. Empty searches, HTTP errors, browser failures, generic career links and unsupported formats receive their observed outcomes. A source remains open for investigation until its applicable methods have results or an explicit reason explains why a method could not run.
