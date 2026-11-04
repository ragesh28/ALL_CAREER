"""Public listing parsers; no login, challenge solving, or private API required."""
import json
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def parse_listing(html, source, city, role=''):
    soup = BeautifulSoup(html, 'html.parser')
    jobs = []
    discovered = datetime.now(timezone.utc).isoformat()
    if source == 'apna':
        for card in soup.select('a[data-testid="job-card"]'):
            title = card.select_one('h2, h3')
            image = card.select_one('img[alt]')
            company = image.get('alt', '').strip() if image else ''
            if not company and title:
                company_node = title.parent.select_one('span')
                company = company_node.get_text(' ', strip=True) if company_node else ''
            location_icon = card.select_one('[data-testid="LocationOnIcon"]')
            location = location_icon.parent.get_text(' ', strip=True) if location_icon else city
            text = card.get_text(' ', strip=True)
            experience = re.search(r'(?:Min\.\s*)?\d+\s*(?:years?|months?)|Any experience', text, re.I)
            if title and company and card.get('href'):
                jobs.append({'title': title.get_text(' ', strip=True), 'company': company, 'location': location, 'url': urljoin('https://apna.co', card['href']), 'experience': experience.group(0) if experience else '', 'source': source, 'fetched_at': discovered, 'role_search': role})
    elif source == 'freshersworld':
        for card in soup.select('div.job-container'):
            title = card.select_one('.wrap-title, .job-desc-title')
            company = card.select_one('.company-name, h3.latest-jobs-title, .job-desc-company')
            location = card.select_one('.job-location')
            experience = card.select_one('.experience')
            link = card.get('job_display_url')
            if not link:
                anchor = next((a for a in card.select('a[href]') if '/jobs/' in a['href'] and 'jobsearch' not in a['href']), None)
                link = anchor['href'] if anchor else ''
            if title and company and link:
                jobs.append({'title': re.sub(r'\s*(?:Less|More|LessMore)\s*$', '', title.get_text(' ', strip=True)), 'company': company.get_text(' ', strip=True), 'location': location.get_text(' ', strip=True) if location else city, 'url': urljoin('https://www.freshersworld.com', link), 'experience': experience.get_text(' ', strip=True) if experience else '', 'source': source, 'fetched_at': discovered, 'role_search': role})
    elif source == 'workindia':
        for script in soup.find_all('script'):
            text = script.string or script.get_text()
            if '__ROUTE_DATA__' not in text:
                continue
            match = re.search(r'__ROUTE_DATA__\s*=\s*', text)
            if not match:
                continue
            try:
                payload, _ = json.JSONDecoder().raw_decode(text[match.end():].lstrip())
            except ValueError:
                continue
            rows = payload.get('data', [])
            if isinstance(rows, dict):
                rows = rows.get('jobs') or rows.get('results') or []
            if not isinstance(rows, list):
                continue
            for item in rows:
                if not isinstance(item, dict):
                    continue
                title = item.get('profile_job_title') or item.get('job_title')
                company = item.get('branch_company_name') or item.get('company_name')
                link = item.get('url') or (f"https://www.workindia.in/jobs/{item['id']}/" if item.get('id') else '')
                if title and company and link:
                    jobs.append({'title': title, 'company': company, 'location': item.get('branch_location_city_name') or city, 'url': urljoin('https://www.workindia.in', link), 'date_posted': str(item.get('created_at') or '')[:10], 'fetched_at': discovered, 'source': source, 'role_search': role, 'experience': item.get('job_experience') or ''})
    # Standards-based fallback when a portal exposes JobPosting structured data.
    def structured(value):
        if isinstance(value, list):
            for item in value:
                yield from structured(item)
        elif isinstance(value, dict):
            if value.get('@type') == 'JobPosting':
                yield value
            for item in value.values():
                if isinstance(item, (dict, list)):
                    yield from structured(item)
    if not jobs:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                payload = json.loads(script.string or script.get_text())
            except ValueError:
                continue
            for item in structured(payload):
                organization = item.get('hiringOrganization') or {}
                if not isinstance(organization, dict):
                    continue
                location = item.get('jobLocation') or {}
                if isinstance(location, list):
                    location = location[0] if location else {}
                address = location.get('address') or {} if isinstance(location, dict) else {}
                if not isinstance(address, dict):
                    address = {}
                if item.get('title') and organization.get('name') and item.get('url'):
                    jobs.append({'title': item['title'], 'company': organization['name'], 'location': address.get('addressLocality') or city, 'date_posted': str(item.get('datePosted') or '')[:10], 'fetched_at': discovered, 'url': item['url'], 'source': source, 'role_search': role})
    return list({j['url']: j for j in jobs}.values())


def scrape_public_listing(source, role, city, requester=None):
    requester = requester or requests.get
    role_slug = role.lower().replace(' ', '-')
    city_slug = 'bengaluru' if city.lower() == 'bangalore' and source != 'freshersworld' else city.lower().replace(' ', '-')
    urls = {'apna': f'https://apna.co/jobs/{role_slug}-jobs-in-{city_slug}', 'workindia': f'https://www.workindia.in/{role_slug}-jobs-in-{city_slug}/', 'freshersworld': f'https://www.freshersworld.com/jobs/jobsearch/{role_slug}-jobs-in-{city_slug}'}
    base = urls[source]
    jobs = {}
    report = {'requests': 0, 'scraped': 0, 'status': 'no_job_cards', 'http_status': None, 'url': base}
    for page in range(1, 2 if source == 'workindia' else 5):
        url = base if page == 1 else base + (f'?page={page}' if source == 'apna' else f'?limit=20&offset={(page - 1) * 20}')
        report['requests'] += 1
        try:
            response = requester(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'}, timeout=25)
            report['http_status'] = response.status_code
            if response.status_code != 200:
                report['status'] = 'blocked' if response.status_code in (401, 403, 429) else 'http_error'
                break
            rows = parse_listing(response.text, source, city, role)
        except (requests.RequestException, ValueError) as error:
            report['status'] = 'request_error'
            report['error'] = str(error)[:150]
            break
        added = [row for row in rows if row['url'] not in jobs]
        jobs.update((row['url'], row) for row in added)
        if not added:
            break
        report['status'] = 'ok'
    report['scraped'] = len(jobs)
    return list(jobs.values()), report
