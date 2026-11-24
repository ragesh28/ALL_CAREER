"""Public ATS adapters with explicit pagination completeness and real location checks."""
import json
import re
import time
import xml.etree.ElementTree as ET
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from scripts.company_job_details import confirmed_india_location, details_from_record, fetch_details, location_text, public_request, text
from scripts.company_recovery import HEADERS, jobs_from_html, records_from_json, unique_jobs

INDIA_ID = 'c4f78be1a8f14da0ab49ce1162348a5e'


@dataclass
class BoardResult:
    jobs: list = field(default_factory=list)
    complete: bool = False
    status: str = 'not_checked'
    pages: int = 0
    http_status: int = 0
    returned: int = 0
    rejected_locations: int = 0
    note: str = ''


def replace_query(url, **changes):
    p = urlsplit(url)
    q = dict(parse_qsl(p.query))
    q.update({k: str(v) for k, v in changes.items()})
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), p.fragment))


def normalized(raw, config, url='', title='', location='', job_id='', posted=None):
    details = details_from_record(raw)
    result = {**details, 'title': text(title or raw.get('title') or raw.get('name')),
              'location': location_text(location or details.get('location') or raw.get('locationsText')),
              'apply_url': urljoin(config['endpoint'], url) if url else '', 'job_id': str(job_id or raw.get('id') or raw.get('job_id') or ''),
              'company': config['company'], 'source': 'company_careers'}
    if posted:
        result['date_posted'] = str(posted)
    if config.get('company_website'):
        result['company_website'] = config['company_website']
    if config.get('company_logo') and not result.get('company_logo'):
        result['company_logo'] = config['company_logo']
    return result


