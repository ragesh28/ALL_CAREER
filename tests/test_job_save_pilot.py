from contextlib import chdir
from datetime import date
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import merge_scraped_jobs
from scripts.build_web_catalog import build
import storage


def job(source="naukri", item="first", **fields):
    return {
        "title": f"Software Engineer {item}", "company": "Example",
        "location": "Chennai", "source": source,
        "url": f"https://example.test/{source}/{item}", "date_posted": date.today().isoformat(),
        **fields,
    }


class JobSavePilotTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.workspace = Path(temp.name)
        self.root = self.workspace / "checkout"
        self.root.mkdir()
        self.enterContext(chdir(self.root))
        self.enterContext(patch.multiple(storage, ROOT_DIR=str(self.root),
                                         INDEX_DIR=str(self.root / "data/index"),
                                         JOBS_DIR=str(self.root / "data/jobs")))
        self.archive = self.root / "data/job_archives/all_jobs_1.json"
        self.journal = self.root / "temp_new_jobs.json"
        self.enterContext(patch.dict("os.environ", {}))

    def test_archive_failure_preserves_previous_records_and_retry_is_idempotent(self):
        first, second = job(), job(item="second")
        self.assertEqual(storage.store_jobs_batch([first]), 1)
        before = self.archive.read_bytes()
        write = storage.os.replace

        def fail_archive(source, destination):
            if destination == self.archive:
                raise OSError("Simulated interrupted archive write")
            write(source, destination)

        with patch.object(storage.os, "replace", side_effect=fail_archive):
            with self.assertRaises(storage.JobStorageError):
                storage.store_jobs_batch([second])
        self.assertEqual(self.archive.read_bytes(), before)
        self.assertTrue(any(row["url"] == second["url"] for row in storage.read_saved_jobs(self.journal)))
        self.assertEqual(storage.store_jobs_batch([second]), 1)
        self.assertEqual(storage.store_jobs_batch([first, second]), 0)
        self.assertEqual(len(storage.read_saved_jobs(self.archive)), 2)

    def test_legacy_shard_only_and_interruption_after_archival_write(self):
        record = job("telegram_post", is_walkin=True, walkin_dates=["Nov 18"])
        self.assertEqual(storage.store_jobs_batch([record]), 1)
        self.archive.unlink()
        self.journal.unlink()
        storage.archived_keys(refresh=True)
        self.assertEqual(storage.store_jobs_batch([record]), 1)
        self.assertEqual(storage.store_jobs_batch([record]), 0)
        self.assertTrue(storage.read_saved_jobs(self.archive)[0]["is_walkin"])

        second = job(item="after-archive")
        write = storage.safe_write_json

        def fail_shard(path, *args, **kwargs):
            if Path(path).is_relative_to(Path(storage.JOBS_DIR)):
                raise OSError("Simulated interrupted shard write")
            return write(path, *args, **kwargs)

        with patch.object(storage, "safe_write_json", side_effect=fail_shard):
            with self.assertRaises(storage.JobStorageError):
                storage.store_jobs_batch([second])
        self.assertEqual(storage.store_jobs_batch([second]), 0)
        self.assertEqual(len(storage.read_saved_jobs(self.archive)), 2)
        self.assertTrue(any(row["url"] == second["url"] for path in Path(storage.JOBS_DIR).glob("*/*.json")
                            for row in storage.read_saved_jobs(path)))

    def test_collector_formats_and_local_saving_without_d1(self):
        import requests
        import scrape_alljobs2
        import scrape_google_jobs

        with patch("requests.sessions.Session.request", side_effect=requests.HTTPError("D1 rejected the write")) as d1:
            self.assertEqual(scrape_alljobs2.store_jobs_batch([job("linkedin"), job("indeed")]), 2)
            self.assertEqual(scrape_google_jobs.store_jobs_batch([job("google_jobs")]), 1)
            d1.assert_not_called()

        self.assertEqual(storage.store_jobs_batch([
            job("naukri"), job("foundit"), job("workindia"), job("apna"), job("freshersworld"),
            job("telegram_message"), job("telegram_post"), job("direct_apply")
        ]), 8)
        flyer = job("google_images", title="Software Engineer Walk-in")
        storage.safe_write_json(self.root / "scraped_image_walkin_jobs.json", [flyer])
        storage.safe_write_json(self.root / "data/index/walkin_jobs.json", [flyer])
        storage.safe_write_json(self.root / "scraped_jobs_output.json", {"results": {"Big Co": [job("employer_report")]}})
        storage.safe_write_json(self.root / "workday_scraper/big_company_jobs.json", [job("big_company")])
        summary = build(self.root)
        self.assertEqual(summary["total_jobs"], 12)
        self.assertEqual(summary["walkins"]["total"], 1)
        self.assertIn("direct_apply", summary["sources"])
        self.assertNotIn("employer_report", summary["sources"])
        self.assertNotIn("big_company", summary["sources"])

    def test_checkpoint_commit_and_push_failure_leave_replayable_journal(self):
        upstream = self.workspace / "upstream.git"
        git = merge_scraped_jobs.git
        git("init", "--bare", str(upstream))
        git("init", "-b", "main")
        git("config", "user.name", "Checkpoint test")
        git("config", "user.email", "test@example.test")
        git("config", "commit.gpgSign", "false")
        git("remote", "add", "origin", str(upstream))
        progress = self.root / "naukri_progress.json"
        storage.safe_write_json(progress, {"finished": False, "index": 1})
        git("add", progress.name)
        git("commit", "-m", "fixture")
        git("push", "-u", "origin", "main")
        initial = git("-C", str(upstream), "rev-parse", "refs/heads/main")
        storage.store_jobs_batch([job()])
        storage.safe_write_json(progress, {"finished": False, "index": 2})

        for fail in ("commit", "push"):
            with self.subTest(fail=fail):
                def fail_once(operation, *args):
                    if operation == fail:
                        raise subprocess.CalledProcessError(1, ["git", operation])
                    return git(operation, *args)

                with patch.object(merge_scraped_jobs, "git", side_effect=fail_once):
                    with self.assertRaises(subprocess.CalledProcessError):
                        merge_scraped_jobs.merge_checkpoint("Save scraped batch", [progress.name])
                self.assertTrue(self.journal.is_file())
                self.assertEqual(git("-C", str(upstream), "rev-parse", "refs/heads/main"), initial)

        merge_scraped_jobs.merge_checkpoint("Save scraped batch", [progress.name])
        self.assertFalse(self.journal.exists())
        self.assertEqual(json.loads(git("-C", str(upstream), "show", "main:" + progress.name))["index"], 2)
        remote_rows = json.loads(git("-C", str(upstream), "show", "main:data/job_archives/all_jobs_1.json"))
        self.assertEqual([row["url"] for row in remote_rows], [job()["url"]])


if __name__ == "__main__":
    unittest.main()
