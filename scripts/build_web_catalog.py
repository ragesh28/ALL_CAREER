"""Build static, newest-first browser pages without a database server.

The temporary SQLite sort keeps memory bounded. Original scraper files are untouched.
Page names are content hashes so an open browser keeps a consistent catalog snapshot.
"""
import argparse
import hashlib
import gzip
import json
import re
import sqlite3
import tempfile
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {'bengaluru': 'bangalore', 'blr': 'bangalore', 'new delhi': 'delhi'}
WALKIN = re.compile(r'\b(?:walk[ -]?in|walking interview|direct interview)\b', re.I)


def city_name(value):
    if isinstance(value, dict):
        value = value.get('city') or value.get('name') or 'Unknown'
    value = str(value or 'Unknown').strip()
    return ALIASES.get(value.lower(), value.lower())


def normalize(job):
    j = dict(job)
    for field in ('company', 'location'):
        if isinstance(j.get(field), dict):
            j[field] = j[field].get('city' if field == 'location' else 'name') or 'Unknown'
    j['title'] = str(j.get('title') or j.get('role') or 'Position')
    j['source'] = str(j.get('source') or j.get('platform') or 'other').lower().replace(' ', '_')
    j['url'] = j.get('url') or j.get('apply_url') or j.get('telegram_url') or ''
    date = str(j.get('date_posted') or j.get('fetchedAt') or j.get('fetched_at') or j.get('date') or '')
    j['date_posted'] = date[:10] if re.match(r'^\d{4}-\d{2}-\d{2}', date) else ''
    j['is_walkin'] = j.get('is_walkin') in (True, 'true') or bool(j.get('walkin_date') or j.get('walkin_dates')) or bool(WALKIN.search(j['title'] + ' ' + str(j.get('description') or ''))) or j['source'] in ('google_images', 'flyer')
    # Only display data goes into browser pages; full originals stay in source shards.
    keys = ('title', 'role', 'company', 'location', 'source', 'url', 'date_posted', 'experience', 'salary', 'skills', 'is_walkin', 'walkin_date', 'walkin_dates', 'walkin_time', 'telegram_url', 'contact_email', 'contact_phone', 'flyer_image_url', 'venue', 'description', 'role_search', 'job_type')
    return {k: (str(j[k])[:3000] if k == 'description' else j[k]) for k in keys if j.get(k) is not None}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)
    return data


