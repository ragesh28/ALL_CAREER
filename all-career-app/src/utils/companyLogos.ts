// companyLogos.ts - Comprehensive Domain Map & Multi-tier Logo Fallback (Clearbit -> Google Favicon -> DuckDuckGo -> Monogram)

export const DOMAIN_MAP: Record<string, string> = {
  // --- FAANG / BIG TECH ---
  "Google": "google.com", "Microsoft": "microsoft.com", "Amazon": "amazon.com",
  "Apple": "apple.com", "Netflix": "netflix.com", "Meta": "meta.com",
  "Facebook": "meta.com", "Adobe": "adobe.com", "Salesforce": "salesforce.com",
  "Oracle": "oracle.com", "Cisco": "cisco.com", "IBM": "ibm.com",
  "Intel": "intel.com", "Nvidia": "nvidia.com", "Samsung": "samsung.com",
  "Samsung Electronics": "samsung.com", "Bloomberg": "bloomberg.com",
  "TikTok": "tiktok.com", "ByteDance": "bytedance.com",
  "Uber": "uber.com", "Lyft": "lyft.com", "Airbnb": "airbnb.com",
  "Twitter": "x.com", "X": "x.com", "LinkedIn": "linkedin.com",
  "Spotify": "spotify.com", "PayPal": "paypal.com", "Intuit": "intuit.com",
  "SAP": "sap.com", "VMware": "vmware.com", "Broadcom": "broadcom.com",
  "Qualcomm": "qualcomm.com", "ServiceNow": "servicenow.com", "Workday": "workday.com",
  "Atlassian": "atlassian.com", "Autodesk": "autodesk.com", "Dell": "dell.com",
  "HP": "hp.com", "AMD": "amd.com", "Texas Instruments": "ti.com",
  "Ericsson": "ericsson.com", "Cloudera": "cloudera.com", "Rubrik": "rubrik.com",
  "Baker Hughes": "bakerhughes.com", "NatWest Group": "natwestgroup.com",
  "PwC": "pwc.com", "Mercedes-Benz Group": "mercedes-benz.com", "Sony Music Global Job Board": "sonymusic.com",
  "Subex": "subex.com",
  "Palantir": "palantir.com", "Databricks": "databricks.com", "Snowflake": "snowflake.com",

  // --- INDIAN IT GIANTS (WITCH & TOP TIER) ---
  "TCS": "tcs.com", "Tata Consultancy Services": "tcs.com",
  "Infosys": "infosys.com", "Wipro": "wipro.com", "HCL": "hcltech.com", "HCLTech": "hcltech.com",
  "Tech Mahindra": "techmahindra.com", "LTIMindtree": "ltimindtree.com",
  "Cognizant": "cognizant.com", "Capgemini": "capgemini.com",
  "Accenture": "accenture.com", "Mindtree": "ltimindtree.com",
  "Persistent": "persistent.com", "Persistent Systems": "persistent.com",
  "Mphasis": "mphasis.com", "Hexaware": "hexaware.com", "KPIT": "kpit.com",
  "L&T": "ltts.com", "L&T Technology Services": "ltts.com",

  // --- INDIAN STARTUPS & UNICORNS ---
  "Flipkart": "flipkart.com", "Myntra": "myntra.com", "Meesho": "meesho.io",
  "Swiggy": "swiggy.com", "Zomato": "zomato.com", "Zepto": "zeptonow.com",
  "Blinkit": "blinkit.com", "BigBasket": "bigbasket.com", "Dunzo": "dunzo.com",
  "Ola": "olacabs.com", "Ola Electric": "olaelectric.com", "Rapido": "rapido.bike",
  "Uber India": "uber.com", "Cred": "cred.club", "Paytm": "paytm.com",
  "PhonePe": "phonepe.com", "Razorpay": "razorpay.com", "Groww": "groww.in",
  "Zerodha": "zerodha.com", "Upstox": "upstox.com", "BharatPe": "bharatpe.com",
  "Pine Labs": "pinelabs.com", "BillDesk": "billdesk.com", "PolicyBazaar": "policybazaar.com",
  "Digit Insurance": "godigit.com", "Acko": "acko.com", "Navi": "navi.com",
  "Lenskart": "lenskart.com", "Nykaa": "nykaa.com", "Mamaearth": "mamaearth.in",
  "Purplle": "purplle.com", "Urban Company": "urbancompany.com",
  "NoBroker": "nobroker.in", "MagicBricks": "magicbricks.com",
  "Housing.com": "housing.com", "ShareChat": "sharechat.com",
  "Dailyhunt": "dailyhunt.in", "InMobi": "inmobi.com", "Glance": "glance.com",
  "Dream11": "dream11.com", "MPL": "mpl.live", "Games24x7": "games24x7.com",
  "Nazara": "nazara.com", "PhysicsWallah": "pw.live", "Unacademy": "unacademy.com",
  "Byju's": "byjus.com", "Vedantu": "vedantu.com", "UpGrad": "upgrad.com",
  "Great Learning": "greatlearning.in", "Eruditus": "eruditus.com",
  "Simplilearn": "simplilearn.com", "Scaler": "scaler.com",
  "Oyo": "oyorooms.com", "MakeMyTrip": "makemytrip.com", "Goibibo": "goibibo.com",
  "Yatra": "yatra.com", "Cleartrip": "cleartrip.com", "EaseMyTrip": "easemytrip.com",
  "Ixigo": "ixigo.com", "RedBus": "redbus.in", "Udaan": "udaan.com",
  "Moglix": "moglix.com", "OfBusiness": "ofbusiness.com", "Zetwerk": "zetwerk.com",
  "Infra.Market": "infra.market", "Delhivery": "delhivery.com",
  "Xpressbees": "xpressbees.com", "Shadowfax": "shadowfax.in",
  "Rivigo": "rivigo.com", "BlackBuck": "blackbuck.com", "Porter": "porter.in",
  "Zoho": "zoho.com", "Freshworks": "freshworks.com", "Postman": "postman.com",
  "BrowserStack": "browserstack.com", "Hasura": "hasura.io",
  "Chargebee": "chargebee.com", "Druva": "druva.com", "Icertis": "icertis.com",
  "HighRadius": "highradius.com", "Zenoti": "zenoti.com", "Amagi": "amagi.com",
  "Gupshup": "gupshup.io", "CleverTap": "clevertap.com", "Whatfix": "whatfix.com",
  "MoEngage": "moengage.com", "WebEngage": "webengage.com", "LeadSquared": "leadsquared.com",

  // --- GLOBAL BANKS / FINTECH / QUANT ---
  "JPMorgan Chase": "jpmorganchase.com", "JPMorgan": "jpmorgan.com", "JP Morgan": "jpmorgan.com",
  "Goldman Sachs": "goldmansachs.com", "Morgan Stanley": "morganstanley.com",
  "Wells Fargo": "wellsfargo.com", "Bank of America": "bankofamerica.com",
  "Citi": "citi.com", "Citigroup": "citi.com", "American Express": "americanexpress.com",
  "Mastercard": "mastercard.com", "Visa": "visa.com", "Barclays": "barclays.com",
  "Deutsche Bank": "db.com", "UBS": "ubs.com", "Credit Suisse": "credit-suisse.com",
  "HSBC": "hsbc.com", "Standard Chartered": "sc.com", "NatWest": "natwestgroup.com",
  "BNY Mellon": "bnymellon.com", "BlackRock": "blackrock.com",
  "Two Sigma": "twosigma.com", "Jane Street": "janestreet.com",
  "Citadel": "citadel.com", "Hudson River Trading": "hudsonrivertrading.com",
  "Tower Research": "tower-research.com", "DE Shaw": "deshaw.com", "D. E. Shaw": "deshaw.com",
  "Arcesium": "arcesium.com", "WorldQuant": "worldquant.com",
  "Fidelity": "fidelity.com", "Capital One": "capitalone.com",
  "Stripe": "stripe.com", "Square": "squareup.com", "Block": "block.xyz",
  "Robinhood": "robinhood.com", "Coinbase": "coinbase.com", "Affirm": "affirm.com",
  "SoFi": "sofi.com", "Chime": "chime.com", "Revolut": "revolut.com", "Wise": "wise.com",
  "Monzo": "monzo.com", "Klarna": "klarna.com", "Adyen": "adyen.com",
  "Walmart": "walmart.com", "Walmart Labs": "walmart.com", "Target": "target.com",

  // --- AUTOMOTIVE / AEROSPACE / HARDWARE ---
  "Tesla": "tesla.com", "Siemens": "siemens.com", "Philips": "philips.com",
  "Honeywell": "honeywell.com", "Schneider Electric": "se.com", "ABB": "abb.com",
  "Bosch": "bosch.com", "Robert Bosch": "bosch.com", "BOSCH": "bosch.com",
  "General Electric": "ge.com", "GE": "ge.com", "Ford": "ford.com", "GM": "gm.com",
  "Mercedes-Benz": "mercedes-benz.com", "BMW": "bmw.com", "Audi": "audi.com",
  "Boeing": "boeing.com", "Airbus": "airbus.com", "SpaceX": "spacex.com"
};

