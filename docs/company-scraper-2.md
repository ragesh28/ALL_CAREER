# Big Company Scraper 2

The workflow collects official India job postings from 36 new boards (35 employers, with Booking Holdings COE and Agoda separate) and 19 previously recovered boards. A configured board is not a guarantee of available jobs: the audit report records live results, foreign-location rejections, blocked requests and missing descriptions separately.

## Schedule and operation

- Workflow file: `.github/workflows/big_company_scraper_2.yml`; displayed name: **Big Company Scraper 2**.
- Daily cron: `30 21 * * *`, which is **03:00 Asia/Kolkata** the following calendar day. GitHub may delay scheduled runs.
- Use **Actions â†’ Big Company Scraper 2 â†’ Run workflow**. Enable `audit_only` to test without changing the catalog. Leave `companies` blank for all boards.
- Scraping uses a 5h45m process budget and saves before the runner's six-hour limit. A successfully published unfinished checkpoint can dispatch a continuation, limited to four per chain. No continuation is dispatched after a failed save.
- A checkpoint records completed boards and processed native IDs within the current board. Resume re-fetches the current board and skips already processed IDs; descriptions never go into the checkpoint.
- Each scraper has its own concurrency group. The generated-data publisher merges catalog/history changes onto the latest main tree through GitHub's Git Data API. It uploads changed JSON only, avoiding a Git push that can fetch/repack unrelated repository blobs in a partial checkout. A non-forced branch update retries concurrent changes without resetting the scraper checkout. `data/big_company_jobs.json` and `workday_scraper/big_company_jobs.json` are updated together. API calls and retries have an eight-minute budget. Publication failures fail visibly; the new workflow's sanitized recovery artifact includes the catalog, ID history and checkpoint. The isolated-worktree Git implementation remains available for local regression tests.

## Listing identity, freshness and retirement

Native job/requisition ID plus company identifies a listing. Canonical URL is the fallback; ID query parameters are retained and tracking parameters removed. The save layer also matches URLs when upgrading a record without a native ID.

The catalog retains a listing for 30 days using its original publication date when known and its first-seen date. Re-scraping never resets `first_seen` or `fetched_at`. An expired listing's identity remains in `data/company_job_history/` while the posting stays online, so it cannot be reintroduced as a new job after retention removes it.

Only a complete, successful board scan can mark IDs missing. After two such missing snapshots, a confirmed HTTP 404/410 on the individual posting is required to retire its identity. Closure verification checks at most 20 postings per board per run, rotates deferred candidates fairly, and stops before the checkpoint deadline. A timeout, rate limit, empty unrecognized response, browser-only page or pagination cap cannot delete IDs. Some career sites return HTTP 200 for closed postings; those identities are conservatively retained until closure can be verified.

Cards sort by first discovery, newest first. The original posting date is separate. A missing original date is displayed as **Found â€¦**, not falsely labeled as posted today. Experience, salary and walk-in badges appear only when corresponding metadata exists. The experience filter excludes unknown requirements rather than guessing from company or title.

## Description and AI privacy contract

Descriptions are fetched in memory, used for structured/regular-expression and AI extraction, then discarded. The published catalog, checkpoint, history files and operational reports retain only job metadata. The three older big-company save paths use the same contract.

Models must return exact evidence quotations for extracted facts. Values without matching evidence, invented numbers and unsupported publication dates are rejected. Salary estimates from the supplied company config are not imported. Unknown experience, salary or dates stay missing.

Cloudflare uses `@cf/meta/llama-3.2-3b-instruct` first, with `@cf/meta/llama-3.1-8b-instruct-fast` as model fallback. The local health test also tried Llama 3.2 1B; it was unavailable and is not in the production chain. Existing `GEMINI_API_KEYS`, `GROQ_API_KEYS`, `MISTRAL_API_KEYS` and `OPENROUTER_API_KEYS` are additional provider fallbacks. OpenRouter's default model uses a `:free` identifier; unavailable models are skipped.

Provider error responses and Retry-After are respected. Daily exhaustion pauses that provider until its retry time; profiles are not cycled to circumvent a daily allowance. There is no runner-IP rotation and no quota-triggered workflow restart. If no AI provider is usable, jobs are saved with known structured metadata and absent fields remain absent. A later healthy run can retry metadata that has not been checked successfully.

## GitHub secret setup

Create one repository Actions secret named **`CLOUDFLARE_WORKERS_AI_ACCOUNTS`**. Its value is a JSON array:

```json
[
  {
    "label": "primary",
    "account_id": "YOUR_32_CHARACTER_CLOUDFLARE_ACCOUNT_ID",
    "api_token": "YOUR_WORKERS_AI_API_TOKEN"
  },
  {
    "label": "backup",
    "account_id": "ANOTHER_32_CHARACTER_ACCOUNT_ID",
    "api_token": "ANOTHER_WORKERS_AI_API_TOKEN"
  }
]
```

Repeat one object per configured profile. Use account-scoped tokens with Workers AI access. Do not use a D1 token merely because it has Cloudflare in its name. Existing `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_D1_URL` remain unrelated to this extraction secret. Never commit the credential file. Tokens exposed outside your secret store should be replaced before use.

Run **Check Company AI Health** after setting the secret. Its tiny factual probes record provider/profile/model outcomes without publishing credentials. GitHub CLI can list secret names but cannot retrieve saved secret values.

## Monitoring and logos

The String Theory dashboard reads small published reports independently of the large job catalog. It shows the last workflow's per-company collection status, India records, newly stored jobs, descriptions read, new-job locations and actual AI request outcomes. Daily quota exhaustion is shown only when reported by the provider; unknown quota balances are not displayed as invented percentages.

Reports are stored in `data/company_scraper2/latest.json`, `ai_status.json` and `runs/`. Per-run details are tied to the actual GitHub run ID. Older run reports are retained for 30 days. The workflow also emits its summary in GitHub Actions.

Portal-supplied structured company logos are preserved. The UI passes logo and website fields to the existing fallback component. Known official domains and cached non-generic website favicons improve fallback coverage; favicons are not claimed to be full-resolution brand logos. Their source manifest is `logos/company-scraper2/sources.json`. Missing images retain the existing question-mark fallback.

## Local verification

```powershell
python -m scripts.company_scraper2 --audit --browser --output company_scraper2_audit.json
python -m unittest tests.test_company_scraper2 tests.test_company_job_details tests.test_company_recovery tests.test_company_investigation_report
```

The audit checks one page and a sample description per board. Its sample counts are not total vacancies. Pagination completeness is tracked separately; HTML and browser captures are conservatively partial. Board-driven modals such as Zerodha and Myntra retain a native ID and the actual official board URL when no stable individual deep link is observed.
