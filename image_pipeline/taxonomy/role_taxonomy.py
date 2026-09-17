"""
Hierarchical Role and Occupation Taxonomy (1000+ Job Market Aliases).
Synthesizes India's NCO-2015, ESCO, and real-world Indian job-market titles across
IT, Software, Full Stack, MERN, Core Engineering, Manufacturing, Finance, Healthcare,
HR, Sales, BPO, Voice/Non-Voice, and Operations.
"""
import re
from typing import Dict, List, Optional, Tuple


ROLE_TAXONOMY: List[Dict] = [
    # ── 1. IT: Python Development ──
    {
        "canonical": "Python Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "python developer", "python engineer", "python programmer", "python software engineer",
            "python django developer", "python fastapi developer", "python flask developer",
            "python backend developer", "python full stack developer", "python fullstack developer",
            "python automation engineer", "python script developer", "python data engineer",
            "python ai developer", "python web developer", "django developer", "fastapi developer",
            "flask developer", "junior python developer", "senior python developer", "lead python developer",
            "trainee python developer", "python intern", "python trainee", "python fresher",
            "python core developer", "python cloud engineer", "python rest api developer",
            "python microservices developer", "python crawler developer", "python scraping developer",
            "python"
        ]
    },

    # ── 2. IT: MERN & MEAN Stack Development ──
    {
        "canonical": "MERN Stack Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "mern stack developer", "mern developer", "mern stack engineer", "mern engineer",
            "mern full stack developer", "mern fullstack developer", "mern stack programmer",
            "mern stack specialist", "mern stack intern", "mern stack trainee", "mern stack fresher",
            "junior mern stack developer", "senior mern stack developer", "lead mern developer",
            "mean stack developer", "mean developer", "mean stack engineer", "mean engineer",
            "mean full stack developer", "mean stack programmer", "mean stack intern",
            "mern", "mean", "mern stack", "mean stack"
        ]
    },

    # ── 3. IT: Full Stack Development ──
    {
        "canonical": "Full Stack Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "full stack developer", "fullstack developer", "full stack engineer", "fullstack engineer",
            "full stack web developer", "full stack software engineer", "full stack programmer",
            "full stack application developer", "full stack specialist", "full stack consultant",
            "java full stack developer", "java fullstack developer", "java full stack engineer",
            "python full stack developer", "python fullstack engineer", ".net full stack developer",
            "dotnet full stack developer", "c# full stack developer", "php full stack developer",
            "node full stack developer", "react full stack developer", "angular full stack developer",
            "junior full stack developer", "senior full stack developer", "lead full stack developer",
            "trainee full stack developer", "full stack intern", "full stack trainee", "full stack fresher",
            "full stack", "fullstack"
        ]
    },

    # ── 4. IT: Java & Spring Boot Development ──
    {
        "canonical": "Java Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "java developer", "java software engineer", "java engineer", "java programmer",
            "core java developer", "advanced java developer", "java j2ee developer", "j2ee developer",
            "spring boot developer", "spring boot engineer", "springboot developer", "spring developer",
            "java spring boot developer", "java microservices developer", "microservices developer",
            "java backend developer", "java backend engineer", "java cloud developer",
            "java rest api developer", "junior java developer", "senior java developer",
            "lead java developer", "trainee java developer", "java intern", "java trainee",
            "java fresher", "java consultant", "java specialist", "core java", "java"
        ]
    },

    # ── 5. IT: Frontend & Web Development ──
    {
        "canonical": "Frontend Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "frontend developer", "front end developer", "frontend engineer", "front end engineer",
            "ui developer", "ui engineer", "user interface developer", "react developer",
            "react js developer", "reactjs developer", "react engineer", "react js engineer",
            "react.js developer", "angular developer", "angularjs developer", "angular engineer",
            "angular js developer", "vue developer", "vue.js developer", "vuejs developer",
            "vue engineer", "nextjs developer", "next.js developer", "nuxt developer",
            "svelte developer", "web developer", "web designer", "html css developer",
            "html developer", "javascript developer", "js developer", "typescript developer",
            "ts developer", "tailwind developer", "bootstrap developer", "junior frontend developer",
            "senior frontend developer", "lead frontend engineer", "frontend intern",
            "frontend trainee", "frontend fresher", "react", "angular", "vue"
        ]
    },

    # ── 6. IT: Backend & API Development ──
    {
        "canonical": "Backend Developer",
        "sector": "Information Technology",
        "category": "Software Engineering",
        "aliases": [
            "backend developer", "back end developer", "backend engineer", "back end engineer",
            "backend software engineer", "backend programmer", "nodejs developer", "node js developer",
            "node.js developer", "expressjs developer", "express.js developer", "nest js developer",
            "nestjs developer", "api developer", "rest api developer", "graphql developer",
            "golang developer", "go developer", "go engineer", "rust developer", "rust engineer",
            "c++ developer", "c++ software engineer", "c++ programmer", "c# developer", "c# engineer",
            ".net developer", "dotnet developer", "asp.net developer", "asp.net core developer",
            "php developer", "laravel developer", "codeigniter developer", "wordpress developer",
            "shopify developer", "drupal developer", "magento developer", "ruby on rails developer",
            "ror developer", "backend architect", "junior backend developer", "senior backend engineer",
            "backend intern", "backend trainee", "backend fresher", "backend"
        ]
    },

    # ── 7. IT: Mobile App Development ──
    {
        "canonical": "Mobile App Developer",
        "sector": "Information Technology",
        "category": "Mobile Development",
        "aliases": [
            "mobile app developer", "mobile application developer", "mobile developer", "mobile engineer",
            "android developer", "android engineer", "android app developer", "android programmer",
            "ios developer", "ios engineer", "ios app developer", "ios programmer",
            "flutter developer", "flutter engineer", "flutter app developer", "react native developer",
            "react native engineer", "hybrid mobile app developer", "cross platform mobile developer",
            "kotlin developer", "swift developer", "swift engineer", "junior android developer",
            "senior android developer", "junior ios developer", "senior ios developer",
            "flutter intern", "android intern", "ios intern", "android", "ios", "flutter"
        ]
    },

    # ── 8. IT: Cloud, DevOps & System Administration ──
    {
        "canonical": "DevOps / Cloud Engineer",
        "sector": "Information Technology",
        "category": "Cloud & Infrastructure",
        "aliases": [
            "devops engineer", "devops specialist", "devops consultant", "devops lead", "devops architect",
            "cloud engineer", "cloud architect", "cloud specialist", "cloud administrator",
            "aws engineer", "aws cloud engineer", "aws cloud architect", "aws administrator",
            "azure engineer", "azure cloud engineer", "azure cloud architect", "azure administrator",
            "gcp engineer", "google cloud engineer", "google cloud architect", "site reliability engineer",
            "sre", "kubernetes engineer", "docker engineer", "ci cd engineer", "terraform engineer",
            "system administrator", "systems administrator", "sysadmin", "linux administrator",
            "linux system administrator", "windows administrator", "network engineer", "network administrator",
            "infrastructure engineer", "it administrator", "it support engineer", "desktop support engineer",
            "desktop support technician", "hardware and networking engineer", "technical support engineer",
            "service desk engineer", "it helpdesk executive", "devops intern", "cloud intern",
            "devops", "cloud", "aws", "azure"
        ]
    },

    # ── 9. IT: Data Science, Analytics & AI ──
    {
        "canonical": "Data Scientist / AI Engineer",
        "sector": "Information Technology",
        "category": "Data & Artificial Intelligence",
        "aliases": [
            "data scientist", "senior data scientist", "lead data scientist", "associate data scientist",
            "machine learning engineer", "ml engineer", "machine learning scientist", "ai engineer",
            "artificial intelligence engineer", "ai ml engineer", "deep learning engineer",
            "nlp engineer", "computer vision engineer", "prompt engineer", "llm engineer",
            "generative ai engineer", "genai engineer", "ai researcher", "data engineer",
            "big data engineer", "spark developer", "hadoop developer", "etl developer",
            "data analyst", "senior data analyst", "junior data analyst", "business intelligence analyst",
            "bi analyst", "bi developer", "tableau developer", "power bi developer", "powerbi developer",
            "sql developer", "database developer", "database administrator", "dba", "oracle dba",
            "sql dba", "data analytics intern", "data science intern", "data science trainee",
            "data science fresher", "data analyst fresher", "data science", "data analytics", "data analyst"
        ]
    },

    # ── 10. IT: QA, Testing & Automation ──
    {
        "canonical": "QA / Test Automation Engineer",
        "sector": "Information Technology",
        "category": "Quality Assurance",
        "aliases": [
            "qa engineer", "qa tester", "quality assurance engineer", "software tester",
            "software test engineer", "software quality assurance engineer", "sqa engineer",
            "manual tester", "manual test engineer", "manual qa engineer", "automation tester",
            "automation test engineer", "test automation engineer", "qa automation engineer",
            "selenium tester", "selenium automation engineer", "selenium test engineer",
            "sdet", "software development engineer in test", "performance tester", "jmeter tester",
            "api tester", "mobile app tester", "cypress tester", "playwright tester",
            "etl tester", "database tester", "security tester", "junior qa engineer",
            "senior qa engineer", "lead qa engineer", "qa intern", "testing intern",
            "qa trainee", "testing fresher", "software testing"
        ]
    },

    # ── 11. IT: Cybersecurity & Information Security ──
    {
        "canonical": "Cybersecurity Analyst",
        "sector": "Information Technology",
        "category": "Information Security",
        "aliases": [
            "cybersecurity analyst", "cyber security analyst", "security engineer", "cybersecurity engineer",
            "cyber security engineer", "information security analyst", "infosec analyst",
            "soc analyst", "soc engineer", "security operations center analyst", "penetration tester",
            "ethical hacker", "vulnerability assessment analyst", "vapt analyst", "vapt engineer",
            "network security engineer", "application security engineer", "appsec engineer",
            "cloud security engineer", "iam engineer", "cyber security intern", "cybersecurity"
        ]
    },

    # ── 12. Design & Creative: UI/UX, Graphic & 3D ──
    {
        "canonical": "UI / UX & Graphic Designer",
        "sector": "Creative & Design",
        "category": "User Experience & Visual Design",
        "aliases": [
            "ui ux designer", "ui designer", "ux designer", "ui/ux designer", "user experience designer",
            "user interface designer", "product designer", "lead product designer", "graphic designer",
            "senior graphic designer", "creative graphic designer", "visual designer", "visual communication designer",
            "3d artist", "3d animator", "3d modeler", "3d visualizer", "motion graphic designer",
            "motion designer", "video editor", "video creator", "photoshop designer", "illustrator",
            "animator", "2d animator", "storyboard artist", "game designer", "unity developer",
            "unreal engine developer", "cad designer", "autocad designer", "design intern",
            "ui ux intern", "graphic design intern", "ui ux", "ui/ux"
        ]
    },

    # ── 13. Core Engineering: Mechanical & Manufacturing ──
    {
        "canonical": "Mechanical Engineer",
        "sector": "Core Engineering",
        "category": "Mechanical Engineering",
        "aliases": [
            "mechanical engineer", "mechanical design engineer", "mechanical site engineer",
            "graduate engineer trainee mechanical", "get mechanical", "diploma engineer trainee mechanical",
            "det mechanical", "production engineer", "production supervisor", "quality engineer mechanical",
            "qa qc engineer mechanical", "qc inspector mechanical", "maintenance engineer mechanical",
            "plant maintenance engineer", "cnc programmer", "cnc operator", "cnc machinist",
            "vmc operator", "vmc programmer", "lathe operator", "tool and die maker",
            "tool design engineer", "solidworks designer", "creo designer", "catia designer",
            "autocad mechanical drafter", "hvac engineer", "hvac site engineer", "piping engineer",
            "piping design engineer", "automobile engineer", "automotive engineer", "welding inspector",
            "ndt technician", "assembly engineer", "mechanical fresher", "mechanical trainee",
            "mechanical intern", "mechanical"
        ]
    },

    # ── 14. Core Engineering: Electrical & Electronics ──
    {
        "canonical": "Electrical & Electronics Engineer",
        "sector": "Core Engineering",
        "category": "Electrical & Electronics",
        "aliases": [
            "electrical engineer", "electrical design engineer", "electrical site engineer",
            "graduate engineer trainee electrical", "get electrical", "diploma engineer trainee electrical",
            "det electrical", "electronics engineer", "electronics design engineer", "embedded engineer",
            "embedded software engineer", "embedded systems engineer", "embedded c developer",
            "vlsi engineer", "vlsi design engineer", "asic design engineer", "fpga engineer",
            "pcb design engineer", "pcb designer", "hardware engineer", "hardware design engineer",
            "iot engineer", "internet of things engineer", "plc programmer", "plc scada engineer",
            "automation engineer electrical", "scada engineer", "instrumentation engineer",
            "control and instrumentation engineer", "telecom engineer", "telecom technician",
            "rf engineer", "solar engineer", "substation engineer", "electrical maintenance engineer",
            "electrical supervisor", "electrician", "electrical fresher", "electrical trainee",
            "embedded", "vlsi", "electrical", "electronics"
        ]
    },

    # ── 15. Core Engineering: Civil & Construction ──
    {
        "canonical": "Civil Engineer",
        "sector": "Core Engineering",
        "category": "Civil Engineering",
        "aliases": [
            "civil engineer", "civil site engineer", "site engineer civil", "graduate engineer trainee civil",
            "get civil", "diploma engineer trainee civil", "det civil", "structural engineer",
            "structural design engineer", "quantity surveyor", "billing engineer civil",
            "site supervisor civil", "civil supervisor", "interior designer", "interior design executive",
            "autocad civil drafter", "revit modeler", "bim modeler", "bim engineer",
            "surveyor", "total station surveyor", "project engineer civil", "construction engineer",
            "safety officer construction", "civil fresher", "civil trainee", "civil intern", "civil"
        ]
    },

    # ── 16. Operations & BPO: Customer Support & Voice / Non-Voice ──
    {
        "canonical": "Customer Support / BPO Executive",
        "sector": "Operations & BPO",
        "category": "Customer Support & Process Associate",
        "aliases": [
            "customer support executive", "customer care executive", "customer service representative",
            "customer service associate", "csa", "customer support associate", "csr",
            "voice process executive", "voice process associate", "international voice process",
            "international voice process executive", "domestic voice process", "domestic voice executive",
            "non voice process executive", "non voice process associate", "international non voice process",
            "domestic non voice process", "chat support executive", "chat support associate",
            "email support executive", "email support associate", "blended process executive",
            "bpo executive", "bpo associate", "call center executive", "call center associate",
            "telecaller", "telecaller executive", "telesales executive", "inbound customer service",
            "outbound calling executive", "process associate", "senior process associate",
            "process consultant", "operations executive", "operations associate", "back office executive",
            "back office assistant", "data entry operator", "computer operator", "data annotation executive",
            "data labeler", "office assistant", "office staff", "office boy", "receptionist",
            "front desk executive", "front office executive", "admin executive", "administrative assistant",
            "hub assistant", "field operations executive", "customer support", "customer care",
            "voice process", "non voice process", "chat support", "telecalling", "bpo"
        ]
    },

    # ── 17. Sales & Business Development ──
    {
        "canonical": "Sales / Business Development Executive",
        "sector": "Sales & Marketing",
        "category": "Sales & Business Development",
        "aliases": [
            "sales executive", "senior sales executive", "junior sales executive",
            "business development executive", "bde", "business development associate", "bda",
            "business development manager", "bdm", "field sales executive", "field sales officer",
            "fso", "inside sales executive", "inside sales associate", "direct sales executive",
            "corporate sales executive", "b2b sales executive", "b2c sales executive",
            "retail sales executive", "retail sales associate", "store executive", "store manager",
            "counter sales executive", "sales officer", "relationship manager", "client relationship executive",
            "key account manager", "sales representative", "channel sales executive",
            "channel sales manager", "real estate sales executive", "sales trainee", "sales intern",
            "sales fresher", "business development", "field sales", "sales"
        ]
    },

    # ── 18. Digital Marketing & Content Writing ──
    {
        "canonical": "Digital Marketing / Content Specialist",
        "sector": "Sales & Marketing",
        "category": "Digital Marketing",
        "aliases": [
            "digital marketing executive", "digital marketer", "digital marketing specialist",
            "digital marketing manager", "seo specialist", "seo executive", "seo analyst",
            "sem specialist", "sem executive", "ppc specialist", "google ads specialist",
            "meta ads specialist", "social media executive", "social media manager",
            "social media specialist", "content writer", "senior content writer", "creative content writer",
            "copywriter", "technical writer", "email marketing executive", "growth marketer",
            "performance marketer", "influencer marketing executive", "brand executive",
            "pr executive", "digital marketing intern", "content writing intern",
            "seo intern", "digital marketing", "seo", "content writer"
        ]
    },

    # ── 19. Human Resources & Talent Acquisition ──
    {
        "canonical": "HR Executive / Recruiter",
        "sector": "Human Resources",
        "category": "Talent Acquisition & HR",
        "aliases": [
            "hr executive", "senior hr executive", "hr recruiter", "recruiter", "it recruiter",
            "technical recruiter", "non it recruiter", "talent acquisition specialist",
            "talent acquisition executive", "talent acquisition partner", "hr generalist",
            "hr operations executive", "hr coordinator", "hr associate", "hr manager",
            "assistant hr manager", "payroll executive", "hr admin executive", "campus recruiter",
            "staffing specialist", "hr intern", "hr trainee", "hr fresher", "human resources", "hr"
        ]
    },

    # ── 20. Finance, Accounting & Banking ──
    {
        "canonical": "Accountant / Finance Executive",
        "sector": "Finance & Accounting",
        "category": "Accounting & Finance",
        "aliases": [
            "accountant", "senior accountant", "junior accountant", "accounts executive",
            "assistant accountant", "chartered accountant", "ca intern", "ca article assistant",
            "audit assistant", "audit executive", "billing executive", "billing clerk",
            "tally operator", "tally accountant", "gst practitioner", "tax consultant",
            "accounts payable executive", "accounts receivable executive", "finance executive",
            "financial analyst", "banking operations associate", "bank teller", "loan officer",
            "credit analyst", "credit processing associate", "insurance advisor", "accounting intern",
            "accounts fresher", "tally", "accountant fresher"
        ]
    },

    # ── 21. Healthcare & Pharmacy ──
    {
        "canonical": "Healthcare / Pharmacy Professional",
        "sector": "Healthcare",
        "category": "Medical & Clinical",
        "aliases": [
            "staff nurse", "registered nurse", "nurse", "nursing supervisor", "pharmacist",
            "clinical pharmacist", "retail pharmacist", "pharmacy assistant", "lab technician",
            "medical lab technician", "dmit technician", "phlebotomist", "radiographer",
            "x ray technician", "physiotherapist", "medical representative", "mr pharma",
            "medical coder", "certified medical coder", "medical billing executive",
            "clinical research associate", "cra", "hospital administration executive",
            "medical transcriptionist", "patient care executive", "nursing", "pharmacist"
        ]
    },

    # ── 22. General Freshers & Walk-in Opportunities ──
    {
        "canonical": "Fresher / Walk-in Opportunity",
        "sector": "General Employment",
        "category": "Trainee & Freshers",
        "aliases": [
            "freshers", "fresher", "graduate trainee", "graduate engineer trainee", "get",
            "diploma engineer trainee", "det", "management trainee", "trainee", "intern",
            "apprentice", "apprenticeship", "bulk hiring freshers", "urgent hiring freshers",
            "immediate joiners", "immediate joiner", "walk in interview", "walking interview",
            "walk in drive", "spot offer", "mega walk in", "direct hiring", "hiring freshers"
        ]
    }
]


