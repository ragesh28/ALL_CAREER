export function isWalkinJob(job: any): boolean {
  if (!job) return false;
  const src = String(job.source || '').toLowerCase();
  if (src === 'google_images' || src.includes('google') || src.includes('flyer')) return true;

  const title = String(job.title || job.role || '');
  const desc = String(job.description || job.other_details || '');
  const walkKwRegex = /\b(walk[\s-]?in|walking[\s-]?interview|walkin|walk-in drive|direct interview)\b/i;

  if (walkKwRegex.test(title) || walkKwRegex.test(desc)) {
    return true;
  }
  if (job.is_walkin === true && (walkKwRegex.test(title) || walkKwRegex.test(desc) || src === 'google_images' || src.includes('google'))) {
    return true;
  }
  return false;
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
