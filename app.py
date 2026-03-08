"""
Flask web server for ALL_CAREER.
Serves the web UI, hub pages, and API endpoints for job data.
"""

import os
import pandas as pd
from flask import Flask, render_template, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
CSV_FILE = os.path.join(BASE_DIR, "jobs.csv")


@app.route("/")
def jobs_page():
    """Serve the jobs page."""
    return render_template("index.html")


@app.route("/hub")
def hub():
    """Serve the main ALL_CAREER hub page."""
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/top-companys")
def top_companys():
    """Serve the Top Companys sub-menu page."""
    return send_from_directory(BASE_DIR, "top_companys.html")


# --- Serve ALL static files from ALL_CAREER directory ---
# This catches career_explorer.html, daily_jobs.html, practice.html,
# companies.js, logos.js, jobs_data.js, etc.
@app.route("/<path:filename>")
def serve_static_files(filename):
    """Serve any file from the ALL_CAREER directory."""
    filepath = os.path.join(BASE_DIR, filename)
    if os.path.isfile(filepath):
        return send_from_directory(BASE_DIR, filename)
    return "Not Found", 404


@app.route("/api/jobs")
def get_jobs():
    """Return jobs from CSV as JSON."""
    if not os.path.exists(CSV_FILE):
        return jsonify({"jobs": [], "message": "No jobs file found."})

    try:
        df = pd.read_csv(CSV_FILE)
        import numpy as np
        df = df.replace({np.nan: None, float('nan'): None})

        jobs = []
        for _, row in df.iterrows():
            job = {}
            for col in df.columns:
                val = row[col]
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    job[col] = None
                elif isinstance(val, (int, float)):
                    job[col] = val
                else:
                    job[col] = str(val) if val else None
            jobs.append(job)

        return jsonify({"jobs": jobs, "message": f"Found {len(jobs)} jobs"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"jobs": [], "message": f"Error: {str(e)}"}), 500


@app.route("/api/scrape", methods=["POST"])
def trigger_scrape():
    """Trigger a new job scrape."""
    try:
        from scraper import scrape_all_jobs, save_to_csv
        search_term = request.json.get("search_term", "Google") if request.json else "Google"
        results = request.json.get("results_per_location", 500) if request.json else 500

        df = scrape_all_jobs(search_term=search_term, results_per_location=results)
        save_to_csv(df, CSV_FILE)

        return jsonify({"success": True, "message": f"Scraped {len(df)} jobs!"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Scrape failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
