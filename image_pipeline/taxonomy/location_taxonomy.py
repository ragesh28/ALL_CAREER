"""
Hierarchical Indian Location Taxonomy.
Maps 50+ major Indian cities, states, districts, IT corridors, industrial zones,
and employment hubs to canonical location entities.
"""
import re
from typing import Dict, List, Optional


# ── 50 Major Indian Job Hubs & Cities ──
LOCATION_DATABASE: List[Dict] = [
    # ── Top 10 Major Tech & Commercial Metros (Tier 1) ──
    {
        "canonical": "Chennai",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "aliases": ["chennai", "madras", "maa", "tambaram", "guindy", "omr", "sholinganallur", "siruseri", "ambattur", "maraimalainagar", "maraimalai nagar", "porur", "perungudi", "taramani", "navalur", "thoraipakkam", "velachery", "mount road", "anna nagar", "t nagar", "sipcot", "meenambakkam", "pallavaram", "chromepet", "avadi", "sriperumbudur", "oragadam", "redhills", "tidel park"],
        "localities": ["omr", "old mahabalipuram road", "guindy", "perungudi", "taramani", "sholinganallur", "siruseri", "ambattur", "sriperumbudur", "maraimalai nagar", "porur", "navalur", "thoraipakkam", "velachery", "mount road", "anna nagar", "nungambakkam", "adyar", "t nagar", "sipcot", "meenambakkam", "pallavaram", "tidel park", "dlf it park", "olympia tech park", "rmz millenia", "ramanujan it city", "ascendas", "one india bulls park", "thousand lights", "greams road"]
    },
    {
        "canonical": "Bengaluru",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "aliases": ["bengaluru", "bangalore", "blr", "whitefield", "electronic city", "manyata", "marathahalli", "koramangala", "bellandur", "hsr layout", "sarjapur", "hebbal", "peenya", "mahadevapura", "outer ring road", "indiranagar", "jayanagar", "yelahanka", "bommasandra"],
        "localities": ["whitefield", "electronic city", "manyata", "manyata tech park", "marathahalli", "koramangala", "bellandur", "hsr layout", "sarjapur", "sarjapur road", "hebbal", "peenya", "domlur", "indiranagar", "mahadevapura", "outer ring road", "orr", "bagmane tech park", "ecospace", "rmz ecoworld", "rmz infinity", "prestige tech park", "embassy tech village", "cessna business park", "itpb", "international tech park", "jayanagar", "bannerghatta road", "rajajinagar", "yelahanka", "bommasandra"]
    },
    {
        "canonical": "Hyderabad",
        "state": "Telangana",
        "district": "Hyderabad",
        "aliases": ["hyderabad", "secunderabad", "hyd", "telangana", "medchal", "medchal-malkajgiri", "shamirpet", "cyberabad", "hitec city", "hiteccity", "madhapur", "gachibowli", "kondapur", "financial district", "kukatpally", "begumpet", "uppal", "ameerpet", "patancheru", "jeedimetla"],
        "localities": ["hitec city", "hiteccity", "madhapur", "gachibowli", "kondapur", "financial district", "jubilee hills", "banjara hills", "kukatpally", "begumpet", "uppal", "pocharam", "nanakramguda", "raidurg", "mindspace", "cyber towers", "cyber gateway", "dlf cybercity", "divyasree orion", "mindspace it park", "somajiguda", "ameerpet", "shamirpet", "biotech park", "medchal", "medchal-malkajgiri", "lalgadi malakpet", "patancheru", "jeedimetla", "nacharam", "kothur", "cherlapally", "miyapur", "bachupally", "kphb", "sanathnagar", "balanagar", "moula ali", "tarnaka", "habsiguda"]
    },
    {
        "canonical": "Pune",
        "state": "Maharashtra",
        "district": "Pune",
        "aliases": ["pune", "poona", "pnq", "hinjewadi", "hinjawadi", "magarpatta", "kharadi", "vimannagar", "viman nagar", "baner", "hadapsar", "chakan", "bhosari", "pimprichinchwad", "pimpri", "chinchwad", "wakad"],
        "localities": ["hinjewadi", "hinjawadi", "hinjewadi phase 1", "hinjewadi phase 2", "hinjewadi phase 3", "magarpatta", "magarpatta city", "kharadi", "eon free zone", "eon it park", "viman nagar", "baner", "hadapsar", "senapati bapat road", "sb road", "aundh", "kothrud", "wakad", "bhosari", "chakan", "pimpri", "chinchwad", "talawade", "yerwada", "commerzone"]
    },
    {
        "canonical": "Mumbai",
        "state": "Maharashtra",
        "district": "Mumbai City",
        "aliases": ["mumbai", "bombay", "bom", "bkc", "andheri", "powai", "airoli", "navimumbai", "navi mumbai", "thane", "goregaon", "lower parel", "malad", "vikhroli", "worli"],
        "localities": ["bkc", "bandra kurla complex", "andheri", "andheri east", "andheri west", "powai", "airoli", "navi mumbai", "thane", "goregaon", "lower parel", "malad", "mindspace malad", "kandivali", "vikhroli", "worli", "dadar", "kurla", "ghatkopar", "borivali", "belapur", "vashi", "mahape", "millennium business park", "nerul", "ghansoli"]
    },
    {
        "canonical": "Delhi",
        "state": "Delhi",
        "district": "New Delhi",
        "aliases": ["delhi", "new delhi", "del", "ncr", "connaught place", "nehru place", "okhla", "saket", "dwarka", "rohini", "pitampura", "janakpuri", "laxmi nagar", "karol bagh"],
        "localities": ["okhla", "okhla industrial area", "okhla phase 1", "okhla phase 2", "okhla phase 3", "nehru place", "connaught place", "cp", "saket", "jasola", "bhikaji cama place", "barakhamba", "netaji subhash place", "nsp", "dwarka", "aerocity", "patparganj", "mayapuri"]
    },
    {
        "canonical": "Noida",
        "state": "Uttar Pradesh",
        "district": "Gautam Buddha Nagar",
        "aliases": ["noida", "greater noida", "noida extension", "sector 62 noida", "sector 125 noida", "sector 132 noida", "sector 135 noida", "sector 142 noida", "sector 18 noida"],
        "localities": ["sector 62", "sector 63", "sector 18", "sector 16", "sector 125", "sector 126", "sector 127", "sector 132", "sector 135", "sector 142", "sector 144", "greater noida", "knowledge park", "advant navis", "expressway noida"]
    },
    {
        "canonical": "Gurgaon",
        "state": "Haryana",
        "district": "Gurugram",
        "aliases": ["gurgaon", "gurugram", "cyber city", "cybercity", "dlf cyber city", "sohna road", "golf course road", "udyog vihar", "manesar", "mg road gurgaon"],
        "localities": ["cyber city", "dlf cyber city", "dlf phase 1", "dlf phase 2", "dlf phase 3", "dlf phase 4", "dlf phase 5", "golf course road", "golf course extension", "sohna road", "udyog vihar", "udyog vihar phase 1", "udyog vihar phase 4", "udyog vihar phase 5", "manesar", "imt manesar", "mg road", "sector 29", "sector 44", "sector 48", "cyber hub"]
    },
    {
        "canonical": "Kolkata",
        "state": "West Bengal",
        "district": "Kolkata",
        "aliases": ["kolkata", "calcutta", "ccu", "salt lake", "saltlake", "sector v", "sector 5", "new town", "rajarhat", "ecospace kolkata"],
        "localities": ["salt lake", "saltlake", "salt lake sector 5", "sector v", "new town", "rajarhat", "action area 1", "action area 2", "ecospace", "dlf it park kolkata", "bengal intelligent park", "unitech infospace kolkata", "park street", "camac street", "ballygunge", "alipore", "howrah"]
    },
    {
        "canonical": "Ahmedabad",
        "state": "Gujarat",
        "district": "Ahmedabad",
        "aliases": ["ahmedabad", "amdavad", "ahd", "sg highway", "sanand", "prahlad nagar", "bodakdev", "satellite ahmedabad", "gandhinagar", "gift city"],
        "localities": ["sg highway", "sarkhej gandhinagar highway", "prahlad nagar", "bodakdev", "satellite", "vastrapur", "navrangpura", "ashram road", "sanand", "changodar", "gift city", "gandhinagar", "infocity gandhinagar"]
    },

    # ── Next 40 Important Cities & Employment Hubs (Tier 2 & 3) ──
    {"canonical": "Coimbatore", "state": "Tamil Nadu", "district": "Coimbatore", "aliases": ["coimbatore", "kovai", "cbe", "saravanampatti", "peelamedu", "gandhipuram", "tidel park coimbatore", "eachanari", "sidco"]},
    {"canonical": "Madurai", "state": "Tamil Nadu", "district": "Madurai", "aliases": ["madurai", "mdu", "elcot it park madurai", "vadapalanji", "mattuthavani"]},
    {"canonical": "Tiruchirappalli", "state": "Tamil Nadu", "district": "Tiruchirappalli", "aliases": ["trichy", "tiruchirappalli", "thuvakudi", "bhel trichy"]},
    {"canonical": "Salem", "state": "Tamil Nadu", "district": "Salem", "aliases": ["salem", "steel plant salem", "suramangalam"]},
    {"canonical": "Tirunelveli", "state": "Tamil Nadu", "district": "Tirunelveli", "aliases": ["tirunelveli", "nellai", "gangaikondan"]},
    {"canonical": "Erode", "state": "Tamil Nadu", "district": "Erode", "aliases": ["erode", "perundurai", "sipcot erode"]},
    {"canonical": "Vellore", "state": "Tamil Nadu", "district": "Vellore", "aliases": ["vellore", "katpadi", "ranipet"]},
    {"canonical": "Kochi", "state": "Kerala", "district": "Ernakulam", "aliases": ["kochi", "cochin", "ernakulam", "infopark", "smartcity kochi", "kakkanad", "kaloor"]},
    {"canonical": "Thiruvananthapuram", "state": "Kerala", "district": "Thiruvananthapuram", "aliases": ["trivandrum", "thiruvananthapuram", "technopark", "kazhakoottam"]},
    {"canonical": "Kozhikode", "state": "Kerala", "district": "Kozhikode", "aliases": ["kozhikode", "calicut", "cyberpark calicut"]},
    {"canonical": "Visakhapatnam", "state": "Andhra Pradesh", "district": "Visakhapatnam", "aliases": ["visakhapatnam", "vizag", "rushikonda", "gajuwaka", "autonagar vizag"]},
    {"canonical": "Vijayawada", "state": "Andhra Pradesh", "district": "NTR", "aliases": ["vijayawada", "gannavaram", "amaravati", "benz circle", "autonagar vijayawada"]},
    {"canonical": "Guntur", "state": "Andhra Pradesh", "district": "Guntur", "aliases": ["guntur", "mangalagiri"]},
    {"canonical": "Tirupati", "state": "Andhra Pradesh", "district": "Tirupati", "aliases": ["tirupati", "sri city", "renigunta"]},
    {"canonical": "Mysuru", "state": "Karnataka", "district": "Mysuru", "aliases": ["mysuru", "mysore", "hebbal mysore", "infosys mysore"]},
    {"canonical": "Hubballi", "state": "Karnataka", "district": "Dharwad", "aliases": ["hubli", "hubballi", "dharwad", "aryabhata tech park"]},
    {"canonical": "Mangaluru", "state": "Karnataka", "district": "Dakshina Kannada", "aliases": ["mangalore", "mangaluru", "surathkal", "kavoor"]},
    {"canonical": "Belagavi", "state": "Karnataka", "district": "Belagavi", "aliases": ["belgaum", "belagavi", "udyambag"]},
    {"canonical": "Jaipur", "state": "Rajasthan", "district": "Jaipur", "aliases": ["jaipur", "sitapura", "malviya nagar jaipur", "mansarovar jaipur", "mahindra world city jaipur"]},
    {"canonical": "Jodhpur", "state": "Rajasthan", "district": "Jodhpur", "aliases": ["jodhpur", "boranada"]},
    {"canonical": "Udaipur", "state": "Rajasthan", "district": "Udaipur", "aliases": ["udaipur", "sukher"]},
    {"canonical": "Indore", "state": "Madhya Pradesh", "district": "Indore", "aliases": ["indore", "crystal it park", "super corridor indore", "vijay nagar indore", "pithampur"]},
    {"canonical": "Bhopal", "state": "Madhya Pradesh", "district": "Bhopal", "aliases": ["bhopal", "mandideep", "govindpura"]},
    {"canonical": "Gwalior", "state": "Madhya Pradesh", "district": "Gwalior", "aliases": ["gwalior", "malanpur"]},
    {"canonical": "Chandigarh", "state": "Chandigarh", "district": "Chandigarh", "aliases": ["chandigarh", "mohali", "panchkula", "tricity", "it park chandigarh", "sector 82 mohali"]},
    {"canonical": "Ludhiana", "state": "Punjab", "district": "Ludhiana", "aliases": ["ludhiana", "focal point ludhiana"]},
    {"canonical": "Amritsar", "state": "Punjab", "district": "Amritsar", "aliases": ["amritsar"]},
    {"canonical": "Lucknow", "state": "Uttar Pradesh", "district": "Lucknow", "aliases": ["lucknow", "gomti nagar", "hcl it city lucknow", "hazratganj", "chinhat"]},
    {"canonical": "Kanpur", "state": "Uttar Pradesh", "district": "Kanpur", "aliases": ["kanpur", "panki", "fazalganj"]},
    {"canonical": "Varanasi", "state": "Uttar Pradesh", "district": "Varanasi", "aliases": ["varanasi", "kashi", "banaras"]},
    {"canonical": "Agra", "state": "Uttar Pradesh", "district": "Agra", "aliases": ["agra", "sikandra"]},
    {"canonical": "Prayagraj", "state": "Uttar Pradesh", "district": "Prayagraj", "aliases": ["allahabad", "prayagraj", "naini"]},
    {"canonical": "Patna", "state": "Bihar", "district": "Patna", "aliases": ["patna", "patliputra industrial area", "danapur"]},
    {"canonical": "Bhubaneswar", "state": "Odisha", "district": "Khordha", "aliases": ["bhubaneswar", "bhubaneshwar", "infocity bhubaneswar", "patia", "chandaka"]},
    {"canonical": "Cuttack", "state": "Odisha", "district": "Cuttack", "aliases": ["cuttack", "choudwar"]},
    {"canonical": "Nagpur", "state": "Maharashtra", "district": "Nagpur", "aliases": ["nagpur", "mihan", "mihan sez", "butibori", "hingna"]},
    {"canonical": "Nashik", "state": "Maharashtra", "district": "Nashik", "aliases": ["nashik", "nasik", "satpur", "ambad"]},
    {"canonical": "Aurangabad", "state": "Maharashtra", "district": "Chhatrapati Sambhajinagar", "aliases": ["aurangabad", "chhatrapati sambhajinagar", "waluj", "chikalthana", "shendra"]},
    {"canonical": "Surat", "state": "Gujarat", "district": "Surat", "aliases": ["surat", "hazira", "pandesara", "sachin gidc"]},
    {"canonical": "Vadodara", "state": "Gujarat", "district": "Vadodara", "aliases": ["vadodara", "baroda", "makarpura", "savli", "nandesari"]},
    {"canonical": "Rajkot", "state": "Gujarat", "district": "Rajkot", "aliases": ["rajkot", "shapar", "metoda"]},
    {"canonical": "Ranchi", "state": "Jharkhand", "district": "Ranchi", "aliases": ["ranchi", "namkum", "tupudana"]},
    {"canonical": "Jamshedpur", "state": "Jharkhand", "district": "East Singhbhum", "aliases": ["jamshedpur", "tatanagar", "adityapur"]},
    {"canonical": "Raipur", "state": "Chhattisgarh", "district": "Raipur", "aliases": ["raipur", "urla", "bhilai"]},
    {"canonical": "Dehradun", "state": "Uttarakhand", "district": "Dehradun", "aliases": ["dehradun", "it park dehradun", "selaqui", "pantnagar"]},
    {"canonical": "Guwahati", "state": "Assam", "district": "Kamrup", "aliases": ["guwahati", "tech city assam", "borjhar", "dispur"]}
]


