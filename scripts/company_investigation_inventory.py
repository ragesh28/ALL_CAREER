"""Build a resumable employer inventory from the actual scraper configurations."""
import json
import re
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit, parse_qsl, urlencode

from scripts.audit_big_companies import companies

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {
    "Google": "https://www.google.com/about/careers/applications/jobs/results/?location=India",
    "Microsoft": "https://apply.careers.microsoft.com/careers?location=India",
    "Amazon": "https://www.amazon.jobs/en/search?country=IND",
    "Apple": "https://jobs.apple.com/en-in/search?location=india-INDC",
    "Meta": "https://www.metacareers.com/jobs/",
    "Netflix": "https://explore.jobs.netflix.net/careers",
    "Adobe": "https://careers.adobe.com/us/en/search-results?keywords=India",
    "Salesforce": "https://careers.salesforce.com/en/jobs/",
    "Oracle": "https://careers.oracle.com/jobs/",
    "SAP": "https://jobs.sap.com/search/?q=India",
    "IBM": "https://www.ibm.com/careers/search?field_keyword_05[0]=India",
    "Intel": "https://jobs.intel.com/en/search-jobs/India",
    "Cisco": "https://careers.cisco.com/global/en/search-results?keywords=India",
    "Qualcomm": "https://careers.qualcomm.com/careers?location=India",
    "NVIDIA": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
    "Samsung": "https://sec.wd3.myworkdayjobs.com/Samsung_Careers",
    "Sony": "https://www.sonyjobs.com/",
    "Dell": "https://jobs.dell.com/en/search-jobs/India",
    "HP": "https://apply.hp.com/careers?location=India",
    "Lenovo": "https://jobs.lenovo.com/en_US/careers/SearchJobs/India",
    "Accenture": "https://www.accenture.com/in-en/careers/jobsearch",
    "TCS": "https://ibegin.tcsapps.com/candidate/jobs/search",
    "Infosys": "https://career.infosys.com/joblist",
    "Wipro": "https://careers.wipro.com/en-US/search",
    "HCLTech": "https://www.hcltech.com/careers/careers-in-india",
    "Cognizant": "https://careers.cognizant.com/india-en/jobs/",
    "Capgemini": "https://careers.capgemini.com/",
    "LTIMindtree": "https://ltimindtree.ripplehire.com/candidate/",
    "Tech Mahindra": "https://careers.techmahindra.com/",
    "Persistent Systems": "https://careers.persistent.com/",
    "Flipkart": "https://www.flipkartcareers.com/",
    "Swiggy": "https://careers.swiggy.com/",
    "Zomato": "https://www.zomato.com/careers",
    "Paytm": "https://jobs.lever.co/paytm",
    "PhonePe": "https://www.phonepe.com/careers/",
    "Razorpay": "https://razorpay.com/jobs/",
    "CRED": "https://jobs.lever.co/cred",
    "Meesho": "https://www.meesho.io/jobs",
    "Zerodha": "https://zerodha.com/careers/",
    "Groww": "https://groww.in/careers",
    "Uber": "https://www.uber.com/global/en/careers/list/",
    "Ola": "https://www.olacabs.com/careers",
    "Myntra": "https://careers.myntra.com/",
    "Nykaa": "https://www.nykaa.com/careers",
    "BigBasket": "https://careers.bigbasket.com/",
    "JPMorgan Chase": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs",
    "Goldman Sachs": "https://higher.gs.com/results?COUNTRY=India",
    "Morgan Stanley": "https://www.morganstanley.com/careers/career-opportunities-search",
    "Bank of America": "https://careers.bankofamerica.com/en-us/job-search",
    "Citi": "https://jobs.citi.com/search-jobs/India",
    "Wells Fargo": "https://www.wellsfargojobs.com/en/jobs/",
    "Barclays": "https://search.jobs.barclays/search-jobs/India",
    "HSBC": "https://mycareer.hsbc.com/en_GB/external/SearchJobs",
    "Deutsche Bank": "https://careers.db.com/professionals/search-roles/",
    "Standard Chartered": "https://jobs.standardchartered.com/",
    "Deloitte": "https://southasiacareers.deloitte.com/",
    "PwC": "https://jobs.in.pwc.com/",
    "EY": "https://careers.ey.com/ey/search/?q=India",
    "KPMG": "https://kpmg.com/in/en/home/careers.html",
    "McKinsey": "https://www.mckinsey.com/careers/search-jobs",
    "Boston Consulting Group": "https://careers.bcg.com/global/en/search-results?keywords=India",
    "Bain & Company": "https://www.bain.com/careers/find-a-role/",
    "Mu Sigma": "https://www.mu-sigma.com/careers/",
    "Fractal Analytics": "https://fractal.wd1.myworkdayjobs.com/Fractalcareers",
    "Tiger Analytics": "https://www.tigeranalytics.com/careers/",
    "Walmart": "https://careers.walmart.com/technology",
    "Target": "https://corporate.target.com/careers/job-search",
    "Visa": "https://corporate.visa.com/en/careers.html",
    "Mastercard": "https://careers.mastercard.com/us/en/search-results?keywords=India",
    "American Express": "https://aexp.eightfold.ai/careers?location=India",
    "PayPal": "https://paypal.eightfold.ai/careers?location=India",
    "Stripe": "https://stripe.com/jobs/search?office_locations=Asia+Pacific--Bengaluru",
    "Intuit": "https://jobs.intuit.com/search-jobs/India",
    "ServiceNow": "https://careers.servicenow.com/jobs/",
    "Workday": "https://workday.wd5.myworkdayjobs.com/Workday",
    "Snowflake": "https://careers.snowflake.com/us/en/search-results?keywords=India",
    "Databricks": "https://www.databricks.com/company/careers/open-positions",
    "Cloudera": "https://cloudera.wd5.myworkdayjobs.com/External_Career",
    "Confluent": "https://careers.confluent.io/",
    "MongoDB": "https://www.mongodb.com/company/careers/teams",
    "Atlassian": "https://www.atlassian.com/company/careers/all-jobs",
    "Freshworks": "https://careers.smartrecruiters.com/Freshworks",
    "Zoho": "https://www.zoho.com/careers/",
    "Postman": "https://www.postman.com/company/careers/open-positions/",
    "BrowserStack": "https://www.browserstack.com/careers",
    "Thoughtworks": "https://www.thoughtworks.com/careers/jobs",
    "Hasura": "https://hasura.io/careers/",
    "Chargebee": "https://www.chargebee.com/careers/",
    "InMobi": "https://www.inmobi.com/company/careers",
    "Honeywell": "https://careers.honeywell.com/us/en/search-results?keywords=India",
    "Bosch": "https://jobs.bosch.com/",
    "Siemens": "https://jobs.siemens.com/en_US/externaljobs/SearchJobs/?21178=%5B%226006%22%5D",
    "ABB": "https://careers.abb/global/en/search-results?keywords=India",
    "Schneider Electric": "https://careers.se.com/jobs?location=India",
    "GE": "https://careers.gevernova.com/global/en/search-results?keywords=India",
    "Philips": "https://www.careers.philips.com/global/en/search-results?keywords=India",
    "3M": "https://3m.wd1.myworkdayjobs.com/Search",
    "Johnson Controls": "https://jobs.johnsoncontrols.com/",
    "Emerson": "https://www.emerson.com/en-us/careers",
    "Mercedes Benz": "https://jobs.mercedes-benz.com/en/",
    "BMW": "https://www.bmwgroup.jobs/en.html",
    "Volkswagen": "https://www.volkswagen-group.com/en/careers-15757",
    "Toyota": "https://www.toyotabharat.com/careers/",
    "Ford": "https://efds.fa.em5.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs",
    "Continental": "https://jobs.continental.com/en/",
    "Caterpillar": "https://careers.caterpillar.com/en/jobs/",
    "John Deere": "https://jobs.deere.com/search/?q=India",
    "Cummins": "https://cummins.jobs/ind/jobs/",
    "Eaton": "https://jobs.eaton.com/",
    "Shell": "https://shell.wd3.myworkdayjobs.com/ShellCareers",
    "Schlumberger": "https://careers.slb.com/",
    "Baker Hughes": "https://careers.bakerhughes.com/global/en/search-results?keywords=India",
    "Halliburton": "https://jobs.halliburton.com/search/?q=India",
    "TotalEnergies": "https://careers.totalenergies.com/en_US/careers/SearchJobs",
    "Ericsson": "https://jobs.ericsson.com/careers?location=India",
    "Nokia": "https://careers.nokia.com/",
    "Juniper Networks": "https://careers.hpe.com/us/en/search-results?keywords=Juniper",
    "Broadcom": "https://broadcom.wd1.myworkdayjobs.com/External_Career",
    "Marvell": "https://marvell.wd1.myworkdayjobs.com/MarvellCareers",
    "Nutanix": "https://nutanix.eightfold.ai/careers?location=India",
    "Rubrik": "https://www.rubrik.com/company/careers",
    "Cohesity": "https://careers.cohesity.com/",
    "VMware": "https://broadcom.wd1.myworkdayjobs.com/External_Career",
    "Palo Alto Networks": "https://jobs.paloaltonetworks.com/en/jobs/",
    "CrowdStrike": "https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers",
    "Fortinet": "https://www.fortinet.com/corporate/careers",
    "Zscaler": "https://www.zscaler.com/careers",
    "Splunk": "https://www.splunk.com/en_us/careers/search-jobs.html",
    "Elastic": "https://www.elastic.co/careers/jobs",
    "Twilio": "https://www.twilio.com/en-us/company/jobs",
    "Datadog": "https://careers.datadoghq.com/all-jobs/",
    "New Relic": "https://newrelic.com/careers",
    "PagerDuty": "https://careers.pagerduty.com/jobs/",
    "Okta": "https://www.okta.com/company/careers/",
    "UiPath": "https://careers.uipath.com/careers/jobs",
    "Automation Anywhere": "https://www.automationanywhere.com/company/careers",
    "Blue Prism": "https://www.blueprism.com/company/careers/",
    "Celonis": "https://www.celonis.com/careers/jobs/",
    "Appian": "https://careers.appian.com/",
    "Epic Games": "https://www.epicgames.com/site/en-US/careers/jobs",
    "Unity": "https://unity.com/careers/positions",
    "EA Sports": "https://jobs.ea.com/en_US/careers",
    "Riot Games": "https://www.riotgames.com/en/work-with-us/jobs",
    "Ubisoft": "https://www.ubisoft.com/en-us/company/careers/search",
    "Spotify": "https://www.lifeatspotify.com/jobs",
    "Twitter": "https://careers.x.com/",
    "LinkedIn": "https://careers.linkedin.com/",
    "Pinterest": "https://www.pinterestcareers.com/en/jobs/",
    "Snap": "https://careers.snap.com/jobs",
    "Rocketlane": "https://careers.kula.ai/rocketlane",
    "Turing": "https://www.turing.com/careers",
    "Virtusa": "https://www.virtusa.com/careers/job-search",
    "Hexaware": "https://fa-etqo-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs",
    "Athenahealth": "https://careers.athenahealth.com/",
    "Ramco Systems": "https://www.ramco.com/careers",
    "Intellect Design": "https://www.intellectdesign.com/careers/",
    "Sify Tech": "https://www.sifytechnologies.com/careers/",
    "Tata Elxsi": "https://www.tataelxsi.com/careers",
    "Zeta Suite": "https://jobs.lever.co/zeta",
    "Cure.fit": "https://careers.cult.fit/",
    "Amadeus": "https://amadeus.wd502.myworkdayjobs.com/jobs",
    "GE Healthcare": "https://careers.gehealthcare.com/global/en/search-results?keywords=India",
    "Maersk": "https://www.maersk.com/careers/vacancies",
    "Arcesium": "https://www.arcesium.com/careers",
    "Juniper Networks / HPE": "https://careers.hpe.com/us/en/search-results?keywords=India",
    "Fidelity Investments": "https://jobs.fidelity.com/",
    "BNY": "https://www.bny.com/corporate/global/en/careers.html",
    "Akamai": "https://www.akamai.com/careers",
    "Publicis Sapient": "https://careers.publicissapient.com/",
    "ZS Associates": "https://jobs.zs.com/",
    "KPIT Technologies": "https://www.kpit.com/careers/",
    "Grundfos": "https://jobs.grundfos.com/",
    "Tally Solutions": "https://tallysolutions.com/careers/",
    "Subex": "https://www.subex.com/careers/",
    "Brillio": "https://www.brillio.com/careers/",
    "Eurofins IT": "https://careers.eurofins.com/",
    "Sabre": "https://sabre.wd1.myworkdayjobs.com/SabreJobs",
    "Alstom": "https://jobsearch.alstom.com/search/?q=India",
    "Danfoss": "https://jobs.danfoss.com/",
    "HackerRank": "https://www.hackerrank.com/careers/",
    "Crossover": "https://www.crossover.com/jobs",
    "Sarvam AI": "https://www.sarvam.ai/careers",
    "Anthropic": "https://www.anthropic.com/careers",
    "Societe Generale": "https://careers.societegenerale.com/en/job-offers",
    "NatWest Group": "https://jobs.natwestgroup.com/",
    "ITC Infotech": "https://jobs.itcinfotech.com/itcinfotech/",
    "OpenAI": "https://openai.com/careers/search/",
}
ALIASES = {"TCS (Prime/Digital)": "TCS", "Infosys (SP/DSE)": "Infosys", "Walmart Global Tech": "Walmart", "SAP Labs": "SAP", "Citibank": "Citi", "Amazon AI": "Amazon"}