def parse_payload(data, config):
    ats, endpoint = config['ats'], config['endpoint']
    p = urlsplit(endpoint)
    origin = f'{p.scheme}://{p.netloc}'
    if ats in ('greenhouse', 'lever', 'gem', 'smartrecruiters', 'verified'):
        if ats == 'gem':
            return [normalized(r, config, r['absolute_url'], location=location_text(r.get('location')), posted=r.get('first_published_at'))
                    for r in data if r.get('absolute_url') and not re.search('talent community', r.get('title',''), re.I)]
        jobs = records_from_json(data, endpoint)
        for job in jobs:
            job['company'] = config['company']
            job['source'] = 'company_careers'
            job['company_website'] = config.get('company_website', '')
            if config.get('company_logo') and not job.get('company_logo'):
                job['company_logo'] = config['company_logo']
        # Greenhouse updated_at is NOT a publication timestamp.
        if ats == 'greenhouse':
            by_url = {r.get('absolute_url'): r for r in data.get('jobs', [])}
            for job in jobs:
                raw = by_url.get(job['apply_url'], {})
                job['job_id'] = str(raw.get('id', ''))
                offices = '; '.join(location_text(o) for o in raw.get('offices', []) if isinstance(o,dict))
                if offices:
                    job['location'] = '; '.join(filter(None,[job.get('location'),offices]))
                if raw.get('first_published'):
                    job['date_posted'] = raw['first_published']
        if ats == 'smartrecruiters':
            for job in jobs:
                job['job_id'] = job['apply_url'].rstrip('/').split('/')[-1]
        return jobs
    if ats == 'workday':
        site = p.path.strip('/').split('/')[3]
        return [normalized(r, config, origin + '/' + site + r['externalPath'], location=r.get('locationsText'), job_id=(r.get('bulletFields') or [''])[0], posted=r.get('postedOn'))
                for r in data.get('jobPostings', []) if r.get('externalPath')]
    if ats == 'jibe':
        jobs = []
        for item in data.get('jobs', []):
            r = item.get('data', item)
            url = r.get('meta_data', {}).get('canonical_url') or r.get('apply_url')
            if url:
                jobs.append(normalized(r, config, url, location=r.get('full_location') or r.get('location_name') or r.get('city'), job_id=r.get('req_id') or r.get('slug'), posted=r.get('posted_date')))
        return jobs
    if ats == 'oracle_hcm':
        jobs = []
        for r in (data.get('items') or [{}])[0].get('requisitionList', []):
            jobs.append(normalized(r, config, config['job_url_template'].format(id=r['Id']), title=r.get('Title'), location=r.get('PrimaryLocation'), job_id=r['Id'], posted=r.get('PostedDate')))
        return jobs
    if ats == 'eightfold':
        jobs = []
        for r in (data.get('data') or data).get('positions', []):
            jid = r.get('id')
            if not jid:
                continue
            loc = r.get('standardizedLocations') or r.get('locations') or r.get('location')
            stamp = r.get('t_create')
            if isinstance(stamp, (int, float)):
                stamp = datetime.fromtimestamp(stamp / 1000 if stamp > 1e11 else stamp, timezone.utc).date().isoformat()
            jobs.append(normalized(r, config, r.get('canonicalPositionUrl') or r.get('positionUrl') or f'{origin}/careers/job/{jid}', location=location_text(loc), job_id=jid, posted=stamp))
        return jobs
    if ats == 'rippling':
        rows = data if isinstance(data, list) else data.get('items', [])
        return [normalized(r, config, r.get('url'), location=location_text(r.get('workLocation')), job_id=r.get('uuid')) for r in rows if r.get('url')]
    if ats == 'workable':
        return [normalized(r, config, f"https://apply.workable.com/j/{r['shortcode']}/", location=location_text(r.get('locations') or r.get('location')), job_id=r['shortcode'], posted=r.get('published')) for r in data.get('results', []) if r.get('shortcode')]
    if ats == 'kpit':
        return [normalized(r, config, f"https://talentojo.kpit.com/tojo/app/job-apply/#/Career%20Portal/{r['id']}", location=r.get('location'), job_id=r['id'], posted=r.get('created_at')) for r in data.get('jobs', [])]
    if ats == 'zerodha':
        # Link format is read from the official page; never invent a /job/ route.
        return [normalized(r, config, config['career_url'], title=r.get('job_title'), location=r.get('location'), job_id=r.get('name')) for r in data.get('data', [])]
    if ats == 'darwinbox':
        rows = data.get('message') or data.get('data') or []
        if isinstance(rows, dict):
            rows = rows.get('jobs', [])
        # Only preserve explicit job links; a board URL cannot represent every vacancy.
        return [normalized(r, config, r.get('apply_url') or r.get('url'), title=r.get('title') or r.get('job_title'), location=r.get('location') or r.get('city'), job_id=r.get('id') or r.get('job_id'), posted=r.get('created_on')) for r in rows if isinstance(r, dict) and (r.get('apply_url') or r.get('url'))]
    if ats == 'phenom':
        rows = data.get('refineSearch', {}).get('data', {}).get('jobs', [])
        return [normalized(r, config, r.get('applyUrl') or r.get('jobUrl'), title=r.get('title'), location=r.get('cityStateCountry') or r.get('location'), job_id=r.get('jobSeqNo') or r.get('reqId'), posted=r.get('postedDate')) for r in rows if r.get('applyUrl') or r.get('jobUrl')]
    return []


