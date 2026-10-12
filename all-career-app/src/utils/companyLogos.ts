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
  "Boeing": "boeing.com", "Airbus": "airbus.com", "SpaceX": "spacex.com",

  // --- BIG COMPANY NAME LIST & CHENNAI/PAN-INDIA HUBS ---
  "TCS (Prime/Digital)": "tcs.com",
  "Infosys (SP/DSE)": "infosys.com",
  "Samsung R&D": "samsung.com",
  "KLA Tencor": "kla.com", "KLA": "kla.com",
  "Rocketlane": "rocketlane.com",
  "Mad Street Den": "madstreetden.com",
  "Uniphore": "uniphore.com",
  "Yubi": "go-yubi.com", "CredAvenue": "go-yubi.com",
  "Kissflow": "kissflow.com",
  "Walmart Global Tech": "walmart.com",
  "LatentView Analytics": "latentview.com", "LatentView": "latentview.com",
  "Tiger Analytics": "tigeranalytics.com",
  "Renault Nissan": "renaultgroup.com", "Renault": "renault.com", "Nissan": "nissan-global.com",
  "Ford Motors": "ford.com", "Ford Motor Company": "ford.com",
  "Verizon": "verizon.com",
  "Comcast": "corporate.comcast.com", "Comcast Corporation": "corporate.comcast.com",
  "Fireflies.ai": "fireflies.ai", "Fireflies": "fireflies.ai",
  "Automattic": "automattic.com",
  "Turing": "turing.com",
  "LTIMindtree Service": "ltimindtree.com",
  "Virtusa": "virtusa.com",
  "Mr. Cooper": "mrcoopergroup.com", "Mr Cooper": "mrcoopergroup.com",
  "Caterpillar": "caterpillar.com",
  "Athenahealth": "athenahealth.com",
  "Temenos": "temenos.com",
  "Kaar Tech": "kaartech.com", "Kaar Technologies": "kaartech.com",
  "Ramco Systems": "ramco.com", "Ramco": "ramco.com",
  "Intellect Design": "intellectdesign.com", "Intellect Design Arena": "intellectdesign.com",
  "Sify Tech": "sifytechnologies.com", "Sify": "sifytechnologies.com",
  "Tata Elxsi": "tataelxsi.com",
  "InMobi / Glance": "inmobi.com",
  "Zeta Suite": "zeta.tech", "Zeta": "zeta.tech",

  // --- TOP 35 HIGH VOLUME PORTAL RECRUITERS ---
  "EY": "ey.com", "Ernst & Young": "ey.com", "EY GDS": "ey.com",
  "Purview Services": "purviewservices.com", "Purview": "purviewservices.com",
  "Deloitte": "deloitte.com", "Deloitte India": "deloitte.com",
  "JLL": "jll.com", "Jones Lang LaSalle": "jll.com", "Jones Lang LaSalle (JLL)": "jll.com",
  "Bajaj Finserv": "bajajfinserv.in", "Bajaj finserv": "bajajfinserv.in", "Bajaj Finance": "bajajfinserv.in",
  "Hindco": "hindco.com", "Hindco Recruitment Consultants": "hindco.com",
  "UST": "ust.com", "UST Global": "ust.com",
  "JPMorganChase": "jpmorgan.com", "J.P. Morgan": "jpmorgan.com",
  "Tekskills": "tekskillsinc.com", "Tekskills Inc": "tekskillsinc.com",
  "Wenger & Watson": "wengerwatson.com", "Wenger and Watson": "wengerwatson.com",
  "Birlasoft": "birlasoft.com",
  "Credicus Business Services": "credicus.in", "Credicus": "credicus.in",
  "Takecare Manpower Services": "takecaremanpower.com", "Takecare": "takecaremanpower.com",
  "Cloudxtreme": "cloudxtreme.com",
  "Reliance Jio": "jio.com", "Jio": "jio.com", "Reliance Jio Infocomm Ltd.": "jio.com",
  "Citibank": "citi.com",
  "Wells Fargo India": "wellsfargo.com",
  "Starworth Global Solutions": "starworthglobal.com", "Starworth Global Soluitons": "starworthglobal.com",
  "Outpace Consulting Services": "outpace.in", "Outpace": "outpace.in",
  "CGI": "cgi.com", "CGI Group": "cgi.com",
  "Genpact": "genpact.com", "Genpact India": "genpact.com",
  "Yash Technologies": "yash.com", "Yash Tech": "yash.com"
};

