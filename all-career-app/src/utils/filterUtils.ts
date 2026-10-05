export function isWalkinJob(job: any): boolean {
  if (!job) return false;
  if (job.is_walkin === true || job.is_walkin === 'true') return true;
  if (Boolean(job.walkin_date)) return true;
  if (Array.isArray(job.walkin_dates) && job.walkin_dates.length > 0) return true;

  const src = String(job.source || '').toLowerCase();
  if (src === 'google_images' || src.includes('google') || src.includes('flyer')) return true;

  const title = String(job.title || job.role || '');
  const desc = String(job.description || job.other_details || '');
  const walkKwRegex = /\b(walk[\s-]?in|walking[\s-]?interview|walkin|walk-in drive|direct interview)\b/i;

  if (walkKwRegex.test(title) || walkKwRegex.test(desc)) {
    return true;
  }
  return false;
}

export const MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function cleanTimeAndNoise(text: string): string {
  if (!text) return "";
  let s = text;
  s = s.replace(/\b\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm)\b(?:\s*(?:-|–|—|to)\s*\b\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm)\b)?/gi, ' ');
  s = s.replace(/\b\d{1,2}[:.]\d{2}\b/g, ' ');
  s = s.replace(/\b\d{1,2}\s*(?:-|–|to)\s*\d{1,2}\s*(?:years?|yrs?)\b/gi, ' ');
  s = s.replace(/\b\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?\s*(?:lacs?|lpa|ctc)\b/gi, ' ');
  s = s.replace(/\b(?:\+?91|0)?[6-9]\d{9}\b/g, ' ');
  return s;
}

export function extractWalkinDateFromText(text: string): string | null {
  if (!text || typeof text !== 'string') return null;
  const labelMatch = text.match(/(?:walk[\s-]?in\s*(?:date|drive)?|interview\s*date|time\s*and\s*venue|date\s*&?\s*time)\s*[:\-]?\s*([^\n\r]+)/i);
  if (labelMatch) {
    const candidate = labelMatch[1].trim();
    const dMatch = candidate.match(/\b(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\s*(?:-|–|—|to|&)\s*\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}|\d{1,2}(?:st|nd|rd|th)?\s*(?:-|–|—|to|&)\s*\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}|\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}(?:\s*,?\s*\d{4})?|\d{1,2}[-/.](?:\d{1,2}|[A-Za-z]{3})[-/.]\d{2,4})\b/i);
    if (dMatch) return dMatch[0].trim();
  }

  const rangeBoth = text.match(/\b(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\s*(?:-|–|—|to|&)\s*\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}(?:\s*,?\s*\d{4})?)\b/i);
  if (rangeBoth) return rangeBoth[1].trim();

  const rangeSame = text.match(/\b(\d{1,2}(?:st|nd|rd|th)?\s*(?:-|–|—|to|&)\s*\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}(?:\s*,?\s*\d{4})?)\b/i);
  if (rangeSame) return rangeSame[1].trim();

  const single = text.match(/\b(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}(?:\s*,?\s*\d{4})?)\b/i);
  if (single) return single[1].trim();

  const std = text.match(/\b(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b/);
  if (std) return std[1].trim();
  return null;
}

