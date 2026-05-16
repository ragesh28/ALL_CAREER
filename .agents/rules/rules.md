# RULES FOR JOB SCRAPER CODEBASE

1. **DO NOT MODIFY** `workday_scraper/scrape_all_companies_v2.py` — it works. Only touch it if the USER reports a specific bug in an existing company.
2. **NEW companies go in NEW files** — never add to `scrape_all_companies_v2.py`. Create separate scrapers (e.g., `scrape_new_companies.py`) to avoid breaking existing 44 companies.
3. **Two-step scraping pattern**: Step 1 = Discovery call (find total jobs/pages). Step 2 = Loop all pages with pagination (pageNumber/offset/start). Never hardcode page counts.
4. **API types we handle**: REST GET/POST JSON APIs, Workday (`/wday/cxs/`), Phenom People (`/api/pcsx/`), Oracle HCM (`/hcmRestApi/`), SSR HTML pages (BeautifulSoup), Playwright for JS-rendered sites.
5. **Always add headers**: `User-Agent` (Chrome), `Origin`, `Referer`, `Accept: application/json`. Bot detection blocks plain `python-requests` User-Agent on GitHub Actions (Ubuntu Linux).
6. **JSON parsing on Linux**: Use `json.loads(resp.text.lstrip("\ufeff").strip())` instead of `resp.json()` — GitHub Actions runners sometimes add BOM bytes.
7. **Rate limiting**: Add `time.sleep(0.3)` between paginated API calls. On error, wait 1s then continue (don't crash). Log progress every 100 pages.
8. **Fallback chain**: API call → HTML scraping → Playwright → JobSpy/LinkedIn multi-city. If one method fails, try the next automatically.
9. **Location cleaning**: Strip HTML tags (`<br/>`), extract city name only, handle list/string variants. Indian cities: Chennai, Bangalore, Hyderabad, Mumbai, Pune, Kolkata, Delhi, Noida, Gurgaon.
10. **Output format** (every job must have): `{"title": str, "location": str, "posted": str, "apply_url": str, "total_jobs": int}`.
11. **Config files**: `workday_scraper/companies_links.json` = company list for `scrape_all_companies_v2.py`. New scrapers use their own config/list.
12. **GitHub Actions**: Workflows in `.github/workflows/`. Never use `sleep` inside a step that might be canceled. Use `if: always()` for save/restart steps.
13. **Testing**: Always test locally before pushing. Test with small limit first (3-5 jobs), then full run.
14. **To understand codebase**: Use graphify (`graphify-out/`) for code structure. View `scrape_all_companies_v2.py` for scraping patterns and solutions.
15. **Push safely**: Always `git pull --rebase origin main` before `git push` to avoid conflicts with automated CI/CD commits.
