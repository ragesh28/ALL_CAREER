import argparse
import json
import re
import sqlite3
from pathlib import Path


def sql_value(value):
    return "'" + str(value).replace("'", "''") + "'"


def build_seed(data):
    lines = [
        "DROP TABLE IF EXISTS problems;",
        "DROP TABLE IF EXISTS company_problems;",
        "DROP TABLE IF EXISTS problem_topics;",
        "CREATE TABLE problems (id INTEGER PRIMARY KEY, title TEXT, url TEXT, difficulty TEXT, acceptance TEXT);",
        "CREATE TABLE company_problems (company_name TEXT, problem_id INTEGER, frequency REAL, PRIMARY KEY (company_name, problem_id));",
        "CREATE TABLE problem_topics (problem_id INTEGER, topic TEXT, PRIMARY KEY (problem_id, topic));",
    ]
    problems_seen = set()
    for company, questions in data.items():
        for question in questions:
            pid = int(question["id"])
            if pid not in problems_seen:
                values = ", ".join(sql_value(question.get(field, "")) for field in ("title", "url", "difficulty", "acceptance"))
                lines.append(f"INSERT INTO problems VALUES ({pid}, {values});")
                problems_seen.add(pid)
                for topic in dict.fromkeys(question.get("topics", [])):
                    lines.append(f"INSERT INTO problem_topics VALUES ({pid}, {sql_value(topic)});")
            frequency = float(question.get("frequency") or 0)
            lines.append(f"INSERT OR REPLACE INTO company_problems VALUES ({sql_value(company)}, {pid}, {frequency});")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Build and validate a local LeetCode SQLite seed.")
    parser.add_argument("--input", type=Path, default=Path("leetcode_data.js"))
    parser.add_argument("--output", type=Path, default=Path("seed_leetcode.sql"))
    args = parser.parse_args()
    match = re.search(r"const\s+leetcodeData\s*=\s*({.*});?\s*$", args.input.read_text(encoding="utf-8"), re.DOTALL)
    if not match:
        parser.error("Could not read the leetcodeData object")
    seed = build_seed(json.loads(match.group(1)))
    database = sqlite3.connect(":memory:")
    try:
        database.executescript(seed)
    finally:
        database.close()
    args.output.write_text(seed, encoding="utf-8")
    print(f"Generated and validated {args.output}")


if __name__ == "__main__":
    main()
