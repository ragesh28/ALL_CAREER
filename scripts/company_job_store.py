"""One retention/identity contract shared by the big-company writers."""
import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from scripts.company_ai import atomic_json, load_json

PUBLIC_FIELDS = {'title', 'company', 'location', 'apply_url', 'job_id', 'source', 'experience', 'salary',
                 'date_posted', 'posted', 'fetched_at', 'first_seen', 'last_seen', 'company_logo',
                 'company_website', 'job_type', 'work_mode', 'employment_type', 'is_walkin',
                 'walkin_date', 'walkin_dates', 'walkin_time', 'walkin_venue', 'contact_phone', 'contact_email', 'metadata_checked_at'}


def india_today():
    return datetime.now(timezone(timedelta(hours=5,minutes=30))).date()


def native_id(job):
    value = str(job.get('job_id') or job.get('id') or '').strip()
    return '' if value.casefold() in ('none','nan','null','undefined') else value


def canonical_url(value):
    parts = urlsplit(str(value).strip())
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        return ''
    # Query strings can contain the only requisition ID. Keep them except known tracking fields.
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not re.match(r'^(utm_|ref$|source$|src$|tracking|gh_src$|rx_|token$)', k, re.I)]
    path = re.sub(r'/en[-_]US(?=/)', '', parts.path, flags=re.I).rstrip('/')
    fragment = parts.fragment if re.search(r'\d', parts.fragment) else ''
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), fragment))


def identity(job):
    url = canonical_url(job.get('apply_url') or job.get('url') or '')
    jid = native_id(job)
    source_id = job.get('company','').casefold() + '|' + jid if jid else url
    return hashlib.sha256(source_id.encode()).hexdigest() if url else ''


