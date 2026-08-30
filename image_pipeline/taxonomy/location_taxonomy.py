"""
Hierarchical Indian Location Taxonomy.
Maps cities, states, districts, IT corridors, industrial zones, and airport codes
to canonical Indian location entities.
"""
from typing import Dict, List, Optional, Tuple


LOCATION_DATABASE: List[Dict] = [
    # ── Tamil Nadu ──
    {
        "canonical": "Chennai",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "aliases": ["chennai", "madras", "maa"],
        "localities": [
            "omr", "old mahabalipuram road", "guindy", "perungudi", "taramani",
            "sholinganallur", "siruseri", "ambattur", "sriperumbudur", "maraimalai nagar",
            "porur", "navalur", "thoraipakkam", "velachery", "mount road", "anna nagar",
            "nungambakkam", "adyar", "t nagar", "sipcot", "meenambakkam", "pallavaram",
            "tidel park", "dlf it park", "olympia tech park", "rmz millenia", "ramanujan it city",
            "ascendas", "one india bulls park"
        ]
    },
    {
        "canonical": "Coimbatore",
        "state": "Tamil Nadu",
        "district": "Coimbatore",
        "aliases": ["coimbatore", "kovai", "cbe"],
        "localities": ["saravanampatti", "peelamedu", "gandhipuram", "tidco", "tidel park coimbatore", "eachanari", "kurichi", "sidco"]
    },
    {
        "canonical": "Madurai",
        "state": "Tamil Nadu",
        "district": "Madurai",
        "aliases": ["madurai", "mdu"],
        "localities": ["elcot it park", "vadapalanji", "mattuthavani", "kk nagar"]
    },
    {
        "canonical": "Tiruchirappalli",
        "state": "Tamil Nadu",
        "district": "Tiruchirappalli",
        "aliases": ["trichy", "tiruchirappalli"],
        "localities": ["elcot", "navalpur", "thuvakudi", "bhel"]
    },

    # ── Karnataka ──
    {
        "canonical": "Bengaluru",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "aliases": ["bengaluru", "bangalore", "blr"],
        "localities": [
            "whitefield", "electronic city", "manyata", "manyata tech park", "marathahalli",
            "koramangala", "bellandur", "hsr layout", "sarjapur", "sarjapur road", "hebbal",
            "peenya", "domlur", "indiranagar", "mahadevapura", "outer ring road", "orr",
            "bagmane tech park", "ecospace", "rmz ecoworld", "rmz infinity", "prestige tech park",
            "embassy tech village", "cessna business park", "itpb", "international tech park",
            "jayanagar", "bannerghatta road", "rajajinagar", "yelahanka", "bommasandra"
        ]
    },
    {
        "canonical": "Mysuru",
        "state": "Karnataka",
        "district": "Mysuru",
        "aliases": ["mysuru", "mysore"],
        "localities": ["hebbal industrial area", "elcot", "infosys campus", "hunsur road"]
    },

    # ── Telangana & Andhra Pradesh ──
    {
        "canonical": "Hyderabad",
        "state": "Telangana",
        "district": "Hyderabad",
        "aliases": ["hyderabad", "secunderabad", "hyd"],
        "localities": [
            "hitec city", "hiteccity", "madhapur", "gachibowli", "kondapur",
            "financial district", "jubilee hills", "banjara hills", "kukatpally",
            "begumpet", "uppal", "pocharam", "nanakramguda", "raidurg", "mindspace",
            "cyber towers", "cyber gateway", "dlf cybercity", "divyasree orion",
            "mindspace it park", "somajiguda", "ameerpet"
        ]
    },
    {
        "canonical": "Visakhapatnam",
        "state": "Andhra Pradesh",
        "district": "Visakhapatnam",
        "aliases": ["visakhapatnam", "vizag"],
        "localities": ["rushikonda", "gambheeram", "gajuwaka", "autonagar"]
    },

    # ── Maharashtra ──
    {
        "canonical": "Mumbai",
        "state": "Maharashtra",
        "district": "Mumbai City",
        "aliases": ["mumbai", "bombay", "bom"],
        "localities": [
            "bkc", "bandra kurla complex", "andheri", "andheri east", "andheri west",
            "powai", "airoli", "navi mumbai", "thane", "goregaon", "lower parel",
            "malad", "vashi", "ghansoli", "rabale", "worli", "nariman point",
            "mindspace malad", "nesco", "nirlon knowledge park", "kalyan"
        ]
    },
    {
        "canonical": "Pune",
        "state": "Maharashtra",
        "district": "Pune",
        "aliases": ["pune", "pnq"],
        "localities": [
            "hinjewadi", "hinjawadi", "magarpatta", "viman nagar", "kharadi",
            "baner", "wakad", "hadapsar", "chakan", "bhosari", "pimpri", "chinchwad",
            "pimpri chinchwad", "eon it park", "quadron business park", "senapati bapat road",
            "yerawada", "commerzone", "kalyani nagar", "tathawade"
        ]
    },

    # ── Delhi NCR ──
    {
        "canonical": "Delhi",
        "state": "Delhi",
        "district": "New Delhi",
        "aliases": ["delhi", "new delhi", "del"],
        "localities": ["connaught place", "cp", "okhla", "nehru place", "jasola", "saket", "dwarka", "janakpuri", "barakhamba"]
    },
    {
        "canonical": "Noida",
        "state": "Uttar Pradesh",
        "district": "Gautam Buddha Nagar",
        "aliases": ["noida", "greater noida"],
        "localities": [
            "sector 62", "sector 125", "sector 135", "sector 142", "sector 16", "sector 18",
            "sector 63", "expressway", "noida expressway", "knowledge park", "pari chowk"
        ]
    },
    {
        "canonical": "Gurgaon",
        "state": "Haryana",
        "district": "Gurugram",
        "aliases": ["gurgaon", "gurugram", "ggn"],
        "localities": [
            "cyber city", "dlf cyber city", "golf course road", "golf course extension",
            "udyog vihar", "sohna road", "sector 29", "sector 44", "sector 48", "manesar",
            "dlf phase 2", "dlf phase 3", "unitech cyber park", "cyber hub"
        ]
    },

    # ── West Bengal, Gujarat, Kerala, Others ──
    {
        "canonical": "Kolkata",
        "state": "West Bengal",
        "district": "Kolkata",
        "aliases": ["kolkata", "calcutta", "ccu"],
        "localities": ["salt lake", "sector v", "sector 5", "new town", "rajarhat", "ecospace kolkata", "park street"]
    },
    {
        "canonical": "Ahmedabad",
        "state": "Gujarat",
        "district": "Ahmedabad",
        "aliases": ["ahmedabad", "amd"],
        "localities": ["gift city", "sg highway", "prahlad nagar", "sanand", "makarba", "bodakdev", "satellite"]
    },
    {
        "canonical": "Kochi",
        "state": "Kerala",
        "district": "Ernakulam",
        "aliases": ["kochi", "cochin", "ernakulam", "cok"],
        "localities": ["infopark", "kakkanad", "kalamassery", "smartcity", "mg road kochi", "edappally"]
    },
    {
        "canonical": "Thiruvananthapuram",
        "state": "Kerala",
        "district": "Thiruvananthapuram",
        "aliases": ["thiruvananthapuram", "trivandrum", "trv"],
        "localities": ["technopark", "kazhakkoottam", "technocity"]
    },
    {
        "canonical": "Jaipur",
        "state": "Rajasthan",
        "district": "Jaipur",
        "aliases": ["jaipur", "jai"],
        "localities": ["sitapura", "malviya nagar", "mansarovar", "vaishali nagar", "mahindra world city jaipur"]
    },
    {
        "canonical": "Chandigarh",
        "state": "Chandigarh",
        "district": "Chandigarh",
        "aliases": ["chandigarh", "mohali", "panchkula", "ixc"],
        "localities": ["it park chandigarh", "sector 82 mohali", "industrial area phase 8"]
    },
    {
        "canonical": "Indore",
        "state": "Madhya Pradesh",
        "district": "Indore",
        "aliases": ["indore", "idr"],
        "localities": ["crystal it park", "super corridor", "vijay nagar", "pithampur"]
    },
    {
        "canonical": "Bhubaneswar",
        "state": "Odisha",
        "district": "Khordha",
        "aliases": ["bhubaneswar", "bhubaneshwar", "bbi"],
        "localities": ["infocity", "chandaka", "patia", "mancheswar"]
    }
]


class LocationTaxonomyResolver:
    """Resolves raw text or locality names to canonical Indian cities/states."""

    @classmethod
    def resolve_location(cls, text: str) -> Optional[Dict]:
        """
        Scan text for matching canonical city, aliases, or locality names.
        Returns: {city, state, district, locality, venue, confidence}
        """
        if not text:
            return None

        low = " " + text.lower() + " "

        # 1. Check direct city / alias match
        for loc in LOCATION_DATABASE:
            for alias in loc["aliases"]:
                if f" {alias} " in low or f"\n{alias}\n" in low or f"\n{alias} " in low or f" {alias}\n" in low or f"({alias})" in low or f"at {alias}" in low or f"in {alias}" in low:
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
                if f" {locality} " in low or f"\n{locality}\n" in low or f"\n{locality} " in low or f" {locality}\n" in low:
                    return {
                        "city": loc["canonical"],
                        "state": loc["state"],
                        "district": loc["district"],
                        "locality": locality.title(),
                        "confidence": 0.90
                    }

        return None