def next_request(config, url, body, data, count):
    ats = config['ats']
    if ats == 'workday':
        body = deepcopy(body)
        body['offset'] += count
        return (url, body) if count and body['offset'] < data.get('total', 0) else None
    if ats == 'smartrecruiters':
        offset = int(dict(parse_qsl(urlsplit(url).query)).get('offset', '0')) + count
        return (replace_query(url, offset=offset), body) if count and offset < data.get('totalFound', 0) else None
    if ats == 'jibe':
        q = dict(parse_qsl(urlsplit(url).query));page = int(q.get('page', 1));size = int(q.get('limit', 20))
        return (replace_query(url, page=page + 1), body) if count and page * size < data.get('totalCount', 0) else None
    if ats == 'eightfold':
        q = dict(parse_qsl(urlsplit(url).query));start = int(q.get('start', 0)) + count
        total = (data.get('data') or data).get('count', 0)
        return (replace_query(url, start=start), body) if count and start < total else None
    if ats == 'oracle_hcm':
        q = dict(parse_qsl(urlsplit(url).query));finder = q.get('finder','');match = re.search(r',offset=(\d+)',finder);offset = int(match[1]) + count if match else count
        total = (data.get('items') or [{}])[0].get('TotalJobsCount',0)
        return (replace_query(url, finder=re.sub(r',offset=\d+','',finder) + f',offset={offset}'), body) if count and offset < total else None
    if ats == 'kpit':
        q = dict(parse_qsl(urlsplit(url).query));offset = int(q.get('offset',0)) + count
        return (replace_query(url, offset=offset), body) if count and offset < data.get('total_count',0) else None
    if ats == 'workable' and data.get('nextPage') and count:
        return url, {**body, 'cursor': data['nextPage']}
    if ats == 'phenom':
        body = {**body, 'from': body.get('from', 0) + count}
        return (url, body) if count and body['from'] < data.get('refineSearch',{}).get('data',{}).get('totalHits',0) else None
    return None


def html_records(html, config, url):
    ats = config['ats']
    jobs = []
    if ats == 'rss':
        for item in ET.fromstring(html).iter('item'):
            raw = {n.tag.split('}')[-1]: n.text or '' for n in item}
            if raw.get('title') and raw.get('link'):
                loc = raw.get('location', '')
                # Country code is a component, not the US state Indiana.
                if re.search(r',\s*IN(?:\s*,|\s*$)', loc):
                    loc += ', India'
                jobs.append(normalized(raw, config, raw['link'], location=loc, job_id=raw.get('guid'), posted=raw.get('pubDate')))
        return jobs
    soup = BeautifulSoup(html, 'html.parser')
    if ats in ('tata', 'ramco'):
        for n in soup.select('.jjbcdeo1' if ats == 'tata' else 'a.job-listing__card'):
            title = n.select_one('h3' if ats == 'tata' else '.job-listing__job-title')
            loc = n.select_one('.jjbcdeo11 p' if ats == 'tata' else '.job-listing__job-description')
            link = n.select_one('a[href]') if ats == 'tata' else n
            if title and link:
                jobs.append(normalized({}, config, urljoin(url,link['href']), title=title.get_text(' ',strip=True),location=loc.get_text(' ',strip=True) if loc else ''))
        return jobs
    jobs = jobs_from_html(html, url)
    # Plain links often lack location: read their own posting, not the board's country.
    for job in jobs:
        job['company'] = config['company']
    return jobs


