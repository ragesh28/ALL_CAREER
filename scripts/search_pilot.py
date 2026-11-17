"""Read-only All Jobs search API for the isolated GitHub Actions pilot."""
import argparse
import base64
from contextlib import closing
from datetime import date, timedelta
from functools import lru_cache
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
from threading import BoundedSemaphore
from time import monotonic
from urllib.parse import parse_qs, urlsplit

PAGE_SIZE = 50
QUERY_SECONDS = 4
DATE_WINDOWS = {"24h": 1, "3d": 3, "7d": 7, "15d": 15}
CATEGORIES = {
    "sales": ("Sales & Marketing",), "software_technical": ("Software Technical",),
    "non_technical": ("Non-Technical",), "banking": ("Banking & Finance",),
    "hr": ("HR & Staffing",), "pharma": ("Pharma",), "others": ("Others", "Electrical"),
}
SORT_FIELDS = {"latest": "j.id", "oldest": "j.date, j.id", "company": "j.company, j.id"}
MULTI = ("source", "city", "role", "skill", "company", "interview")
SINGLE = ("q", "posted", "as_of", "experience", "exact", "walkin", "category", "sort",
          "version", "cursor", "limit")


class RequestError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def get_parameters(query):
    options = parse_qs(query, keep_blank_values=True, max_num_fields=80)
    for key, values in options.items():
        if key not in SINGLE + MULTI or (key in SINGLE and len(values) != 1):
            raise ValueError("Unknown or repeated filter")
        if any(len(value) > 512 or "\0" in value for value in values):
            raise ValueError("Invalid filter value")
    return (
        {key: options[key][0].strip() for key in SINGLE if key in options},
        {key: sorted({val.strip() for val in options.get(key, []) if val.strip()}) for key in MULTI},
    )


def source_filter(sources):
    clauses, values = ["value IN (" + ",".join("?" for _ in sources) + ")"], list(sources)
    if "telegram" in sources:
        clauses.append("instr(value, 'telegram') > 0")
    if "other" in sources:
        clauses.append("is_other = 1")
    if {"images", "google_images"}.intersection(sources):
        clauses.append("(instr(value, 'google') > 0 OR instr(value, 'image') > 0)")
    return "j.source IN (SELECT value FROM sources WHERE " + " OR ".join(clauses) + ")", values


def experience_filter(year, exact):
    if year == 10:
        return "(j.min_exp IS NOT NULL AND (j.min_exp >= 10 OR j.max_exp >= 10))", []
    if exact:
        return "(j.min_exp = ? AND (j.max_exp IS NULL OR j.max_exp = ?))", [year, year]
    if year == 0:
        return "j.min_exp = 0", []
    return "(j.min_exp <= ? AND (j.max_exp IS NULL OR j.max_exp >= ?))", [year, year]


def match_clause(parts, args):
    return "(" + " OR ".join(parts) + ")", args


