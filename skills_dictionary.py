import json
import os

SKILLS_DICT = {
    # --- Technical Skills (1 - 99) ---
    "Python": {"id": 1, "synonyms": ["python", "py", "python3", "django", "flask", "fastapi"]},
    "Java": {"id": 2, "synonyms": ["java", "jdk", "jee", "spring", "spring boot", "springboot", "hibernate"]},
    "JavaScript": {"id": 3, "synonyms": ["javascript", "js", "ecmascript", "jquery", "node", "node.js", "nodejs", "express", "expressjs"]},
    "TypeScript": {"id": 4, "synonyms": ["typescript", "ts"]},
    "C++": {"id": 5, "synonyms": ["c\\+\\+", "cpp"]},
    "C#": {"id": 6, "synonyms": ["c#", "csharp", "\\.net", "dotnet", "asp\\.net"]},
    "Go": {"id": 7, "synonyms": ["go", "golang", "go-lang"]},
    "Ruby": {"id": 8, "synonyms": ["ruby", "rails", "rubyonrails"]},
    "PHP": {"id": 9, "synonyms": ["php", "laravel", "wordpress"]},
    "Swift": {"id": 10, "synonyms": ["swift", "ios dev", "objective-c", "cocoa"]},
    "Kotlin": {"id": 11, "synonyms": ["kotlin", "android dev"]},
    "SQL": {"id": 12, "synonyms": ["sql", "mysql", "postgresql", "postgres", "sqlite", "oracle sql", "pl/sql", "plsql"]},
    "NoSQL": {"id": 13, "synonyms": ["nosql", "mongodb", "cassandra", "redis", "dynamodb", "firebase"]},
    "AWS": {"id": 14, "synonyms": ["aws", "amazon web services", "ec2", "s3", "rds", "lambda", "dynamodb"]},
    "Azure": {"id": 15, "synonyms": ["azure", "microsoft azure", "aks"]},
    "GCP": {"id": 16, "synonyms": ["gcp", "google cloud", "google cloud platform", "bigquery"]},
    "Docker": {"id": 17, "synonyms": ["docker", "containerization", "containers"]},
    "Kubernetes": {"id": 18, "synonyms": ["kubernetes", "k8s", "helm"]},
    "CI/CD": {"id": 19, "synonyms": ["ci/cd", "cicd", "jenkins", "github actions", "gitlab ci", "bitbucket pipelines"]},
    "Git": {"id": 20, "synonyms": ["git", "github", "gitlab", "bitbucket"]},
    "React": {"id": 21, "synonyms": ["react", "react\\.js", "reactjs", "next\\.js", "nextjs", "redux"]},
    "Angular": {"id": 22, "synonyms": ["angular", "angularjs", "angular\\.js"]},
    "Vue": {"id": 23, "synonyms": ["vue", "vuejs", "vue\\.js", "nuxt", "nuxtjs"]},
    "HTML/CSS": {"id": 24, "synonyms": ["html", "css", "html5", "css3", "sass", "tailwind", "bootstrap"]},
    "Machine Learning": {"id": 25, "synonyms": ["machine learning", "ml", "supervised learning", "unsupervised learning", "scikit-learn", "sklearn", "xgboost", "random forest"]},
    "Deep Learning": {"id": 26, "synonyms": ["deep learning", "neural networks", "cnn", "rnn", "lstm", "tensorflow", "keras", "pytorch"]},
    "NLP": {"id": 27, "synonyms": ["nlp", "natural language processing", "spacy", "nltk", "bert", "gpt", "huggingface", "transformers"]},
    "Computer Vision": {"id": 28, "synonyms": ["computer vision", "opencv", "image processing", "object detection", "yolo"]},
    "Data Science": {"id": 29, "synonyms": ["data science", "pandas", "numpy", "matplotlib", "seaborn", "jupyter"]},
    "Data Engineering": {"id": 30, "synonyms": ["data engineering", "spark", "apache spark", "hadoop", "etl", "airflow", "data pipeline", "kafka", "redshift", "snowflake"]},
    "PowerBI": {"id": 31, "synonyms": ["powerbi", "power bi", "dax"]},
    "Tableau": {"id": 32, "synonyms": ["tableau"]},
    "Excel": {"id": 33, "synonyms": ["excel", "vlookup", "pivot tables", "advanced excel"]},
    "Linux": {"id": 34, "synonyms": ["linux", "unix", "ubuntu", "centos", "redhat", "bash", "shell scripting"]},
    "Cybersecurity": {"id": 35, "synonyms": ["cybersecurity", "cyber security", "infosec", "information security", "firewall", "penetration testing", "pentest", "ethical hacking", "siem", "owasp"]},
    "Android": {"id": 36, "synonyms": ["android", "kotlin", "java android"]},
    "iOS": {"id": 37, "synonyms": ["ios", "swift", "objective-c"]},
    "Flutter": {"id": 38, "synonyms": ["flutter", "dart"]},
    "React Native": {"id": 39, "synonyms": ["react native", "react-native"]},
    "Blockchain": {"id": 40, "synonyms": ["blockchain", "ethereum", "solidity", "smart contracts", "web3", "bitcoin"]},
    "Embedded Systems": {"id": 41, "synonyms": ["embedded", "embedded systems", "microcontrollers", "arduino", "raspberry pi", "rtos", "firmware", "iot"]},
    "VLSI": {"id": 42, "synonyms": ["vlsi", "verilog", "vhdl", "asic", "fpga"]},
    "SAP": {"id": 43, "synonyms": ["sap", "abap", "hana"]},
    "Salesforce": {"id": 44, "synonyms": ["salesforce", "apex", "visualforce", "lightning"]},

    # --- Non-Technical Skills (100 - 199) ---
    "Project Management": {"id": 100, "synonyms": ["project management", "pmp", "prince2", "project coordinator", "jira", "trello", "gantt"]},
    "Product Management": {"id": 101, "synonyms": ["product management", "product owner", "product roadmaps", "product lifecycle", "roadmap"]},
    "Agile/Scrum": {"id": 102, "synonyms": ["agile", "scrum", "scrum master", "sprints", "kanban"]},
    "Communication": {"id": 103, "synonyms": ["communication", "interpersonal skills", "presentation", "written communication", "verbal communication"]},
    "Leadership": {"id": 104, "synonyms": ["leadership", "team management", "mentoring", "coaching", "people management", "team lead"]},
    "Sales": {"id": 105, "synonyms": ["sales", "selling", "account management", "lead generation", "sales targets", "cold calling"]},
    "Business Development": {"id": 106, "synonyms": ["business development", "bd", "bde", "partnership", "client acquisition"]},
    "Digital Marketing": {"id": 107, "synonyms": ["digital marketing", "marketing", "social media marketing", "smm", "sem", "google ads", "email marketing"]},
    "SEO": {"id": 108, "synonyms": ["seo", "search engine optimization", "google analytics", "semrush", "ahrefs"]},
    "Content Writing": {"id": 109, "synonyms": ["content writing", "copywriting", "blogging", "technical writing", "creative writing"]},
    "Financial Analysis": {"id": 110, "synonyms": ["financial analysis", "corporate finance", "valuation", "financial modeling", "auditing"]},
    "Accounting": {"id": 111, "synonyms": ["accounting", "bookkeeping", "tally", "gst", "taxation", "auditing", "invoice"]},
    "HRBP/Recruiting": {"id": 112, "synonyms": ["hr", "human resources", "recruiting", "recruitment", "talent acquisition", "hrbp", "payroll", "employee relations"]},
    "Customer Success": {"id": 113, "synonyms": ["customer success", "client success", "customer retention", "csm"]},
    "Customer Support": {"id": 114, "synonyms": ["customer support", "customer care", "helpdesk", "technical support", "tech support", "chat support", "voice support"]},
    "Graphic Design": {"id": 115, "synonyms": ["graphic design", "photoshop", "illustrator", "indesign", "coreldraw", "canvas", "branding"]},
    "UI/UX Design": {"id": 116, "synonyms": ["ui/ux", "ui ux", "user experience", "user interface", "figma", "sketch", "wireframing", "prototyping"]},
    "Video Editing": {"id": 117, "synonyms": ["video editing", "premiere pro", "after effects", "final cut", "da vinci", "motion graphics"]}
}

def generate_skills_index():
    index = {}
    for skill_name, info in SKILLS_DICT.items():
        index[str(info["id"])] = skill_name
        
    with open("skills_map.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print("Generated skills_map.json successfully!")

if __name__ == "__main__":
    generate_skills_index()