export interface LogoData {
  clearbit: string;
  google: string;
  duckduckgo: string;
  initial: string;
  domain: string;
}

export const PORTAL_LOGOS_MAP: Record<string, string> = {
  naukri: '/logos/portals/naukri.png',
  linkedin: '/logos/portals/linkedin.png',
  indeed: '/logos/portals/indeed.png',
  internshala: '/logos/portals/internshala.png',
  glassdoor: '/logos/portals/glassdoor.ico',
  shine: '/logos/portals/shine.ico',
  timesjobs: '/logos/portals/timesjobs.svg',
  hirist: '/logos/portals/hirist.ico',
  workindia: '/logos/portals/workindia.png',
  foundit: '/logos/portals/foundit.png',
  apna: '/logos/portals/apna.png',
  freshersworld: '/logos/portals/freshersworld.ico',
  telegram: '/logos/portals/telegram.svg',
  telegram_message: '/logos/portals/telegram.svg',
  telegram_post: '/logos/portals/telegram.svg',
  google: '/logos/portals/google.svg',
  google_images: '/logos/portals/google.svg',
  images: '/logos/portals/google.svg',
  walkin: '/logos/portals/google.svg'
};

export interface PortalInfo {
  id: string;
  label: string;
  logo: string;
  url?: string;
}