export function parseWalkinDates(rawStr: string | undefined | null): string[] {
  if (!rawStr) return [];
  let text = cleanTimeAndNoise(String(rawStr).replace(/_/g, ' '));
  text = text.replace(/\b(\d{1,2}(?:st|nd|rd|th)?)([A-Za-z]{3,9})\b/gi, '$1 $2');

  const results: string[] = [];

  const getMonthIdx = (mStr: string) => {
    if (!mStr) return -1;
    const s = mStr.toLowerCase().slice(0, 3);
    return MONTH_SHORT.findIndex(m => m.toLowerCase() === s);
  };

  const addD = (_y: number, m: number, d: number) => {
    if (m >= 0 && m <= 11 && d >= 1 && d <= 31) {
      const lbl = `${MONTH_SHORT[m]} ${d}`;
      if (!results.includes(lbl)) {
        results.push(lbl);
      }
    }
  };

  // ISO date 2026-09-22
  const iso = text.match(/\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b/);
  if (iso) {
    addD(parseInt(iso[1]), parseInt(iso[2]) - 1, parseInt(iso[3]));
  }

  // D-M-Y: 22-09-2026
  const dmy = text.match(/\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2}|\d{2})\b/);
  if (dmy) {
    let y = parseInt(dmy[3]);
    if (y < 100) y += 2000;
    addD(y, parseInt(dmy[2]) - 1, parseInt(dmy[1]));
  }

  // 19 Sep 26 or 19-Sep-26 or 19th Sep 2026 or 19 September
  const dm = text.match(/\b(\d{1,2})(?:st|nd|rd|th)?[-/\s]+([A-Za-z]{3,9})(?:[-/\s]+(20\d{2}|\d{2}))?\b/i);
  if (dm) {
    const mIdx = getMonthIdx(dm[2]);
    if (mIdx !== -1) {
      let y = dm[3] ? parseInt(dm[3]) : 2026;
      if (y < 100) y += 2000;
      addD(y, mIdx, parseInt(dm[1]));
    }
  }

  // Month-Day: Sep 22 or September 22 or Sept 12
  const md = text.match(/\b([A-Za-z]{3,9})[-/\s]+(\d{1,2})(?:st|nd|rd|th)?(?:[-/\s]+(20\d{2}|\d{2}))?\b/i);
  if (md) {
    const mIdx = getMonthIdx(md[1]);
    if (mIdx !== -1) {
      let y = md[3] ? parseInt(md[3]) : 2026;
      if (y < 100) y += 2000;
      addD(y, mIdx, parseInt(md[2]));
    }
  }

  // Range: 21 Sep - 25 Sep
  const rngBoth = text.match(/\b(\d{1,2})[-/\s]+([A-Za-z]{3,9})\s*(?:-|–|to)\s*(\d{1,2})[-/\s]+([A-Za-z]{3,9})\b/i);
  if (rngBoth) {
    const m1 = getMonthIdx(rngBoth[2]);
    const m2 = getMonthIdx(rngBoth[4]);
    const d1 = parseInt(rngBoth[1]);
    const d2 = parseInt(rngBoth[3]);
    if (m1 !== -1 && m2 !== -1) {
      addD(2026, m1, d1);
      addD(2026, m2, d2);
    }
  }

  // Range: 21 - 25 Sep
  const rngSame = text.match(/\b(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\s+([A-Za-z]{3,9})\b/i);
  if (rngSame) {
    const mIdx = getMonthIdx(rngSame[3]);
    if (mIdx !== -1) {
      const d1 = parseInt(rngSame[1]);
      const d2 = parseInt(rngSame[2]);
      for (let day = Math.min(d1, d2); day <= Math.max(d1, d2); day++) {
        addD(2026, mIdx, day);
      }
    }
  }

  return results;
}

export function getJobWalkinDates(job: any): string[] {
  if (Array.isArray(job.walkin_dates) && job.walkin_dates.length > 0) {
    return job.walkin_dates;
  }
  let raw = job.walkin_date || '';
  if (!raw) {
    raw = extractWalkinDateFromText(job.title || '') || extractWalkinDateFromText(job.description || '') || '';
  }
  if (!raw) {
    raw = job.date || job.posted || job.date_posted || job.fetchedAt || '';
  }
  return parseWalkinDates(raw);
}

