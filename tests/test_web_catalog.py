import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_web_catalog import build


class WebCatalogTests(unittest.TestCase):
    def test_recovers_both_archive_conflict_alternatives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            common = {'title': 'Common', 'company': 'A', 'source': 'apna', 'location': 'Chennai', 'url': 'https://apna.co/job/1'}
            left = {**common, 'title': 'Left', 'url': 'https://apna.co/job/2'}
            right = {**common, 'title': 'Right', 'url': 'https://apna.co/job/3'}
            raw = '<<<<<<< Updated upstream\n' + json.dumps([common, left]) + '\n=======\n' + json.dumps([common, right]) + '\n>>>>>>> Stashed changes\n'
            archive = root / 'all_jobs_1.json'
            archive.write_text(raw, encoding='utf8')
            summary = build(root)
            self.assertEqual(summary['total_jobs'], 3)
            self.assertEqual(summary['sources']['apna'], 3)
            self.assertEqual(summary['audit']['recovered_conflict_files'], ['all_jobs_1.json'])
            self.assertEqual(archive.read_text(encoding='utf8'), raw)

    def test_recovers_sources_and_archive_only_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shards = root / 'data/jobs/developer'
            shards.mkdir(parents=True)
            legacy = {'title': 'Legacy opening', 'company': 'A', 'location': 'Chennai', 'url': 'https://example.com/old', 'date_posted': '2026-07-01'}
            (shards / 'workindia_chennai.json').write_text(json.dumps([legacy]), encoding='utf-8')
            archive_only = {'title': 'Archived opening', 'company_name': 'B', 'location': 'Chennai', 'apply_link': 'https://apna.co/job/123', 'job_posted_date': '2026-11-01'}
            (root / 'all_jobs_1.json').write_text(json.dumps([archive_only]), encoding='utf-8')
            summary = build(root)
            self.assertEqual(summary['total_jobs'], 2)
            self.assertEqual(summary['sources'], {'apna': 1, 'workindia': 1})
            self.assertEqual(summary['audit']['input_records'], {'archive': 1, 'shard': 1})
            manifest = json.loads(gzip.decompress((root / summary['manifest']).read_bytes()))
            self.assertEqual(manifest['sources']['apna'][0]['count'], 1)

    def test_walkin_enrichment_keeps_posting_date_and_source_consistent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shards = root / 'data/jobs/developer'
            shards.mkdir(parents=True)
            job = {'title': 'Engineer', 'company': 'A', 'location': 'Chennai', 'url': 'https://example.com/job', 'date_posted': '2026-11-04'}
            (shards / 'naukri_chennai.json').write_text(json.dumps([job]), encoding='utf-8')
            index = root / 'data/index'
            index.mkdir()
            (index / 'walkin_jobs.json').write_text(json.dumps([{**job, 'source': 'naukri', 'date_posted': '2026-11-01', 'is_walkin': True, 'walkin_date': '5 November 2026'}]), encoding='utf-8')
            summary = build(root)
            row = json.loads((root / 'data/web/latest.json').read_bytes())[0]
            self.assertEqual(summary['walkins']['total'], 1)
            self.assertIs(row['is_walkin'], True)
            self.assertEqual(row['date_posted'], '2026-11-04')
            self.assertEqual(row['source'], 'naukri')

    def test_paging_sort_counts_and_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shards = root / 'data/jobs/developer'
            shards.mkdir(parents=True)
            jobs = [
                {'title': 'Old', 'company': 'A', 'location': 'Chennai', 'source': 'naukri', 'url': 'https://example.com/old', 'date_posted': '2025-01-01'},
                {'title': 'New', 'company': 'A', 'location': 'Chennai', 'source': 'naukri', 'url': 'https://example.com/new', 'date_posted': '2026-11-04', 'is_walkin': True, 'walkin_date': '5 November 2026'},
                {'title': 'Middle', 'company': {'name': 'B'}, 'location': {'city': 'Bengaluru'}, 'source': 'telegram_post', 'url': 'https://example.com/mid', 'date_posted': '2026-10-20'},
            ]
            (shards / 'naukri_chennai.json').write_text(json.dumps(jobs), encoding='utf-8')
            index = root / 'data/index'
            index.mkdir()
            (index / 'walkin_jobs.json').write_text(json.dumps([jobs[1]]), encoding='utf-8')
            original = (shards / 'naukri_chennai.json').read_bytes()
            summary = build(root, page_size=2)
            self.assertEqual(summary['total_jobs'], 3)
            self.assertEqual(summary['locations'], {'bangalore': 1, 'chennai': 2})
            self.assertEqual(summary['source_locations']['naukri']['chennai'], 2)
            self.assertEqual(summary['walkins']['total'], 1)
            manifest = json.loads(gzip.decompress((root / summary['manifest']).read_bytes()))
            loaded = []
            for page in manifest['pages']:
                rows = json.loads(gzip.decompress((root / page['path']).read_bytes()))
                self.assertLessEqual(len(rows), 2)
                loaded.extend(rows)
            self.assertEqual([j['title'] for j in loaded], ['New', 'Middle', 'Old'])
            self.assertEqual((shards / 'naukri_chennai.json').read_bytes(), original)
            second = build(root, page_size=2)
            self.assertEqual(summary['manifest'], second['manifest'])

    def test_broken_source_does_not_publish_empty_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shards = root / 'data/jobs/developer'
            shards.mkdir(parents=True)
            (shards / 'naukri_chennai.json').write_text('{broken', encoding='utf-8')
            with self.assertRaises(json.JSONDecodeError):
                build(root)
            self.assertFalse((root / 'data/web/summary.json').exists())


if __name__ == '__main__':
    unittest.main()
