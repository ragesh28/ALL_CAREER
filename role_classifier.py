import re

# Ordered list of roles to match specific first, generic last
ROLE_KEYWORDS = [
    # TECH - SPECIALIZED
    ('Full Stack Developer', ['full stack', 'fullstack', 'full-stack']),
    ('Frontend Developer', ['frontend', 'front-end', 'front end', 'react', 'angular', 'vue', 'ui developer', 'ui engineer']),
    ('Backend Developer', ['backend', 'back-end', 'back end', 'node', 'django', 'flask', 'spring boot']),
    ('Mobile App Developer', ['mobile', 'ios', 'android', 'flutter', 'react native', 'swift', 'kotlin']),
    ('Data Scientist', ['data scientist', 'data science']),
    ('AI Engineer', ['ai engineer', 'artificial intelligence', 'generative ai', 'openai', 'llm']),
    ('ML Engineer', ['machine learning', 'ml engineer', 'deep learning', 'computer vision', 'nlp']),
    ('Data Engineer', ['data engineer', 'data pipeline', 'etl', 'spark', 'hadoop']),
    ('Data Analyst', ['data analyst', 'business analyst', 'analytics', 'bi analyst']),
    ('DevOps Engineer', ['devops', 'dev ops', 'site reliability', 'sre', 'ci/cd']),
    ('Cloud Architect', ['cloud architect', 'cloud engineer', 'aws', 'azure', 'gcp', 'cloud practitioner']),
    ('Software Architect', ['software architect', 'solution architect', 'technical architect']),
    ('Penetration Tester', ['penetration', 'pentest', 'ethical hacker', 'red team']),
    ('Security Analyst', ['security analyst', 'cybersecurity', 'information security', 'infosec', 'security engineer']),
    ('Network Engineer', ['network engineer', 'network admin']),
    ('SDET', ['sdet', 'test automation', 'automation engineer', 'qa automation']),
    ('QA Analyst', ['qa analyst', 'qa engineer', 'quality assurance', 'tester', 'manual testing']),
    ('DBA', ['database admin', 'dba', 'database engineer', 'database administrator']),
    ('Systems Administrator', ['system admin', 'sysadmin', 'systems engineer']),
    
    # NON-TECH - SPECIALIZED
    ('UI/UX Designer', ['ui/ux', 'ui ux', 'user experience', 'user interface', 'designer', 'graphic designer', 'product designer']),
    ('Scrum Master', ['scrum master', 'agile coach', 'agile']),
    ('Technical Writer', ['technical writer', 'content writer', 'documentation']),
    ('Digital Marketer', ['digital market', 'seo', 'social media', 'marketing']),
    ('Technical Recruiter', ['recruiter', 'talent acquisition', 'hiring']),
    ('HR Business Partner', ['hr', 'human resource', 'people ops', 'hrbp']),
    ('Customer Success Manager', ['customer success', 'client success', 'csm']),
    ('Operations Manager', ['operations manager', 'ops manager']),
    ('Financial Analyst', ['financial analyst', 'finance', 'accounting', 'accountant']),
    ('Pre-Sales Consultant', ['pre-sales', 'presales', 'solutions consultant']),
    ('UX Researcher', ['ux research', 'user research']),
    ('IT Support', ['it support', 'helpdesk', 'help desk', 'tech support', 'desktop support']),
    ('Legal Counsel', ['legal', 'counsel', 'compliance', 'attorney']),
    
    # GENERIC / FALLBACKS
    ('Product Manager', ['product manager', 'product owner', 'product lead']),
    ('Project Manager', ['project manager', 'program manager', 'pmo']),
    ('Sales Executive', ['sales', 'account executive', 'business development', 'bde']),
    ('Software Engineer', ['software engineer', 'software developer', 'swe', 'sde', 'programmer', 'developer']),
]

def classify_job(job):
    """
    Classify a job into a role category.
    Returns: (role_category, confidence)
    """
    title = str(job.get("title") or job.get("role") or "").strip().lower()
    search_kw = str(job.get("search_keyword") or job.get("role_search") or "").strip().lower()
    
    # Remove boundary characters to make matching cleaner
    title_words = re.findall(r'\b\w+\b', title)
    title_clean = " ".join(title_words)
    
    # 1. Match by Title (most specific/accurate)
    for category, keywords in ROLE_KEYWORDS:
        for kw in keywords:
            # We want word boundaries for keywords, or check if they are in the clean title
            # E.g. "react" matches "react developer", but we should be careful with substring issues.
            # Using regex with \b for word boundaries.
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, title_clean):
                return category
                
    # 2. Match by Search Keyword (if title match failed)
    if search_kw:
        for category, keywords in ROLE_KEYWORDS:
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, search_kw):
                    return category
                    
    # 3. Fallback check for any keyword match in search_kw directly (substring match)
    if search_kw:
        for category, keywords in ROLE_KEYWORDS:
            if search_kw in [k.lower() for k in keywords]:
                return category
                
    return "Other"