class LocationTaxonomyResolver:
    """Resolves raw text or locality names to canonical Indian cities/states."""

    @classmethod
    def resolve_location(cls, text: str) -> Optional[Dict]:
        """
        Scan text for matching canonical city, aliases, or locality names.
        Returns: {city, state, district, locality, confidence}
        """
        if not text:
            return None

        # Clean punctuation to separate glued words e.g. "Bengaluru-560048" -> "bengaluru 560048"
        low = " " + re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower()) + " "

        # 1. Check direct city / alias match with word boundaries
        for loc in LOCATION_DATABASE:
            for alias in loc["aliases"]:
                if re.search(r'\b' + re.escape(alias) + r'\b', low):
                    return {
                        "city": loc["canonical"],
                        "state": loc["state"],
                        "district": loc["district"],
                        "locality": None,
                        "confidence": 0.95
                    }

        # 2. Check employment locality match (e.g. "OMR" -> Chennai, "Hitec City" -> Hyderabad)
        for loc in LOCATION_DATABASE:
            for locality in loc.get("localities", []):
                if re.search(r'\b' + re.escape(locality) + r'\b', low):
                    return {
                        "city": loc["canonical"],
                        "state": loc["state"],
                        "district": loc["district"],
                        "locality": locality.title(),
                        "confidence": 0.90
                    }

        return None
