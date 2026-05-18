# Job API Calls — Working Endpoints Reference

## 1. Qualcomm (Phenom People) ✅
- **Discovery**: `GET https://careers.qualcomm.com/api/pcsx/search?domain=qualcomm.com&location=india&start=0&num=10`
- **Pagination**: Increment `start` by 10 → `start=10`, `start=20`, etc.
- **Required**: `domain=qualcomm.com` param (422 without it)
- **Response**: `data.positions[]` → `name`, `locations[]`, `id`
- **Total**: `data.numFound` (may return 0, use positions count)

## 2. Ericsson (Phenom People) ✅
- **Discovery**: `GET https://jobs.ericsson.com/api/pcsx/search?domain=ericsson.com&location=India&start=0&num=10`
- **Pagination**: Increment `start` by 10
- **Required**: `domain=ericsson.com` param
- **Response**: Same as Qualcomm — `data.positions[]`

## 3. Siemens (HTML SSR) ✅
- **Discovery**: `GET https://jobs.siemens.com/en_US/externaljobs/SearchJobs/?42414=[812053]&folderRecordsPerPage=10`
- **Pagination**: `folderOffset=10`, `folderOffset=20`, etc.
- **Parse**: `article.article--result` → `h2` for title, `.location` class for location
- **Total**: Parse from page text (e.g. "60 results found")

## 4. Amadeus (Workday) ✅
- **Discovery**: `POST https://amadeus.wd502.myworkdayjobs.com/wday/cxs/amadeus/jobs/jobs`
  - Body: `{"appliedFacets":{},"limit":20,"offset":0,"searchText":"India"}`
- **Pagination**: Increment `offset` by 20
- **Response**: `total`, `jobPostings[]` → `title`, `locationsText`, `externalPath`

## 5. GE Healthcare (SSR HTML) ✅
- **Method**: HTML Parsing (BeautifulSoup)
- **Endpoint**: `GET https://careers.gehealthcare.com/global/en/search-results?from=0&location=India`
- **Pagination**: Increment `from` parameter by 10 (`from=10`, `from=20`)
- **Parsing Logic**: Find `li.jobs-list-item`, extract `div.job-title`, `span.job-location`, `span.job-id`

## 6. Bank of America (REST API) ✅
- **Discovery**: `GET https://careers.bankofamerica.com/services/jobssearchservlet?start=0&rows=10&search=jobsByLocation&searchstring=India`
- **Pagination**: Increment `start` by 10
- **Required Headers**:
  - `Referer: https://careers.bankofamerica.com/en-us/job-search/india`
  - `x-requested-with: XMLHttpRequest`
- **Response**: `totalMatches`, `jobsList[]` → `postingTitle`, `primaryLocation`, `jcrURL`

## 7. Honeywell (Oracle HCM) ✅
- **Endpoint**: `GET https://ibqbjb.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations,flexFieldsFacet.values&finder=findReqs;siteNumber=CX_1,locationId=300000000469485,sortBy=POSTING_DATES_DESC,limit=25`
- **Pagination**: Add `&offset=25`, `&offset=50`
- **Requirement**: `finder` must contain `locationId=300000000469485` for India
- **Response**: `items[0].TotalJobsCount`, jobs inside `items[0].requisitionList[]`
- **Multi-city**: Handled via `PrimaryLocation` and `otherWorkLocations[]`

## 8. Bosch (CaaS API) ✅
- **Count**: `GET https://bosch-i3-caas-api.e-spirit.cloud/bosch-i3-prod/bosch-de.jobs.content/?count&filter={"location.country":"in"}`
- **Jobs**: `GET https://bosch-i3-caas-api.e-spirit.cloud/bosch-i3-prod/bosch-de.jobs.content/_aggrs/get_jobs?page=1&pagesize=8&avars={"country":["in"]}`
- **Required**: `Authorization: Bearer <session_token>` (Token is successfully parsed from the initial `https://jobs.bosch.com` HTML/scripts)
- **API Keys found**: `b05c4012-4856-4f3d-bb0d-520f2e075e8a`, `2b760fb7-49ef-4e83-b4ba-9c3a8d185e5e`

