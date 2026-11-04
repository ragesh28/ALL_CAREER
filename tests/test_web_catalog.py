import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_web_catalog import build


class WebCatalogTests(unittest.TestCase):
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