def scrape_board(config, max_pages=60, budget=180, browser=False):
    if browser and config['ats'] in ('sify','myntra'):
        return special_browser_board(config,budget)
    result = BoardResult()
    deadline = time.monotonic() + budget
    url, body = config['endpoint'], deepcopy(config.get('payload'))
    if config['ats'] == 'workday' and body is None:
        body = {'limit':20,'offset':0,'searchText':'','appliedFacets':{'locationCountry':[INDIA_ID]}}
    method = config.get('method','GET')
    seen = set()
    session = requests.Session()
    headers = dict(HEADERS)
    if config['ats'] == 'phenom':
        try:
            seed = session.get(config['seed_url'],timeout=(5,15))
            match = re.search(r'"csrfToken"\s*:\s*"([^"]+)"',seed.text)
            if not match:
                return BoardResult(status='needs_browser',note='No public session bootstrap token in seed page')
            headers.update({'x-csrf-token':match[1],'Referer':config['seed_url']})
            body = {'ddoKey':'refineSearch','from':0,'size':20,'pageName':'search-results','jobs':True,'counts':True,'siteType':'external','lang':'en_in','country':'in'}
        except requests.RequestException:
            return BoardResult(status='network_error')
    try:
        for _ in range(max_pages):
            if time.monotonic() >= deadline:
                result.note = 'Per-company time budget reached';break
            requester = public_request if (urlsplit(url).hostname or '').endswith('myworkdayjobs.com') else session.request
            response = requester(method,url,json=body,headers=headers,timeout=(5,min(20,max(1,deadline-time.monotonic()))))
            result.http_status = response.status_code
            result.pages += 1
            if response.status_code != 200:
                result.status = 'rate_limited' if response.status_code == 429 else 'http_error'
                break
            content_type = response.headers.get('content-type','')
            if 'json' in content_type:
                data = response.json()
                required = {'greenhouse':'jobs','workday':'jobPostings','smartrecruiters':'content','jibe':'jobs','oracle_hcm':'items','kpit':'jobs','workable':'results','zerodha':'data'}.get(config['ats'])
                if required and (not isinstance(data,dict) or not isinstance(data.get(required),list)):
                    result.status='parse_error';result.note='Expected listing array missing';break
                found = parse_payload(data, config)
                raw_count = len(data.get('jobPostings',[])) if config['ats']=='workday' else len(data.get('content',[])) if config['ats']=='smartrecruiters' else len(data.get('jobs',[])) if config['ats'] in ('jibe','kpit') else len((data.get('data') or data).get('positions',[])) if config['ats']=='eightfold' else len((data.get('items') or [{}])[0].get('requisitionList',[])) if config['ats']=='oracle_hcm' else len(data.get('results',[])) if config['ats']=='workable' else len(found)
                following = next_request(config,url,body,data,raw_count)
            else:
                found = html_records(response.text, config, response.url)
                following = None
            fresh = [j for j in found if (j.get('job_id') or j.get('apply_url')) not in seen]
            if found and not fresh:
                result.note = 'Repeated page detected; history deletion disabled';break
            seen.update(j.get('job_id') or j.get('apply_url') for j in fresh)
            result.jobs.extend(fresh)
            if not following:
                # HTML and generic browser captures are never claimed to be a complete board.
                result.complete = config['ats'] not in ('radancy_html','avature_html','trakstar_html','custom_html','brassring','taleo','tata','ramco','verified')
                result.status = 'ok' if result.jobs else 'empty_confirmed' if result.complete and (config['ats']=='rss' or 'json' in content_type and (required or config['ats'] in ('lever','gem','rippling'))) else 'empty_or_unparsed'
                break
            url, body = following
            time.sleep(0.15)
    except (requests.RequestException, ValueError, TypeError, KeyError) as error:
        result.status = 'network_error' if isinstance(error,requests.RequestException) else 'parse_error'
        result.note = type(error).__name__
    if not result.jobs and browser and time.monotonic() < deadline:
        try:
            from scripts.company_sources import browser_listing
            if config['ats'] in ('tata','ramco'):
                return special_browser_board(config,max(1,deadline-time.monotonic()))
            result.jobs = browser_listing(config['company'], config['career_url'], 1000)
            result.complete = False
            result.status = 'browser_ok' if result.jobs else 'no_usable_sample'
        except Exception as error:
            result.status = 'browser_failed';result.note = type(error).__name__
    result.returned = len(result.jobs)
    accepted = []
    unique = {}
    for job in result.jobs:
        unique.setdefault(job.get('job_id') or job.get('apply_url'),job)
    for job in unique.values():
        if not job.get('title') or not job.get('apply_url'):
            continue
        if not confirmed_india_location(job.get('location')) and time.monotonic() < deadline:
            # A missing place may be recovered; an explicitly foreign place is never replaced by India.
            if not job.get('location'):
                job.update(fetch_details(job['apply_url']))
        if confirmed_india_location(job.get('location')):
            job['company'] = config['company']
            job['company_website'] = config.get('company_website','')
            accepted.append(job)
        else:
            result.rejected_locations += 1
    result.jobs = accepted
    if result.returned and not accepted and result.status in ('ok','browser_ok'):
        result.status='no_india_sample'
    if result.status == 'not_checked':
        result.status = 'partial'
    return result