export const LOCAL_COMPANY_LOGOS: Record<string, string> = {
  // Comcast
  "comcast": "/logos/companies/comcast.svg",
  "comcast corporation": "/logos/companies/comcast.svg",

  // 1. EY (Ernst & Young)
  "ey": "/logos/companies/ey.svg",
  "ey gds": "/logos/companies/ey.svg",
  "ey india": "/logos/companies/ey.svg",
  "ernst & young": "/logos/companies/ey.svg",
  "ernst and young": "/logos/companies/ey.svg",

  // 2. Tata Consultancy Services (TCS)
  "tcs": "/logos/companies/tcs.svg",
  "tcs digital": "/logos/companies/tcs.svg",
  "tcs ninja": "/logos/companies/tcs.svg",
  "tcs prime": "/logos/companies/tcs.svg",
  "tata consultancy services": "/logos/companies/tcs.svg",
  "tata consultancy services ltd": "/logos/companies/tcs.svg",
  "tata consultancy services limited": "/logos/companies/tcs.svg",

  // 3. Accenture
  "accenture": "/logos/companies/accenture.svg",
  "accenture in india": "/logos/companies/accenture.svg",
  "accenture solutions": "/logos/companies/accenture.svg",
  "accenture solutions pvt ltd": "/logos/companies/accenture.svg",

  // 4. HCLTech (HCL Technologies)
  "hcl": "/logos/companies/hcltech.svg",
  "hcltech": "/logos/companies/hcltech.svg",
  "hcl technologies": "/logos/companies/hcltech.svg",
  "hcl technologies ltd": "/logos/companies/hcltech.svg",
  "hcl technologies limited": "/logos/companies/hcltech.svg",

  // 5. Cognizant
  "cognizant": "/logos/companies/cognizant.svg",
  "cognizant technology solutions": "/logos/companies/cognizant.svg",
  "cognizant technology solutions india": "/logos/companies/cognizant.svg",
  "cts": "/logos/companies/cognizant.svg",

  // 6. Amazon
  "amazon": "/logos/companies/amazon.svg",
  "amazon.com": "/logos/companies/amazon.svg",
  "amazon web services": "/logos/companies/amazon.svg",
  "aws": "/logos/companies/amazon.svg",
  "amazon dev center": "/logos/companies/amazon.svg",
  "amazon development centre": "/logos/companies/amazon.svg",
  "amazon development centre india": "/logos/companies/amazon.svg",

  // 7. Infosys
  "infosys": "/logos/companies/infosys.svg",
  "infosys limited": "/logos/companies/infosys.svg",
  "infosys ltd": "/logos/companies/infosys.svg",
  "infosys bpm": "/logos/companies/infosys.svg",
  "infosys technologies": "/logos/companies/infosys.svg",

  // 8. Purview Services (Official site logo)
  "purview services": "/logos/companies/purview.png",
  "purview": "/logos/companies/purview.png",
  "purview it": "/logos/companies/purview.png",

  // 9. Deloitte
  "deloitte": "/logos/companies/deloitte.svg",
  "deloitte india": "/logos/companies/deloitte.svg",
  "deloitte usi": "/logos/companies/deloitte.svg",
  "deloitte consulting": "/logos/companies/deloitte.svg",

  // 10. PwC (PricewaterhouseCoopers)
  "pwc": "/logos/companies/pwc.svg",
  "pwc india": "/logos/companies/pwc.svg",
  "pricewaterhousecoopers": "/logos/companies/pwc.svg",
  "pricewaterhousecoopers private limited": "/logos/companies/pwc.svg",

  // 11. JLL (Jones Lang LaSalle)
  "jll": "/logos/companies/jll.svg",
  "jones lang lasalle": "/logos/companies/jll.svg",
  "jones lang lasalle (jll)": "/logos/companies/jll.svg",
  "jll india": "/logos/companies/jll.svg",

  // 12. Capgemini
  "capgemini": "/logos/companies/capgemini.svg",
  "capgemini technology services": "/logos/companies/capgemini.svg",
  "capgemini technology services india": "/logos/companies/capgemini.svg",
  "capgemini india": "/logos/companies/capgemini.svg",

  // 13. Bajaj Finserv
  "bajaj finserv": "/logos/companies/bajajfinserv.svg",
  "bajaj finance": "/logos/companies/bajajfinserv.svg",
  "bajaj finance limited": "/logos/companies/bajajfinserv.svg",

  // 14. Wipro
  "wipro": "/logos/companies/wipro.svg",
  "wipro limited": "/logos/companies/wipro.svg",
  "wipro ltd": "/logos/companies/wipro.svg",
  "wipro technologies": "/logos/companies/wipro.svg",

  // 15. Hindco Recruitment Consultants (Official site logo)
  "hindco": "/logos/companies/hindco.jpg",
  "hindco recruitment consultants": "/logos/companies/hindco.jpg",
  "hindco consulting": "/logos/companies/hindco.jpg",

  // 16. UST (UST Global)
  "ust": "/logos/companies/ust.svg",
  "ust global": "/logos/companies/ust.svg",
  "ust global inc": "/logos/companies/ust.svg",

  // 17. JPMorgan Chase
  "jpmorgan": "/logos/companies/jpmorgan.svg",
  "jpmorgan chase": "/logos/companies/jpmorgan.svg",
  "jpmorganchase": "/logos/companies/jpmorgan.svg",
  "jp morgan": "/logos/companies/jpmorgan.svg",
  "chase": "/logos/companies/jpmorgan.svg",

  // 18. Tekskills (Official site logo)
  "tekskills": "/logos/companies/tekskills.png",
  "tekskills inc": "/logos/companies/tekskills.png",

  // 19. Wenger & Watson (Official site logo)
  "wenger & watson": "/logos/companies/wengerwatson.png",
  "wenger and watson": "/logos/companies/wengerwatson.png",

  // 20. Birlasoft
  "birlasoft": "/logos/companies/birlasoft.svg",
  "birlasoft limited": "/logos/companies/birlasoft.svg",
  "birlasoft ltd": "/logos/companies/birlasoft.svg",

  // 21. Credicus Business Services (Official brand icon)
  "credicus": "/logos/companies/credicus.png",
  "credicus business services": "/logos/companies/credicus.png",

  // 22. Takecare Manpower Services (Official site logo)
  "takecare": "/logos/companies/takecare.jpg",
  "takecare manpower services": "/logos/companies/takecare.jpg",

  // 23. Cloudxtreme (Official site logo)
  "cloudxtreme": "/logos/companies/cloudxtreme.png",
  "cloudxtreme solutions": "/logos/companies/cloudxtreme.png",

  // 24. Virtusa
  "virtusa": "/logos/companies/virtusa.svg",
  "virtusa consulting services": "/logos/companies/virtusa.svg",

  // 25. Reliance Jio
  "jio": "/logos/companies/jio.svg",
  "reliance jio": "/logos/companies/jio.svg",
  "reliance jio infocomm": "/logos/companies/jio.svg",
  "reliance jio infocomm ltd.": "/logos/companies/jio.svg",
  "reliance jio infocomm ltd": "/logos/companies/jio.svg",

  // 26. Citi
  "citi": "/logos/companies/citi.svg",
  "citigroup": "/logos/companies/citi.svg",
  "citibank": "/logos/companies/citi.svg",

  // 27. Google
  "google": "/logos/companies/google.svg",
  "alphabet": "/logos/companies/google.svg",

  // 28. Wells Fargo
  "wells fargo": "/logos/companies/wellsfargo.svg",
  "wells fargo india": "/logos/companies/wellsfargo.svg",

  // 29. Starworth Global Solutions -> Falls back dynamically to elegant monogram badge (No official web logo registered)

  // 30. Outpace Consulting Services (Official brand icon)
  "outpace": "/logos/companies/outpace.png",
  "outpace consulting services": "/logos/companies/outpace.png",

  // 31. CGI
  "cgi": "/logos/companies/cgi.svg",
  "cgi group": "/logos/companies/cgi.svg",
  "cgi information systems": "/logos/companies/cgi.svg",

  // 32. Genpact
  "genpact": "/logos/companies/genpact.svg",
  "genpact india": "/logos/companies/genpact.svg",

  // 33. Tech Mahindra
  "tech mahindra": "/logos/companies/techmahindra.svg",
  "tech mahindra limited": "/logos/companies/techmahindra.svg",
  "techm": "/logos/companies/techmahindra.svg",

  // 34. IBM
  "ibm": "/logos/companies/ibm.svg",
  "ibm india": "/logos/companies/ibm.svg",

  // 35. Yash Technologies
  "yash": "/logos/companies/yash.svg",
  "yash technologies": "/logos/companies/yash.svg",
  "yash tech": "/logos/companies/yash.svg"
};