## 9. Maersk (Native API) ✅
- **Endpoint**: `GET https://api.maersk.com/careers/vacancies?limit=24&offset=0&city=india`
- **Pagination**: Increment `offset` by 24
- **Required Header**: `consumer-key` (extract dynamically from JS on `https://www.maersk.com/careers/vacancies` or hardcode if static)
- **Response**: `ResultCount`, jobs inside `Results[]` -> `Title`, `City`, `Key` (for URL)

## 10. Wipro (SAP SuccessFactors) ✅
- **Discovery**: `POST https://careers.wipro.com/services/recruiting/v1/jobs`
  - Body: `{"facetingOnly": true, "locale": "en_US"}`
- **Pagination**: `{"pageNumber": 0, "locale": "en_US"}` → increment pageNumber
- **Response**: `totalJobs` = 9914, `jobSearchResult[]` → `response.unifiedStandardTitle`, `response.sfstd_jobLocation_obj`
- **Page size**: 10 per page
- **Required Headers**: `Origin: https://careers.wipro.com`, `Referer: https://careers.wipro.com/en-US/search`
- **Linux fix**: Strip BOM with `resp.text.lstrip("\ufeff")`


## 11. Arcesium (Greenhouse) ✅
- **Endpoint**: `GET https://boards-api.greenhouse.io/v1/boards/arcesiumllc/jobs?content=true`
- **Pagination**: None. Returns all open positions in a single JSON array.
- **Response**: `jobs[]` → `title`, `location.name`, `absolute_url`

## 12. Juniper Networks / HPE (Phenom) ⚠️ Count only (SSR jobs)
- **Endpoint**: `POST https://careers.hpe.com/widgets`
- **Required**: `x-csrf-token` from `https://careers.hpe.com/us/en/search-results?location=India`
- **Payload**: `{"lang":"en_us","deviceType":"desktop","pageName":"search-results","ddoKey":"refineSearch","payload":{"from":0,"size":10,"location":"India"}}`
- **Fallback**: HTML parsing (SSR). The JSON array is empty, always fall back to parsing the HTML of that same page.

## 13. Mastercard (Phenom) ⚠️ Count only (SSR jobs)
- **Endpoint**: `POST https://careers.mastercard.com/widgets`
- **Required**: `x-csrf-token` from `https://careers.mastercard.com/us/en/search-results?location=India`
- **Fallback**: HTML parsing (SSR). If JSON array is empty, parse the HTML.

## 14. Barclays (SSR HTML) ✅
- **Method**: HTML Parsing (BeautifulSoup)
- **Endpoint**: `GET https://search.jobs.barclays/search-jobs/India`
- **Pagination**: URL parameter `p=2`, `p=3` (e.g. `?p=2`)

## 15. Fidelity Investments (SSR HTML) ✅
- **Method**: HTML Parsing (BeautifulSoup)
- **Endpoint**: `GET https://jobs.fidelity.com/in/jobs/`
- **Pagination**: URL parameter `p=2`, `p=3` (e.g. `?p=2`)

## 16. BNY (Oracle HCM) ✅
- **Endpoint**: `GET https://eofe.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1001,locationId=300000000378365,limit=25`
- **Requirement**: `finder` must contain `locationId=300000000378365` (found in search results URL)
- **Pagination**: Add `&offset=25`, `&offset=50`

## 17. American Express (Oracle HCM) ✅
- **Endpoint**: `GET https://egug.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1,locationId=300000000228786,limit=10`
- **Important**: Do not use `expand` parameters as they cause timeouts. Use this lightweight URL.
- **Pagination**: Add `&offset=10`, `&offset=20`

## 18. Societe Generale (Playwright / Browser) ⚠️ Slow
- **Status**: ✅ Working via Browser, but requires Playwright (due to Imperva blocking cloud IPs).
- **Note**: Direct API calls via proxy work locally, but cloud IPs return 403 Forbidden. Using Playwright completely bypasses the block but makes the scraping process slower.
- **Step 1**: `GET https://careers.societegenerale.com/sg-careers-offers/get-token` -> returns Bearer token (expires in 10 mins).
- **Step 2**: `POST https://careers.societegenerale.com/search-proxy.php`
- **Required Header**: `authorization-api: Bearer <your_token>`
- **Payload**: `{"profile":"ces_profile_sgcareers","query":{"advanced":[{"name":"geo","op":"eq","value":"INDIA"}]}}`