def special_browser_board(config, budget):
    from playwright.sync_api import sync_playwright
    deadline=time.monotonic()+budget
    result=BoardResult(complete=False)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(service_workers='block')
        page=context.new_page()
        try:
            if config['ats']=='myntra':
                with page.expect_response(lambda r:'/requisition/_search?' in r.url and r.status==200,timeout=min(40000,budget*1000)) as pending:
                    page.goto(config['career_url'],wait_until='domcontentloaded',timeout=25000)
                data=pending.value.json()
                for r in data.get('entities',[]):
                    # This site's job detail is client-state driven. Preserve its
                    # actual board URL and stable native ID, never invent a link.
                    result.jobs.append(normalized(r,config,config['career_url'],title=r.get('jobTitle'),location=location_text(r.get('jobLocation')),job_id=r.get('id')))
                result.status='browser_ok';result.http_status=200
                result.note='Public requisition API; first page only. Apply opens the official board because no stable individual link was observed.'
            elif config['ats'] in ('ramco','tata'):
                response=page.goto(config['career_url'],wait_until='domcontentloaded',timeout=25000)
                page.wait_for_timeout(3000)
                result.http_status=response.status if response else 0
                result.jobs=html_records(page.content(),config,page.url)
                result.status='browser_ok' if result.jobs else 'no_usable_sample'
            elif config['ats']=='sify':
                page.goto(config['career_url'],wait_until='domcontentloaded',timeout=25000)
                page.get_by_role('button',name='View Job',exact=True).first.wait_for(timeout=15000)
                count=page.get_by_role('button',name='View Job',exact=True).count()
                for i in range(count):
                    if time.monotonic()>deadline-15:break
                    rows=page.get_by_role('row').filter(has=page.get_by_role('button',name='View Job',exact=True))
                    cells=rows.nth(i).get_by_role('cell').all_inner_texts()
                    title=cells[0].strip();loc=cells[3].strip() if len(cells)>3 else ''
                    rows.nth(i).get_by_role('button',name='View Job',exact=True).click(timeout=5000)
                    page.wait_for_url('**/job/**',timeout=8000)
                    page.wait_for_function("title => document.body.innerText.includes(title) && document.body.innerText.includes('Job Description')",arg=title,timeout=12000)
                    page.wait_for_timeout(300)
                    body=page.locator('body').inner_text()
                    a=body.find('Job Description');z=body.rfind('Skills')
                    if a>=0 and z<=a:
                        end=body.find('Privacy Policy',a)
                        z=end if end>a else len(body)
                    if re.search(r'Region\s+IN\b',body):loc+=', India'
                    result.jobs.append(normalized({'description':body[a:z] if a>=0 and z>a else ''},config,page.url,title=title,location=loc,job_id=urlsplit(page.url).path.split('/')[-1]))
                    if i+1<count:
                        page.goto(config['career_url'],wait_until='domcontentloaded',timeout=20000)
                        page.get_by_role('button',name='View Job',exact=True).first.wait_for(timeout=15000)
                result.status='browser_ok' if result.jobs else 'no_usable_sample';result.http_status=200
                result.note='Browser-rendered job list and individual descriptions; current visible page only.'
        except Exception as error:
            result.status='partial' if result.jobs else 'browser_failed'
            result.note=type(error).__name__
        finally:
            context.close();browser.close()
    result.returned=len(result.jobs)
    result.jobs=[j for j in result.jobs if confirmed_india_location(j.get('location'))]
    result.rejected_locations=result.returned-len(result.jobs)
    return result


_browser_detail_count = 0