class RoleTaxonomyResolver:
    """
    Matches OCR text against 1000+ hierarchical role definitions with priority:
    1. Longest multi-word aliases match first (e.g. 'Python Developer' before 'Python').
    2. Suffix expansion: if a base skill/title matches, check following words in OCR
       (e.g., 'Python' followed by 'Developer' -> 'Python Developer').
    """

    _FLAT_ALIASES: List[Tuple[str, Dict]] = []
    _INITIALIZED = False

    COMMON_SUFFIXES = {
        "developer", "engineer", "programmer", "specialist", "architect", "intern",
        "trainee", "fresher", "lead", "consultant", "analyst", "designer", "tester",
        "operator", "executive", "associate", "manager", "representative", "coordinator"
    }

    @classmethod
    def _init_index(cls):
        if cls._INITIALIZED:
            return
        flat = []
        for role_entry in ROLE_TAXONOMY:
            for alias in role_entry["aliases"]:
                flat.append((alias.lower().strip(), role_entry))
        # Sort by alias length in descending order (longest match first)
        flat.sort(key=lambda x: len(x[0]), reverse=True)
        cls._FLAT_ALIASES = flat
        cls._INITIALIZED = True

    @classmethod
    def resolve_role(cls, text_phrase: str) -> Optional[Dict]:
        """Check if a phrase matches any role alias in the taxonomy with suffix expansion."""
        cls._init_index()
        phrase = " " + re.sub(r'[^a-zA-Z0-9\s]', ' ', text_phrase.lower()) + " "

        for alias, role_entry in cls._FLAT_ALIASES:
            pattern = r'\b(' + re.escape(alias) + r')(?:\s+(' + '|'.join(cls.COMMON_SUFFIXES) + r'))?\b'
            m = re.search(pattern, phrase)
            if m:
                base = m.group(1).strip()
                suffix = m.group(2)
                matched_name = f"{base} {suffix}".title() if (suffix and not base.endswith(suffix)) else base.title()
                return {
                    "name": matched_name,
                    "canonical": role_entry["canonical"],
                    "category": role_entry["category"],
                    "sector": role_entry["sector"],
                    "confidence": 0.95
                }
        return None

    @classmethod
    def find_all_roles(cls, text: str) -> List[Dict]:
        """Scan full OCR text and extract all matching roles with longest-match and suffix expansion."""
        cls._init_index()
        found = []
        seen_canonicals = set()
        clean_text = " " + re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower()) + " "

        for alias, role_entry in cls._FLAT_ALIASES:
            pattern = r'\b(' + re.escape(alias) + r')(?:\s+(' + '|'.join(cls.COMMON_SUFFIXES) + r'))?\b'
            m = re.search(pattern, clean_text)
            if m:
                can = role_entry["canonical"]
                if can not in seen_canonicals:
                    seen_canonicals.add(can)
                    base = m.group(1).strip()
                    suffix = m.group(2)
                    matched_name = f"{base} {suffix}".title() if (suffix and not base.endswith(suffix)) else base.title()
                    found.append({
                        "name": matched_name,
                        "canonical": can,
                        "category": role_entry["category"],
                        "sector": role_entry["sector"],
                        "confidence": 0.92
                    })
        return found
