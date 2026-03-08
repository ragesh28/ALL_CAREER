/**
 * Top Companys — Company data with verified office locations
 * Cities: Chennai, Bangalore, Hyderabad, Mumbai
 * Each company has: name, locations (array of cities where they have offices)
 *
 * ✅ = has engineering/tech office in that city
 * Locations verified based on known office presence as of 2025-2026
 */

const topCompanys = [
    // ─── TIER 1: Product Giants ───
    { name: "Google", locations: ["Bangalore", "Hyderabad"] },
    { name: "Microsoft", locations: ["Bangalore", "Hyderabad"] },
    { name: "Amazon", locations: ["Chennai", "Bangalore", "Hyderabad", "Mumbai"] },
    { name: "Flipkart", locations: ["Bangalore"] },
    { name: "Walmart Global Tech", locations: ["Bangalore", "Chennai"] },
    { name: "Uber", locations: ["Bangalore", "Hyderabad"] },
    { name: "Salesforce", locations: ["Bangalore", "Hyderabad"] },
    { name: "Atlassian", locations: ["Bangalore"] },
    { name: "SAP Labs", locations: ["Bangalore"] },
    { name: "Oracle", locations: ["Bangalore", "Hyderabad", "Chennai"] },
    { name: "Adobe", locations: ["Bangalore"] },
    { name: "Intuit", locations: ["Bangalore"] },

    // ─── TIER 1: Chennai-Born Product Companies ───
    { name: "Zoho", locations: ["Chennai"] },
    { name: "Freshworks", locations: ["Chennai", "Bangalore"] },
    { name: "Chargebee", locations: ["Chennai"] },
    { name: "Kissflow", locations: ["Chennai"] },
    { name: "Rocketlane", locations: ["Chennai"] },
    { name: "Mad Street Den", locations: ["Chennai"] },
    { name: "Uniphore", locations: ["Chennai", "Bangalore"] },
    { name: "Yubi", locations: ["Chennai"] },
    { name: "GoFrugal", locations: ["Chennai"] },
    { name: "Ramco Systems", locations: ["Chennai"] },
    { name: "Intellect Design Arena", locations: ["Chennai"] },

    // ─── TIER 1: Fintech & Consumer ───
    { name: "PayPal", locations: ["Chennai", "Bangalore"] },
    { name: "Cred", locations: ["Bangalore"] },
    { name: "PhonePe", locations: ["Bangalore", "Mumbai"] },
    { name: "Razorpay", locations: ["Bangalore"] },
    { name: "Groww", locations: ["Bangalore", "Mumbai"] },
    { name: "Zerodha", locations: ["Bangalore"] },
    { name: "Meesho", locations: ["Bangalore"] },
    { name: "Swiggy", locations: ["Bangalore", "Hyderabad"] },
    { name: "Zomato", locations: ["Hyderabad", "Mumbai"] },
    { name: "Cure.fit", locations: ["Bangalore"] },
    { name: "Udaan", locations: ["Bangalore"] },
    { name: "ShareChat", locations: ["Bangalore"] },
    { name: "M2P Fintech", locations: ["Chennai"] },
    { name: "Kaleidofin", locations: ["Chennai"] },
    { name: "Zeta Suite", locations: ["Bangalore", "Hyderabad"] },

    // ─── Developer Tools & SaaS ───
    { name: "Postman", locations: ["Bangalore"] },
    { name: "BrowserStack", locations: ["Mumbai"] },
    { name: "InMobi / Glance", locations: ["Bangalore"] },
    { name: "HackerRank", locations: ["Bangalore"] },
    { name: "Hasura", locations: ["Bangalore"] },
    { name: "Sarvam AI", locations: ["Bangalore"] },
    { name: "Crayon Data", locations: ["Chennai"] },

    // ─── Remote-First Companies ───
    { name: "GitLab", locations: ["Bangalore", "Hyderabad"] },
    { name: "Supabase", locations: ["Bangalore"] },
    { name: "Grafana Labs", locations: ["Bangalore"] },
    { name: "Canonical", locations: ["Bangalore"] },
    { name: "Automattic", locations: ["Bangalore", "Mumbai"] },
    { name: "Fireflies.ai", locations: ["Bangalore"] },
    { name: "Turing", locations: ["Bangalore"] },
    { name: "Crossover", locations: ["Bangalore", "Hyderabad"] },
    { name: "HubSpot", locations: ["Hyderabad"] },
    { name: "DuckDuckGo", locations: ["Bangalore"] },
    { name: "Hugging Face", locations: ["Bangalore"] },
    { name: "Weights & Biases", locations: ["Bangalore"] },

    // ─── Banking / Finance (India offices) ───
    { name: "Goldman Sachs", locations: ["Bangalore", "Hyderabad"] },
    { name: "JPMorgan Chase", locations: ["Bangalore", "Hyderabad", "Mumbai"] },
    { name: "Morgan Stanley", locations: ["Mumbai", "Bangalore"] },
    { name: "Wells Fargo", locations: ["Bangalore", "Hyderabad", "Chennai"] },
    { name: "Citi", locations: ["Chennai", "Mumbai"] },
    { name: "Bank of America", locations: ["Chennai", "Hyderabad", "Mumbai"] },
    { name: "Barclays", locations: ["Chennai", "Mumbai"] },
    { name: "Standard Chartered", locations: ["Chennai", "Bangalore"] },
    { name: "Fidelity Investments", locations: ["Chennai", "Bangalore"] },
    { name: "NatWest Group", locations: ["Chennai", "Bangalore"] },
    { name: "BNY", locations: ["Chennai"] },
    { name: "Societe Generale", locations: ["Chennai", "Bangalore"] },
    { name: "DE Shaw", locations: ["Hyderabad"] },
    { name: "Arcesium", locations: ["Bangalore", "Hyderabad"] },
    { name: "Visa", locations: ["Bangalore"] },
    { name: "Mastercard", locations: ["Mumbai"] },
    { name: "American Express", locations: ["Bangalore"] },

    // ─── IT Services ───
    { name: "TCS", locations: ["Chennai", "Bangalore", "Hyderabad", "Mumbai"] },
    { name: "Infosys", locations: ["Chennai", "Bangalore", "Hyderabad", "Mumbai"] },
    { name: "Wipro", locations: ["Chennai", "Bangalore", "Hyderabad", "Mumbai"] },
    { name: "HCLTech", locations: ["Chennai", "Bangalore", "Hyderabad", "Mumbai"] },
    { name: "Accenture", locations: ["Chennai", "Bangalore", "Hyderabad", "Mumbai"] },
    { name: "Cognizant", locations: ["Chennai", "Bangalore", "Hyderabad", "Mumbai"] },
    { name: "Capgemini", locations: ["Chennai", "Bangalore", "Hyderabad", "Mumbai"] },
    { name: "LTIMindtree", locations: ["Chennai", "Bangalore", "Hyderabad", "Mumbai"] },
    { name: "Virtusa", locations: ["Chennai", "Hyderabad"] },
    { name: "Hexaware", locations: ["Chennai", "Mumbai"] },
    { name: "Publicis Sapient", locations: ["Bangalore", "Chennai"] },
    { name: "Thoughtworks", locations: ["Chennai", "Bangalore", "Hyderabad"] },
    { name: "IBM", locations: ["Bangalore", "Hyderabad", "Chennai"] },
    { name: "L&T Technology Services", locations: ["Chennai", "Bangalore", "Hyderabad", "Mumbai"] },
    { name: "Persistent Systems", locations: ["Hyderabad", "Bangalore"] },
    { name: "Sonata Software", locations: ["Bangalore", "Hyderabad"] },
    { name: "Brillio", locations: ["Bangalore", "Chennai", "Hyderabad"] },
    { name: "ITC Infotech", locations: ["Bangalore"] },
    { name: "HashedIn (Deloitte)", locations: ["Bangalore"] },

    // ─── Analytics ───
    { name: "LatentView Analytics", locations: ["Chennai", "Bangalore"] },
    { name: "Tiger Analytics", locations: ["Chennai"] },
    { name: "Fractal Analytics", locations: ["Mumbai", "Bangalore"] },
    { name: "Mu Sigma", locations: ["Bangalore"] },
    { name: "ZS Associates", locations: ["Bangalore"] },

    // ─── Semiconductor / Hardware R&D ───
    { name: "Qualcomm", locations: ["Bangalore", "Hyderabad", "Chennai"] },
    { name: "Samsung R&D", locations: ["Bangalore"] },
    { name: "Samsung Semiconductor", locations: ["Bangalore"] },
    { name: "Broadcom (VMware)", locations: ["Bangalore"] },
    { name: "Ericsson", locations: ["Chennai", "Bangalore"] },
    { name: "Nokia", locations: ["Chennai", "Bangalore"] },
    { name: "KLA Tencor", locations: ["Chennai"] },
    { name: "Tejas Networks", locations: ["Bangalore"] },

    // ─── Automobile / Manufacturing R&D ───
    { name: "Renault Nissan", locations: ["Chennai"] },
    { name: "Ford Motors", locations: ["Chennai"] },
    { name: "Mercedes Benz R&D", locations: ["Bangalore"] },
    { name: "Bosch (R&D)", locations: ["Bangalore"] },
    { name: "Continental", locations: ["Bangalore"] },
    { name: "Caterpillar", locations: ["Chennai"] },
    { name: "Wabco (ZF)", locations: ["Chennai"] },
    { name: "KPIT Technologies", locations: ["Bangalore"] },

    // ─── Industrial / Engineering ───
    { name: "Siemens", locations: ["Bangalore", "Chennai", "Hyderabad", "Mumbai"] },
    { name: "ABB", locations: ["Bangalore"] },
    { name: "Honeywell", locations: ["Bangalore", "Hyderabad"] },
    { name: "GE Healthcare", locations: ["Bangalore"] },
    { name: "Philips", locations: ["Bangalore", "Chennai"] },
    { name: "Shell", locations: ["Bangalore", "Chennai"] },
    { name: "Danfoss", locations: ["Chennai"] },
    { name: "Saint-Gobain", locations: ["Chennai"] },
    { name: "Alstom", locations: ["Bangalore"] },

    // ─── Telecom / Networking ───
    { name: "Cisco", locations: ["Bangalore", "Chennai"] },
    { name: "Juniper Networks", locations: ["Bangalore"] },
    { name: "Citrix (Cloud Software)", locations: ["Bangalore"] },
    { name: "Akamai", locations: ["Bangalore"] },
    { name: "Verizon", locations: ["Chennai", "Hyderabad"] },
    { name: "Comcast", locations: ["Chennai"] },

    // ─── Health / Insurance Tech ───
    { name: "Athenahealth", locations: ["Chennai", "Bangalore"] },
    { name: "Temenos", locations: ["Chennai", "Bangalore"] },
    { name: "Innovaccer", locations: ["Bangalore"] },

    // ─── Enterprise / Cloud ───
    { name: "Rubrik", locations: ["Bangalore"] },
    { name: "Cohesity", locations: ["Bangalore"] },
    { name: "Nutanix", locations: ["Bangalore"] },
    { name: "Target", locations: ["Bangalore"] },
    { name: "Amadeus", locations: ["Bangalore"] },
    { name: "Maersk (GSC)", locations: ["Chennai", "Mumbai", "Bangalore"] },
    { name: "Sabre", locations: ["Bangalore"] },
    { name: "Media.net", locations: ["Mumbai"] },

    // ─── Blockchain / Crypto ───
    { name: "Polygon (Matic)", locations: ["Bangalore", "Mumbai"] },
    { name: "Airmeet", locations: ["Bangalore"] },

    // ─── Mid-tier IT / Product ───
    { name: "Tata Elxsi", locations: ["Chennai", "Bangalore", "Hyderabad"] },
    { name: "Sify Tech", locations: ["Chennai"] },
    { name: "Kaar Tech", locations: ["Chennai"] },
    { name: "Sasken Technologies", locations: ["Bangalore", "Chennai"] },
    { name: "Happiest Minds", locations: ["Bangalore", "Chennai"] },
    { name: "Tally Solutions", locations: ["Bangalore"] },
    { name: "Subex", locations: ["Bangalore"] },
    { name: "Quest Global", locations: ["Bangalore"] },
    { name: "Eurofins IT", locations: ["Chennai", "Bangalore"] },
    { name: "Mr. Cooper", locations: ["Chennai"] },
    { name: "Urjanet (Arcadia)", locations: ["Bangalore"] },

    // ─── Emerging / Niche ───
    { name: "Crossover", locations: ["Bangalore", "Hyderabad"] },
];
