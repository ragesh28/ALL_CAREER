<div align="center">

📡 ALL_CAREER | Intelligent Job Aggregator

An automated, stealth-enabled ETL pipeline that extracts job market intelligence from top tech companies.

🔴 VIEW LIVE HUB

</div>

⚡️ The Concept

Most job boards are cluttered and slow. ALL_CAREER creates a private, noise-free feed of opportunities by directly tapping into the career portals of companies like Zoho, HCL, and Amazon. It runs on a 24-hour autonomous cycle, ensuring the data is always synchronized with the source.

🧬 Core Architecture

This project is not just a scraper; it's a self-maintaining data ecosystem running entirely on GitHub infrastructure.

graph TD
    subgraph "00:00 UTC Trigger"
    A[⏰ Cron Scheduler] --> B(GitHub Action Runner)
    end
    
    subgraph "Extraction Layer"
    B --> C{Stealth Scraper Bot}
    C -->|Bypasses Bot Detection| D[Target: HCLTech]
    C -->|Direct Extraction| E[Target: Zoho]
    C -->|API Intercept| F[Target: Amazon]
    end
    
    subgraph "Data Processing"
    D & E & F --> G[Raw Data Collection]
    G --> H{Deduplication Engine}
    H -->|Filter Locations| I[Chennai / Bangalore Only]
    end
    
    subgraph "Storage & Cleanup"
    I --> J[(jobs.json)]
    J --> K{The Janitor Script}
    K -->|Delete records > 30 days| L[Clean Database]
    L --> M[Update Web UI]
    end


🛡️ Engineering Features

1. 👻 Stealth Mode Extraction

Standard scrapers get blocked immediately by firewalls (WAF). This engine uses puppeteer-extra-plugin-stealth to mimic human behavior:

Fingerprint Masking: Hides the fact that it is a robot.

Dynamic Viewports: Changes screen size to look like a real laptop.

Smart Waiting: Uses "Cool Down" timers to handle skeleton loaders (crucial for Accenture/HCL).

2. 🧠 Intelligent Filtering

The system doesn't just grab everything. It applies logic during the fetch:

Location Locking: Discards jobs not in specific tech hubs.

Duplicate Guard: Checks URLs against the existing database to prevent double entries.

Fallback Logic: If a specific job link is hidden behind JavaScript (like TCS), it intelligently falls back to the main portal link.

3. 🧹 "The Janitor" (Auto-Maintenance)

A database that only grows will eventually become useless.

The Problem: Old jobs expire but stay in the JSON file.

The Solution: A dedicated clean_jobs.js script runs after every fetch. It parses dates and performs a "Hard Delete" on any record older than 30 days.

📦 Installation & Setup

If you want to run this engine on your local machine for development:

1. Clone the repository

git clone [https://github.com/ragesh28/ALL_CAREER.git](https://github.com/ragesh28/ALL_CAREER.git)
cd ALL_CAREER


2. Install dependencies

npm install


3. Configure Secrets (Important)
Create a file named companies.json in the root folder. Note: This file is git-ignored for security.

[
  {
    "name": "Zoho",
    "url": "[https://www.zoho.com/careers/](https://www.zoho.com/careers/)",
    "itemSelector": ".job-item",
    "titleSelector": "h3",
    "linkSelector": "a",
    "isItemLink": false
  }
]


4. Ignite the Engine

npm start