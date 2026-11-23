# Company investigation summary

Checked on 23 November 2026. Code and reports are on the `codex/big-company-description-audit` branch in [PR #2](https://github.com/ragesh28/ALL_CAREER/pull/2). Scheduled production runs will use these changes after the PR is merged.

**189 employer names and 244 overlapping company/source entries were checked.**

| Employer result | Count |
|---|---:|
| Confirmed India sample with a description | 134 |
| Confirmed India sample, description still missing | 1 |
| Foreign or unconfirmed sample location | 13 |
| No usable sample recovered | 41 |

All 31 focused parsing, source recovery, report and save-format regression tests pass locally. The latest completed GitHub production-engine checks also passed their regression tests. Tests cover new-job saving, already-seen job upgrades, repeated-page termination, job URLs, source metadata and company/source counting.

These are bounded samples. An empty recent Indeed search, a global first page without India roles, an unavailable description and a blocked website are different outcomes. The reports preserve those distinctions. No sample jobs replaced the production catalog.

## Files

- [Every company, URL, source status and method attempt](company-investigation-results.md)
- [Machine-readable monitor and history](company-investigation-monitor.json)
- [Company-specific fixes and limitations](company-investigation-fixes.md)
- [Research and methods](company-scraping-methods.md)
- [Completed checklist](company-investigation-plan.md)

## Still no usable sample in these checks

| Company | Career URL | Latest observation |
|---|---|---|
| Accenture | [Career page](https://www.accenture.com/in-en/careers/jobsearch) | No usable linked sample recovered in the bounded searches. public-api: 429; observed-api-replay: 429; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; proxy-render: no_healthy_configured_provider |
| Automation Anywhere | [Career page](https://www.automationanywhere.com/company/careers) | No usable linked sample recovered in the bounded searches. playwright: Error, 0 linked records; hasdata-2-http: 400; proxy-http: no_healthy_configured_provider; hasdata-2-render: 400; proxy-render: no_healthy_configured_provider |
| BigBasket | [Career page](https://careers.bigbasket.com/) | No usable linked sample recovered in the bounded searches. proxy-http: no_healthy_configured_provider; proxy-render: no_healthy_configured_provider |
| Blue Prism | [Career page](https://www.blueprism.com/company/careers/) | No usable linked sample recovered in the bounded searches. playwright: 404, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| BMW | [Career page](https://www.bmwgroup.jobs/en.html) | No usable linked sample recovered in the bounded searches. playwright: 200, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Continental | [Career page](https://jobs.continental.com/en/) | No usable linked sample recovered in the bounded searches. playwright: 200, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Cure.fit | [Career page](https://careers.cult.fit/) | No usable linked sample recovered in the bounded searches. proxy-http: no_healthy_configured_provider; proxy-render: no_healthy_configured_provider |
| Fidelity Investments | [Career page](https://jobs.fidelity.com/) | No usable linked sample recovered in the bounded searches. playwright: 403, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Hasura | [Career page](https://promptql.io/careers) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Intellect Design | [Career page](https://www.intellectdesign.com/careers/) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 400; proxy-http: no_healthy_configured_provider; proxy-render: no_healthy_configured_provider |
| John Deere | [Career page](https://jobs.deere.com/search/?q=India) | No usable linked sample recovered in the bounded searches. proxy-http: no_healthy_configured_provider; proxy-render: no_healthy_configured_provider |
| KPIT Technologies | [Career page](https://www.kpit.com/careers/) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| LatentView Analytics | [Career page](https://www.latentview.com/career/) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| LinkedIn | [Career page](https://careers.linkedin.com/) | No usable linked sample recovered in the bounded searches. direct-html: 403, 0 linked records; playwright: 403, 0 linked records; proxy-http: no_healthy_configured_provider; proxy-render: no_healthy_configured_provider |
| LTIMindtree | [Career page](https://ltimindtree.ripplehire.com/candidate/) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Maersk | [Career page](https://www.maersk.com/careers/vacancies) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; proxy-render: no_healthy_configured_provider |
| McKinsey | [Career page](https://www.mckinsey.com/careers/search-jobs) | No usable linked sample recovered in the bounded searches. playwright: Error, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Meta | [Career page](https://www.metacareers.com/jobs/) | No usable linked sample recovered in the bounded searches. hasdata-1-http: 403; proxy-http: no_healthy_configured_provider; hasdata-1-render: 403; proxy-render: no_healthy_configured_provider |
| Mu Sigma | [Career page](https://www.mu-sigma.com/careers/) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 403; proxy-render: no_healthy_configured_provider |
| Myntra | [Career page](https://careers.myntra.com/) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Nykaa | [Career page](https://www.nykaa.com/careers) | No usable linked sample recovered in the bounded searches. playwright: Error, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Ramco Systems | [Career page](https://www.ramco.com/careers) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| SAP | [Career page](https://jobs.sap.com/search/?q=India) | No usable linked sample recovered in the bounded searches. playwright: 403, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Schlumberger | [Career page](https://careers.slb.com/) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Sify Tech | [Career page](https://www.sifytechnologies.com/careers/) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 403; proxy-render: no_healthy_configured_provider |
| Sony | [Career page](https://www.sonyjobs.com/) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 403; proxy-render: no_healthy_configured_provider |
| Splunk | [Career page](https://www.splunk.com/en_us/careers/search-jobs.html) | No usable linked sample recovered in the bounded searches. playwright: 403, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Spotify | [Career page](https://www.lifeatspotify.com/jobs) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Stripe | [Career page](https://stripe.com/jobs/search?office_locations=Asia+Pacific--Bengaluru) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 403; proxy-render: no_healthy_configured_provider |
| Subex | [Career page](https://www.subex.com/careers/) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Tata Elxsi | [Career page](https://www.tataelxsi.com/careers) | No usable linked sample recovered in the bounded searches. hasdata-1-http: 403; proxy-http: no_healthy_configured_provider; hasdata-1-render: 403; proxy-render: no_healthy_configured_provider |
| Tech Mahindra | [Career page](https://careers.techmahindra.com/) | No usable linked sample recovered in the bounded searches. playwright: 200, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Tiger Analytics | [Career page](https://www.tigeranalytics.com/careers/) | No usable linked sample recovered in the bounded searches. direct-html: 403, 0 linked records; playwright: 200, 0 linked records; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| TotalEnergies | [Career page](https://careers.totalenergies.com/en_US/careers/SearchJobs) | No usable linked sample recovered in the bounded searches. playwright: 404, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Ubisoft | [Career page](https://www.ubisoft.com/en-us/company/careers/search) | No usable linked sample recovered in the bounded searches. proxy-http: no_healthy_configured_provider; hasdata-2-render: 403; proxy-render: no_healthy_configured_provider |
| Unity | [Career page](https://unity.com/careers/positions) | No usable linked sample recovered in the bounded searches. playwright: 403, 0 linked records; proxy-http: no_healthy_configured_provider; hasdata-2-render: 403; proxy-render: no_healthy_configured_provider |
| Virtusa | [Career page](https://www.virtusa.com/careers/job-search) | No usable linked sample recovered in the bounded searches. playwright: 403, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Volkswagen | [Career page](https://www.volkswagen-group.com/en/careers-15757) | No usable linked sample recovered in the bounded searches. playwright: 404, 0 linked records; hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 403; proxy-render: no_healthy_configured_provider |
| Walmart | [Career page](https://careers.walmart.com/technology) | No usable linked sample recovered in the bounded searches. scraperapi-2-http: 403; hasdata-1-http: 403; proxy-http: no_healthy_configured_provider; hasdata-1-render: 403; proxy-render: no_healthy_configured_provider |
| Zerodha | [Career page](https://zerodha.com/careers/) | No usable linked sample recovered in the bounded searches. hasdata-2-http: 429; proxy-http: no_healthy_configured_provider; hasdata-2-render: 429; proxy-render: no_healthy_configured_provider |
| Zomato | [Career page](https://www.zomato.com/careers) | No usable linked sample recovered in the bounded searches. playwright: Error, 0 linked records; proxy-http: no_healthy_configured_provider; hasdata-2-render: 403; proxy-render: no_healthy_configured_provider |

## Description gap

- **Publicis Sapient**: an India listing was recovered, but the checked API/page did not supply a usable job description. The individual link and attempts are saved in the monitor.

## Provider limits found

GitHub Secrets can be used inside a workflow, but their stored values cannot be read back with GitHub CLI. The provider checks record only availability, HTTP/proxy errors and remaining credits. Oxylabs and the tested Webshare endpoints returned proxy authentication failures; ScrapingAnt requests were rejected. Some ScraperAPI accounts were rejected or exhausted. HasData passed account connectivity checks but still failed on some target websites. See the provider table in the full report for each tested label.

The final optional two-company browser rerun was canceled during dependency installation and is not counted as a successful check. The completed full and targeted runs are linked in the report.
