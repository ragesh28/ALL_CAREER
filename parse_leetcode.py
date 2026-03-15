import json
import re

with open('leetcode_data.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

json_match = re.search(r'const\s+leetcodeData\s*=\s*({.*});?', js_content, re.DOTALL)
if json_match:
    data = json.loads(json_match.group(1))
    
    with open('seed_leetcode.sql', 'w', encoding='utf-8') as f:
        f.write("DROP TABLE IF EXISTS problems;\n")
        f.write("DROP TABLE IF EXISTS company_problems;\n")
        f.write("DROP TABLE IF EXISTS problem_topics;\n\n")
        f.write("CREATE TABLE problems (id INTEGER PRIMARY KEY, title TEXT, url TEXT, difficulty TEXT, acceptance TEXT);\n")
        f.write("CREATE TABLE company_problems (company_name TEXT, problem_id INTEGER, frequency REAL, PRIMARY KEY (company_name, problem_id));\n")
        f.write("CREATE TABLE problem_topics (problem_id INTEGER, topic TEXT, PRIMARY KEY (problem_id, topic));\n\n")
        
        problems_seen = set()
        
        for company, questions in data.items():
            for q in questions:
                pid = q['id']
                if pid not in problems_seen:
                    title = q['title'].replace("'", "''")
                    url = q.get('url', '')
                    diff = q.get('difficulty', '')
                    acc = q.get('acceptance', '')
                    f.write(f"INSERT INTO problems (id, title, url, difficulty, acceptance) VALUES ({pid}, '{title}', '{url}', '{diff}', '{acc}');\n")
                    problems_seen.add(pid)
                    
                    for topic in q.get('topics', []):
                        t_safe = topic.replace("'", "''")
                        f.write(f"INSERT INTO problem_topics (problem_id, topic) VALUES ({pid}, '{t_safe}');\n")
                
                c_safe = company.replace("'", "''")
                freq = q.get('frequency', 0)
                f.write(f"INSERT INTO company_problems (company_name, problem_id, frequency) VALUES ('{c_safe}', {pid}, {freq});\n")
    print(f"Generated seed_leetcode.sql with {len(problems_seen)} problems.")
else:
    print("Could not parse JS.")
