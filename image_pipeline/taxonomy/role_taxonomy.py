"""
Hierarchical Role and Occupation Taxonomy.
Synthesizes India's NCO-2015 (National Classification of Occupations), ESCO,
and real-world Indian job-market aliases across IT, Core Engineering, Manufacturing,
Finance, Healthcare, Sales, HR, BPO, and Operations.
"""
from typing import Dict, List, Optional, Tuple


ROLE_TAXONOMY: List[Dict] = [
    # ── IT: Software & App Development ──
    {
        "canonical": "Software Engineer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "nco_code": "2512.0100",
        "aliases": [
            "software engineer", "software developer", "sde", "software development engineer",
            "programmer", "application developer", "software programmer", "systems engineer",
            "associate software engineer", "senior software engineer", "lead software engineer",
            "trainee software engineer", "software specialist", "java developer", "java",
            "python developer", "python", "c++ developer", "c# developer", ".net developer",
            "dotnet developer", "spring boot developer", "spring boot", "springboot"
        ]
    },
    {
        "canonical": "Frontend Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "frontend developer", "front end developer", "frontend engineer", "front end engineer",
            "ui developer", "react developer", "react js developer", "reactjs developer", "react",
            "angular developer", "angular", "vue developer", "javascript developer", "web developer",
            "html css developer", "nextjs developer"
        ]
    },
    {
        "canonical": "Backend Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "backend developer", "back end developer", "backend engineer", "back end engineer",
            "java developer", "python developer", "nodejs developer", "node js developer",
            "golang developer", "go developer", "c++ developer", "c# developer", ".net developer",
            "dotnet developer", "spring boot developer", "django developer", "fastapi developer"
        ]
    },
    {
        "canonical": "Full Stack Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "full stack developer", "fullstack developer", "full stack engineer", "fullstack engineer",
            "mern stack developer", "mean stack developer", "java full stack developer",
            "python full stack developer", ".net full stack developer"
        ]
    },
    {
        "canonical": "Mobile App Developer",
        "sector": "Information Technology",
        "category": "Mobile Development",
        "aliases": [
            "mobile app developer", "mobile developer", "android developer", "ios developer",
            "flutter developer", "react native developer", "android engineer", "ios engineer",
            "swift developer", "kotlin developer"
        ]
    },

    # ── IT: Data, AI & Analytics ──
    {
        "canonical": "Data Scientist",
        "sector": "Information Technology",
        "category": "Data & AI",
        "aliases": [
            "data scientist", "senior data scientist", "lead data scientist",
            "applied scientist", "decision scientist", "ai research scientist"
        ]
    },
    {
        "canonical": "Machine Learning Engineer",
        "sector": "Information Technology",
        "category": "Data & AI",
        "aliases": [
            "machine learning engineer", "ml engineer", "ai engineer", "artificial intelligence engineer",
            "deep learning engineer", "nlp engineer", "computer vision engineer", "genai engineer",
            "llm engineer", "ai specialist"
        ]
    },
    {
        "canonical": "Data Engineer",
        "sector": "Information Technology",
        "category": "Data & AI",
        "aliases": [
            "data engineer", "big data engineer", "etl developer", "data pipeline engineer",
            "spark developer", "snowflake developer", "databricks engineer"
        ]
    },
    {
        "canonical": "Data Analyst",
        "sector": "Information Technology",
        "category": "Data & AI",
        "aliases": [
            "data analyst", "business intelligence analyst", "bi analyst", "power bi developer",
            "tableau developer", "sql analyst", "analytics consultant", "reporting analyst"
        ]
    },

    # ── IT: Cloud, DevOps & Infrastructure ──
    {
        "canonical": "DevOps Engineer",
        "sector": "Information Technology",
        "category": "Cloud & Infrastructure",
        "aliases": [
            "devops engineer", "site reliability engineer", "sre", "devsecops engineer",
            "platform engineer", "build and release engineer", "ci cd engineer"
        ]
    },
    {
        "canonical": "Cloud Engineer",
        "sector": "Information Technology",
        "category": "Cloud & Infrastructure",
        "aliases": [
            "cloud engineer", "aws engineer", "azure engineer", "gcp engineer",
            "cloud architect", "aws solutions architect", "cloud administrator"
        ]
    },
    {
        "canonical": "System Administrator",
        "sector": "Information Technology",
        "category": "IT Support & Admin",
        "aliases": [
            "system administrator", "sysadmin", "linux administrator", "windows administrator",
            "network administrator", "it administrator", "desktop support engineer", "it support engineer",
            "service desk engineer", "technical support engineer", "hardware and networking engineer"
        ]
    },

    # ── IT: Quality Assurance & Testing ──
    {
        "canonical": "QA / Automation Test Engineer",
        "sector": "Information Technology",
        "category": "Quality Assurance",
        "aliases": [
            "qa engineer", "quality assurance engineer", "software test engineer", "tester",
            "automation test engineer", "sdet", "software development engineer in test",
            "manual tester", "selenium tester", "performance test engineer", "qa analyst"
        ]
    },

    # ── IT: Cyber Security ──
    {
        "canonical": "Cyber Security Analyst",
        "sector": "Information Technology",
        "category": "Information Security",
        "aliases": [
            "security analyst", "cyber security analyst", "soc analyst", "information security analyst",
            "penetration tester", "ethical hacker", "vulnerability assessor", "security engineer"
        ]
    },

    # ── Core Engineering & Hardware ──
    {
        "canonical": "Embedded Systems Engineer",
        "sector": "Core Engineering",
        "category": "Embedded & IoT",
        "aliases": [
            "embedded engineer", "embedded software engineer", "embedded systems engineer",
            "firmware engineer", "iot engineer", "microcontroller developer", "automotive embedded engineer"
        ]
    },
    {
        "canonical": "VLSI Design Engineer",
        "sector": "Core Engineering",
        "category": "Semiconductor & VLSI",
        "aliases": [
            "vlsi engineer", "asic design engineer", "fpga engineer", "rtl design engineer",
            "physical design engineer", "verification engineer", "semiconductor engineer"
        ]
    },
    {
        "canonical": "Electrical Engineer",
        "sector": "Core Engineering",
        "category": "Electrical & Electronics",
        "aliases": [
            "electrical engineer", "electrician", "electrical maintenance engineer",
            "electronics engineer", "power systems engineer", "automation engineer", "plc scada engineer",
            "instrumentation engineer", "service engineer"
        ]
    },
    {
        "canonical": "Mechanical Engineer",
        "sector": "Core Engineering",
        "category": "Mechanical & Automobile",
        "aliases": [
            "mechanical engineer", "design engineer", "cad engineer", "autocad designer",
            "catia designer", "solidworks designer", "maintenance engineer", "production engineer",
            "quality engineer", "qc engineer", "qa qc engineer", "automobile engineer"
        ]
    },
    {
        "canonical": "Civil Engineer",
        "sector": "Core Engineering",
        "category": "Civil & Construction",
        "aliases": [
            "civil engineer", "site engineer", "structural engineer", "project engineer",
            "billing engineer", "quantity surveyor", "construction supervisor", "architect"
        ]
    },

    # ── Manufacturing & Garments & Operations ──
    {
        "canonical": "Industrial Engineer",
        "sector": "Manufacturing",
        "category": "Industrial & Operations",
        "aliases": [
            "industrial engineer", "ie executive", "smv executive", "line balancing engineer",
            "time study engineer", "productivity engineer", "plant engineer", "operations executive",
            "garment ie", "apparel ie"
        ]
    },

    # ── Business, Management & HR ──
    {
        "canonical": "HR Executive / Recruiter",
        "sector": "Human Resources",
        "category": "HR & Talent",
        "aliases": [
            "hr executive", "hr recruiter", "talent acquisition specialist", "technical recruiter",
            "us it recruiter", "recruitment specialist", "hr generalist", "hr manager",
            "hr associate", "hr intern", "human resources executive", "hr bp", "hr business partner"
        ]
    },
    {
        "canonical": "Product Manager",
        "sector": "Business & Management",
        "category": "Product",
        "aliases": [
            "product manager", "associate product manager", "apm", "senior product manager",
            "product owner", "business analyst", "scrum master", "project manager"
        ]
    },

    # ── Sales, Marketing & BPO ──
    {
        "canonical": "Business Development / Sales Executive",
        "sector": "Sales & Marketing",
        "category": "Sales",
        "aliases": [
            "sales executive", "business development executive", "bde", "business development manager",
            "bdm", "inside sales executive", "field sales executive", "telecaller", "telesales executive",
            "account executive", "pre sales consultant", "channel sales executive"
        ]
    },
    {
        "canonical": "Digital Marketing Executive",
        "sector": "Sales & Marketing",
        "category": "Marketing",
        "aliases": [
            "digital marketing executive", "seo executive", "digital marketer", "content writer",
            "social media manager", "performance marketing executive", "copywriter"
        ]
    },
    {
        "canonical": "Customer Support Executive",
        "sector": "BPO & Customer Care",
        "category": "Customer Support",
        "aliases": [
            "customer support executive", "customer service representative", "csr",
            "bpo executive", "voice process executive", "non voice process executive",
            "chat support executive", "international voice process", "domestic voice process"
        ]
    },

    # ── Finance & Accounts ──
    {
        "canonical": "Accountant / Financial Analyst",
        "sector": "Banking & Finance",
        "category": "Accounting & Finance",
        "aliases": [
            "accountant", "senior accountant", "tally operator", "gst accountant",
            "chartered accountant", "ca intern", "financial analyst", "accounts executive",
            "auditor", "accounts payable executive", "accounts receivable executive"
        ]
    },

    # ── Healthcare & Pharma ──
    {
        "canonical": "Medical Representative / Pharmacist",
        "sector": "Healthcare & Pharma",
        "category": "Healthcare",
        "aliases": [
            "medical representative", "mr", "pharmacist", "clinical research associate",
            "medical coder", "staff nurse", "lab technician", "pharma executive"
        ]
    }
]


