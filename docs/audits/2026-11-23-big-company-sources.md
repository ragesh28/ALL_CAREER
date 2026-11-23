# Big Company source and description audit — 23 November 2026

244 configured company/source entries were checked: 44 direct sources, 51 API/browser configurations, and 149 Indeed company searches. These lists overlap; 244 is not a unique employer count. Windows probes and GitHub Actions probes used the production scraper functions with bounded sample sizes.

## What the results mean

- A returned sample proves that one listing was retrievable at test time. It does not prove every job or every page works.
- Indeed probes used India, a 72-hour posting window, and at most five search results. An empty result is not proof that the employer has no vacancies or that its whole website is broken.
- Direct probes inspected up to 20 search results; a global first page can lack India jobs even when later pages contain them. Missing locations and a location stated only as Remote retain the existing store policy and are not confirmed India locations.
- Description recovery makes additional requests for individual postings. A missing description can be a blocked detail page, absent data, a generic listing link, or an unsupported format.
- Experience and salary columns show explicitly extracted source values. Not extracted does not establish that the posting omits the information. No AI model was used in this audit.
- All three Big Company workflows were inspected. None passes configured proxy credentials to its scraper. The previously invalid proxy argument was removed/corrected; unrelated portal-workflow proxy secrets were not copied into this audit.

## Latest GitHub sample results

| Engine | Checked | Returned sample | Description present in sample | Other outcomes |
|---|---:|---:|---:|---|
| direct | 44 | 25 | 16 | No jobs returned: 17; Only invalid/navigation links: 2 |
| md | 51 | 33 | 28 | Only invalid/navigation links: 7; No jobs returned: 11 |
| indeed | 149 | 73 | 73 | No jobs returned: 76 |

## Confirmed code fixes

| Problem | Change and verification |
|---|---|
| All 149 Indeed company searches raised an unexpected proxy keyword exception while the workflow stayed green | Use the installed JobSpy signature, its proxies parameter, and supported description option. Live local and GitHub samples now return descriptions. |
| Descriptions and other details were dropped before saving | Preserve description, experience, salary when supplied, employment metadata and the source posting date. Upgrade existing duplicate jobs with newly available details. Persistence tests cover new and seen jobs. |
| Google search provided only job-card summaries | Read minimum qualifications, preferred qualifications, job overview and responsibilities from its individual job page. |
| Microsoft search returned no jobs with the old parameter combination | Remove unnecessary empty query/sort parameters and fetch the official position-details response. Confirmed on Windows and GitHub. |
| Hexaware requested the Oracle employer tenant | Use the verified Hexaware Oracle Cloud tenant. New samples come from Hexaware rather than Oracle. Existing mislabeled historical records were not bulk deleted. |
| Oracle-hosted company descriptions were missing | Read the per-requisition detail response and preserve the description and qualifications. Covers sampled JPMorgan, Oracle, Honeywell, BNY, American Express, Nokia and Akamai postings when accessible. |
| Siemens detail page uses HTML without JobPosting JSON-LD | Extract the full Siemens description article and its explicitly labeled posted date. |
| Bosch and Eurofins search results omitted full descriptions | Fetch the public SmartRecruiters posting detail and its description/qualification sections. |
| Workday links from the Markdown scraper omitted the career site segment | Generate the individual job URL with the site segment, then use its CXS detail endpoint when accessible. |
| Generic APIs counted results without returning job records | Traverse nested posting records and return actual linked jobs; an API count alone no longer indicates retrievable jobs. |
| Wipro Markdown pagination could repeat/consume the probe budget and omitted job links | Deduplicate page IDs, stop repeated pages, return job links and locations, and cap the sample run. The sampled Wipro description remains unavailable. |
| OpenAI navigation text was interpreted as a job | Reject navigation links and use the official public Ashby job board. Foreign US Remote listings are excluded by the corrected location rule. |
| Remote or substring matches could turn foreign locations into India results | Use city/country word matches; tests exclude US - Remote, Indiana, Indianapolis and Indonesia. |

## Original workflow runs