export function getPortalLogo(source: string | undefined): string {
  if (!source) return '';
  const s = source.toLowerCase().trim();
  if (PORTAL_LOGOS_MAP[s]) return PORTAL_LOGOS_MAP[s];
  for (const [key, val] of Object.entries(PORTAL_LOGOS_MAP)) {
    if (s.includes(key)) return val;
  }
  return '';
}

export function detectPortalInfo(job: any): PortalInfo {
  if (!job) return { id: 'other', label: 'Direct Apply', logo: '' };

  const rawSrc = String(job.source || job.platform || '').toLowerCase().trim();
  const url = String(job.url || job.apply_link || job.apply_url || '');
  const tgUrl = String(job.telegram_url || (url.includes('t.me/') ? url : ''));
  const flyerUrl = String(job.flyer_image_url || job.raw_flyer_src || '');

  // 1. Google Images (Flyers & Google search images)
  if (rawSrc.includes('google') || rawSrc === 'images' || flyerUrl || url.includes('google.com') || url.includes('lh3.googleusercontent')) {
    return {
      id: 'google_images',
      label: 'Images',
      logo: '/logos/portals/google.svg',
      url: flyerUrl || (url.startsWith('http') ? url : undefined)
    };
  }

  // 2. Telegram Messages & Posts
  if (rawSrc.includes('telegram') || tgUrl || url.includes('t.me/')) {
    const isPost = rawSrc.includes('post');
    return {
      id: isPost ? 'telegram_post' : 'telegram_message',
      label: isPost ? 'Post' : 'Messages',
      logo: '/logos/portals/telegram.svg',
      url: tgUrl || (url.startsWith('http') ? url : undefined)
    };
  }

  // 3. Known portals mapping
  const knownLabels: Record<string, string> = {
    linkedin: 'LinkedIn',
    naukri: 'Naukri',
    indeed: 'Indeed',
    internshala: 'Internshala',
    glassdoor: 'Glassdoor',
    shine: 'Shine',
    timesjobs: 'TimesJobs',
    hirist: 'Hirist',
    workindia: 'WorkIndia',
    foundit: 'Foundit',
    apna: 'Apna',
    freshersworld: 'FreshersWorld'
  };

  for (const [k, lbl] of Object.entries(knownLabels)) {
    if (rawSrc === k || rawSrc.includes(k) || url.toLowerCase().includes(k)) {
      return {
        id: k,
        label: lbl,
        logo: PORTAL_LOGOS_MAP[k] || '',
        url: url.startsWith('http') ? url : undefined
      };
    }
  }

  if (rawSrc && rawSrc !== 'other' && rawSrc !== 'none') {
    return {
      id: rawSrc,
      label: rawSrc.charAt(0).toUpperCase() + rawSrc.slice(1).replace(/_/g, ' '),
      logo: getPortalLogo(rawSrc),
      url: url.startsWith('http') ? url : undefined
    };
  }

  return {
    id: 'other',
    label: 'Direct Apply',
    logo: '',
    url: url.startsWith('http') ? url : undefined
  };
}

export function getCompanyLogo(name: string): LogoData {
  const clean = (name || '').replace(/\(.*\)/, '').replace(/\b(inc|corp|corporation|llc|pvt|ltd|limited|india)\b/gi, '').trim();
  
  // 1. Direct match in DOMAIN_MAP
  let domain = DOMAIN_MAP[name] || DOMAIN_MAP[clean];

  // 2. Case-insensitive search in DOMAIN_MAP
  if (!domain) {
    const low = clean.toLowerCase();
    for (const [k, v] of Object.entries(DOMAIN_MAP)) {
      if (k.toLowerCase() === low) {
        domain = v;
        break;
      }
    }
  }

  // 3. Fallback sanitized domain
  if (!domain) {
    const slug = clean.toLowerCase().replace(/\s+/g, '').replace(/[^\w]/g, '');
    domain = slug ? `${slug}.com` : 'direct.com';
  }

  return {
    clearbit: `https://logo.clearbit.com/${domain}`,
    google: `https://www.google.com/s2/favicons?domain=${domain}&sz=128`,
    duckduckgo: `https://icons.duckduckgo.com/ip3/${domain}.ico`,
    initial: (clean.charAt(0) || 'C').toUpperCase(),
    domain
  };
}