class RoleTaxonomyResolver:
    """Matches OCR text against hierarchical role definitions."""

    @classmethod
    def resolve_role(cls, text_phrase: str) -> Optional[Dict]:
        """
        Check if a phrase matches any role alias in the taxonomy.
        Returns dict with canonical, sector, category, confidence.
        """
        phrase = text_phrase.lower().strip()
        for role_entry in ROLE_TAXONOMY:
            for alias in role_entry["aliases"]:
                if alias == phrase or f" {alias} " in f" {phrase} ":
                    return {
                        "name": text_phrase,
                        "canonical": role_entry["canonical"],
                        "category": role_entry["category"],
                        "sector": role_entry["sector"],
                        "confidence": 0.95 if alias == phrase else 0.85
                    }
        return None

    @classmethod
    def find_all_roles(cls, text: str) -> List[Dict]:
        """
        Scan a full document text and extract all matching canonical roles.
        """
        found = []
        seen_canonicals = set()
        low_text = " " + text.lower() + " "

        for role_entry in ROLE_TAXONOMY:
            for alias in role_entry["aliases"]:
                if f" {alias} " in low_text or f"\n{alias}\n" in low_text or f"\n{alias} " in low_text or f" {alias}\n" in low_text:
                    can = role_entry["canonical"]
                    if can not in seen_canonicals:
                        seen_canonicals.add(can)
                        found.append({
                            "name": alias.title(),
                            "canonical": can,
                            "category": role_entry["category"],
                            "sector": role_entry["sector"],
                            "confidence": 0.92
                        })
                    break
        return found
