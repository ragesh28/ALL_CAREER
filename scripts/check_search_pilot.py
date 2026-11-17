"""Run a bounded loopback benchmark and a small Quick Tunnel smoke test."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
from threading import Thread
from time import monotonic, sleep, time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .search_pilot import PilotServer, Search

CHENNAI = {"source": "naukri", "city": "Chennai", "experience": "0"}
ROLE = {**CHENNAI, "role": "Software Engineer"}
SOFTWARE = {**CHENNAI, "category": "software_technical"}
QUERIES = (
    ROLE, SOFTWARE,
    {**CHENNAI, "source": ["naukri", "indeed"], "city": ["Chennai", "Bengaluru"]},
    {"city": "Chennai", "source": "telegram", "walkin": "1"},
    {"source": "naukri", "city": "Chennai", "q": "python"},
)
QUICK_URL = re.compile(rb"https://[a-z0-9-]+\.trycloudflare\.com\b")


def jobs_path(filters):
    return "/jobs?" + urlencode(filters, doseq=True)


def get(base, path, token=None, timeout=6):
    headers = {"Authorization": "Bearer " + token} if token else {}
    try:
        with urlopen(Request(base + path, headers=headers), timeout=timeout) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        with error:
            return error.code, None
    except (OSError, URLError, ValueError):
        return None, None


def page_ids(jobs):
    return [(job.get("url"), job.get("title"), job.get("company"), job.get("location")) for job in jobs]


def same_page(actual, expected):
    return (
        isinstance(actual, dict)
        and actual.get("catalog_version") == expected["catalog_version"]
        and actual.get("total") == expected["total"]
        and actual.get("next_cursor") == expected["next_cursor"]
        and page_ids(actual.get("jobs", [])) == page_ids(expected["jobs"])
    )


def prepared_queries(root):
    summary = json.loads((root / "data/web/summary.json").read_bytes())
    raw = gzip.decompress((root / summary["filtered_catalog"]).read_bytes())
    return json.loads(raw)["queries"]


def parity(search, catalog):
    prepared = prepared_queries(catalog)
    totals = {}
    for name, filters in (
        ("role/Software%20Engineer", ROLE),
        ("software_technical", SOFTWARE),
    ):
        for experience in ("zero", "exact-zero"):
            key = f"naukri/chennai/{name}/{experience}"
            baseline = prepared[key]
            options = {**filters, "exact": int(experience == "exact-zero")}
            first = search.jobs(urlencode(options))
            if first["total"] != baseline["count"]:
                raise ValueError(f"{key}: SQLite count {first['total']} differs from prepared count {baseline['count']}")
            cursor = None
            for file in baseline["pages"][:2]:
                actual = search.jobs(urlencode({**options, "cursor": cursor})) if cursor else first
                expected = json.loads(gzip.decompress((catalog / file).read_bytes()))
                if page_ids(actual["jobs"]) != page_ids(expected):
                    raise ValueError(f"{key}: SQLite page differs from prepared catalog page")
                cursor = actual["next_cursor"]
            totals[key] = first["total"]
    return totals


def benchmark(base, token, expected):
    reports = []
    paths = list(expected)

    def query(index):
        path = paths[index % len(paths)]
        start = monotonic()
        status, page = get(base, path, token)
        elapsed = monotonic() - start
        return elapsed, status == 200 and same_page(page, expected[path])

    for concurrency in (1, 4, 8, 16, 32):
        requests = max(25, concurrency * 3)
        start = monotonic()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(query, range(requests)))
        duration = monotonic() - start
        latencies = sorted(latency for latency, _ in results)
        failures = sum(not passed for _, passed in results)
        reports.append({
            "concurrency": concurrency, "requests": requests, "failures": failures,
            "requests_per_second": round((requests - failures) / duration, 2),
            "p95_ms": round(1000 * latencies[math.ceil(0.95 * requests) - 1], 1),
        })
    return reports


def tunnel_smoke(binary, local, token, health, smoke_path, expected, hold):
    started = monotonic()
    with tempfile.TemporaryDirectory() as temporary:
        log_path = Path(temporary) / "cloudflared.log"
        log = log_path.open("wb")
        with subprocess.Popen(
            [str(binary.resolve()), "--no-autoupdate", "tunnel", "--protocol", "http2", "--url", local],
            stdout=log, stderr=subprocess.STDOUT,
        ) as tunnel:
            log.close()
            try:
                # Never send traffic to an arbitrary hostname from child process output.
                deadline = started + 90
                quick_url = None
                while monotonic() < deadline and tunnel.poll() is None:
                    if not quick_url:
                        match = QUICK_URL.search(log_path.read_bytes())
                        if match:
                            quick_url = match.group().decode("ascii")
                    if quick_url and get(quick_url, "/healthz", token, timeout=4) == (200, health):
                        break
                    sleep(2)
                else:
                    raise RuntimeError("Cloudflare Quick Tunnel did not become ready within 90 seconds")
                ready_at = time()
                ready_seconds = round(monotonic() - started, 2)
                if get(quick_url, "/healthz")[0] != 401:
                    raise RuntimeError("Quick Tunnel origin did not reject an unauthenticated request")
                status, page = get(quick_url, smoke_path, token)
                if status != 200 or not same_page(page, expected):
                    raise RuntimeError(f"Quick Tunnel search differed from loopback (HTTP {status})")
                sleep(hold)
                if get(quick_url, "/healthz", token) != (200, health):
                    raise RuntimeError("Quick Tunnel stopped responding during the readiness window")
                return {"tunnel_seconds": ready_seconds, "ready_at": ready_at, "last_ready_at": time()}
            finally:
                tunnel.terminate()
                try:
                    tunnel.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    tunnel.kill()


def check(args):
    index = json.loads(args.build_report.read_bytes())
    token = secrets.token_urlsafe(32)
    started = monotonic()
    with PilotServer(args.database, token=token) as server:
        worker = Thread(target=server.serve_forever)
        worker.start()
        local = f"http://127.0.0.1:{server.server_port}"
        try:
            health = server.search.info
            if get(local, "/healthz", token) != (200, health):
                raise RuntimeError("Local search API did not become ready")
            local_seconds = round(monotonic() - started, 3)
            cases = {jobs_path(filters): server.search.jobs(urlencode(filters, doseq=True)) for filters in QUERIES}
            report = {
                **index, "runner": args.runner, "server_seconds": local_seconds,
                "runner_started_at": float(os.getenv("PILOT_STARTED_AT", time())),
                "parity": parity(server.search, args.catalog),
            }
            if args.cloudflared:
                smoke_path = jobs_path(ROLE)
                report.update(tunnel_smoke(args.cloudflared, local, token, health, smoke_path,
                                           cases[smoke_path], args.hold_seconds))
            if args.runner == "primary":
                report["benchmark"] = benchmark(local, token, cases)
            return report
        finally:
            server.shutdown()
            worker.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("build_report", type=Path)
    parser.add_argument("--runner", choices=("primary", "replacement"), default="primary")
    parser.add_argument("--cloudflared", type=Path)
    parser.add_argument("--hold-seconds", type=int, default=90)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0 <= args.hold_seconds <= 180:
        parser.error("The test readiness window must be between 0 and 180 seconds")
    report = json.dumps(check(args), indent=2)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    print(report)
