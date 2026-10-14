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

export interface WalkinDateItem {
  label: string;
  dateObj: Date;
}

export function parseWalkinDateObjects(rawDateStr: string | undefined | null): WalkinDateItem[] {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const maxFuture = new Date(now.getTime() + 60 * 24 * 60 * 60 * 1000); // 60 days rolling window
  maxFuture.setHours(23, 59, 59, 999);
  const currentYear = now.getFullYear();
  const resultDates: WalkinDateItem[] = [];

  if (!rawDateStr || typeof rawDateStr !== 'string') return resultDates;
  let text = cleanTimeAndNoise(String(rawDateStr).replace(/[_]/g, ' '));
  text = text.replace(/\b(\d{1,2}(?:st|nd|rd|th)?)([A-Za-z]{3,9})\b/gi, '$1 $2');

  function addDate(y: number, m: number, d: number) {
    if (m >= 0 && m <= 11 && d >= 1 && d <= 31) {
      const dObj = new Date(y, m, d);
      dObj.setHours(0, 0, 0, 0);
      if (dObj >= now && dObj <= maxFuture) {
        resultDates.push({
          label: `${MONTH_SHORT[m]} ${d}`,
          dateObj: dObj
        });
      }
    }
  }

  function getMonthIndex(str: string): number {
    if (!str) return -1;
    const s = str.toLowerCase().slice(0, 3);
    return MONTH_SHORT.findIndex(m => m.toLowerCase() === s);
  }

  function dedupe(arr: WalkinDateItem[]): WalkinDateItem[] {
    const seen = new Set<string>();
    return arr.filter(item => {
      if (seen.has(item.label)) return false;
      seen.add(item.label);
      return true;
    });
  }

  const low = text.toLowerCase();
  if (low.includes('today')) {
    addDate(now.getFullYear(), now.getMonth(), now.getDate());
  }
  if (low.includes('tomorrow')) {
    const tom = new Date(now.getTime() + 86400000);
    addDate(tom.getFullYear(), tom.getMonth(), tom.getDate());
  }

  // 1. Cross-month or discrete dates with two months:
  // e.g. '28th Aug - 2nd Sep 2026', '7th Sep & 8th Sep 2026', '16 Sep - 15 Dec'
  const crossMonth = text.match(/\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\s*(?:(-|–|—|\bto\b)|(&|\band\b|,))\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})(?:\s*,?\s*(\d{2,4}))?\b/i);
  if (crossMonth) {
    const d1 = parseInt(crossMonth[1], 10), m1 = getMonthIndex(crossMonth[2]);
    const isRange = Boolean(crossMonth[3]);
    const d2 = parseInt(crossMonth[5], 10), m2 = getMonthIndex(crossMonth[6]);
    let yr = crossMonth[7] ? parseInt(crossMonth[7], 10) : currentYear;
    if (yr < 100) yr += 2000;
    if (m1 !== -1 && m2 !== -1) {
      if (isRange) {
        const sDate = new Date(yr, m1, d1);
        const eDate = new Date(yr, m2, d2);
        sDate.setHours(0, 0, 0, 0); eDate.setHours(0, 0, 0, 0);
        const diff = Math.round((eDate.getTime() - sDate.getTime()) / 86400000);
        if (diff >= 0 && diff <= 90) {
          for (let cur = new Date(sDate); cur <= eDate; cur.setDate(cur.getDate() + 1)) {
            addDate(cur.getFullYear(), cur.getMonth(), cur.getDate());
          }
          return dedupe(resultDates);
        }
      } else {
        addDate(yr, m1, d1);
        addDate(yr, m2, d2);
        return dedupe(resultDates);
      }
    }
  }

  // 2. Same-month discrete dates or range BEFORE month name:
  // e.g. '7th - 9th September 2026', '7th & 8th Sep 2026', '10th to 12th Sep', '7, 8 & 9 Sep'
  const preMonthRange = text.match(/\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:(-|–|—|\bto\b|&|\band\b|,)\s*(\d{1,2})(?:st|nd|rd|th)?)+\s+([A-Za-z]{3,9})(?:\s*,?\s*(\d{2,4}))?\b/i);
  if (preMonthRange) {
    const mIdx = getMonthIndex(preMonthRange[4]);
    let yr = preMonthRange[5] ? parseInt(preMonthRange[5], 10) : currentYear;
    if (yr < 100) yr += 2000;
    if (mIdx !== -1) {
      const fullMatchedStr = preMonthRange[0];
      const daysSection = fullMatchedStr.slice(0, fullMatchedStr.toLowerCase().lastIndexOf(preMonthRange[4].toLowerCase()));
      const days = [...daysSection.matchAll(/\b(\d{1,2})(?:st|nd|rd|th)?\b/gi)]
        .map(m => parseInt(m[1], 10))
        .filter(d => d >= 1 && d <= 31);

      const isContinuousRange = /(-|–|—|\bto\b)/i.test(daysSection);
      if (isContinuousRange && days.length >= 2) {
        const minD = Math.min(...days);
        const maxD = Math.max(...days);
        if (maxD - minD <= 31) {
          for (let d = minD; d <= maxD; d++) addDate(yr, mIdx, d);
          return dedupe(resultDates);
        }
      } else if (days.length > 0) {
        days.forEach(d => addDate(yr, mIdx, d));
        return dedupe(resultDates);
      }
    }
  }

  // 3. Month name followed by day range: e.g. 'September 7 - 9, 2026' or 'Sep 7 to 10'
  const postMonthRange = text.match(/\b([A-Za-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?\s*(?:-|–|—|\bto\b|&|\band\b)\s*(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{2,4}))?\b/i);
  if (postMonthRange) {
    const mIdx = getMonthIndex(postMonthRange[1]);
    let yr = postMonthRange[4] ? parseInt(postMonthRange[4], 10) : currentYear;
    if (yr < 100) yr += 2000;
    if (mIdx !== -1) {
      const d1 = parseInt(postMonthRange[2], 10);
      const d2 = parseInt(postMonthRange[3], 10);
      const minD = Math.min(d1, d2);
      const maxD = Math.max(d1, d2);
      if (maxD - minD <= 31) {
        for (let d = minD; d <= maxD; d++) addDate(yr, mIdx, d);
        return dedupe(resultDates);
      }
    }
  }

  // 4. Single full date:
  // e.g. '5-Sep-26', '05-Sep-2026', '5th Sep 2026', '7 September 2026', 'Sep 7, 2026'
  const dayMonthSingle = text.match(/\b(\d{1,2})(?:st|nd|rd|th)?[-/\s]+([A-Za-z]{3,9})(?:[-/\s]+(20\d{2}|\b\d{2}\b))?\b/i);
  if (dayMonthSingle) {
    const d = parseInt(dayMonthSingle[1], 10);
    const mIdx = getMonthIndex(dayMonthSingle[2]);
    let yr = dayMonthSingle[3] ? parseInt(dayMonthSingle[3], 10) : currentYear;
    if (yr < 100) yr += 2000;
    if (mIdx !== -1) {
      addDate(yr, mIdx, d);
      return dedupe(resultDates);
    }
  }

  const monthDaySingle = text.match(/\b([A-Za-z]{3,9})[-/\s]+(\d{1,2})(?:st|nd|rd|th)?(?:[-/\s,]+(20\d{2}|\b\d{2}\b))?\b/i);
  if (monthDaySingle) {
    const mIdx = getMonthIndex(monthDaySingle[1]);
    const d = parseInt(monthDaySingle[2], 10);
    let yr = monthDaySingle[3] ? parseInt(monthDaySingle[3], 10) : currentYear;
    if (yr < 100) yr += 2000;
    if (mIdx !== -1) {
      addDate(yr, mIdx, d);
      return dedupe(resultDates);
    }
  }

  // 5. ISO format: YYYY-MM-DD
  const isoMatch = text.match(/\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b/);
  if (isoMatch) {
    addDate(parseInt(isoMatch[1], 10), parseInt(isoMatch[2], 10) - 1, parseInt(isoMatch[3], 10));
    return dedupe(resultDates);
  }

  // 6. Numeric: DD/MM/YYYY or DD-MM-YYYY
  const numMatch = text.match(/\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b/);
  if (numMatch) {
    let d = parseInt(numMatch[1], 10), m = parseInt(numMatch[2], 10) - 1, y = parseInt(numMatch[3], 10);
    if (y < 100) y += 2000;
    if (m > 11 && d <= 12) { const tmp = d; d = m + 1; m = tmp - 1; }
    addDate(y, m, d);
    return dedupe(resultDates);
  }

  return dedupe(resultDates);
}

