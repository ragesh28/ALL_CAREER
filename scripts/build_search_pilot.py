"""Build and validate a temporary search index from one public catalog snapshot."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
from time import monotonic

from .build_web_catalog import city_name

NORMALIZER = Path(__file__).with_name("search_pilot_normalize.mjs")
SCHEMA = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    catalog_key BLOB NOT NULL UNIQUE,
    catalog_source TEXT NOT NULL, catalog_city TEXT NOT NULL, catalog_walkin INTEGER NOT NULL,
    source TEXT NOT NULL, city TEXT NOT NULL, company TEXT NOT NULL,
    date TEXT NOT NULL, posted TEXT NOT NULL,
    category TEXT NOT NULL, min_exp REAL, max_exp REAL,
    title TEXT NOT NULL, role TEXT NOT NULL, search TEXT NOT NULL, skills TEXT NOT NULL,
    walkin INTEGER NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE cities (value TEXT PRIMARY KEY) WITHOUT ROWID;
CREATE TABLE sources (value TEXT PRIMARY KEY, is_other INTEGER NOT NULL) WITHOUT ROWID;
CREATE TABLE role_options (name TEXT PRIMARY KEY) WITHOUT ROWID;
CREATE TABLE roles (job_id INTEGER, name TEXT, PRIMARY KEY (job_id, name)) WITHOUT ROWID;
CREATE TABLE interviews (job_id INTEGER, label TEXT, PRIMARY KEY (job_id, label)) WITHOUT ROWID;
CREATE VIRTUAL TABLE job_text USING fts5(search, tokenize='trigram case_sensitive 1',
    content='', detail=none, columnsize=0);
"""
INDEXES = """
CREATE INDEX jobs_source_city_exp ON jobs(source, city, min_exp);
CREATE INDEX jobs_city_exp ON jobs(city, min_exp);
CREATE INDEX jobs_category ON jobs(category);
CREATE INDEX jobs_posted ON jobs(posted);
CREATE INDEX jobs_walkin ON jobs(walkin) WHERE walkin=1;
CREATE INDEX jobs_oldest ON jobs(date, id);
CREATE INDEX jobs_company ON jobs(company, id);
"""


def read_catalog(root):
    summary = json.loads((root / "data/web/summary.json").read_bytes())
    match = re.fullmatch(r"data/web/manifest-([0-9a-f]{24})\.json\.gz", summary["manifest"])
    if (summary["schema"] != 1 or not re.fullmatch(r"[0-9a-f]{64}", summary["inputs_hash"])
            or not match):
        raise ValueError("Invalid catalog summary")
    raw = gzip.decompress((root / summary["manifest"]).read_bytes())
    if hashlib.sha256(raw).hexdigest()[:24] != match[1]:
        raise ValueError("Catalog manifest checksum mismatch")
    manifest = json.loads(raw)
    if manifest["schema"] != 1 or manifest["total_jobs"] != summary["total_jobs"]:
        raise ValueError("Catalog summary and manifest disagree")
    if sum(page["count"] for page in manifest["pages"]) != summary["total_jobs"]:
        raise ValueError("Catalog page counts do not add up to the published total")
    return summary, manifest["pages"]


def read_page(root, descriptor):
    path = descriptor["path"]
    match = re.fullmatch(r"data/web/pages/([0-9a-f]{24})\.json\.gz", path)
    if not match:
        raise ValueError("Invalid catalog page path")
    packed = (root / path).read_bytes()
    if hashlib.sha256(packed).hexdigest()[:24] != match[1]:
        raise ValueError(f"Catalog page checksum mismatch: {path}")
    jobs = json.loads(gzip.decompress(packed))
    if not isinstance(jobs, list) or not jobs or len(jobs) != descriptor["count"]:
        raise ValueError(f"Wrong number of jobs in {path}")
    if (descriptor["newest"] != jobs[0]["date_posted"]
            or descriptor["sources"] != sorted({job["source"] for job in jobs})
            or descriptor["locations"] != sorted({city_name(job.get("location")) for job in jobs})):
        raise ValueError(f"Catalog page facets disagree: {path}")
    return jobs


def job_key(job):
    identity = [job["url"], job["title"].strip().lower(),
                str(job.get("company", "")).strip().lower(), city_name(job.get("location"))]
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).digest()