def build(root=ROOT, page_size=250):
    root = Path(root)
    out = root / 'data/web'
    with tempfile.TemporaryDirectory() as temporary, closing(sqlite3.connect(str(Path(temporary) / 'sort.db'))) as db:
        db.execute('CREATE TABLE jobs (id TEXT PRIMARY KEY, date TEXT, payload TEXT, walkin INTEGER, city TEXT, source TEXT)')
        sources = sorted((root / 'data/jobs').glob('*/*.json'))
        sources += [root / 'data/index/walkin_jobs.json']
        for path in sources:
            if not path.exists():
                continue
            # Fail rather than publishing a silently incomplete catalog.
            rows = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(rows, list):
                raise ValueError(f'Expected job array: {path}')
            inserts = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                j = normalize(row)
                identity = [j.get('url'), j['title'].strip().lower(), str(j.get('company', '')).strip().lower(), city_name(j.get('location'))]
                key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
                inserts.append((key, j['date_posted'], json.dumps(j, ensure_ascii=False, separators=(',', ':')), int(j['is_walkin']), city_name(j.get('location')), j['source']))
            db.executemany('INSERT OR IGNORE INTO jobs VALUES (?,?,?,?,?,?)', inserts)
        db.commit()
        db.execute('CREATE INDEX newest ON jobs(date DESC, id)')

        def pages(query, params=()):
            descriptors, batch, size = [], [], 0
            def flush():
                nonlocal batch, size
                data = json.dumps(batch, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                compressed = gzip.compress(data, mtime=0)
                name = hashlib.sha256(compressed).hexdigest()[:24] + '.json.gz'
                target = out / 'pages' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.write_bytes(compressed)
                descriptors.append({'path': 'data/web/pages/' + name, 'count': len(batch), 'newest': batch[0].get('date_posted', ''), 'sources': sorted({j['source'] for j in batch}), 'locations': sorted({city_name(j.get('location')) for j in batch})})
                batch, size = [], 0
            for payload, in db.execute(query, params):
                item = json.loads(payload)
                # Day boundaries keep historical pages stable as new jobs arrive.
                if batch and (len(batch) >= page_size or size + len(payload.encode('utf-8')) > 240000 or item['date_posted'] != batch[0]['date_posted']):
                    flush()
                batch.append(item); size += len(payload.encode('utf-8'))
            if batch:
                flush()
            return descriptors

        feed = pages('SELECT payload FROM jobs ORDER BY date DESC, id')
        walkin_pages = {}
        for city, in db.execute('SELECT DISTINCT city FROM jobs WHERE walkin=1').fetchall():
            walkin_pages[city] = pages('SELECT payload FROM jobs WHERE walkin=1 AND city=? ORDER BY date DESC,id', (city,))

        counts = lambda column, where='': dict(db.execute(f'SELECT {column},count(*) FROM jobs {where} GROUP BY {column}'))
        date_groups = Counter()
        cross = defaultdict(Counter)
        for payload, city, source in db.execute('SELECT payload,city,source FROM jobs WHERE walkin=1'):
            j = json.loads(payload)
            raw = j.get('walkin_dates') or ([j['walkin_date']] if j.get('walkin_date') else [])
            date_groups[(city, source, json.dumps(raw), j.get('date_posted', ''))] += 1
            cross[source][city] += 1
        summary = {
            'schema': 1, 'generated_at': datetime.now(timezone.utc).isoformat(),
            'total_jobs': db.execute('SELECT count(*) FROM jobs').fetchone()[0],
            'sources': counts('source'), 'locations': counts('city'),
            'walkins': {'total': db.execute('SELECT count(*) FROM jobs WHERE walkin=1').fetchone()[0], 'locations': counts('city', 'WHERE walkin=1'), 'sources': counts('source', 'WHERE walkin=1'), 'source_locations': dict(cross), 'date_groups': [[city, src, json.loads(raw), date, count] for (city, src, raw, date), count in date_groups.items()]}
        }
        source_locations = defaultdict(dict)
        for source, city, count in db.execute('SELECT source,city,count(*) FROM jobs GROUP BY source,city'):
            source_locations[source][city] = count
        summary['source_locations'] = dict(source_locations)
        manifest_data = {'schema': 1, 'page_size': page_size, 'total_jobs': summary['total_jobs'], 'pages': feed, 'walkins': walkin_pages}
        manifest_bytes = json.dumps(manifest_data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        manifest_name = 'manifest-' + hashlib.sha256(manifest_bytes).hexdigest()[:24] + '.json.gz'
        (out / manifest_name).parent.mkdir(parents=True, exist_ok=True)
        (out / manifest_name).write_bytes(gzip.compress(manifest_bytes, mtime=0))
        summary['manifest'] = 'data/web/' + manifest_name
        write_json(out / 'summary.json', summary)
        preview = [json.loads(row[0]) for row in db.execute('SELECT payload FROM jobs ORDER BY date DESC,id LIMIT 50')]
        write_json(out / 'latest.json', preview)
        # Preserve source indexes: scraper commits can arrive while publishing.
        retention_path = out / 'retention.json'
        retained = json.loads(retention_path.read_text()) if retention_path.exists() else {}
        now = datetime.now(timezone.utc).timestamp()
        paths = {p['path'] for p in feed}
        paths.update(p['path'] for rows in walkin_pages.values() for p in rows)
        paths.add('data/web/' + manifest_name)
        for path in paths:
            retained[path] = now
        for path, referenced in list(retained.items()):
            if now - referenced > 3 * 86400:
                target = (root / path).resolve()
                if not target.is_relative_to(out.resolve()):
                    raise ValueError('Invalid retention path')
                target.unlink(missing_ok=True)
                del retained[path]
        write_json(retention_path, retained)
        print(f"Published {summary['total_jobs']:,} jobs, {len(feed):,} browser pages; walk-ins: {summary['walkins']['total']:,}", flush=True)
        return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=str(ROOT))
    parser.add_argument('--page-size', type=int, default=250)
    args = parser.parse_args()
    if not 1 <= args.page_size <= 250:
        parser.error('page-size must be between 1 and 250')
    build(args.root, args.page_size)
