# Company scraping methods and references

Research recorded 23 November 2026.

| Method | Existing use | Investigation and verification |
|---|---|---|
| Direct HTTP JSON | Microsoft, Workday, Oracle, Phenom, SAP and custom company APIs | Inspect real response fields, pagination, country filtering, stable IDs and detail endpoints. A total count requires actual posting records before it can produce saved jobs. |
| Public ATS feeds | Greenhouse, Lever, Ashby and SmartRecruiters | Confirm the board identifier from the official career page. Preserve supplied content, compensation and date fields. Fetch individual detail endpoints when search results omit descriptions. |
| Static HTML and JobPosting JSON-LD | Google, Siemens and SSR sites | Read individual job pages and structured data. Verify canonical URLs and posting identity. |
| Playwright network observation | Existing browser interceptors | Open an isolated Chromium context. Observe XHR/fetch JSON and rendered job links. Record public endpoint paths and response status. Check service-worker handling when requests are absent. |
| Playwright rendered HTML | Existing browser fallbacks | Wait for job elements and inspect the actual page state. Save a screenshot and bounded HTML evidence for failures. A navigation link requires rejection before saving. |
| Individual description recovery | Existing `company_job_details.py` | Check API detail records, structured data and specific description containers. Record missing fields instead of inventing requirements or salary. |
| Alternate public employer board | Existing company-specific overrides | Follow career links that the official company website publishes when an old board or job URL has moved. |
| JobSpy Indeed/LinkedIn | Existing fallback and 149-company workflow | Confirm supported arguments, company matching, requested country, date window and description options. An empty recent search requires its date window in the report. |
| Authenticated proxy transport | Configured provider secrets | Test authentication and availability first. Use a valid product host/port and the existing provider account. Record provider failures separately from company failures. |
| ScraperAPI rendered response | Optional configured provider | Check account availability and request cost, then request rendered HTML when applicable. Respect provider quota and plan errors and record exhausted or unsupported capabilities. |
| GitHub/local comparison | Existing manual audits | Run the same parser against local and runner responses. Record differences in HTTP status, returned jobs, geography and descriptions. |

## Primary documentation

- Playwright network events, redirects, service workers and proxies — https://playwright.dev/python/docs/network
- Playwright browser context options — https://playwright.dev/python/docs/api/class-browsercontext
- Ashby public postings and optional compensation — https://developers.ashbyhq.com/docs/public-job-posting-api
- Greenhouse public Job Board API — https://developers.greenhouse.io/job-board.html
- SmartRecruiters posting structures and description sections — https://developers.smartrecruiters.com/docs/objects
- Lever public postings — https://github.com/lever/postings-api
- JobSpy supported arguments and descriptions — https://github.com/speedyapply/JobSpy
- Oxylabs product locations and entry points — https://developers.oxylabs.io/help-center/products-and-features/how-to-select-your-proxy-location
- ScraperAPI request options — https://docs.scraperapi.com/control-and-optimization/supported-parameters
- ScraperAPI cost checks — https://docs.scraperapi.com/control-and-optimization/cost-control

## Failure patterns to check

- Outdated company ATS host, board identifier, job ID, or career URL.
- Browser-only search state, location facets, pagination or changed response nesting.
- Service-worker responses missing from interception.
- HTTP 200 pages containing challenges, maintenance content, redirects or navigation links.
- Expired individual postings used as a search starting point.
- Global search pages that need an India facet before sampling.
- Missing description/detail fetches or fields dropped during persistence.
- HTTP 403/429, proxy authentication errors, exhausted quota and plan restrictions.
- Repeated pages, empty cursors, timeouts and missing browser dependencies.


## Additional methods verified during the second pass

- **Workday HTTP compatibility:** a normal requests client can receive an edge 429 while a browser TLS client returns the public listing. Use one optional `curl_cffi` Chrome request for public Workday URLs, keep certificate verification enabled, and do not make this alternate request when the response supplies `Retry-After`. [curl_cffi quick start](https://curl-cffi.readthedocs.io/en/stable/quick_start.html).
- **India-first native searches:** use the documented SmartRecruiters `country=in`, public destination, limit 100 and offset pagination. Bosch and ServiceNow have global first pages that otherwise conceal their India openings. [Official posting API filters](https://developers.smartrecruiters.com/reference/v1listpostings).
- **TCS browser session:** observe the public `/candidate/next/api/en-IN/search/jobs` POST. Its response contains job IDs, locations and explicit experience ranges; `/job/desc/{id}` supplies descriptions. When a bare HTTP replay is rejected, use a fresh browser session. `applyBy` is a deadline, not a posting date.
- **Zoho embedded data:** some public detail pages embed the complete record in a `jobs = JSON.parse(...)` string. Decode only that JSON string; do not execute page JavaScript in Python. The public Zoho board returns visible jobs with `Keep_on_Career_Site=false`, so that flag alone is not evidence of a hidden job. A separate `Publish=false` record is excluded.
- **Source migrations:** PhonePe to the PHONEPELIMITED SmartRecruiters board; Razorpay to the razorpaysoftwareprivatelimited Greenhouse board; Postman to its wd108 Workday site; NVIDIA to jobs.nvidia.com; Swiggy to careers.swiggy.in and the SWIGGY public board; American Express, Nokia and Akamai to their current Oracle career sites.
- **Individual links:** Turing uses `/job/{id}`, not `/jobs/{id}`. Rocketlane's Kula records require their individual ID/title link and nested ATS office/description data. Wipro supplies `unifiedUrlTitle`; use the corresponding `/job/{slug}/{id}-en_US` page when present. Citi's listing heading changed from h2 to h3.
- **Description preservation:** Capgemini's job-search JSON already contains descriptions and `apply_job_url`; preserve those fields. Workday `/apply` links require removing that suffix for the public detail API. Short truncated summaries are upgraded when a longer posting-specific description is recovered.

The production registry in `scripts/company_sources.json` contains public career URLs and reusable listing endpoints. A company is enabled for a new primary route only after a live posting was verified. A generic HTTP 200, saved-job link, media asset, company-introduction paragraph or search total is not a verified posting. Raw browser evidence stays in the workflow artifacts; reports contain statuses and short excerpts, not credentials.
