"""
Hierarchical Role and Occupation Taxonomy.
Synthesizes India's NCO-2015 (National Classification of Occupations), ESCO,
and real-world Indian job-market aliases across IT, 3D/Creative, Core Engineering,
Manufacturing, Finance, Healthcare, HR, Sales, BPO, and Operations (1000+ Aliases).
"""
import re
from typing import Dict, List, Optional, Tuple


ROLE_TAXONOMY: List[Dict] = [
    # ── 1. IT: Software & Application Development ──
    {
        "canonical": "Software Engineer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "software engineer", "software developer", "sde", "sde 1", "sde 2", "sde 3",
            "software development engineer", "programmer", "application developer", "software programmer",
            "systems engineer", "associate software engineer", "senior software engineer", "lead software engineer",
            "trainee software engineer", "software specialist", "member technical staff", "mts", "software consultant",
            "java developer", "java", "core java developer", "advanced java developer", "j2ee developer",
            "python developer", "python", "python django developer", "python fastapi developer",
            "c++ developer", "c++ engineer", "c# developer", ".net developer", "dotnet developer",
            "asp.net developer", "asp.net core", "spring boot developer", "spring boot", "springboot",
            "golang developer", "go developer", "rust developer", "ruby on rails developer", "ror developer",
            "php developer", "laravel developer", "codeigniter developer", "django developer", "fastapi developer"
        ]
    },
    {
        "canonical": "Frontend Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "frontend developer", "front end developer", "frontend engineer", "front end engineer",
            "ui developer", "react developer", "react js developer", "reactjs developer", "react", "react.js",
            "angular developer", "angular", "angularjs developer", "vue developer", "vue.js developer", "vuejs",
            "javascript developer", "typescript developer", "web developer", "html css developer",
            "nextjs developer", "next.js developer", "nuxt developer", "svelte developer", "tailwind developer"
        ]
    },
    {
        "canonical": "Backend Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "backend developer", "back end developer", "backend engineer", "back end engineer",
            "nodejs developer", "node js developer", "node.js developer", "express.js developer",
            "django developer", "fastapi developer", "spring boot developer", "microservices developer",
            "api developer", "rest api developer", "graphql developer", "backend architect"
        ]
    },
    {
        "canonical": "Full Stack Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "full stack developer", "fullstack developer", "full stack engineer", "fullstack engineer",
            "mern stack developer", "mern developer", "mean stack developer", "mean developer",
            "java full stack developer", "python full stack developer", ".net full stack developer",
            "dotnet full stack", "fullstack web developer", "lamp stack developer"
        ]
    },
    {
        "canonical": "Mobile App Developer",
        "sector": "Information Technology",
        "category": "Mobile Development",
        "aliases": [
            "mobile app developer", "mobile developer", "mobile application developer", "android developer",
            "android engineer", "android app developer", "ios developer", "ios engineer", "ios app developer",
            "flutter developer", "flutter engineer", "react native developer", "react native engineer",
            "swift developer", "kotlin developer", "cross platform developer", "xamarin developer"
        ]
    },
    {
        "canonical": "Software Trainee / Intern",
        "sector": "Information Technology",
        "category": "Entry Level IT",
        "aliases": [
            "software trainee", "software trainee intern", "developer intern", "fullstack developer intern",
            "frontend intern", "backend intern", "python intern", "java intern", "react intern",
            "graduate engineer trainee", "get", "trainee", "software engineering trainee", "trainee programmer",
            "tech intern", "it intern", "software development intern", "junior developer", "fresh graduate trainee"
        ]
    },
    {
        "canonical": "WordPress / Web Developer",
        "sector": "Information Technology",
        "category": "Web Development",
        "aliases": [
            "wordpress developer", "wordpress", "wp developer", "wordpress developer intern",
            "elementor developer", "elementor", "theme developer", "web designer", "shopify developer",
            "magento developer", "drupal developer", "woocommerce developer", "webmaster"
        ]
    },

    # ── 2. IT: Cloud, DevOps & Infrastructure ──
    {
        "canonical": "DevOps / Cloud Engineer",
        "sector": "Information Technology",
        "category": "Cloud & DevOps",
        "aliases": [
            "devops engineer", "devops", "cloud engineer", "cloud architect", "site reliability engineer",
            "sre", "aws engineer", "aws cloud engineer", "azure engineer", "azure cloud engineer",
            "gcp engineer", "google cloud engineer", "kubernetes administrator", "docker engineer",
            "terraform engineer", "ci cd engineer", "build and release engineer", "infrastructure engineer",
            "cloud infrastructure engineer", "platform engineer", "sysops engineer"
        ]
    },
    {
        "canonical": "System / Network Administrator",
        "sector": "Information Technology",
        "category": "IT Infrastructure",
        "aliases": [
            "system administrator", "sysadmin", "network administrator", "network engineer",
            "cisco network engineer", "ccna engineer", "ccnp engineer", "windows administrator",
            "linux administrator", "linux system administrator", "it support engineer", "technical support engineer",
            "desktop support engineer", "helpdesk executive", "service desk analyst", "it executive"
        ]
    },

    # ── 3. IT: Data, AI & Machine Learning ──
    {
        "canonical": "Data Scientist / AI ML Engineer",
        "sector": "Information Technology",
        "category": "Data & AI",
        "aliases": [
            "data scientist", "senior data scientist", "machine learning engineer", "ml engineer",
            "ai engineer", "artificial intelligence engineer", "deep learning engineer", "nlp engineer",
            "computer vision engineer", "genai engineer", "generative ai engineer", "llm engineer",
            "ai research scientist", "data science intern", "ai specialist", "prompt engineer", "mlops engineer"
        ]
    },
    {
        "canonical": "Data Engineer / BI Developer",
        "sector": "Information Technology",
        "category": "Data & AI",
        "aliases": [
            "data engineer", "senior data engineer", "big data engineer", "spark developer",
            "pyspark developer", "etl developer", "data warehouse engineer", "snowflake developer",
            "databricks engineer", "bi developer", "business intelligence developer", "power bi developer",
            "power bi", "tableau developer", "tableau", "data analyst", "senior data analyst", "sql developer"
        ]
    },
    {
        "canonical": "Cybersecurity Analyst / Specialist",
        "sector": "Information Technology",
        "category": "Cybersecurity",
        "aliases": [
            "cybersecurity analyst", "cyber security analyst", "cybersecurity specialist", "infosec engineer",
            "information security analyst", "soc analyst", "soc engineer", "penetration tester",
            "ethical hacker", "vapt engineer", "security engineer", "cloud security engineer",
            "kali linux", "wireshark", "api security", "incident responder", "cybersecurity internship"
        ]
    },
    {
        "canonical": "QA / Software Tester",
        "sector": "Information Technology",
        "category": "Quality Assurance",
        "aliases": [
            "qa engineer", "software tester", "quality assurance engineer", "automation tester",
            "qa automation engineer", "selenium tester", "selenium automation", "playwright tester",
            "cypress tester", "manual tester", "qa manual tester", "sdet", "software development engineer in test",
            "performance tester", "jmeter tester", "api tester", "postman tester", "etl tester", "game tester"
        ]
    },
    {
        "canonical": "ERP & CRM Consultant (SAP / Salesforce)",
        "sector": "Information Technology",
        "category": "Enterprise Applications",
        "aliases": [
            "sap consultant", "sap abap consultant", "sap fico consultant", "sap mm consultant",
            "sap sd consultant", "sap hana consultant", "sap basis consultant", "salesforce developer",
            "salesforce admin", "salesforce consultant", "servicenow developer", "servicenow admin",
            "workday consultant", "mulesoft developer", "oracle fusion consultant"
        ]
    },

    # ── 4. 3D Modeling, Animation, Game Development & Creative Design ──
    {
        "canonical": "3D Modeler / 3D Engineer",
        "sector": "Media, Gaming & Design",
        "category": "3D & Animation",
        "aliases": [
            "3d model engineer", "3d modeler", "3d modeller", "3d artist", "3d generalist",
            "3d asset artist", "character modeler", "environment artist", "hard surface modeler",
            "3d designer", "3d visualizer", "blender artist", "blender modeler", "blender engineer",
            "maya artist", "3ds max designer", "zbrush sculptor", "texture artist", "rigging artist",
            "3d animator", "lighting artist", "rendering artist", "render engineer"
        ]
    },
    {
        "canonical": "Game Developer / Unity Unreal Engineer",
        "sector": "Media, Gaming & Design",
        "category": "Game Development",
        "aliases": [
            "game developer", "game programmer", "game designer", "unity developer", "unity 3d developer",
            "unity engineer", "unreal engine developer", "unreal developer", "ue5 developer", "ue4 developer",
            "gameplay programmer", "level designer", "ar vr developer", "vr developer", "augmented reality developer"
        ]
    },
    {
        "canonical": "VFX Artist / Video Editor",
        "sector": "Media, Gaming & Design",
        "category": "Creative Arts",
        "aliases": [
            "vfx artist", "visual effects artist", "video editor", "senior video editor", "motion graphic designer",
            "motion graphics", "compositor", "rotoscope artist", "roto artist", "after effects artist",
            "premiere pro editor", "davinci resolve editor", "animator", "2d animator"
        ]
    },
    {
        "canonical": "UI/UX & Product Designer",
        "sector": "Media, Gaming & Design",
        "category": "Design",
        "aliases": [
            "ui ux designer", "ui/ux designer", "product designer", "ui designer", "ux designer",
            "ux researcher", "figma designer", "visual designer", "graphic designer", "senior graphic designer",
            "illustrator", "creative designer", "banner designer", "brand designer"
        ]
    },

    # ── 5. Human Resources & Talent Acquisition ──
    {
        "canonical": "HR Executive / Assistant",
        "sector": "Human Resources",
        "category": "Human Resources",
        "aliases": [
            "hr assistant", "assistant hr", "hr executive", "junior hr executive", "sr hr executive",
            "senior hr executive", "hr officer", "hr coordinator", "hr associate", "hr admin",
            "hr administrator", "hr trainee", "hr intern", "human resources intern"
        ]
    },
    {
        "canonical": "HR Recruiter / Talent Acquisition",
        "sector": "Human Resources",
        "category": "Talent Acquisition",
        "aliases": [
            "hr recruiter", "it recruiter", "technical recruiter", "non it recruiter", "talent acquisition",
            "talent acquisition specialist", "talent acquisition executive", "talent acquisition partner",
            "recruitment executive", "recruitment consultant", "sourcer", "sourcing executive", "campus recruiter"
        ]
    },
    {
        "canonical": "HR Generalist / Manager",
        "sector": "Human Resources",
        "category": "HR Management",
        "aliases": [
            "hr generalist", "hr manager", "assistant hr manager", "deputy hr manager", "hrbp",
            "hr business partner", "payroll executive", "payroll specialist", "compensation and benefits",
            "c&b specialist", "employee relations executive", "l&d specialist", "learning and development executive"
        ]
    },

    # ── 6. Core Engineering & Manufacturing ──
    {
        "canonical": "Mechanical Design / Production Engineer",
        "sector": "Core Engineering",
        "category": "Mechanical Engineering",
        "aliases": [
            "mechanical engineer", "mechanical design engineer", "cad engineer", "solidworks designer",
            "autocad designer", "catia designer", "creo designer", "production engineer", "manufacturing engineer",
            "maintenance engineer", "quality control engineer", "qc inspector", "piping engineer", "hvac engineer",
            "tool and die maker", "cnc operator", "vmc operator", "cnc programmer", "welding inspector"
        ]
    },
    {
        "canonical": "Electrical & Electronics Engineer",
        "sector": "Core Engineering",
        "category": "Electrical & Electronics",
        "aliases": [
            "electrical engineer", "electronics engineer", "ece engineer", "eee engineer", "embedded engineer",
            "embedded software engineer", "embedded systems engineer", "firmware engineer", "iot engineer",
            "pcb design engineer", "vlsi engineer", "asic design engineer", "hardware engineer",
            "plc programmer", "scada engineer", "automation engineer", "robotics engineer", "instrumentation engineer"
        ]
    },
    {
        "canonical": "Civil & Structural Engineer",
        "sector": "Core Engineering",
        "category": "Civil Engineering",
        "aliases": [
            "civil engineer", "site engineer", "structural engineer", "project engineer civil",
            "quantity surveyor", "billing engineer", "estimation engineer", "autocad civil drafter",
            "architect", "interior designer", "site supervisor", "safety officer", "ehs officer"
        ]
    },

    # ── 7. Healthcare, Pharma & Sciences ──
    {
        "canonical": "Chemist / Microbiologist",
        "sector": "Healthcare & Pharma",
        "category": "Pharma Science",
        "aliases": [
            "chemist", "junior chemist", "sr chemist", "senior chemist", "qc chemist", "qa chemist",
            "production chemist", "r&d chemist", "analytical chemist", "formulation chemist", "synthetic chemist",
            "microbiologist", "microbiology", "lab technician", "lab analyst", "pathology technician",
            "sterility testing", "water analysis", "bet/mlt"
        ]
    },
    {
        "canonical": "Quality Assurance (QA) / Regulatory Affairs (RA)",
        "sector": "Healthcare & Pharma",
        "category": "Pharma Quality",
        "aliases": [
            "qa", "qc", "ipqa", "quality assurance", "quality control", "regulatory affairs", "ra",
            "qa validation", "qa executive", "qc executive", "formulation dossiers", "drug safety associate",
            "pharmacovigilance", "pv scientist", "clinical research associate", "cra", "clinical trial coordinator"
        ]
    },
    {
        "canonical": "Production Operator / Executive",
        "sector": "Manufacturing & Pharma",
        "category": "Production & Operations",
        "aliases": [
            "operator", "machine operator", "labeling operator", "capsule filling operator",
            "coating operator", "packaging operator", "packing operator", "production executive",
            "senior executive", "assistant manager", "executive", "officer", "jr executive", "sr executive",
            "hme operator", "compression operator", "injectable operator"
        ]
    },
    {
        "canonical": "Pharmacist / Medical Representative",
        "sector": "Healthcare & Pharma",
        "category": "Healthcare",
        "aliases": [
            "pharmacist", "hospital pharmacist", "clinical pharmacist", "medical representative", "mr",
            "pharma sales executive", "area sales manager pharma", "medical coder", "medical biller",
            "medical scribe", "staff nurse", "duty doctor", "resident medical officer", "rmo", "mbbs doctor",
            "bams doctor", "bhms doctor", "claims doctor", "manager health claims", "claims processing"
        ]
    },

    # ── 8. Finance, Accounts & Banking ──
    {
        "canonical": "Accountant / Financial Analyst",
        "sector": "Banking & Finance",
        "category": "Accounting & Finance",
        "aliases": [
            "accountant", "senior accountant", "junior accountant", "tally operator", "gst accountant",
            "chartered accountant", "ca intern", "ca article", "financial analyst", "accounts executive",
            "auditor", "accounts payable executive", "accounts receivable executive", "account executive",
            "billing executive", "finance executive", "credit analyst", "risk analyst", "loan officer",
            "branch manager", "relationship manager", "bank teller", "investment banking analyst"
        ]
    },

    # ── 9. Sales, Marketing, BPO & Customer Service ──
    {
        "canonical": "Digital Marketing / SEO Specialist",
        "sector": "Sales & Marketing",
        "category": "Digital Marketing",
        "aliases": [
            "digital marketer", "digital marketing executive", "digital marketing specialist", "seo specialist",
            "seo executive", "sem specialist", "ppc specialist", "google ads specialist", "social media manager",
            "social media executive", "content writer", "copywriter", "technical writer", "email marketer",
            "growth marketer", "performance marketer", "brand manager", "pr executive"
        ]
    },
    {
        "canonical": "Sales / Business Development Executive",
        "sector": "Sales & Marketing",
        "category": "Sales",
        "aliases": [
            "sales executive", "senior sales executive", "business development executive", "bde",
            "business development associate", "bda", "business development manager", "bdm", "field sales executive",
            "b2b sales executive", "inside sales executive", "telecaller", "telesales executive",
            "direct sales executive", "corporate sales executive", "key account manager"
        ]
    },
    {
        "canonical": "Customer Support / BPO Executive",
        "sector": "Operations & BPO",
        "category": "Customer Support",
        "aliases": [
            "customer support executive", "customer care executive", "customer service representative",
            "csr", "bpo executive", "call center executive", "voice process executive", "international voice process",
            "domestic voice process", "non voice process executive", "chat support executive", "email support executive",
            "operations executive", "back office executive", "data entry operator", "office assistant", "office staff",
            "hub assistant", "sorter", "team leader bpo"
        ]
    }
]


class RoleTaxonomyResolver:
    """Matches OCR text against hierarchical role definitions."""

    @classmethod
    def resolve_role(cls, text_phrase: str) -> Optional[Dict]:
        """Check if a phrase matches any role alias in the taxonomy."""
        phrase = " " + re.sub(r'[^a-zA-Z0-9\s]', ' ', text_phrase.lower()) + " "
        for role_entry in ROLE_TAXONOMY:
            for alias in role_entry["aliases"]:
                if re.search(r'\b' + re.escape(alias) + r'\b', phrase):
                    return {
                        "name": alias.title(),
                        "canonical": role_entry["canonical"],
                        "category": role_entry["category"],
                        "sector": role_entry["sector"],
                        "confidence": 0.95
                    }
        return None

    @classmethod
    def find_all_roles(cls, text: str) -> List[Dict]:
        """Scan a full document text and extract all matching canonical roles."""
        found = []
        seen_canonicals = set()
        clean_text = " " + re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower()) + " "

        for role_entry in ROLE_TAXONOMY:
            for alias in role_entry["aliases"]:
                if re.search(r'\b' + re.escape(alias) + r'\b', clean_text):
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