export function parseExperience(expStr: string | undefined | null): [number | null, number | null] {
  if (!expStr) return [null, null];
  const s = String(expStr).toLowerCase().trim();

  // 1. Try to extract numbers first (HIGHEST PRIORITY)
  const nums = s.match(/\d+/g);
  if (nums) {
    const parsed = nums.map(Number).filter(n => n <= 30);
    if (parsed.length >= 2) {
      return [Math.min(parsed[0], parsed[1]), Math.max(parsed[0], parsed[1])];
    } else if (parsed.length === 1) {
      if (s.includes('+') || s.includes('to ')) return [parsed[0], 30];
      if (s.includes('-')) return [0, parsed[0]];
      return [parsed[0], parsed[0]];
    }
  }

  // 2. Keyword fallback (no numbers found)
  if (s.includes('fresher') || s.includes('entry')) return [0, 0];
  if (s.includes('intern') || s.includes('trainee')) return [0, 1];
  if (s.includes('lead') || s.includes('tech lead')) return [7, 30];
  if (s.includes('senior') || s === 'sr') return [5, 30];
  if (s.includes('principal') || s.includes('staff')) return [10, 30];
  if (s.includes('manager') || s.includes('director')) return [8, 30];

  return [null, null];
}

export const ROLE_KEYWORDS: Record<string, string[]> = {
  // --- Tech Roles (High Popularity) ---
  'Software Engineer': ['software engineer', 'swe', 'sde'],
  'Software Developer': ['software developer', 'programmer', 'developer'],
  'Full Stack Developer': ['full stack', 'fullstack', 'full-stack'],
  'Frontend Developer': ['frontend', 'front-end', 'front end', 'react', 'angular', 'vue', 'html', 'css', 'ui developer'],
  'Backend Developer': ['backend', 'back-end', 'back end', 'node', 'django', 'spring', 'flask'],
  'React Developer': ['react js', 'reactjs', 'react developer', 'react.js'],
  'Java Developer': ['java ', 'spring boot', 'springboot', 'j2ee'],
  'Python Developer': ['python', 'django', 'flask'],
  'Node.js Developer': ['node.js', 'nodejs', 'node js'],
  'Android Developer': ['android developer', 'kotlin', 'android'],
  'iOS Developer': ['ios developer', 'swift', 'objective-c', 'ios'],
  'Mobile App Developer': ['mobile', 'app developer', 'ios', 'android'],
  'Data Analyst': ['data analyst', 'business analyst', 'analytics'],
  'Data Scientist': ['data scientist', 'data science', 'ai/ml'],
  'Data Engineer': ['data engineer', 'big data', 'etl', 'spark', 'hadoop'],
  'DevOps Engineer': ['devops', 'dev ops', 'site reliability', 'sre', 'ci/cd'],
  'UI UX Designer': ['ui', 'ux', 'user experience', 'user interface', 'figma', 'sketch'],
  'QA Engineer': ['qa engineer', 'tester', 'qa', 'testing'],
  'QA Analyst': ['qa analyst', 'quality assurance', 'testing'],
  'QA Automation Engineer': ['qa automation', 'automation engineer', 'selenium'],
  'Test Automation Engineer': ['test automation', 'automation tester'],
  'SDET': ['sdet', 'software development engineer in test', 'automation test'],
  'AI Engineer': ['ai engineer', 'artificial intelligence', 'generative ai', 'openai', 'llm'],
  'Machine Learning Engineer': ['machine learning', 'ml engineer', 'deep learning'],

  // --- Business & Management ---
  'Product Manager': ['product manager', 'product owner', 'product lead'],
  'Project Manager': ['project manager', 'program manager', 'pmo'],
  'Technical Project Manager': ['technical project manager', 'tpm'],
  'Business Development Executive': ['business development', 'bde', 'sales development'],
  'Business Development Manager': ['business development manager', 'bdm'],
  'Sales Executive': ['sales executive', 'inside sales', 'telecaller', 'sales'],
  'Sales Manager': ['sales manager', 'account manager'],

  // --- Non-Tech, Marketing & Design ---
  'HR Executive': ['hr executive', 'human resources executive', 'hr'],
  'HR Manager': ['hr manager', 'human resource manager'],
  'Technical Recruiter': ['technical recruiter', 'it recruiter', 'recruiter'],
  'Talent Acquisition Specialist': ['talent acquisition', 'ta specialist', 'hiring'],
  'HR Business Partner': ['hrbp', 'hr business partner'],
  'Customer Support Executive': ['customer support', 'customer care', 'helpdesk', 'voice process'],
  'Customer Success Manager': ['customer success', 'client success'],
  'Digital Marketer': ['digital marketing', 'digital marketer', 'sem', 'ppc'],
  'Digital Marketing Manager': ['digital marketing manager', 'marketing manager'],
  'Product Marketing Manager': ['product marketing', 'marketing manager'],
  'SEO Specialist': ['seo', 'search engine optimization'],
  'Content Writer': ['content writer', 'copywriter', 'blog writer'],
  'Graphic Designer': ['graphic designer', 'illustrator', 'photoshop'],

  // --- Cloud, Network & Security ---
  'Cloud Engineer': ['cloud engineer', 'aws', 'azure', 'gcp'],
  'Cloud Architect': ['cloud architect', 'solutions architect'],
  'AWS Engineer': ['aws engineer', 'amazon web services'],
  'Azure Engineer': ['azure engineer', 'microsoft azure'],
  'Systems Administrator': ['system admin', 'sysadmin', 'systems administrator'],
  'System Administrator': ['system admin', 'sysadmin', 'system administrator'],
  'Network Engineer': ['network engineer', 'network administrator'],
  'Cybersecurity Analyst': ['cybersecurity analyst', 'security analyst'],
  'Cybersecurity Engineer': ['cybersecurity engineer', 'information security'],
  'Security Analyst': ['security analyst', 'soc analyst'],
  'Penetration Tester': ['penetration', 'pentest', 'ethical hacker'],
  'Database Administrator': ['dba', 'database administrator', 'sql admin'],

  // --- Specialized Tech ---
  'Flutter Developer': ['flutter'],
  'React Native Developer': ['react native'],
  'Angular Developer': ['angular'],
  'Salesforce Developer': ['salesforce', 'sfdc'],
  'SAP Consultant': ['sap '],
  'Blockchain Developer': ['blockchain', 'solidity', 'web3'],
  'Game Developer': ['game developer', 'unity', 'unreal'],
  'Embedded Systems Engineer': ['embedded', 'microcontroller', 'rtos'],
  'VLSI Engineer': ['vlsi', 'asic', 'fpga'],
  'Hardware Engineer': ['hardware engineer', 'pcb'],
  'ETL Developer': ['etl', 'informatica', 'talend'],
  'Business Intelligence Analyst': ['bi analyst', 'power bi', 'tableau'],
  'Deep Learning Engineer': ['deep learning', 'neural network'],
  'NLP Engineer': ['nlp ', 'natural language processing'],
  'Site Reliability Engineer': ['sre', 'site reliability'],
  'Software Architect': ['software architect', 'solution architect', 'technical architect'],

  // --- Operations, Finance & Specialized Non-Tech ---
  'Operations Manager': ['operations manager', 'ops manager'],
  'Financial Analyst': ['financial analyst', 'finance analyst'],
  'Accountant': ['accountant', 'tally', 'bookkeeper'],
  'Finance Executive': ['finance executive', 'accounts executive'],
  'Supply Chain Analyst': ['supply chain analyst', 'logistics analyst'],
  'Supply Chain Manager': ['supply chain manager', 'scm'],
  'Logistics Executive': ['logistics executive', 'dispatch'],
  'Legal Counsel': ['legal counsel', 'corporate lawyer', 'compliance officer'],
  'Scrum Master': ['scrum master'],
  'UX Researcher': ['ux research', 'user research'],
  'Technical Writer': ['technical writer', 'documentation specialist'],
  'Video Editor': ['video editor', 'premiere pro', 'after effects'],
  'Social Media Manager': ['social media manager', 'smm'],
  'Pre-Sales Consultant': ['pre-sales', 'presales'],
  'IT Support Specialist': ['it support', 'helpdesk', 'help desk', 'tech support'],

  // --- Legacy Slugs Support ---
  'software-engineer': ['software engineer', 'swe', 'sde', 'developer', 'software developer'],
  'full-stack': ['full stack', 'fullstack', 'full-stack'],
  'frontend': ['frontend', 'front-end', 'front end', 'react', 'angular', 'vue', 'html', 'css', 'ui developer'],
  'backend': ['backend', 'back-end', 'back end', 'node', 'django', 'spring', 'flask'],
  'python': ['python', 'django', 'flask', 'fastapi'],
  'java': ['java ', 'spring boot', 'springboot', 'j2ee'],
  'devops': ['devops', 'dev ops', 'site reliability', 'sre', 'ci/cd', 'cloud', 'aws', 'docker'],
  'data-science': ['data analyst', 'business analyst', 'analytics', 'data scientist', 'data science', 'ai/ml', 'data engineer'],
  'sales-marketing': ['sales', 'marketing', 'bde', 'business development', 'inside sales', 'tele sales', 'telesales', 'telecaller'],
  'customer-support': ['customer support', 'customer care', 'helpdesk', 'voice process', 'bpo', 'kpo', 'chat support'],
  'hr': ['hr executive', 'human resources', 'recruiter', 'technical recruiter', 'talent acquisition'],
  'qa-tester': ['qa engineer', 'tester', 'qa', 'testing', 'qa analyst', 'automation engineer', 'selenium', 'sdet']
};