def insert_page(db, normalizer, jobs, first_id):
    normalizer.stdin.write(json.dumps(jobs, ensure_ascii=True) + "\n")
    normalizer.stdin.flush()
    output = normalizer.stdout.readline()
    if not output:
        raise ValueError("Catalog filter normalizer exited before finishing")
    indexed = json.loads(output)
    if len(indexed) != len(jobs):
        raise ValueError("Catalog filter normalizer changed the page length")

    rows, roles, interviews, sources, cities = [], [], [], set(), set()
    for job_id, (job, fields) in enumerate(zip(jobs, indexed), first_id):
        rows.append((
            job_id, job_key(job), job["source"], city_name(job.get("location")), int(job["is_walkin"]),
            fields["source"], fields["city"], fields["company"], fields["date"], fields["posted"],
            fields["category"], fields["min"], fields["max"], fields["title"], fields["role"],
            fields["search"], fields["skills"], fields["walkin"],
            json.dumps(job, ensure_ascii=False, separators=(",", ":")),
        ))
        cities.add((fields["city"],))
        sources.add((fields["source"], fields["other"]))
        roles.extend((job_id, role) for role in fields["roles"])
        interviews.extend((job_id, label) for label in fields["interviews"])

    placeholders = ",".join("?" for _ in rows[0])
    db.executemany(f"INSERT INTO jobs VALUES ({placeholders})", rows)
    db.executemany("INSERT OR IGNORE INTO cities VALUES (?)", sorted(cities))
    db.executemany("INSERT OR IGNORE INTO sources VALUES (?, ?)", sorted(sources))
    db.executemany("INSERT INTO roles VALUES (?, ?)", roles)
    db.executemany("INSERT INTO interviews VALUES (?, ?)", interviews)
    db.executemany("INSERT INTO job_text(rowid, search) VALUES (?, ?)",
                   ((row[0], fields["search"]) for row, fields in zip(rows, indexed)))


def verify_counts(db, summary):
    totals = [0, 0]
    sources = [Counter(), Counter()]
    cities = [Counter(), Counter()]
    combinations = [defaultdict(Counter), defaultdict(Counter)]
    for source, city, walkin, count in db.execute("""
        SELECT catalog_source, catalog_city, catalog_walkin, count(*)
        FROM jobs GROUP BY catalog_source, catalog_city, catalog_walkin
    """):
        for group in range(walkin + 1):
            totals[group] += count
            sources[group][source] += count
            cities[group][city] += count
            combinations[group][source][city] += count
    if totals != [summary["total_jobs"], summary["walkins"]["total"]]:
        raise ValueError(f"SQLite total or walk-in count differs from the published catalog: {totals}")
    for group, expected in enumerate((summary, summary["walkins"])):
        if (sources[group] != expected["sources"] or cities[group] != expected["locations"]
                or combinations[group] != expected["source_locations"]):
            raise ValueError("SQLite source or city counts differ from the published catalog")


def build(root, output):
    root, output = Path(root), Path(output)
    summary, pages = read_catalog(root)
    start = monotonic()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Validate the whole replacement before changing the path readers use.
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        db_path = Path(tmp) / "pilot.sqlite"
        with closing(sqlite3.connect(db_path)) as db:
            db.execute("PRAGMA journal_mode=OFF")
            db.execute("PRAGMA synchronous=OFF")
            db.execute("PRAGMA cache_size=-65536")
            db.execute("PRAGMA temp_store=FILE")
            db.executescript(SCHEMA)
            next_id = 1
            previous_date = "9999-99-99"
            with subprocess.Popen(["node", str(NORMALIZER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, encoding="utf-8") as normalizer:
                try:
                    options = json.loads(normalizer.stdout.readline())
                    db.executemany("INSERT INTO role_options VALUES (?)", ((name,) for name in options))
                    for page in pages:
                        jobs = read_page(root, page)
                        for job in jobs:
                            if job["date_posted"] > previous_date:
                                raise ValueError("Catalog pages must be ordered newest first")
                            previous_date = job["date_posted"]
                        insert_page(db, normalizer, jobs, next_id)
                        next_id += len(jobs)
                finally:
                    normalizer.stdin.close()
                if normalizer.wait():
                    raise ValueError("Catalog filter normalizer failed")
            db.commit()
            db.executescript(INDEXES)
            verify_counts(db, summary)
            check = db.execute("PRAGMA quick_check").fetchone()[0]
            if check != "ok":
                raise ValueError(f"SQLite validation failed: {check}")
            db.executemany("INSERT INTO metadata VALUES (?, ?)", (
                ("version", summary["inputs_hash"]),
                ("total", str(summary["total_jobs"])),
                ("walkins", str(summary["walkins"]["total"])),
            ))
            db.commit()
        os.replace(db_path, output)

    with output.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    return {
        "catalog_version": summary["inputs_hash"], "jobs": summary["total_jobs"],
        "walkins": summary["walkins"]["total"], "pages": len(pages),
        "build_seconds": round(monotonic() - start, 2),
        "database_bytes": output.stat().st_size, "database_sha256": digest,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog_root", type=Path)
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.catalog_root, args.database), indent=2))