def search_filters(options, selections):
    clauses, parameters = [], []

    def add(sql, *args):
        clauses.append(sql)
        parameters.extend(args)

    term = options.get("q", "").lower()
    if term:
        # Trigrams discard nonmatches quickly. The substring check preserves literal punctuation
        # and exact match semantics, including one- and two-character searches.
        trigrams = list(dict.fromkeys(term[i:i + 3] for i in range(len(term) - 2)))[:8]
        if trigrams:
            match = " AND ".join('"' + part.replace('"', '""') + '"' for part in trigrams)
            add("j.id IN (SELECT rowid FROM job_text WHERE job_text MATCH ?)", match)
        add("instr(j.search, ?) > 0", term)
    if selections["source"]:
        part, values = source_filter(selections["source"])
        add(part, *values)
    if selections["city"]:
        cities = [
            re.sub(r"\bnew delhi\b", "delhi", re.sub(r"\bbengaluru\b", "bangalore", city.lower(),
                   flags=re.ASCII), flags=re.ASCII)
            for city in selections["city"]
        ]
        where, args = match_clause(["instr(value, ?) > 0"] * len(cities), cities)
        add(f"j.city IN (SELECT value FROM cities WHERE {where})", *args)
    if selections["role"]:
        known = """(EXISTS (SELECT 1 FROM roles WHERE job_id = j.id AND name = ?)
                    OR (NOT EXISTS (SELECT 1 FROM role_options WHERE name = ?)
                        AND (instr(j.title, ?) > 0 OR instr(j.role, ?) > 0)))"""
        names = selections["role"]
        part, args = match_clause([known] * len(names),
                                  [value for name in names for value in (name, name, name.lower(), name.lower())])
        add(part, *args)
    if "experience" in options:
        if not re.fullmatch(r"[0-9]|10", options["experience"]):
            raise ValueError("Experience must be between 0 and 10")
        part, args = experience_filter(int(options["experience"]), options.get("exact") == "1")
        add(part, *args)
    for key, column in (("skill", "skills"), ("company", "company")):
        if selections[key]:
            values = sorted({value.lower() for value in selections[key]})
            part, args = match_clause([f"instr(j.{column}, ?) > 0"] * len(values), values)
            add(part, *args)

    category = options.get("category", "all")
    if category != "all":
        names = CATEGORIES.get(category)
        if names is None:
            raise ValueError("Unknown category")
        add("j.category IN (" + ",".join("?" for _ in names) + ")", *names)
    posted = options.get("posted", "all")
    if posted != "all":
        if posted not in DATE_WINDOWS:
            raise ValueError("Unknown posted date window")
        today = date.fromisoformat(options["as_of"]) if "as_of" in options else date.today()
        cutoff = today - timedelta(days=DATE_WINDOWS[posted])
        add("j.posted >= ?", cutoff.isoformat())
    if any(options.get(flag, "0") not in ("0", "1") for flag in ("exact", "walkin")):
        raise ValueError("Invalid filter flag")
    if options.get("walkin") == "1" or selections["interview"]:
        add("j.walkin = 1")
    if selections["interview"]:
        values = selections["interview"]
        if any(not re.fullmatch(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (?:[1-9]|[12][0-9]|3[01])",
                                label) for label in values):
            raise ValueError("Invalid interview date")
        placeholders = ",".join("?" for _ in values)
        add(f"EXISTS (SELECT 1 FROM interviews WHERE job_id = j.id AND label IN ({placeholders}))", *values)
    return " AND ".join(clauses) or "1", tuple(parameters)


class Search:
    def __init__(self, database):
        self.uri = Path(database).resolve().as_uri() + "?mode=ro&immutable=1"
        with closing(self.connect()) as db:
            metadata = dict(db.execute("SELECT key, value FROM metadata"))
        self.version = metadata["version"]
        self.info = {
            "catalog_version": self.version, "jobs": int(metadata["total"]),
            "walkins": int(metadata["walkins"]),
        }
        self.count = lru_cache(maxsize=128)(self.count_matches)

    def connect(self):
        return sqlite3.connect(self.uri, uri=True)

    def count_matches(self, where, parameters):
        with closing(self.connect()) as db:
            self.time_limit(db)
            return db.execute("SELECT count(*) FROM jobs j WHERE " + where, parameters).fetchone()[0]

    @staticmethod
    def time_limit(db):
        deadline = monotonic() + QUERY_SECONDS
        db.set_progress_handler(lambda: int(monotonic() > deadline), 5000)

    def jobs(self, query):
        options, selections = get_parameters(query)
        if "version" in options and options["version"] != self.version:
            raise RequestError(409, "Catalog version changed")
        sort = options.get("sort", "latest")
        if sort not in SORT_FIELDS:
            raise ValueError("Unknown sort order")
        limit = int(options.get("limit", str(PAGE_SIZE)))
        if limit < 1:
            raise ValueError("Limit must be positive")
        limit = min(limit, PAGE_SIZE)
        where, args = search_filters(options, selections)
        fingerprint = hashlib.sha256(json.dumps([self.version, sort, where, args]).encode()).hexdigest()
        keyset, position = "", ()
        sort_fields = SORT_FIELDS[sort]
        with closing(self.connect()) as db:
            self.time_limit(db)
            if options.get("cursor"):
                raw = options["cursor"]
                token = json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4), altchars=b"-_", validate=True))
                if (not isinstance(token, list) or len(token) != 2 or token[0] != fingerprint
                        or type(token[1]) is not int):
                    raise ValueError("Cursor belongs to a different search")
                position = db.execute(f"SELECT {sort_fields} FROM jobs j WHERE j.id = ?", (token[1],)).fetchone()
                if not position:
                    raise ValueError("Unknown page position")
                marks = ",".join("?" for _ in position)
                keyset = f" AND ({sort_fields}) > ({marks})"
            rows = db.execute(f"""
                SELECT j.id, j.payload FROM jobs j WHERE ({where}){keyset}
                ORDER BY {sort_fields} LIMIT ?
            """, (*args, *position, limit + 1)).fetchall()

        total = self.count(where, args)
        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            token = json.dumps([fingerprint, rows[-1][0]]).encode()
            next_cursor = base64.urlsafe_b64encode(token).decode().rstrip("=")
        return {
            "catalog_version": self.version, "jobs": [json.loads(payload) for _, payload in rows],
            "total": total, "next_cursor": next_cursor,
        }


