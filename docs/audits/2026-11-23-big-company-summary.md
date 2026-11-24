# Big Company Scraper Summary

Audit date: 23 November 2026.

| Workflow | Company/source checks | Returned a job sample | No usable sample returned | Description found |
|---|---:|---:|---:|---:|
| Direct company scraper | 44 | 25 | 19 | 16 |
| API/browser scraper | 51 | 33 | 18 | 28 |
| Indeed company searches | 149 | 73 | 76 | 73 |
| **Total** | **244** | **131** | **113** | **117** |

- **131** checks returned a job sample.
- **113** checks returned no usable sample, including blocked requests, invalid links and empty searches.
- **117** checks returned a sample with a description.
- **14** checks returned a job sample without a description.

These are company/source checks, not unique companies: an employer can appear in multiple workflows. No usable sample does not prove the employer has no vacancies.

[Full company-by-company report](2026-11-23-big-company-sources.md)

The fixes and reports are on the `codex/big-company-description-audit` branch in PR #2. They are awaiting merge into main.
