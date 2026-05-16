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

## 5. GE Healthcare (Phenom /widgets) ⚠️ Count only (SSR jobs)
- **Discovery**: `POST https://careers.gehealthcare.com/widgets`
  - Required Header: `x-csrf-token` (extract from `https://careers.gehealthcare.com/global/en/search-results?location=India` HTML `csrfToken`)
  - Body: `{"lang":"en_global","deviceType":"desktop","pageName":"search-results","ddoKey":"refineSearch","payload":{"from":0,"size":10,"location":"India"}}`
- **Response**: `refineSearch.totalHits` = 1266 (count works, but `data.jobs` is typically empty because this instance serves jobs via SSR HTML)
- **Fallback**: JobSpy/LinkedIn multi-city

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

## 8. Bosch (CaaS API) ❌ Auth-gated
- **Count**: `GET https://bosch-i3-caas-api.e-spirit.cloud/bosch-i3-prod/bosch-de.jobs.content/?count&filter={"location.country":"in"}`
- **Jobs**: `GET https://bosch-i3-caas-api.e-spirit.cloud/bosch-i3-prod/bosch-de.jobs.content/_aggrs/get_jobs?page=1&pagesize=8&avars={"country":["in"]}`
- **Required**: `Authorization: Bearer <session_token>` (token from visiting https://jobs.bosch.com)
- **API Keys found**: `b05c4012-4856-4f3d-bb0d-520f2e075e8a`, `2b760fb7-49ef-4e83-b4ba-9c3a8d185e5e`
- **Fallback**: JobSpy/LinkedIn multi-city

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