class PilotServer(ThreadingHTTPServer):
    request_queue_size = 64

    def __init__(self, database, port=0, token=None, browser_origin=None):
        self.search = Search(database)
        self.token = token
        self.browser_origin = browser_origin
        self.slots = BoundedSemaphore(32)
        super().__init__(("127.0.0.1", port), PilotHandler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            with closing(request):
                request.settimeout(1)
                try:
                    request.sendall(b"HTTP/1.0 429 Too Many Requests\r\nContent-Length: 0\r\nRetry-After: 1\r\n\r\n")
                except OSError:
                    pass
            return
        super().process_request(request, address)

    def process_request_thread(self, request, address):
        try:
            request.settimeout(6)
            super().process_request_thread(request, address)
        finally:
            self.slots.release()

    def handle_error(self, request, client_address):
        # Disconnected clients are normal. Keep URLs and request headers out of pilot logs.
        return


class PilotHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def reply(self, code, data):
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        origin = self.headers.get("Origin")
        if origin and origin == self.server.browser_origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        expected = self.server.token
        if expected:
            sent = self.headers.get("Authorization", "")
            authorized = secrets.compare_digest(sent.encode("utf-8"), ("Bearer " + expected).encode())
        else:
            authorized = bool(self.server.browser_origin and self.headers.get("Origin") == self.server.browser_origin)
        if not authorized:
            self.reply(401, {"error": "Pilot authorization required"})
            return

        try:
            url = urlsplit(self.path)
            if url.path == "/healthz":
                self.reply(200, self.server.search.info)
            elif url.path == "/jobs":
                self.reply(200, self.server.search.jobs(url.query))
            else:
                self.reply(404, {"error": "Unknown endpoint"})
        except RequestError as error:
            self.reply(error.status, {"error": str(error)})
        except (ValueError, OverflowError):
            self.reply(400, {"error": "Invalid filters or page cursor"})
        except sqlite3.Error:
            self.reply(503, {"error": "Search is temporarily unavailable"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--browser-origin", choices=("http://localhost:5173", "http://127.0.0.1:5173"))
    args = parser.parse_args()
    token = os.environ.get("SEARCH_PILOT_TOKEN")
    if not token and not args.browser_origin:
        parser.error("Set SEARCH_PILOT_TOKEN or authorize a local Vite browser origin")
    with PilotServer(args.database, args.port, token, args.browser_origin) as service:
        print(f"Pilot SQLite API listening on loopback port {service.server_port}", flush=True)
        service.serve_forever()
