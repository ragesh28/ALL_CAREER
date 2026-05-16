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

## 5. GE Healthcare (Phenom /widgets) ⚠️ Count only
- **Discovery**: `POST https://careers.gehealthcare.com/widgets`
  - Body: `{"lang":"en_global","deviceType":"desktop","country":"global","ddoKey":"refineSearch","from":0,"size":10,"location":"India"}`
- **Response**: `refineSearch.totalHits` = 1266 (count works, but `data.jobs` is empty)
- **Fallback**: JobSpy/LinkedIn multi-city
- **Note**: This Phenom instance serves job data via SSR HTML, not JSON API

## 6. Bank of America (REST API) ✅
- **Discovery**: `GET https://careers.bankofamerica.com/services/jobssearchservlet?start=0&rows=10&search=jobsByLocation&searchstring=India`
- **Pagination**: Increment `start` by 10
- **Required Headers**:
  - `Referer: https://careers.bankofamerica.com/en-us/job-search/india`
  - `x-requested-with: XMLHttpRequest`
- **Response**: `totalMatches`, `jobsList[]` → `postingTitle`, `primaryLocation`, `jcrURL`

## 7. Honeywell (Oracle HCM) ❌ Blocked
- **Endpoint**: `GET https://ibqbjb.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&limit=25`
- **Problem**: `locationId` param rejected, `finder` returns search metadata not jobs
- **Fallback**: JobSpy/LinkedIn multi-city

## 8. Bosch (CaaS API) ❌ Auth-gated
- **Count**: `GET https://bosch-i3-caas-api.e-spirit.cloud/bosch-i3-prod/bosch-de.jobs.content/?count&filter={"location.country":"in"}`
- **Jobs**: `GET https://bosch-i3-caas-api.e-spirit.cloud/bosch-i3-prod/bosch-de.jobs.content/_aggrs/get_jobs?page=1&pagesize=8&avars={"country":["in"]}`
- **Required**: `Authorization: Bearer <session_token>` (token from visiting https://jobs.bosch.com)
- **API Keys found**: `b05c4012-4856-4f3d-bb0d-520f2e075e8a`, `2b760fb7-49ef-4e83-b4ba-9c3a8d185e5e`
- **Fallback**: JobSpy/LinkedIn multi-city

## 9. Maersk (HTML/JS) ❌ JS-rendered
- **Page**: `GET https://www.maersk.com/careers/vacancies?searchText=&city=INDIA`
- **Problem**: Page is JS-rendered, needs Playwright
- **Fallback**: JobSpy/LinkedIn multi-city

## 10. Wipro (SAP SuccessFactors) ✅
- **Discovery**: `POST https://careers.wipro.com/services/recruiting/v1/jobs`
  - Body: `{"facetingOnly": true, "locale": "en_US"}`
- **Pagination**: `{"pageNumber": 0, "locale": "en_US"}` → increment pageNumber
- **Response**: `totalJobs` = 9914, `jobSearchResult[]` → `response.unifiedStandardTitle`, `response.sfstd_jobLocation_obj`
- **Page size**: 10 per page
- **Required Headers**: `Origin: https://careers.wipro.com`, `Referer: https://careers.wipro.com/en-US/search`
- **Linux fix**: Strip BOM with `resp.text.lstrip("\ufeff")`