export function parseWalkinDates(rawStr: string | undefined | null): string[] {
  return parseWalkinDateObjects(rawStr).map(item => item.label);
}

export function getWalkinDateObjects(job: any): WalkinDateItem[] {
  if (!job || !isWalkinJob(job)) return [];

  let rawDateStr = String(job.walkin_date || '').trim();
  if (!rawDateStr && Array.isArray(job.walkin_dates) && job.walkin_dates.length > 0) {
    rawDateStr = job.walkin_dates.join(' ');
  }
  if (!rawDateStr) {
    rawDateStr = extractWalkinDateFromText(job.title) || extractWalkinDateFromText(job.description) || '';
  }
  if (!rawDateStr) return [];
  return parseWalkinDateObjects(rawDateStr);
}

export function getJobWalkinDates(job: any): string[] {
  return getWalkinDateObjects(job).map(item => item.label);
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

export const PRIMARY_PORTAL_IDS = new Set([
  'linkedin',
  'naukri',
  'indeed',
  'internshala',
  'glassdoor',
  'shine',
  'timesjobs',
  'hirist',
  'workindia',
  'foundit',
  'apna',
  'freshersworld',
  'telegram_message',
  'telegram_post',
  'telegram',
  'google_images',
  'images'
]);

export function isOtherSource(source: string | null | undefined): boolean {
  if (!source) return true;
  const s = source.toLowerCase().trim();
  if (PRIMARY_PORTAL_IDS.has(s)) return false;
  if (s.includes('telegram')) return false;
  if (s.includes('google') || s.includes('flyer')) return false;
  return true;
}