export interface LogoData {
  local?: string;
  unavatar: string;
  duckduckgo: string;
  google: string;
  clearbit: string;
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

const COMPANY_LOGO_MEMO_CACHE = new Map<string, LogoData>();

export function getCompanyLogo(name: string): LogoData {
  const rawKey = String(name || 'DIRECT RECRUITER').trim();
  if (COMPANY_LOGO_MEMO_CACHE.has(rawKey)) {
    return COMPANY_LOGO_MEMO_CACHE.get(rawKey)!;
  }

  const clean = rawKey.replace(/\(.*\)/, '').replace(/\b(inc|corp|corporation|llc|pvt|ltd|limited|india)\b/gi, '').trim();
  
  // 1. Direct match in DOMAIN_MAP
  let domain = DOMAIN_MAP[rawKey] || DOMAIN_MAP[clean];

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

  // 2b. Word boundary matching (e.g. "TCS Prime" -> "TCS", "Samsung R&D" -> "Samsung", "Ford Motors" -> "Ford")
  if (!domain) {
    const low = clean.toLowerCase();
    for (const [k, v] of Object.entries(DOMAIN_MAP)) {
      const kLow = k.toLowerCase();
      if (kLow.length >= 3) {
        const regex = new RegExp(`(^|\\b)${kLow.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')}(\\b|$)`, 'i');
        if (regex.test(low)) {
          domain = v;
          break;
        }
      }
    }
  }

  // 3. Fallback sanitized domain
  if (!domain) {
    const slug = clean.toLowerCase().replace(/\s+/g, '').replace(/[^\w]/g, '');
    domain = slug ? `${slug}.com` : 'direct.com';
  }

  const rawLower = rawKey.toLowerCase().trim();
  const cleanLower = clean.toLowerCase().trim();

  let localLogo = LOCAL_COMPANY_LOGOS[rawLower] || LOCAL_COMPANY_LOGOS[cleanLower];
  if (!localLogo) {
    for (const [k, v] of Object.entries(LOCAL_COMPANY_LOGOS)) {
      if (k.length >= 3 && (rawLower.includes(k) || cleanLower.includes(k))) {
        localLogo = v;
        break;
      }
    }
  }

  const result: LogoData = {
    local: localLogo,
    unavatar: localLogo || `https://unavatar.io/${domain}`,
    duckduckgo: localLogo || `https://icons.duckduckgo.com/ip3/${domain}.ico`,
    google: localLogo || `https://www.google.com/s2/favicons?domain=${domain}&sz=128`,
    clearbit: localLogo || `https://logo.clearbit.com/${domain}`,
    initial: (clean.charAt(0) || 'C').toUpperCase(),
    domain
  };

  COMPANY_LOGO_MEMO_CACHE.set(rawKey, result);
  return result;
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
