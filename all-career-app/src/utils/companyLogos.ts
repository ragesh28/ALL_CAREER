/**
 * Company Domain & Logo Resolution Utility
 * 
 * Provides fallback logo resolution across Clearbit, Google S2 Favicon,
 * DuckDuckGo, and uppercase letter fallback.
 */

export const COMPANY_DOMAIN_MAP: Record<string, string> = {
  'tcs': 'tcs.com',
  'tata consultancy services': 'tcs.com',
  'infosys': 'infosys.com',
  'wipro': 'wipro.com',
  'hcl': 'hcltech.com',
  'hcl technologies': 'hcltech.com',
  'cognizant': 'cognizant.com',
  'accenture': 'accenture.com',
  'capgemini': 'capgemini.com',
  'tech mahindra': 'techmahindra.com',
  'ltimindtree': 'ltimindtree.com',
  'mphasis': 'mphasis.com',
  'hexaware': 'hexaware.com',
  'amazon': 'amazon.com',
  'google': 'google.com',
  'microsoft': 'microsoft.com',
  'apple': 'apple.com',
  'meta': 'meta.com',
  'netflix': 'netflix.com',
  'flipkart': 'flipkart.com',
  'swiggy': 'swiggy.com',
  'zomato': 'zomato.com',
  'paytm': 'paytm.com',
  'phonepe': 'phonepe.com',
  'razorpay': 'razorpay.com',
  'cred': 'cred.club',
  'uber': 'uber.com',
  'deloitte': 'deloitte.com',
  'ey': 'ey.com',
  'kpmg': 'kpmg.com',
  'pwc': 'pwc.com',
  'jpmorgan': 'jpmorgan.com',
  'goldman sachs': 'goldmansachs.com',
  'morgan stanley': 'morganstanley.com',
  'zoho': 'zoho.com',
  'freshworks': 'freshworks.com',
  'salesforce': 'salesforce.com',
  'oracle': 'oracle.com',
  'ibm': 'ibm.com',
  'intel': 'intel.com',
  'nvidia': 'nvidia.com',
  'amd': 'amd.com',
  'cisco': 'cisco.com',
  'qualcomm': 'qualcomm.com',
  'walmart': 'walmart.com',
  'naukri': 'naukri.com',
  'indeed': 'indeed.com',
  'linkedin': 'linkedin.com'
};

export interface LogoInfo {
  clearbit: string;
  google: string;
  ddg: string;
  initial: string;
}

export function getCompanyLogoData(name: string): LogoInfo {
  const clean = (name || '').replace(/\(.*\)/, '').trim();
  const key = clean.toLowerCase();
  const initial = (clean.charAt(0) || 'J').toUpperCase();

  let domain = COMPANY_DOMAIN_MAP[key];
  if (!domain) {
    const slug = key.replace(/[^a-z0-9]/g, '');
    domain = `${slug || 'company'}.com`;
  }

  return {
    clearbit: `https://logo.clearbit.com/${domain}`,
    google: `https://www.google.com/s2/favicons?domain=${domain}&sz=128`,
    ddg: `https://icons.duckduckgo.com/ip3/${domain}.ico`,
    initial
  };
}