## 19. Visa (Workday) ✅
- **Endpoint**: `POST https://visa.wd5.myworkdayjobs.com/wday/cxs/visa/Visa/jobs`
- **Payload**: `{"limit":20,"offset":0,"searchText":""}`
- **Pagination**: Update `offset` by 20.

## 20. NatWest Group (Playwright / Browser) ⚠️ Slow
- **Status**: ✅ Working via Browser, but requires Playwright.
- **Endpoint**: `https://jobs.natwestgroup.com/search/jobs/in/country/india`
- **Note**: WAF blocks API requests from cloud IPs. Must use a headless browser (Playwright) which bypasses the block successfully but takes significantly more time to scrape.

---

### Global API Rules Updated:
1. **Phenom (HPE, Mastercard, GE)**: If the JSON array is empty, always fall back to parsing the HTML of that same page. They use the same layout.
2. **Oracle (Amex, BNY, Honeywell)**: Always use the `locationId` parameter. You can find this ID by looking at the search results URL in your browser.
3. **SocGen**: You must call the `/get-token` endpoint every time you start your script, as the token expires in 10 minutes.


### HTML Parsing Selectors Reference (SSR-Locked Sites):
For sites that require HTML parsing (BeautifulSoup), use the following CSS selectors:

| Company | Main Container | Job Row / Card |
| :--- | :--- | :--- |
| **Juniper / Mastercard** | `ul.search-results-list` | `li.jobs-list-item` |
| **Barclays** | `section#search-results` | `div.job-info` |
| **Fidelity** | `div.search-results-list` | `div.job-item` |
| **NatWest (Fallback)** | `div#search-results` | `a.job-result` |

### Blocked Sites Mitigation Notes:
- **NatWest Group**: Attempts to use the native `.json` endpoint require strict headers (`Referer`, `X-Requested-With: XMLHttpRequest`). Even with headers, cloud IPs are often blocked (403). Use the HTML parser fallback above.
- **Societe Generale**: The `/search-proxy.php` endpoint aggressively blocks Cloud Provider IPs (AWS, GCP, DigitalOcean) via Imperva/Incapsula. Must be run locally or via a Residential Proxy.


## 21. Fractal Analytics (Workday) ✅
- **Endpoint**: `POST https://fractal.wd1.myworkdayjobs.com/wday/cxs/fractal/Careers/jobs`
- **Payload**: `{"limit":20,"offset":0,"searchText":""}`

## 22. Broadcom (Workday) ✅
- **Endpoint**: `POST https://broadcom.wd1.myworkdayjobs.com/wday/cxs/broadcom/External_Career/jobs`
- **Payload**: `{"limit":20,"offset":0,"searchText":""}`

## 23. Akamai (Oracle HCM) ✅
- **Endpoint**: `GET https://fa-extu-saasfaprod1.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1,locationId=300000000469285,limit=25`

## 24. ABB (Phenom) ⚠️ Count only (SSR jobs)
- **Endpoint**: `POST https://careers.abb/widgets`
- **Fallback**: HTML parsing (SSR). The JSON array is empty, always fall back to parsing the HTML of that same page.

## 25. Publicis Sapient (Playwright / Browser) ⚠️ Slow
- **Status**: ✅ Working via Browser, but requires Playwright.
- **Endpoint**: `https://careers.publicissapient.com/job-search`
- **Note**: WAF blocks API requests from cloud IPs. Headless browser successfully loads page and renders jobs (e.g. 14 jobs in India).

## 26. IBM (Playwright / Browser) ⚠️ Slow
- **Status**: ✅ Working via Browser, but requires Playwright.
- **Note**: API throws 400 Bad Request, likely requiring strict browser context.

## 27. ZS Associates (Playwright / Browser) ⚠️ Slow
- **Status**: ✅ Working via Browser, but requires Playwright.
- **Note**: API returns 0 jobs without strict session tracking.

## 28. Continental (Playwright / Browser) ⚠️ Slow
- **Status**: ✅ Working via Browser, but requires Playwright.
- **Note**: API returns 0 jobs via native requests, requires full browser evaluation.