def public_url(url):
    url = str(url or "").replace("https.://", "https://")
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if not re.search(r"token|key|secret|auth|password", k, re.I)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def build():
    employers = {}
    for engine in ("direct", "md", "indeed"):
        previous_path = next((ROOT / ".git" / ("github-audit" if engine == "indeed" else "github-final-" + engine)).rglob(engine + ".json"), None)
        previous = {r["company"]: r for r in json.loads(previous_path.read_text(encoding="utf-8"))} if previous_path else {}
        for index, config in enumerate(companies(engine)):
            original = config["company"]
            name = ALIASES.get(original, original)
            item = employers.setdefault(name, {"id": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"), "company": name, "career_url": DIRECTORIES.get(name, ""), "sources": [], "candidate_urls": [], "state": "pending", "attempts": []})
            urls = config.get("urls") or [config.get("url", "")]
            if engine == "indeed":
                urls = ["https://in.indeed.com/jobs?q=" + quote(original) + "&l=India"]
            item["sources"].append({"engine": engine, "index": index, "company_label": original, "source_url": public_url(urls[0]), "previous_status": previous.get(original, {}).get("status", "unavailable"), "previous_description": previous.get(original, {}).get("description_after", False)})
            for url in urls:
                url = public_url(url)
                if url and url not in item["candidate_urls"]:
                    item["candidate_urls"].append(url)
    result = list(employers.values())
    for item in result:
        item["candidate_urls"] = list(dict.fromkeys([item["career_url"]] + item["candidate_urls"]))
    return result


if __name__ == "__main__":
    path = ROOT / "docs/audits/company-investigation-monitor.json"
    rows = build()
    path.write_text(json.dumps({"started": "2026-11-23", "companies": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(rows)} employers / {sum(len(r['sources']) for r in rows)} source entries")