def posting_details(job, config, allow_browser=False):
    if job.get('description'):
        return job
    ats = config['ats']
    try:
        if ats in ('workable','kpit','eightfold','oracle_hcm'):
            identifier = job['job_id']
            if ats=='workable':url=f'https://apply.workable.com/api/v2/accounts/tiger-analytics/jobs/{identifier}'
            elif ats=='kpit':url=f'https://talentojo.kpit.com/service/jobs/{identifier}'
            elif ats=='eightfold':
                parsed=urlsplit(config['endpoint']);domain=dict(parse_qsl(parsed.query)).get('domain','')
                url=f'{parsed.scheme}://{parsed.netloc}/api/pcsx/position_details?'+urlencode({'position_id':identifier,'domain':domain,'hl':'en'})
            else:
                parsed=urlsplit(config['endpoint']);url=f'{parsed.scheme}://{parsed.netloc}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?finder=ById;Id={identifier}'
            response = requests.get(url,headers=HEADERS,timeout=(5,15))
            if response.status_code==200:
                data = response.json()
                if ats=='kpit' and isinstance(data.get('job'),dict):data=data['job']
                if ats=='eightfold':data=data.get('data',{}).get('position',data.get('data',{}))
                if ats=='oracle_hcm':data=(data.get('items') or [{}])[0]
                job.update(details_from_record(data))
        else:
            job.update(fetch_details(job['apply_url']))
        if not job.get('description') and ats in ('tata','ramco'):
            response=requests.get(job['apply_url'],headers=HEADERS,timeout=(5,15))
            if response.status_code==200:
                soup=BeautifulSoup(response.text,'html.parser');node=soup.select_one('.jbpam1' if ats=='tata' else '.job-details__content')
                if node:job.update(details_from_record({'description':node.get_text(' ',strip=True)}))
    except (requests.RequestException,ValueError,TypeError):
        pass
    if allow_browser and not job.get('description'):
        global _browser_detail_count
        import os
        if _browser_detail_count < int(os.environ.get('COMPANY_BROWSER_DETAILS_MAX','120')):
            _browser_detail_count += 1
            job.update(browser_posting_details(job))
    return job


def browser_posting_details(job):
    from playwright.sync_api import sync_playwright
    details = {}
    expected = re.sub(r'\s+',' ',job['title']).casefold().strip()
    def matches(title):
        title=re.sub(r'\s+',' ',text(title)).casefold().strip()
        return bool(title and (title==expected or expected.startswith(title+' ')))
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True);page=browser.new_page()
        def observe(r):
            if r.request.resource_type not in ('fetch','xhr') or r.status!=200 or 'json' not in r.headers.get('content-type',''):return
            try:
                data=r.json()
                if isinstance(data,dict):
                    row=data.get('jobPostingInfo') or data.get('job') or data.get('data') or data
                    if isinstance(row,dict):row=row.get('position',row)
                    if isinstance(row,dict) and matches(row.get('title') or row.get('name') or row.get('jobTitle')):
                        candidate=details_from_record(row)
                        if len(candidate.get('description',''))>len(details.get('description','')):details.update(candidate)
            except (ValueError,TypeError):pass
        page.on('response',observe)
        try:
            page.goto(job['apply_url'],wait_until='domcontentloaded',timeout=25000)
            page.wait_for_timeout(3000)
            soup=BeautifulSoup(page.content(),'html.parser')
            headings=[n.get_text(' ',strip=True) for n in soup.select('h1,h2')]
            if any(matches(h) for h in headings):
                for selector in ('.ATS_htmlPreview','[itemprop="description"]','.job-description','.jobdetail-description','.article__content__view','.posting-description'):
                    node=soup.select_one(selector)
                    if node and len(node.get_text(' ',strip=True))>len(details.get('description','')):
                        details.update(details_from_record({'description':node.get_text(' ',strip=True)}))
        except Exception:pass
        finally:browser.close()
    return details
