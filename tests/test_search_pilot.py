import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.build_search_pilot import build, read_catalog
from scripts.build_web_catalog import build as publish
from scripts.search_pilot import PilotServer, RequestError, Search


def listing(number, **fields):
    return {
        "title": f"Software Engineer {number}", "company": "Example",
        "location": "Chennai", "source": "naukri",
        "experience": "0–2 years", "date_posted": "2026-11-15",
        "url": f"https://example.test/listing/{number}", **fields,
    }


class SearchPilotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.archive = cls.root / "data/job_archives/all_jobs_1.json"
        cls.archive.parent.mkdir(parents=True)
        cls.rows = [listing(i) for i in range(101)] + [
            listing("exact", experience="0 years", date_posted="2026-11-16",
                    description='Uses "C++" and café tools', skills=["Python"]),
            listing("undated", experience="0 years", date_posted=""),
            listing("old", experience="4 years", date_posted="2026-11-09"),
            listing("alias", source="indeed", location="Bengaluru", company="AB Tech"),
            listing("walk", source="telegram_post", title="Python Developer Walk-in",
                    walkin_dates=["2026-11-17", "2026-11-18"], is_walkin=True),
            listing("flyer", source="google_image", title="Walk-in Help Desk", is_walkin=True),
            listing("electrical", title="Electrical Purchase Executive", experience="0–2 years"),
            listing("employer", source="example_careers", company="Other Employer", location="Mumbai"),
        ]
        # The same imported ad can also exist in its granular shard.
        shard = cls.root / "data/jobs/software/naukri_chennai.json"
        shard.parent.mkdir(parents=True)
        shard.write_text(json.dumps([cls.rows[0]]), encoding="utf-8")
        cls.archive.write_text(json.dumps(cls.rows), encoding="utf-8")
        cls.summary = publish(cls.root, page_size=25)
        cls.database = cls.root / "pilot.sqlite"
        cls.metrics = build(cls.root, cls.database)
        cls.search = Search(cls.database)

    def query_jobs(self, **params):
        return self.search.jobs(urlencode(params, doseq=True))

    def test_snapshot_count_and_filters_with_stable_pagination(self):
        self.assertEqual(self.metrics["jobs"], len(self.rows))
        self.assertEqual(self.metrics["walkins"], 2)
        self.assertEqual(self.metrics["catalog_version"], self.summary["inputs_hash"])
        filters = dict(source="naukri", city="Chennai", role="Software Engineer", experience=0)
        first = self.query_jobs(**filters, limit=500)
        self.assertEqual(first["total"], 103)
        self.assertEqual(len(first["jobs"]), 50)
        self.assertTrue(first["jobs"][0]["title"].endswith("exact"))
        second = self.query_jobs(**filters, cursor=first["next_cursor"])
        third = self.query_jobs(**filters, cursor=second["next_cursor"])
        urls = [item["url"] for page in (first, second, third) for item in page["jobs"]]
        self.assertEqual((len(urls), len(set(urls))), (103, 103))
        self.assertEqual(len(third["jobs"]), 3)
        self.assertIsNone(third["next_cursor"])
        exact = self.query_jobs(**filters, exact=1)
        self.assertEqual(len(exact["jobs"]), 2)
        self.assertEqual(self.query_jobs(**filters, exact=1, posted="24h", as_of="2026-11-16")["total"], 1)
        self.assertEqual(self.query_jobs(**filters, exact=1, sort="oldest")["jobs"][0]["date_posted"], "")
        self.assertEqual(self.query_jobs(category="software_technical", source="naukri", experience=0)["total"], 103)
        for sort in ("oldest", "company"):
            first_page = self.query_jobs(**filters, sort=sort, limit=9)
            next_page = self.query_jobs(**filters, sort=sort, limit=9, cursor=first_page["next_cursor"])
            self.assertFalse({job["url"] for job in first_page["jobs"]} & {job["url"] for job in next_page["jobs"]})

    def test_source_city_role_search_skills_and_walkins(self):
        self.assertEqual(self.query_jobs(source=["naukri", "indeed"], city=["Bengaluru", "Chennai"],
                                         sort="company")["jobs"][0]["company"], "AB Tech")
        self.assertEqual(self.query_jobs(source="other", city="Mumbai")["total"], 1)
        self.assertEqual(self.query_jobs(source="telegram", interview=["Nov 17", "Nov 19"])["total"], 1)
        self.assertEqual(self.query_jobs(source="images", walkin=1)["total"], 1)
        self.assertEqual(self.query_jobs(source="telegram", interview="Nov 19")["total"], 0)
        self.assertEqual(self.query_jobs(city="chennai", role="Python Developer", walkin=1)["total"], 1)
        self.assertEqual(self.query_jobs(city="chennai", role="walk-in", walkin=1)["total"], 2)
        for keyword in ('"C++"', "café tools", "C++", "é", "uses  \""):
            with self.subTest(keyword=keyword):
                self.assertEqual(self.query_jobs(city="Chennai", q=keyword)["total"], int("  " not in keyword))
        self.assertEqual(self.query_jobs(skill=["python", "rust"], company="Example")["total"], 2)
        empty = self.query_jobs(source="unlisted", city="Chennai")
        self.assertEqual((empty["total"], empty["jobs"], empty["next_cursor"]), (0, [], None))

    def test_rejects_mismatched_snapshot_and_cursor(self):
        cursor = self.query_jobs(source="naukri", limit=1)["next_cursor"]
        with self.assertRaises(ValueError):
            self.query_jobs(source="indeed", cursor=cursor)
        with self.assertRaises(ValueError):
            self.query_jobs(cursor="%%")
        with self.assertRaises(RequestError) as error:
            self.query_jobs(version="outdated")
        self.assertEqual(error.exception.status, 409)

    def test_missing_page_keeps_previous_snapshot_and_removal_changes_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(self.root / "data", root / "data")
            target = root / "copy.sqlite"
            shutil.copyfile(self.database, target)
            original = hashlib.sha256(target.read_bytes()).hexdigest()
            _, pages = read_catalog(root)
            (root / pages[0]["path"]).write_bytes(b"Broken catalog page")
            with self.assertRaises(ValueError):
                build(root, target)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), original)

            # Regenerate the original content-addressed path before simulating a new release.
            shutil.copyfile(self.root / pages[0]["path"], root / pages[0]["path"])
            archive = root / self.archive.relative_to(self.root)
            archive.write_text(json.dumps([job for job in self.rows if job["source"] != "indeed"]), encoding="utf-8")
            summary = publish(root, page_size=25)
            self.assertNotEqual(summary["inputs_hash"], self.search.version)
            report = build(root, target)
            self.assertEqual(report["jobs"], self.metrics["jobs"] - 1)
            self.assertEqual(Search(target).jobs("source=indeed")["total"], 0)

    def test_auth_readiness_and_one_http_page(self):
        with PilotServer(self.database, token="short-lived-fixture") as server:
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}"
                with self.assertRaises(HTTPError) as error:
                    urlopen(url + "/healthz", timeout=2)
                with error.exception:
                    self.assertEqual(error.exception.code, 401)
                for path in ("/healthz", "/jobs?source=naukri&city=Chennai"):
                    request = Request(url + path, headers={"Authorization": "Bearer short-lived-fixture"})
                    with urlopen(request, timeout=2) as response:
                        self.assertEqual(response.headers["Cache-Control"], "no-store")
                        data = json.load(response)
                        self.assertEqual(data["catalog_version"], self.search.version)
                self.assertEqual(len(data["jobs"]), 50)
            finally:
                server.shutdown()
                worker.join()


if __name__ == "__main__":
    unittest.main()