def posted_day(value, today=None):
    """Parse original publication only; updated-at fields must not be supplied here."""
    today = today or india_today()
    value = str(value or '').strip()
    if not value or value.lower() in ('none', 'nan', 'null'):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace('Z','+00:00')) if 'T' in value else None
        parsed = stamp.astimezone(timezone(timedelta(hours=5,minutes=30))).date() if stamp and stamp.tzinfo else date.fromisoformat(value[:10])
        return parsed if parsed <= today + timedelta(days=1) else None
    except ValueError:
        pass
    match = re.fullmatch(r'(?:posted\s+)?(\d+)\+?\s*(days?|weeks?|months?)\s+ago', value, re.I)
    if match:
        return today - timedelta(days=int(match[1]) * (7 if match[2].lower().startswith('week') else 30 if match[2].lower().startswith('month') else 1))
    if re.fullmatch(r'(?:posted\s+)?(today|yesterday|just now)', value, re.I):
        return today - timedelta(days=int('yesterday' in value.lower()))
    for fmt in ('%d-%b-%Y', '%B %d, %Y', '%b %d, %Y', '%d %B %Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def public_job(job):
    return {k: v for k, v in job.items() if k in PUBLIC_FIELDS and v is not None and v != ''}


class CompanyJobStore:
    def __init__(self, root='.', today=None):
        self.root = Path(root)
        self.today = today or india_today()
        self.directory = self.root / 'data/company_job_history'
        self.file = self.root / 'workday_scraper/big_company_jobs.json'
        self.jobs = {}
        self.histories = {}
        self.new_count = self.updated_count = self.old_count = 0
        self.legacy_seen = load_json(self.root / 'seen_job_ids.json', {})
        for job in load_json(self.file, []):
            if not isinstance(job, dict):
                continue
            key = identity(job)
            if not key:
                continue
            clean = public_job(job)
            clean['apply_url'] = job.get('apply_url') or job.get('url')
            company = clean.get('company', 'Unknown')
            entries = self.history(company)['entries']
            first = str(job.get('first_seen') or job.get('fetched_at') or job.get('fetchedAt') or self.today.isoformat())[:10]
            if not posted_day(first,self.today):first=self.today.isoformat()
            record = entries.setdefault(key, {'first_seen': first, 'last_seen': first, 'url': clean['apply_url'], 'job_id': str(job.get('job_id', ''))})
            if not posted_day(record.get('first_seen'),self.today):record['first_seen']=first
            clean['first_seen'] = clean['fetched_at'] = record['first_seen']
            published = posted_day(record.get('date_posted') or clean.get('date_posted') or clean.get('posted'), self.today)
            if published:
                record['date_posted'] = published.isoformat()
            cutoff = min(published or self.today, posted_day(record['first_seen'], self.today) or self.today)
            record['expired'] = bool(record.get('expired') or (self.today-cutoff).days >= 30)
            if not record['expired']:
                self.jobs.setdefault(key, clean)

    def history(self, company):
        slug = re.sub(r'[^a-z0-9]+', '-', company.casefold()).strip('-') or 'unknown'
        if slug not in self.histories:
            self.histories[slug] = load_json(self.directory / (slug + '.json'), {'company': company, 'entries': {}})
        return self.histories[slug]

    def is_known(self, job):
        return identity(job) in self.jobs or identity(job) in self.history(job.get('company', 'Unknown'))['entries']

    def upsert(self, job):
        key = identity(job)
        if not key or not job.get('title') or not job.get('company'):
            return 'invalid'
        entries = self.history(job['company'])['entries']
        today = self.today.isoformat()
        jid = native_id(job)
        # Native requisition IDs survive URL changes, locale changes and tracking parameters.
        previous_key = next((k for k, e in entries.items() if (jid and e.get('job_id') == jid) or (canonical_url(e.get('url') or '') == canonical_url(job.get('apply_url') or job.get('url') or '') and not (jid and e.get('job_id') and jid != e.get('job_id')))), None)
        if previous_key and not jid and entries[previous_key].get('job_id'):
            jid = entries[previous_key]['job_id']
            key = identity({**job,'job_id':jid})
        if previous_key and previous_key != key:
            entries[key] = entries.pop(previous_key)
            if previous_key in self.jobs:
                self.jobs[key] = self.jobs.pop(previous_key)
        old = entries.get(key)
        legacy = self.legacy_seen.get(job['company'], [])
        was_legacy_seen = jid in legacy or job.get('apply_url') in legacy
        first = old.get('first_seen') if old else today
        original = posted_day(job.get('date_posted') or job.get('posted'), self.today)
        prior_original = posted_day(old.get('date_posted'),self.today) if old else None
        original = min(original,prior_original) if original and prior_original else original or prior_original
        # Remember older records without publishing them as newly discovered work.
        entries[key] = {'first_seen': first, 'last_seen': today, 'url': job.get('apply_url') or job.get('url'), 'job_id': jid, 'missing_scans': 0, 'date_posted':original.isoformat() if original else '', 'expired':bool(old and old.get('expired'))}
        age_day = min(original or self.today, posted_day(first, self.today) or self.today)
        if entries[key]['expired'] or (self.today - age_day).days >= 30 or (was_legacy_seen and key not in self.jobs and not old):
            entries[key]['expired'] = True
            if was_legacy_seen and not old:
                entries[key]['first_seen'] = (self.today - timedelta(days=30)).isoformat()
            self.jobs.pop(key, None)
            self.old_count += 1
            return 'old'
        clean = public_job({**job, 'apply_url': job.get('apply_url') or job.get('url'), 'job_id': jid,
                            'first_seen': first, 'fetched_at': first, 'last_seen': today})
        if original:
            clean['date_posted'] = original.isoformat()
            clean['posted'] = original.isoformat()
        if key in self.jobs:
            before = self.jobs[key].copy()
            # Missing extraction must not erase already verified metadata.
            self.jobs[key].update(clean)
            self.updated_count += before != self.jobs[key]
            return 'existing'
        if old:
            # Replay after a history-first crash: restore the young listing with
            # its original first_seen, without counting it as newly discovered.
            self.jobs[key] = clean
            return 'existing'
        self.jobs[key] = clean
        self.new_count += 1
        return 'new'

    def reconcile(self, company, present_keys, complete=False, verify_closed=None):
        """Failures, pagination caps and partial pages never delete history IDs."""
        if not complete:
            return 0
        entries = self.history(company)['entries']
        removed = 0
        for key, entry in list(entries.items()):
            if key in present_keys:
                entry['missing_scans'] = 0
                continue
            entry['missing_scans'] = entry.get('missing_scans', 0) + 1
            if entry['missing_scans'] >= 2 and verify_closed and verify_closed(entry['url']):
                del entries[key]
                self.jobs.pop(key, None)
                removed += 1
        return removed

    def save(self):
        jobs = sorted(self.jobs.values(), key=lambda j: (j.get('first_seen', ''), j.get('date_posted', '')), reverse=True)
        # Write history first. A crash before the catalog write can be replayed safely:
        # first_seen is retained; current records younger than 30 days are restored below.
        for slug, history in self.histories.items():
            atomic_json(self.directory / (slug + '.json'), history)
        atomic_json(self.file, jobs)
        atomic_json(self.root / 'data/big_company_jobs.json', jobs)
        return len(jobs)


def save_legacy_batch(jobs, existing=None, company=None, root=None):
    """Legacy entry points use the same AI/privacy/identity rules as the new workflow."""
    from scripts.company_ai import extract_transient
    from scripts.company_job_details import confirmed_india_location, details_from_record
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    store = CompanyJobStore(root)
    for raw in jobs:
        job = {**raw, **details_from_record(raw)}
        job['company'] = company or job.get('company')
        job['apply_url'] = job.get('apply_url') or job.get('url')
        if not job.get('date_posted'):
            job['date_posted'] = raw.get('posted') or raw.get('date') or ''
        if not confirmed_india_location(job.get('location')):
            continue
        previous = store.jobs.get(identity(job), {})
        if not previous.get('metadata_checked_at'):
            extract_transient(job)
        store.upsert(job)
    store.save()
    if existing is not None:
        existing[:] = list(store.jobs.values())
    return store.new_count


def without_descriptions(value):
    if isinstance(value, dict):
        return {k:without_descriptions(v) for k,v in value.items()
                if k.casefold() not in ('description','jobdescription','job_description','content','content_plain','description_source','descriptionhtml','descriptionplain','jobdescriptionhtml','jobdescriptionplain','jobdescriptiontext','externaldescriptionstr','externalqualificationsstr')
                and not (k.casefold().endswith('description') and isinstance(v,str))}
    if isinstance(value, list):
        return [without_descriptions(v) for v in value]
    return value
