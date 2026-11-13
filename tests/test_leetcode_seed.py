import sqlite3
import unittest
from contextlib import closing

from parse_leetcode import build_seed


class LeetCodeSeedTests(unittest.TestCase):
    def test_import_into_clean_sqlite_database(self):
        question = {
            "id": 1, "title": "What's next?", "url": "https://example.com/?q='sql'",
            "difficulty": "Easy", "acceptance": "50%", "topics": ["Arrays", "Arrays"],
        }
        seed = build_seed({"Company's name": [question, {**question, "frequency": 42}]})
        with closing(sqlite3.connect(":memory:")) as database:
            database.executescript(seed)
            self.assertEqual(database.execute("SELECT title FROM problems").fetchall(), [("What's next?",)])
            self.assertEqual(database.execute("SELECT company_name, frequency FROM company_problems").fetchall(),
                             [("Company's name", 42)])
            self.assertEqual(database.execute("SELECT topic FROM problem_topics").fetchall(), [("Arrays",)])
