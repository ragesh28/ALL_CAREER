# Changes made during the company investigation

The investigation covers 189 employer names and 244 overlapping source configurations. The current counts, sample links, tested methods and remaining gaps are in [company-investigation-results.md](company-investigation-results.md); the resumable data is in [company-investigation-monitor.json](company-investigation-monitor.json).

## Corrected sources and links

| Company | Observed problem | Implemented change |
|---|---|---|
| TCS | A standalone replay of its new public search API is rejected; the previous engine relied on LinkedIn. | Use the current career-page browser session, real job IDs, bounded pagination and public detail responses. Preserve explicit experience. Keep application deadlines separate from posting dates. |
| PhonePe | The previous Greenhouse board returns 404. | Use the current PHONEPELIMITED public SmartRecruiters board, its individual posting links and detail API. Exclude non-public states in the old website cache. |
| Razorpay | The previous board identifier stopped returning listings. | Use the verified razorpaysoftwareprivatelimited Greenhouse board, retaining inline descriptions. |
| Postman | The previous Greenhouse board returns 404; its website cache supplies short summaries. | Use the current wd108 Workday board and retrieve full individual descriptions. |
| Rocketlane | The scraper saved the career homepage as every application link and dropped nested descriptions/offices. | Build individual Kula posting links from the observed ID/title route and preserve nested description and office records. |
| Turing | The scraper used `/jobs/`, while the public site uses `/job/`. | Correct the link and use the browser-observed per-job API for full descriptions. |
| Qualcomm, Ericsson | The existing API parser discarded application URLs. | Preserve each position's URL and details; paginate the search and query the corresponding public detail API. |
| NVIDIA | The former Workday route no longer reliably provided results. | Use the current jobs.nvidia.com Eightfold listing and detail APIs. |
| Swiggy | The old career domain did not expose a usable listing. | Use the current careers.swiggy.in site and SWIGGY public SmartRecruiters board. Support the site's compact jobs JSON. |
| American Express | The former Eightfold URL returns 404. | Follow the current Oracle career site and its observed public listing/detail endpoints. |
| Nokia, Akamai | The old corporate/career URLs did not expose usable postings. | Connect their current Oracle boards, including expanded requisitions and bounded pagination. |
| Bosch, ServiceNow | The corporate page alone yielded no usable India sample. | Use their verified public SmartRecruiters boards with `country=in`, public destination and pagination. |
| Fractal Analytics | The previous Workday site name was wrong. | Follow the official site's redirect to the Careers board. |
| Rubrik, Appian, Okta, MongoDB, Datadog, InMobi, Epic Games, PagerDuty | Browser-only discovery was blocked, incomplete, or missed the actual public board. | Add verified Greenhouse listing endpoints and preserve inline descriptions. Global/foreign samples remain distinct from confirmed India jobs. |
| Elastic, Pinterest | Valid links using `/jobs?gh_jid=…` were rejected as generic job-list pages. | Recognize an explicit job ID in the query before rejecting a list-shaped path. Add verified native boards. |
| Thoughtworks, Zscaler | The available career page/Indeed search did not recover a usable sample. | Connect their verified public Greenhouse boards. An empty India result is reported separately from a broken source. |
| Citi | Listing headings changed from h2 to h3, producing empty job titles. | Parse the current heading and individual link, with browser recovery available. |
| Goldman Sachs | An internal `roleId` suffix produced an error page, even though the list API returned a real role. | Use the external source ID in browser URLs and the observed GetRoleById query for descriptions and explicit compensation. |
| Wipro | Generic `/jobs/{id}` links did not always expose the description; a company introduction could be mistaken for job duties. | Use the published URL slug where available. Extract the role's Job Description block and explicit posting date, excluding the company introduction. |
| Zoho | The public list truncates descriptions and the complete job is embedded in the detail page. | Decode the public JSON string without executing JavaScript; upgrade the summary with the complete matching job record. |
| Capgemini | Its public job-search JSON already contained a description and application URL, but the scraper dropped them. | Preserve these fields and use the verified India query with pagination. |

## Shared recovery and saving

- All three production scraper entry points can use the small public-source registry. Existing successful routes remain available when a new source fails.
- Direct HTML, embedded structured data, documented ATS feeds, observed browser APIs, individual detail pages and configured providers have separate outcomes. A search total, saved-jobs link, image asset or navigation label does not count as a job.
- Workday requests can use one optional browser-compatible HTTP client when the normal client is rejected. TLS remains verified; a `Retry-After` response does not trigger that alternate request.
- Repeated pagination pages stop immediately. Per-company sample/description limits bound extra requests without dropping already retrieved job records.
- Source descriptions, explicit experience, salary and posting dates survive all existing save paths. A previously seen job can receive newly recovered details without a duplicate record.
- The audit workflows only write artifacts and reports. Production catalog data was not replaced by these test samples. Extension files and desktop application files were not changed.

## Remaining cases

The report records each employer's latest career-page result alongside every configured engine's result. Some employers work through Indeed even while their own career site is blocked. Others return only foreign/global listings, have no match in the bounded recent search, require a new parser, or reject the tested clients/providers. Those observations are preserved with URLs and status codes; they are not described as proof that the employer has no vacancies.

Raw browser screenshots and public network responses are retained in the linked workflow artifacts. Credentials remain in GitHub Secrets or local private configuration and are not included in the reports.
