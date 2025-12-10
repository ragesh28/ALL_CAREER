🚀 Daily Job Scraper & Career Hub

A fully automated career platform that scrapes, aggregates, and filters job listings from top tech companies daily.

🔴 LIVE DEMO
(Note: Enable GitHub Pages in Settings -> Pages -> Source: main branch to view the live site)

🧐 How It Works

This project runs on a 24-hour cycle using GitHub Actions to ensure job listings are always fresh.

graph LR
    A[🕒 Midnight UTC] -->|Triggers| B(GitHub Action)
    B -->|Spins Up| C{Scraper Bot}
    C -->|Visits| D[Company Career Pages]
    D -->|Extracts| E[Job Data]
    E -->|Saves to| F[jobs.json]
    F -->|Auto-Cleans| G[Remove Jobs > 30 Days]
    G -->|Updates| H[Web Interface]


Automated Scraping: Every day at 00:00 UTC, a virtual browser visits career pages (Zoho, Amazon, HCL, etc.).

Smart Filtering: It extracts only relevant roles and filters by location (Chennai/Bangalore).

Self-Cleaning Database: A maintenance script runs automatically to delete expired jobs older than 30 days.

Instant UI Update: The website (index.html) reads the updated data immediately without needing a database server.

✨ Features

🕵️‍♂️ Stealth Scraping: Uses puppeteer-extra-plugin-stealth to bypass bot detection.

🌍 Multi-Company Support: Currently supports 15+ major tech companies including Zoho, Freshworks, HCL, Amazon, and more.

🧹 Auto-Maintenance: "Janitor" script keeps the database clean by removing old entries.

📱 Responsive Hub: A modern, dark-mode UI to browse jobs, company stats, and practice DSA.

⚡ Zero-Config: Works out of the box with GitHub Actions.

📂 Project Structure

scrape.js - The brain of the operation. Fetches data using Puppeteer.

clean_jobs.js - The janitor. Removes jobs older than 30 days.

companies.json - Configuration file containing URLs and CSS Selectors.

daily_jobs.html - The user interface for viewing active listings.

index.html - The main landing hub.

.github/workflows/scrape.yml - The automation timer configuration.

🚀 Getting Started (Run Locally)

Want to run this on your own machine?

Clone the repo

git clone [https://github.com/ragesh28/ALL_CAREER.git](https://github.com/ragesh28/ALL_CAREER.git)
cd ALL_CAREER


Install Dependencies

npm install


Run the Scraper

npm start


This will scrape the jobs and update jobs_data.js.

Open the App

Open index.html in your browser to see the Career Hub.

🤝 Contributing

Got a new company to add?

Open companies.json.

Add the URL and CSS Selectors.

Submit a Pull Request!

Built with ❤️ by Ragesh