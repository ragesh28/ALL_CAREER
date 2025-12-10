<div align="center">

# 📡 ALL_CAREER — Intelligent Job Aggregator  

An automated, stealth-enabled ETL pipeline that extracts job market intelligence from top tech companies.

<br />

<a href="https://ragesh28.github.io/ALL_CAREER/" target="_blank">
<img src="https://img.shields.io/badge/🔴_VIEW_LIVE_HUB-Click_Here-red?style=for-the-badge" height="40" />
</a>

<br /><br />

(If the link returns 404, enable **GitHub Pages → Deploy from main**)

</div>

---

## ⚡️ The Concept

Most job boards are cluttered and slow. **ALL_CAREER** creates a private, noise-free feed of opportunities by directly tapping into the career portals of companies like Zoho, HCL, and Amazon.  
It runs on a **24-hour autonomous cycle**, ensuring that stored listings always match the original source.

---

## 🧬 Core Architecture (Self-Maintaining Data Ecosystem)

> Fully powered using GitHub Actions, Puppeteer Stealth, and JSON data storage.

```mermaid
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