export const getCompanyLogoData = getCompanyLogo;

export function formatAuthenticDate(dateStr?: string): string {
  if (!dateStr) return '';
  const clean = String(dateStr).replace(/[^a-zA-Z0-9\s-:,]/g, '').trim();
  if (!clean || clean.toLowerCase() === 'today') return 'Today';
  if (clean.toLowerCase() === 'yesterday') return 'Yesterday';

  const d = new Date(clean);
  if (isNaN(d.getTime())) return clean;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays > 1 && diffDays <= 7) return `${diffDays} days ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const MONTH_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function getMonthIdx(mStr: string): number {
  if (!mStr) return -1;
  const s = mStr.toLowerCase().slice(0, 3);
  return MONTH_SHORT.findIndex(m => m.toLowerCase() === s);
}

/** Walk-in dates strictly formatted as 3-letter month + day number (e.g. 'Sep 22', 'Oct 6'), never relative terms and never with year */
export function formatWalkinDate(dateStr?: string, fallbackStr?: string): string {
  const target = (dateStr || fallbackStr || '').trim();
  if (!target) return '';

  const clean = target.replace(/[^a-zA-Z0-9\s,/-]/g, ' ').trim();
  const low = clean.toLowerCase();

  // 1. Convert relative terms "Today" / "Tomorrow" / "Yesterday" to authentic date
  if (low.includes('today')) {
    const now = new Date();
    return `${MONTH_SHORT[now.getMonth()]} ${now.getDate()}`;
  }
  if (low.includes('tomorrow')) {
    const tom = new Date(Date.now() + 86400000);
    return `${MONTH_SHORT[tom.getMonth()]} ${tom.getDate()}`;
  }
  if (low.includes('yesterday')) {
    const yest = new Date(Date.now() - 86400000);
    return `${MONTH_SHORT[yest.getMonth()]} ${yest.getDate()}`;
  }

  // 2. Month-Day format: e.g. "Sep 22", "September 22", "Sep-22", "Sep 22, 2026"
  const mdMatch = clean.match(/\b([A-Za-z]{3,9})[\s,/-]+(\d{1,2})(?:st|nd|rd|th)?\b/i);
  if (mdMatch) {
    const mIdx = getMonthIdx(mdMatch[1]);
    if (mIdx !== -1) {
      return `${MONTH_SHORT[mIdx]} ${parseInt(mdMatch[2], 10)}`;
    }
  }

  // 3. Day-Month format: e.g. "22 Sep", "22nd September", "19-Sept-2026", "05th Sep"
  const dmMatch = clean.match(/\b(\d{1,2})(?:st|nd|rd|th)?[\s,/-]+([A-Za-z]{3,9})\b/i);
  if (dmMatch) {
    const mIdx = getMonthIdx(dmMatch[2]);
    if (mIdx !== -1) {
      return `${MONTH_SHORT[mIdx]} ${parseInt(dmMatch[1], 10)}`;
    }
  }

  // 4. ISO format: "2026-09-22" or "2026/09/22"
  const isoMatch = clean.match(/\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b/);
  if (isoMatch) {
    const m = parseInt(isoMatch[2], 10) - 1;
    if (m >= 0 && m <= 11) {
      return `${MONTH_SHORT[m]} ${parseInt(isoMatch[3], 10)}`;
    }
  }

  // 5. Day-Month-Year numeric: "22-09-2026" or "22/09/2026"
  const dmyMatch = clean.match(/\b(\d{1,2})[-/.](\d{1,2})[-/.](?:20\d{2}|\d{2})\b/);
  if (dmyMatch) {
    const m = parseInt(dmyMatch[2], 10) - 1;
    if (m >= 0 && m <= 11) {
      return `${MONTH_SHORT[m]} ${parseInt(dmyMatch[1], 10)}`;
    }
  }

  // 6. Check fallback string (e.g. rawDate or date_posted) if initial string was weekday like "Wednesday to Friday"
  if (fallbackStr && fallbackStr !== dateStr) {
    const fb = formatWalkinDate(fallbackStr);
    if (fb) return fb;
  }

  // 7. General date parse fallback (without year)
  const parsed = new Date(clean);
  if (!Number.isNaN(parsed.getTime())) {
    return `${MONTH_SHORT[parsed.getMonth()]} ${parsed.getDate()}`;
  }

  const now = new Date();
  return `${MONTH_SHORT[now.getMonth()]} ${now.getDate()}`;
}
