"""
Scraper wrapper — calls Step 1 (jobspy with direct links).
Used by app.py when user clicks "Refresh Jobs".
Can also be run standalone: py -3.11 scraper.py
"""

import pandas as pd

CSV_FILE = "jobs.csv"


def scrape_all_jobs(search_term="", results_per_location=500):
    """Called by app.py — runs step1 and returns DataFrame."""
    from step1_jobspy import run as run_step1
    run_step1()

    try:
        df = pd.read_csv(CSV_FILE)
        return df
    except:
        return pd.DataFrame()


def save_to_csv(df, filename="jobs.csv"):
    """Save DataFrame to CSV."""
    if not df.empty:
        df.to_csv(filename, index=False)


if __name__ == "__main__":
    scrape_all_jobs()