- [Big Company Indeed production run](https://github.com/ragesh28/ALL_CAREER/actions/runs/45171002507): completed with the original broken proxy argument. A green workflow was not proof of company scraping success.
- [44-company production run](https://github.com/ragesh28/ALL_CAREER/actions/runs/45171009740): completed; reported 29 working / 15 failed and 4,053 raw jobs. Full pagination and bounded sample counts are different measurements.
- [51-company original production run](https://github.com/ragesh28/ALL_CAREER/actions/runs/45171015645): manually stopped after reaching entry 14. It was superseded by the completed per-company audits. It must not be described as a completed full scrape.
- [Initial full 244-entry sample audit](https://github.com/ragesh28/ALL_CAREER/actions/runs/45171703993).
- [Final direct-source audit](https://github.com/ragesh28/ALL_CAREER/actions/runs/45175470481).
- [Final API/browser audit](https://github.com/ragesh28/ALL_CAREER/actions/runs/45175477130).

## Every company: direct

| Company | Local sample result | GitHub sample result | Description | Experience | Source date | Salary | Sample job |
|---|---|---|---|---|---|---|---|
| Google | Sample returned | Sample returned | Recovered (4,995 chars) | Not extracted | Not extracted | Not extracted | [Senior Software Engineer, Search AI Infra](https://www.google.com/about/careers/applications/jobs/results/102559582366114502-senior-software-engineer-search-ai-infra) |
| Microsoft | Sample returned | Sample returned | Recovered (17,475 chars) | 0 - 2 years experience | 2026-11-16 | Not extracted | [Product Management](https://apply.careers.microsoft.com/careers/job/1970393557074091) |
| PayPal | Sample returned | Sample returned | Recovered (17,215 chars) | 10-12 years of experience | 2026-10-30T00:00:00 | Not extracted | [Chief Information Security Officer (CISO)](https://paypal.eightfold.ai/careers?pid=274923174563) |
| Amazon | Sample returned | Sample returned | Inline (1,388 chars) | Not extracted | November  9, 2026 | Not extracted | [Sr Vendor Ops Associate, AWIPL](https://www.amazon.jobs/en/jobs/10599645/sr-vendor-ops-associate-awipl) |
| TCS (Prime/Digital) | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Infosys (SP/DSE) | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Chargebee | Sample returned | Sample returned | Inline (2,945 chars) | 5-10 years of experience | 2026-11-23 | Not extracted | [Senior Solution Engineer - Support](https://www.linkedin.com/jobs/view/4493740644) |
| Swiggy | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Uber | Sample returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Salesforce | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Rocketlane | Sample returned | Sample returned | Missing | Not extracted | Not extracted | Not extracted | [Technical Account Manager - US TimeZone](https://careers.kula.ai/rocketlane) |
| Walmart Global Tech | Sample returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| JPMorgan Chase | Sample returned | Sample returned | Recovered (3,226 chars) | Not extracted | 2026-11-23 | Not extracted | [Software Engineer II - Java / TypeScript](https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210743912) |
| Wells Fargo | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Citi | No India sample in response | Only invalid/navigation links | Missing | Not extracted | Not extracted | Not extracted | No sample |
| LatentView Analytics | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Tiger Analytics | Sample returned | Sample returned | Recovered (2,702 chars) | Not extracted | 2022-02-01T19:15:39+00:00 | Not extracted | [People Development Specialist](https://tiger-analytics.sensehq.com/careers/jobs/56924) |
| Comcast | Sample returned | Sample returned | Recovered (7,471 chars) | Not extracted | 2026-11-10 | Not extracted | [Supply Chain Data Scientist 3](https://jobs.comcast.com/job/chennai/supply-chain-data-scientist-3/45483/99024766688) |
| Turing | Sample returned | Sample returned | Missing | Not extracted | Not extracted | Not extracted | [Forward-Deployed AI Engineer](https://careers.turing.com/jobs/6192725004) |
| Accenture | Sample returned | Sample returned | Inline (5,625 chars) | Not extracted | Posted 3 d | Not extracted | [O2C Offering Advisor](https://www.accenture.com/in-en/careers/jobdetails?id=R00352050_en) |
| Wipro | Sample returned | Sample returned | Missing | Not extracted | Not extracted | Not extracted | [Configurator - L4](https://careers.wipro.com/jobs/40585) |
| LTIMindtree | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Capgemini | No jobs returned | Sample returned | Missing | Not extracted | Not extracted | Not extracted | [SAP MM Functional Consultant](https://careers.capgemini.com/job/Mumbai-%28ex-Bombay%29-Senior-Software-Engineer/1387990233/?feedId=388633&utm_source=CareerSite&tcsource=apply) |
| Virtusa | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| HCLTech | Sample returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Hexaware | Sample returned | Sample returned | Recovered (1,344 chars) | Not extracted | 2026-11-23 | Not extracted | [ES Workday Architect](https://fa-etqo-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/689203) |
| Athenahealth | Sample returned | Sample returned | Missing | Not extracted | Not extracted | Not extracted | [Senior Member of Technical Staff   SMTS](https://careers.athenahealth.com) |
| Ramco Systems | No jobs returned | Sample returned | Missing | Not extracted | Not extracted | Not extracted | [Regional Sales (Hunting Role) - India](https://www.ramco.com/careers/jobs-by-locations/sa) |
| Intellect Design | No jobs returned | Sample returned | Missing | Not extracted | Not extracted | Not extracted | [{'CAND_GENR_btnApl': 'APPLY~E', 'CAND_GENR_btnLogi](https://cloud.myadrenalin.com/CandidateMAX/#/?CompanyID=INTELLECT) |
| Sify Tech | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Tata Elxsi | No jobs returned | Sample returned | Missing | Not extracted | 2026-11-03 | Not extracted | [Assistant Manager - Digital Fabric](https://www.linkedin.com/jobs/view/4486306289) |
| PhonePe | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Razorpay | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Postman | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Zeta Suite | Sample returned | Sample returned | Inline (3,686 chars) | Not extracted | Not extracted | Not extracted | [Associate Director - Legal](https://jobs.lever.co/zeta/892ad297-ed0e-4f9c-98b8-fd30358a5517) |
| Meesho | Sample returned | Sample returned | Inline (2,058 chars) | Not extracted | Not extracted | Not extracted | [AM/ Manager - Risk & Decision Science](https://jobs.lever.co/meesho/7d9af9b5-c1c7-48ec-bbb5-9b25e49f6596) |
| Groww | Sample returned | Sample returned | Inline (4,076 chars) | Not extracted | 2026-09-14 | Not extracted | [Assistant Manager - Internal Audit](https://job-boards.eu.greenhouse.io/groww/jobs/4970739101) |
| Shell | Sample returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Oracle | Sample returned | Sample returned | Recovered (338 chars) | Not extracted | 2026-11-23 | Not extracted | [Sales Pipeline](https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/313133) |
| Cure.fit | No India sample in response | Only invalid/navigation links | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Goldman Sachs | Sample returned | Sample returned | Missing | Not extracted | Not extracted | Not extracted | [Asset & Wealth Management-Private Bank Underwriting- Associate- B…](https://higher.gs.com/roles/187271_GS_MID_CAREER) |
| Intuit | Sample returned | Sample returned | Recovered (5,921 chars) | Not extracted | 2026-08-28 | Not extracted | [Staff Software Engineer - Full Stack Finance Bangalore, India](https://jobs.intuit.com/job/bengaluru/staff-software-engineer-full-stack-finance/27595/99834291664) |
| Target | Sample returned | Sample returned | Recovered (6,336 chars) | Not extracted | 2026-11-20 | Not extracted | [Lead Fullstack Engineer- Advanced AI job id: R0000441608 job fami…](https://indiajobs.target.com/job/bengaluru/lead-fullstack-engineer-advanced-ai/34386/99859092176) |
| SAP Labs | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |

### Remaining gaps in this engine

- **TCS (Prime/Digital)** — No jobs returned. Observed: www.linkedin.com: HTTP 200; www.linkedin.com: HTTP 429.
- **Infosys (SP/DSE)** — No jobs returned.
- **Swiggy** — No jobs returned.
- **Uber** — No jobs returned. Observed: www.linkedin.com: HTTP 429; www.linkedin.com: HTTP 200.
- **Salesforce** — No jobs returned. Observed: careers.salesforce.com: HTTP 200.
- **Rocketlane** — Job returned; description missing. Observed: careers.kula.ai: HTTP 200.
- **Walmart Global Tech** — No jobs returned. Observed: www.linkedin.com: HTTP 429.
- **Wells Fargo** — No jobs returned. Observed: www.linkedin.com: HTTP 429; www.linkedin.com: HTTP 200.
- **Citi** — Only invalid/navigation links. Observed: jobs.citi.com: HTTP 200.
- **LatentView Analytics** — No jobs returned. Observed: www.linkedin.com: HTTP 429.
- **Turing** — Job returned; description missing. Observed: careers.turing.com: HTTP 200; careers.turing.com: HTTP 404.
- **Wipro** — Job returned; description missing. Observed: careers.wipro.com: HTTP 200.
- **LTIMindtree** — No jobs returned. Observed: careers.ltimindtree.com: ConnectionError.
- **Capgemini** — Job returned; description missing. Observed: careers.capgemini.com: HTTP 200.
- **Virtusa** — No jobs returned. Observed: prod.agenticweb-marketing.com: HTTP 200.
- **HCLTech** — No jobs returned. Observed: www.linkedin.com: HTTP 429.
- **Athenahealth** — Job returned; description missing. Observed: careers.athenahealth.com: HTTP 200.
- **Ramco Systems** — Job returned; description missing. Observed: www.ramco.com: HTTP 200.
- **Intellect Design** — Job returned; description missing. Observed: cloud.myadrenalin.com: HTTP 200.
- **Sify Tech** — No jobs returned. Observed: www.linkedin.com: HTTP 429.
- **Tata Elxsi** — Job returned; description missing. Observed: www.linkedin.com: HTTP 429; www.linkedin.com: HTTP 200.
- **PhonePe** — No jobs returned. Observed: boards-api.greenhouse.io: HTTP 404.
- **Razorpay** — No jobs returned.
- **Postman** — No jobs returned. Observed: boards-api.greenhouse.io: HTTP 404.
- **Shell** — No jobs returned. Observed: shell.wd3.myworkdayjobs.com: HTTP 429.
- **Cure.fit** — Only invalid/navigation links. Observed: careers.cult.fit: HTTP 200; public.zwayam.com: HTTP 200.
- **Goldman Sachs** — Job returned; description missing. Observed: api-higher.gs.com: HTTP 200; higher.gs.com: HTTP 200.
- **SAP Labs** — No jobs returned. Observed: jobs.sap.com: HTTP 403.

## Every company: md

| Company | Local sample result | GitHub sample result | Description | Experience | Source date | Salary | Sample job |
|---|---|---|---|---|---|---|---|
| Qualcomm | No India sample in response | Only invalid/navigation links | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Ericsson | No India sample in response | Only invalid/navigation links | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Siemens | Sample returned | Sample returned | Recovered (4,876 chars) | Not extracted | 23-Nov-2026 | Not extracted | [Technical Bid Manager](https://jobs.siemens.com/en_US/externaljobs/JobDetail/530419) |
| Amadeus | No jobs returned | Sample returned | Recovered (4,474 chars) | Not extracted | Not extracted | Not extracted | [Senior Manager, Information Security](https://amadeus.wd502.myworkdayjobs.com/en-US/jobs/job/Bangalore/Senior-Manager--Information-Security_R32625-1) |
| GE Healthcare | No India sample in response | Only invalid/navigation links | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Bank of America | Sample returned | Sample returned | Recovered (5,608 chars) | Not extracted | 11/20/2026 | Not extracted | [Analyst - GBS](https://careers.bankofamerica.com/en-us/job-detail/26029146/analyst-gbs-mumbai-india) |
| Honeywell | Sample returned | Sample returned | Recovered (1,245 chars) | Not extracted | Not extracted | Not extracted | [Electrician - Level 1](https://ibqbjb.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/155320) |
| Bosch | Sample returned | Sample returned | Recovered (1,714 chars) | Not extracted | Not extracted | Not extracted | [Mechanical Integrator - Mechatronics](https://jobs.smartrecruiters.com/BoschGroup/744000163209628) |
| Maersk | No India sample in response | Only invalid/navigation links | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Wipro | Sample returned | Sample returned | Missing | Not extracted | Not extracted | Not extracted | [Configurator - L4](https://careers.wipro.com/jobs/40585) |
| Arcesium | Sample returned | Sample returned | Inline (5,218 chars) | 3-5 years of experience | Not extracted | Not extracted | [Analyst - India Payroll, Finance](https://job-boards.greenhouse.io/arcesiumllc/jobs/5259908007) |
| Juniper Networks / HPE | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Mastercard | Request/parser error | Sample returned | Inline (5,811 chars) | Not extracted | 2026-11-21 | Not extracted | [Director, Technical Program Management](https://www.linkedin.com/jobs/view/4483925552) |
| Barclays | No India sample in response | Only invalid/navigation links | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Fidelity Investments | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| BNY | Sample returned | Sample returned | Recovered (4,305 chars) | Not extracted | Not extracted | Not extracted | [Vice President, Full-Stack Engineer](https://eofe.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/83840) |
| American Express | Sample returned | Sample returned | Recovered (1,831 chars) | Not extracted | Not extracted | Not extracted | [Team Leader-Operations](https://egug.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/26014466) |
| Visa | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Fractal Analytics | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Broadcom | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Akamai | Sample returned | Sample returned | Recovered (3,455 chars) | Not extracted | Not extracted | Not extracted | [Senior II Software Engineer](https://fa-extu-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/4435) |
| ABB | No jobs returned | Sample returned | Recovered (3,416 chars) | Not extracted | 2026-11-20 | Not extracted | [Team Leader - MOSE - Hyderabad/Raipur](https://www.linkedin.com/jobs/view/4492948762) |
| Publicis Sapient | No jobs returned | Sample returned | Recovered (203 chars) | Not extracted | 2025-11-26T16:12:00Z | Not extracted | [Sales/Business Development / Full-timeSr. Client Partner, Financi…](https://careers.publicissapient.com/job-details/2025-130981-sr--client-partner--financial-services-new-york?trid=fabf8f5c-18fc-43ce-ba06-84dac34b9203) |
| IBM | Sample returned | Sample returned | Inline (3,259 chars) | Not extracted | 2026-11-20 | Not extracted | [Applied AI Specialist-Cloud FullStack](https://www.linkedin.com/jobs/view/4491911556) |
| ZS Associates | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Continental | No jobs returned | Sample returned | Inline (6,443 chars) | Not extracted | 2026-11-23 | Not extracted | [IT Engineer data Lakehouse](https://www.linkedin.com/jobs/view/4493758154) |
| Nokia | Sample returned | Sample returned | Recovered (1,648 chars) | Not extracted | Not extracted | Not extracted | [VAPT & Red Teaming Analyst](https://fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/39387) |
| Cognizant | Sample returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| KPIT Technologies | No India sample in response | Only invalid/navigation links | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Comcast | Sample returned | Sample returned | Recovered (7,471 chars) | Not extracted | 2026-11-10 | Not extracted | [Supply Chain Data Scientist 3](https://jobs.comcast.com/job/chennai/supply-chain-data-scientist-3/45483/99024766688) |
| Grundfos | Sample returned | Sample returned | Inline (3,688 chars) | Not extracted | 2026-11-20 | Not extracted | [Supply Chain Master Data Manager](https://www.linkedin.com/jobs/view/4492912696) |
| Tally Solutions | Sample returned | Sample returned | Recovered (2,370 chars) | Not extracted | 2026-11-11 | Not extracted | [Sales Planning Manager](https://www.linkedin.com/jobs/view/4488653891) |
| Subex | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Brillio | No jobs returned | Sample returned | Missing | Not extracted | 2026-11-18 | Not extracted | [Project Manager - R01573863](https://www.linkedin.com/jobs/view/4490872937) |
| Eurofins IT | Sample returned | Sample returned | Recovered (3,667 chars) | Not extracted | Not extracted | Not extracted | [QA Automation Tester (Selenium/Playwright)](https://jobs.smartrecruiters.com/Eurofins/744000162729145-qa-automation-tester-selenium-playwright-) |
| Sabre | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Alstom | Sample returned | Sample returned | Recovered (3,386 chars) | Not extracted | Not extracted | Not extracted | [GCC SC Material Planner](https://jobsearch.alstom.com/job/Bangalore-GCC-SC-Material-Planner/1396879333/) |
| Danfoss | Sample returned | Sample returned | Missing | Not extracted | 2026-11-19 | Not extracted | [Product Marketing Manager, APR/TMA](https://www.linkedin.com/jobs/view/4492432145) |
| HackerRank | Sample returned | Sample returned | Missing | Not extracted | Not extracted | Not extracted | [Senior Backend Engineer](https://job-boards.greenhouse.io/hackerrank/jobs/7693789) |
| Crossover | No India sample in response | Only invalid/navigation links | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Sarvam AI | Sample returned | Sample returned | Recovered (3,919 chars) | Not extracted | 2026-04-17 | Not extracted | [Data Scientist - Evaluations, Chanakya](https://www.sarvam.ai/careers/jobs/7c42207a-bb56-413c-839f-9ad692df840e) |
| Cohesity | No jobs returned | Sample returned | Missing | Not extracted | 2026-11-19 | Not extracted | [Director, Solution Test Engineering](https://www.linkedin.com/jobs/view/4484488349) |
| Nutanix | Sample returned | Sample returned | Inline (5,530 chars) | Not extracted | 2026-11-21 | Not extracted | [Manager,Partner Help](https://www.linkedin.com/jobs/view/4492889143) |
| BrowserStack | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Anthropic | Sample returned | Sample returned | Inline (8,196 chars) | Not extracted | Not extracted | Not extracted | [Applied AI Architect](https://job-boards.greenhouse.io/anthropic/jobs/5424310008) |
| Amazon AI | Sample returned | Sample returned | Inline (5,280 chars) | Not extracted | Not extracted | Not extracted | [Software Development Engineer III, PaySec, StoreSec](https://www.amazon.jobs/en/jobs/10610387/software-development-engineer-iii-paysec-storesec) |
| Societe Generale | Sample returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| NatWest Group | Sample returned | Sample returned | Inline (2,591 chars) | Not extracted | 2026-11-23 | Not extracted | [Java Engineer, AVP](https://www.linkedin.com/jobs/view/4493629711) |
| ITC Infotech | No jobs returned | Sample returned | Inline (990 chars) | Not extracted | 2026-11-21 | Not extracted | [Salesforce Developer - LifeScience / Health Cloud](https://www.linkedin.com/jobs/view/4492889660) |
| OpenAI | Sample returned | Sample returned | Inline (6,267 chars) | Not extracted | 2026-09-10T06:21:47.936+00:00 | Not extracted | [Account Director, Digital Natives](https://jobs.ashbyhq.com/openai/d085d2ec-0256-4ecf-b493-81ea34942e51) |
| Meta | Sample returned | Sample returned | Inline (4,659 chars) | Not extracted | 2026-11-18 | Not extracted | [ASIC Engineer, Physical Design CAD](https://www.linkedin.com/jobs/view/4482295878) |

### Remaining gaps in this engine

- **Qualcomm** — Only invalid/navigation links. Observed: careers.qualcomm.com: HTTP 200; careers.qualcomm.com: HTTP 429.
- **Ericsson** — Only invalid/navigation links. Observed: jobs.ericsson.com: HTTP 200.
- **GE Healthcare** — Only invalid/navigation links. Observed: careers.gehealthcare.com: HTTP 200.
- **Maersk** — Only invalid/navigation links. Observed: www.maersk.com: ReadTimeout; api.maersk.com: HTTP 200.
- **Wipro** — Job returned; description missing. Observed: careers.wipro.com: HTTP 200.
- **Juniper Networks / HPE** — No jobs returned. Observed: www.linkedin.com: HTTP 200; www.linkedin.com: HTTP 429. Error: JobSpy returned 0 jobs.
- **Barclays** — Only invalid/navigation links. Observed: search.jobs.barclays: HTTP 200.
- **Fidelity Investments** — No jobs returned. Observed: jobs.fidelity.com: HTTP 403.
- **Visa** — No jobs returned. Observed: visa.wd5.myworkdayjobs.com: HTTP 429.
- **Fractal Analytics** — No jobs returned. Observed: fractal.wd1.myworkdayjobs.com: HTTP 429.
- **Broadcom** — No jobs returned. Observed: broadcom.wd1.myworkdayjobs.com: HTTP 429.
- **ZS Associates** — No jobs returned. Observed: www.linkedin.com: HTTP 429. Error: JobSpy returned 0 jobs.
- **Cognizant** — No jobs returned. Observed: www.linkedin.com: HTTP 429. Error: JobSpy returned 0 jobs.
- **KPIT Technologies** — Only invalid/navigation links. Observed: www.kpit.com: HTTP 200.
- **Subex** — No jobs returned. Observed: subex.darwinbox.in: HTTP 403.
- **Brillio** — Job returned; description missing. Observed: www.linkedin.com: HTTP 200; www.linkedin.com: HTTP 429.
- **Sabre** — No jobs returned. Observed: sabre.wd1.myworkdayjobs.com: HTTP 429.
- **Danfoss** — Job returned; description missing. Observed: jobs.danfoss.com: HTTP 200; www.linkedin.com: HTTP 200; www.linkedin.com: HTTP 429.
- **HackerRank** — Job returned; description missing. Observed: boards-api.greenhouse.io: HTTP 200; job-boards.greenhouse.io: HTTP 200.
- **Crossover** — Only invalid/navigation links. Observed: profile-api.crossover.com: HTTP 200.
- **Cohesity** — Job returned; description missing. Observed: www.linkedin.com: HTTP 200; www.linkedin.com: HTTP 429.
- **BrowserStack** — No jobs returned. Observed: browserstack.wd3.myworkdayjobs.com: HTTP 429.
- **Societe Generale** — No jobs returned. Observed: www.linkedin.com: HTTP 429.

## Every company: indeed

| Company | Local sample result | GitHub sample result | Description | Experience | Source date | Salary | Sample job |
|---|---|---|---|---|---|---|---|
| Google | Sample returned | Sample returned | Inline (3,082 chars) | Not extracted | 2026-11-23 | Not extracted | [RTL Design Engineer, Silicon Engineering](https://careers.google.com/jobs/results/124960405205197510-rtl-design-engineer/) |
| Microsoft | Sample returned | Sample returned | Inline (5,000 chars) | Not extracted | 2026-11-21 | Not extracted | [Data Center Technician](https://apply.careers.microsoft.com/careers/job/1970393557075208?utm_source=indeed&domain=microsoft.com) |
| Amazon | Sample returned | Sample returned | Inline (6,407 chars) | Not extracted | 2026-11-20 | Not extracted | [Inv Specialist, IN, Worlwide Operations Investigations](https://www.amazon.jobs/jobs/10610415/inv-specialist-in-worlwide-operations-investigations-?cmpid=DA_INAD200785B) |
| Apple | Sample returned | Sample returned | Inline (2,277 chars) | 5–7 years of experience | 2026-11-22 | Not extracted | [Audio Software Development Engineer — Apple Products](https://jsv3.recruitics.com/redirect?rx_cid=3427&rx_jobId=200696416-0321-en-US&rx_url=https%3A%2F%2Fjobs.apple.com%2Fen-us%2Fdetails%2F200696416-0321%3Fboard_id%3DJB001%26rx_a%3D0%26rx_c%3D%26rx_ch%3Djobp4p%26rx_group%3D122365%26rx_id%3Ded3391b8-e670-11f1-832e-3f6bfc4d2d93%26rx_job%3D200696416-0321-en-US%26rx_medium%3Dcpc%26rx_product%3Dprogrammatic-ppc%252Ccore%26rx_r%3Dnone%26rx_source%3Dindeed%26rx_ts%3D20261123T120408Z%26rx_vp%3Dcpc) |
| Meta | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Netflix | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Adobe | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Salesforce | Sample returned | Sample returned | Inline (5,184 chars) | 4-5 years of experience | 2026-11-23 | Not extracted | [Software Engineering MTS](https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site/job/India---Hyderabad/Software-Engineering-MTS_JR367568) |
| Oracle | Sample returned | Sample returned | Inline (4,506 chars) | Not extracted | 2026-11-21 | Not extracted | [Platform Software Engineer](https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/351029) |
| SAP | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| IBM | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Intel | Sample returned | Sample returned | Inline (5,863 chars) | Not extracted | 2026-11-23 | Not extracted | [IP Design Verification Engineer](https://intel.wd1.myworkdayjobs.com/en-US/External/job/India-Bangalore/IP-Design-Verification-Engineer_JR0289542) |
| Cisco | Sample returned | Sample returned | Inline (4,938 chars) | Not extracted | 2026-11-21 | Not extracted | [Software Engineering Technical Leader](https://careers.cisco.com/global/en/job/2031192) |
| Qualcomm | Sample returned | Sample returned | Inline (5,388 chars) | 8- 12 years of experience | 2026-11-20 | Not extracted | [Staff System Modelling Engineer](https://app.eightfold.ai/careers/job/446719704937?domain=qualcomm.com) |
| NVIDIA | Sample returned | Sample returned | Inline (3,234 chars) | Not extracted | 2026-11-21 | Not extracted | [Senior Verification Engineer](https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/India-Bengaluru/Senior-Verification-Engineer_JR2030308) |
| Samsung | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Sony | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Dell | Sample returned | Sample returned | Inline (6,174 chars) | Not extracted | 2026-11-23 | Not extracted | [Principal Systems Development Engineer](https://enterpriseplatform.dell.com:443/hcmUI/CandidateExperience/en/job/301949) |
| HP | Sample returned | Sample returned | Inline (190 chars) | Not extracted | 2026-11-22 | Not extracted | [Petrol Pump Attendant](https://in.indeed.com/viewjob?jk=1d6ae1c7046618df) |
| Lenovo | Sample returned | Sample returned | Inline (13,832 chars) | 7–12 years of relevant experience | 2026-11-23 | Not extracted | [Advisory Solution Architect/FDE](https://jobs.lenovo.com/en_US/careers/JobDetail/Advisory-Solution-Architect-FDE/84210) |
| Accenture | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| TCS | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Infosys | Sample returned | Sample returned | Inline (1,943 chars) | Not extracted | 2026-11-23 | Not extracted | [Associate Consultant](https://career.infosys.com/jobdesc?jobReferenceCode=PROGEN-EXTERNAL-256713&sourceId=44014) |
| Wipro | Sample returned | Sample returned | Inline (1,362 chars) | Not extracted | 2026-11-23 | Not extracted | [AI INTEGRATION ENGINEER L3](https://careers.wipro.com/job/AI-INTEGRATION-ENGINEER-L3/220371-en_US) |
| HCLTech | Sample returned | Sample returned | Inline (3,094 chars) | Not extracted | 2026-11-23 | Not extracted | [Test Specialist](https://career55.sapsf.eu/career?company=HCLPRD&career_ns=job_listing&career_job_req_id=196772&lang=en_US&jobPipeline=Indeed) |
| Cognizant | Sample returned | Sample returned | Inline (4,788 chars) | Not extracted | 2026-11-23 | Not extracted | [Architect](https://careers.cognizant.com/global-en/jobs/00070614982/architect/) |
| Capgemini | Sample returned | Sample returned | Inline (5,152 chars) | Not extracted | 2026-11-23 | Not extracted | [AI Platform Engineer](https://apply.workable.com/j/992CEE59ED) |
| LTIMindtree | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Tech Mahindra | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Persistent Systems | Sample returned | Sample returned | Inline (6,227 chars) | Not extracted | 2026-11-23 | Not extracted | [Manual QA Engineer](https://careers.persistent.com/jobview/programmer-qa-india-pune-2026111210351994) |
| Flipkart | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Swiggy | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Zomato | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Paytm | Sample returned | Sample returned | Inline (863 chars) | Not extracted | 2026-11-23 | Not extracted | [Team Lead](https://in.indeed.com/viewjob?jk=f0d8005d0e465d71) |
| PhonePe | Sample returned | Sample returned | Inline (5,493 chars) | Not extracted | 2026-11-23 | Not extracted | [Associate Manager, Compliance Testing & Monitoring (CTM)](https://jobs.smartrecruiters.com/PHONEPELIMITED/1000000000006563-associate-manager-compliance-testing-monitoring-ctm-) |
| Razorpay | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| CRED | Sample returned | Sample returned | Inline (3,555 chars) | 8–12 years of experience | 2026-11-20 | Not extracted | [business category lead – UPI + BBPS](https://jobs.lever.co/cred/78ee55e7-8b44-4ffc-a566-ab404eeac1ab) |
| Meesho | No jobs returned | Sample returned | Inline (7,125 chars) | Not extracted | 2026-11-23 | Not extracted | [Senior Manager HR - COE](https://jobs.lever.co/meesho/bae9f9ed-0f2f-4f7d-87d6-2d4e63092a6e) |
| Zerodha | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Groww | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Uber | Sample returned | Sample returned | Inline (5,434 chars) | Not extracted | 2026-11-23 | Not extracted | [Software Engineer II - Frontend (Security Team)](https://tnl2.jometer.com/v2/job?jz=5wqzs27d5a20ec660846ad4d741242ea49d4cOAAAKAAAAABQ&utm_medium=jobboard&utm_source=joveo_indeed_organic) |
| Ola | Sample returned | Sample returned | Inline (611 chars) | Not extracted | 2026-11-21 | Not extracted | [Car Sales Executive](https://in.indeed.com/viewjob?jk=3feda07ea07f82bf) |
| Myntra | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Nykaa | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| BigBasket | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| JPMorgan Chase | Sample returned | Sample returned | Inline (4,959 chars) | Not extracted | 2026-11-21 | Not extracted | [Fund Servicing Associate](https://JPMorganChase.contacthr.com/154304397) |
| Goldman Sachs | Sample returned | Sample returned | Inline (6,494 chars) | Not extracted | 2026-11-20 | Not extracted | [Tax Operations-Tax Information Reporting-Analyst-Bengaluru](https://higher.gs.com/roles/188595) |
| Morgan Stanley | Sample returned | Sample returned | Inline (9,687 chars) | Not extracted | 2026-11-20 | Not extracted | [Vice President - KYC Refresh – Core Services](https://morganstanley.eightfold.ai/careers/job?domain=morganstanley.com&pid=549801221642) |
| Bank of America | Sample returned | Sample returned | Inline (10,119 chars) | Not extracted | 2026-11-22 | Not extracted | [Info Security Controls Specialist II A](https://careers.bankofamerica.com/en-us/job-detail/26040517/info-security-controls-specialist-ii-a-multiple-locations) |
| Citibank | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Wells Fargo | Sample returned | Sample returned | Inline (6,061 chars) | Not extracted | 2026-11-23 | Not extracted | [Securities Operations Associate](https://wd1.myworkdaysite.com/recruiting/wf/WellsFargoJobs/job/Bengaluru-India/Securities-Operations-Associate_R-574368) |
| Barclays | Sample returned | Sample returned | Inline (5,059 chars) | Not extracted | 2026-11-20 | Not extracted | [Remediation KYC Analyst](https://search.jobs.barclays/job/chennai/remediation-kyc-analyst/13015/103565438320) |
| HSBC | Sample returned | Sample returned | Inline (14,886 chars) | Not extracted | 2026-11-23 | Not extracted | [AVP Operations](https://portal.careers.hsbc.com/careers/job/563774612676847) |
| Deutsche Bank | Sample returned | Sample returned | Inline (6,855 chars) | Not extracted | 2026-11-20 | Not extracted | [Client Service Analyst, AS](https://db.wd3.myworkdayjobs.com/en-US/DBWebsite/job/do-not-use-Mumbai-Nirlon-Knowledge-Pk-B1/Client-Service-Analyst--AS_R0453315) |
| Standard Chartered | Sample returned | Sample returned | Inline (6,072 chars) | Not extracted | 2026-11-23 | Not extracted | [Relationship Manager Employee Banking](https://jobs.standardchartered.com/job/Relationship-Manager-Employee-Banking/65672-en_GB) |
| Deloitte | Sample returned | Sample returned | Inline (1,283 chars) | Not extracted | 2026-11-23 | Not extracted | [Consultant / SAP MM / Hyderabad / SAP / DSA Emerging](https://southasiacareers.deloitte.com/job/Hyderabad-Consultant-SAP-MM-Hyderabad-SAP-DSA-Emerging/61752344/) |
| PwC | Sample returned | Sample returned | Inline (3,221 chars) | Not extracted | 2026-11-20 | Not extracted | [Audit and Assurance - Internal Audit - Specialist 2- CS - G](https://pwc.wd3.myworkdayjobs.com/en-US/Global_Experienced_Careers/job/Hyderabad---Salarpuria/Audit-and-Assurance---Internal-Audit---Specialist--2--CS---G_DB_010202-1) |
| EY | Sample returned | Sample returned | Inline (4,622 chars) | 0 – 2 years of experience | 2026-11-21 | Not extracted | [IDT - VAT-GST Compliance - TFO And Multi country - Staff](https://careers.ey.com/ey/job/Bengaluru-IDT-VAT-GST-Compliance-TFO-And-Multi-country-Staff-KA-560016/1459490233/) |
| KPMG | Sample returned | Sample returned | Inline (2,885 chars) | Not extracted | 2026-11-23 | Not extracted | [Early Careers Coordinator - Fixed Term](https://jobs.lever.co/kpmgnz/d91c36f2-2b06-4b1f-802b-7dfac3c7a3a7) |
| McKinsey | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Boston Consulting Group | Sample returned | Sample returned | Inline (3,590 chars) | Not extracted | 2026-11-20 | Not extracted | [India Lead Analyst - Benefits](https://jsv3.recruitics.com/redirect?rx_cid=3493&rx_jobId=60390_1001&rx_url=https%3A%2F%2Fcareers.bcg.com%2Fglobal%2Fen%2Fjob%2FBCG1US60390EXTERNALENGLOBAL%2FIndia-Lead-Analyst-Benefits%3Frx_a%3D0%26rx_c%3D%26rx_ch%3Djobp4p%26rx_group%3D129838%26rx_id%3Dbeffedcc-e4ff-11f1-87cc-49b2304b8c68%26rx_job%3D60390_1001%26rx_medium%3Dcpc%26rx_product%3Dprogrammatic-ppc%252Ccore%26rx_r%3Dnone%26rx_source%3Dindeed%26rx_ts%3D20261123T120410Z%26rx_vp%3Dcpc%26utm_campaign%3Dglobal_other-jobs%26utm_medium%3Dglobal_organic%26utm_source%3Djobboard_indeed) |
| Bain & Company | Sample returned | Sample returned | Inline (2,530 chars) | Not extracted | 2026-11-23 | Not extracted | [IIM Indore - Associate - Batch of 2027](https://www.bain.com/careers/find-a-role/position/?jobid=112636) |
| Mu Sigma | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Fractal Analytics | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Tiger Analytics | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Walmart | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Target | Sample returned | Sample returned | Inline (10,679 chars) | Not extracted | 2026-11-21 | Not extracted | [Sr Data Scientist- MarTech](https://corporate.target.com/job/id/R0000442385) |
| Visa | Sample returned | Sample returned | Inline (1,996 chars) | Not extracted | 2026-11-21 | Not extracted | [Digital Marketing Specialist](https://in.indeed.com/viewjob?jk=9eee22e173095648) |
| Mastercard | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| American Express | Sample returned | Sample returned | Inline (3,088 chars) | Not extracted | 2026-11-23 | Not extracted | [Apprentice](https://egug.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/requisitions/preview/26016839) |
| PayPal | Sample returned | Sample returned | Inline (6,744 chars) | Not extracted | 2026-11-23 | Not extracted | [Sr Analyst, Revenue Operations](https://paypal.eightfold.ai/careers/job/274923489496) |
| Stripe | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Intuit | Sample returned | Sample returned | Inline (7,593 chars) | Not extracted | 2026-11-21 | Not extracted | [Senior Staff Software Engineer](https://dsp.prng.co/KZtMNDb) |
| ServiceNow | Sample returned | Sample returned | Inline (4,886 chars) | Not extracted | 2026-11-23 | Not extracted | [Software Engineer (Go & Kubernetes)](https://jobs.smartrecruiters.com/ServiceNow/744000163147028-software-engineer-go-kubernetes-) |
| Workday | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Snowflake | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Databricks | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Cloudera | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Confluent | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| MongoDB | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Atlassian | Sample returned | Sample returned | Inline (5,547 chars) | Not extracted | 2026-11-21 | Not extracted | [Senior Forward Deployed Engineer, AI](https://globalcareers-atlassian.icims.com/jobs/27430/job?utm_source=indeed_integration&iis=Job%20Board&iisn=Indeed&indeed-apply-token=73a2d2b2a8d6d5c0a62696875eaebd669103652d3f0c2cd5445d3e66b1592b0f) |
| Freshworks | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Zoho | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Postman | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| BrowserStack | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Thoughtworks | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Hasura | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Chargebee | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| InMobi | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Honeywell | Sample returned | Sample returned | Inline (2,786 chars) | Not extracted | 2026-11-23 | Not extracted | [Advanced Cyber Sec Archt/Engr](https://ibqbjb.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/requisitions/preview/161815) |
| Bosch | Sample returned | Sample returned | Inline (2,515 chars) | Not extracted | 2026-11-23 | Not extracted | [Senior Project Manager_EBH](https://jobs.smartrecruiters.com/BoschGroup/744000163148738-senior-project-manager-ebh) |
| Siemens | Sample returned | Sample returned | Inline (1,704 chars) | Not extracted | 2026-11-21 | Not extracted | [Associate Engineer](https://jobs.siemens.com/externaljobs/JobDetail/529771?source=Indeed) |
| ABB | Sample returned | Sample returned | Inline (4,976 chars) | 0-2 years of experience | 2026-11-23 | Not extracted | [Finance Analyst](https://abb.wd3.myworkdayjobs.com/External_Career_Page/job/Bangalore-Karnataka-India/Finance-Analyst_JR00053896) |
| Schneider Electric | Sample returned | Sample returned | Inline (5,518 chars) | Not extracted | 2026-11-21 | Not extracted | [Workforce Operations Deputy Manager](https://careers.se.com/jobs/143173/job?utm_source=indeed_integration&iis=Job%20Board&iisn=Indeed&indeed-apply-token=73a2d2b2a8d6d5c0a62696875eaebd669103652d3f0c2cd5445d3e66b1592b0f) |
| GE | Sample returned | Sample returned | Inline (3,511 chars) | 8–12 years of experience | 2026-11-20 | Not extracted | [Deputy Manager – Site Administration & Security](https://careers.geaerospace.com/global/en/job/R5043531/Deputy-Manager-Site-Administration-Security?utm_source=indeed&utm_medium=phenom-feeds) |
| Philips | Sample returned | Sample returned | Inline (5,681 chars) | 6 - 8 years of experience | 2026-11-23 | Not extracted | [CH and Vigilance Reporting Specialist](https://philips.wd3.myworkdayjobs.com/en-US/jobs-and-careers/job/Pune/CH-and-Vigilance-Reporting-Specialist_594806) |
| 3M | Sample returned | Sample returned | Inline (4,846 chars) | Not extracted | 2026-11-23 | Not extracted | [Area Pricing Specialist](https://3m.wd1.myworkdayjobs.com/en-US/Search/job/IN-Bangalore-Kar/Area-Pricing-Specialist_R01173541) |
| Johnson Controls | Sample returned | Sample returned | Inline (3,481 chars) | Not extracted | 2026-11-23 | Not extracted | [Program Manager](https://click.appcast.io/t/YMjylVz-1ASbrq6hTtU8xzoxGFdMiDPfdizIvAT9qCA=) |
| Emerson | Sample returned | Sample returned | Inline (3,453 chars) | Not extracted | 2026-11-23 | Not extracted | [Software Engineer - Digital Applications](https://hdjq.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/requisitions/preview/26014169?utm_medium=jobboard&utm_source=indeed) |
| Mercedes Benz | Sample returned | Sample returned | Inline (7,373 chars) | Not extracted | 2026-11-21 | Not extracted | [AI/ML Engineer](https://jobs.mercedes-benz.com/ai-ml-engineer-247842-MER0004AL6) |
| BMW | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Volkswagen | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Toyota | Sample returned | Sample returned | Inline (932 chars) | Not extracted | 2026-11-21 | Not extracted | [Service Trainer in Automobiles](https://in.indeed.com/viewjob?jk=c664170dba7861cf) |
| Ford | Sample returned | Sample returned | Inline (1,553 chars) | minimum of 1 years of experience | 2026-11-23 | Not extracted | [Automobile Mechanic](https://in.indeed.com/viewjob?jk=88d2b04a1703ea0e) |
| Continental | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Caterpillar | Sample returned | Sample returned | Inline (9,016 chars) | 10 to 15 years of relevant experience | 2026-11-23 | Not extracted | [Manager Accounting](https://careers.caterpillar.com/en/jobs/r0000406302/manager-accounting/) |
| John Deere | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Cummins | Sample returned | Sample returned | Inline (4,557 chars) | Not extracted | 2026-11-20 | Not extracted | [Product Design Technician - Level I](https://cummins.jobs/AE1DF3D659B741778E1434F856352DF2/job/) |
| Eaton | Sample returned | Sample returned | Inline (2,723 chars) | 5-7 years of experience | 2026-11-23 | Not extracted | [Associate Analyst](https://career41.sapsf.com/career?company=eatoncorpo&career_ns=job_listing&career_job_req_id=77979&lang=en_US&jobPipeline=Indeed) |
| Shell | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Schlumberger | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Baker Hughes | Sample returned | Sample returned | Inline (4,598 chars) | Not extracted | 2026-11-20 | Not extracted | [ARMO Tech - Electro Mech III](https://careers.bakerhughes.com/global/en/job/BAHUGLOBALR172468EXTERNALENGLOBAL/ARMO-Tech-Electro-Mech-III?utm_source=indeed&utm_medium=phenom-feeds) |
| Halliburton | Sample returned | Sample returned | Inline (5,118 chars) | Not extracted | 2026-11-20 | Not extracted | [Accountant- Record to Report (RTR)](https://careers.halliburton.com/job/bengaluru/accountant-record-to-report-rtr/543/103551530016) |
| TotalEnergies | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Ericsson | Sample returned | Sample returned | Inline (2,295 chars) | Not extracted | 2026-11-23 | Not extracted | [Engineer- IP](https://jobs.ericsson.com/careers/job/563121777633710?domain=ericsson.com) |
| Nokia | Sample returned | Sample returned | Inline (3,350 chars) | Not extracted | 2026-11-23 | Not extracted | [MW Integration & SW Upgrade Specialist](https://fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/requisitions/preview/41047) |
| Juniper Networks | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Broadcom | Sample returned | Sample returned | Inline (1,576 chars) | Not extracted | 2026-11-23 | Not extracted | [SoC RTL Design and Implementation Engineer](https://broadcom.wd1.myworkdayjobs.com/es/External_Career/job/IND-Bangalore-Electronic-City---S1/SoC-RTL-Design-and-Implementation-Engineer_R027845) |
| Marvell | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Nutanix | Sample returned | Sample returned | Inline (10,443 chars) | Not extracted | 2026-11-22 | Not extracted | [Sr Serviceability Engineer - Life Cycle Manager (LCM)](https://app.jobvite.com/CompanyJobs/Job.aspx?j=oHw6AfwD&s=Indeed) |
| Rubrik | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Cohesity | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| VMware | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Palo Alto Networks | Sample returned | Sample returned | Inline (5,700 chars) | Not extracted | 2026-11-20 | Not extracted | [Staff Engineer, DevOps - Prisma AIRS Gateway (NetSec)](https://jobs.paloaltonetworks.com/en/job/bengaluru/staff-engineer-devops-prisma-airs-gateway-netsec/47263/103549545088) |
| CrowdStrike | Sample returned | Sample returned | Inline (5,501 chars) | 3–5 years of experience | 2026-11-23 | Not extracted | [GBS Sr. Analyst 1, Sales Support](https://crowdstrike.wd5.myworkdayjobs.com/en-US/crowdstrikecareers/job/India---Pune/GBS-Sr-Analyst-1--Sales-Support_R30996) |
| Fortinet | No jobs returned | Sample returned | Inline (4,513 chars) | Not extracted | 2026-11-23 | Not extracted | [Named Account Manager - Emerging](https://edel.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_xx/requisitions/preview/24762) |
| Zscaler | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Splunk | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Elastic | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Twilio | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Datadog | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| New Relic | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| PagerDuty | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Okta | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| UiPath | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Automation Anywhere | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Blue Prism | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Celonis | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Appian | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Epic Games | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Unity | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| EA Sports | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Riot Games | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Ubisoft | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Spotify | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Twitter | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| LinkedIn | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Pinterest | No jobs returned | No jobs returned | Missing | Not extracted | Not extracted | Not extracted | No sample |
| Snap | Sample returned | Sample returned | Inline (1,827 chars) | Not extracted | 2026-11-20 | Not extracted | [Photography Assistant](https://in.indeed.com/viewjob?jk=5dd60c1751f59db6) |

### Remaining gaps in this engine

- **Meta** — No jobs returned.
- **Netflix** — No jobs returned.
- **Adobe** — No jobs returned.
- **SAP** — No jobs returned.
- **IBM** — No jobs returned.
- **Samsung** — No jobs returned.
- **Sony** — No jobs returned.
- **Accenture** — No jobs returned.
- **TCS** — No jobs returned.
- **LTIMindtree** — No jobs returned.
- **Tech Mahindra** — No jobs returned.
- **Flipkart** — No jobs returned.
- **Swiggy** — No jobs returned.
- **Zomato** — No jobs returned.
- **Razorpay** — No jobs returned.
- **Zerodha** — No jobs returned.
- **Groww** — No jobs returned.
- **Myntra** — No jobs returned.
- **Nykaa** — No jobs returned.
- **BigBasket** — No jobs returned.
- **Citibank** — No jobs returned.
- **McKinsey** — No jobs returned.
- **Mu Sigma** — No jobs returned.
- **Fractal Analytics** — No jobs returned.
- **Tiger Analytics** — No jobs returned.
- **Walmart** — No jobs returned.
- **Mastercard** — No jobs returned.
- **Stripe** — No jobs returned.
- **Workday** — No jobs returned.
- **Snowflake** — No jobs returned.
- **Databricks** — No jobs returned.
- **Cloudera** — No jobs returned.
- **Confluent** — No jobs returned.
- **MongoDB** — No jobs returned.
- **Freshworks** — No jobs returned.
- **Zoho** — No jobs returned.
- **Postman** — No jobs returned.
- **BrowserStack** — No jobs returned.
- **Thoughtworks** — No jobs returned.
- **Hasura** — No jobs returned.
- **Chargebee** — No jobs returned.
- **InMobi** — No jobs returned.
- **BMW** — No jobs returned.
- **Volkswagen** — No jobs returned.
- **Continental** — No jobs returned.
- **John Deere** — No jobs returned.
- **Shell** — No jobs returned.
- **Schlumberger** — No jobs returned.
- **TotalEnergies** — No jobs returned.
- **Juniper Networks** — No jobs returned.
- **Marvell** — No jobs returned.
- **Rubrik** — No jobs returned.
- **Cohesity** — No jobs returned.
- **VMware** — No jobs returned.
- **Zscaler** — No jobs returned.
- **Splunk** — No jobs returned.
- **Elastic** — No jobs returned.
- **Twilio** — No jobs returned.
- **Datadog** — No jobs returned.
- **New Relic** — No jobs returned.
- **PagerDuty** — No jobs returned.
- **Okta** — No jobs returned.
- **UiPath** — No jobs returned.
- **Automation Anywhere** — No jobs returned.
- **Blue Prism** — No jobs returned.
- **Celonis** — No jobs returned.
- **Appian** — No jobs returned.
- **Epic Games** — No jobs returned.
- **Unity** — No jobs returned.
- **EA Sports** — No jobs returned.
- **Riot Games** — No jobs returned.
- **Ubisoft** — No jobs returned.
- **Spotify** — No jobs returned.
- **Twitter** — No jobs returned.
- **LinkedIn** — No jobs returned.
- **Pinterest** — No jobs returned.

## Saving behavior and operational limits

The existing static catalog remains the publishing path. These changes preserve more fields in scraper output and add bounded detail discovery; they do not run AI in visitors' browsers. The default detail-discovery budget is three additional posting pages per company per save batch, configurable with COMPANY_DETAIL_LIMIT, plus a 180-second aggregate discovery budget per process configurable with COMPANY_DETAIL_BUDGET_SECONDS. The budget bounds additional detail discovery time; inline descriptions are preserved after it is spent. Fields already present in API responses are preserved for every returned job. The audit uses one selected job per company and a 120-second process budget.

This report is a dated network snapshot, not an uptime guarantee. Blocked sources, access restrictions, changed ATS boards, and employers with no matching recent India results remain separate from code defects. Full job descriptions are present in downloaded audit artifacts where recovered.

## Repeat the audit

After merging, open **Actions → Audit Big Company Samples and Descriptions → Run workflow**. Choose `all`, `direct`, `md`, or `indeed`; optionally enter a comma separated company list. Download the `company-audit-*` artifacts when it finishes. They contain individual samples and description text. This audit does not save to the production catalog.

```powershell
gh workflow run audit-big-companies.yml --repo ragesh28/ALL_CAREER --field engine=all
```

Twelve focused regression tests pass locally. GitHub audit runs also execute the tests present at their pinned source commit. The network sample runs are linked above; source availability can change between runs.