export const ROLE_CATEGORIES_DICT: Record<string, string[]> = {
  'Technical': [
    'software', 'developer', 'engineer', 'full stack', 'frontend', 'backend', 'java', 'python', 'react', 'node',
    'sql', 'dba', 'devops', 'cloud', 'aws', 'azure', 'tester', 'testing', 'qa', 'quality assurance', 'sdet',
    'automation', 'data analyst', 'data engineer', 'data scientist', 'machine learning', 'ai', 'ml'
  ],
  'Electrical': [
    'electrical', 'electrician', 'electronics', 'ece', 'eee', 'embedded', 'vlsi', 'panel design', 'plc', 'scada',
    'pcb', 'mechanical', 'civil', 'autocad', 'cad', 'technician', 'assembly'
  ],
  'Non-Technical': [
    'voice', 'semi voice', 'non voice', 'chat', 'chat support', 'customer support', 'customer care',
    'bpo', 'kpo', 'call center', 'front desk', 'back office', 'data entry', 'executive', 'operations'
  ],
  'Pharma': [
    'pharma', 'pharmacy', 'pharmacist', 'healthcare', 'medical', 'clinical', 'nursing', 'biotech',
    'hospital', 'mbbs', 'b.pharm', 'm.pharm', 'chemist', 'chemistry'
  ],
  'Banking & Finance': [
    'banker', 'banking', 'bank', 'accountant', 'accounts', 'finance', 'financial', 'audit', 'ca', 'tally', 'tax', 'credit', 'loan'
  ],
  'Sales & Marketing': [
    'sales', 'marketing', 'bde', 'business development', 'inside sales', 'tele sales', 'telesales', 'digital marketing', 'telecaller'
  ],
  'HR & Staffing': [
    'hr', 'human resources', 'recruiter', 'recruitment', 'talent acquisition', 'staffing', 'payroll'
  ]
};

export function classifyJobCategory(job: any): string {
  if (!job) return 'Others';
  const text = `${job.title || ''} ${job.role || ''} ${job.role_category || ''} ${job.company || ''} ${job.description || ''}`.toLowerCase();

  for (const [cat, keywords] of Object.entries(ROLE_CATEGORIES_DICT)) {
    for (const kw of keywords) {
      if (text.includes(kw.toLowerCase())) return cat;
    }
  }
  return 'Others';
}
