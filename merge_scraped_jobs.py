import os
import json
import subprocess

TEMP_FILE = "temp_new_jobs.json"

def run_cmd(args):
    print(f"Running: {' '.join(args)}")
    res = subprocess.run(args, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error: {res.stderr}")
    else:
        print(res.stdout)
    return res.returncode == 0

def main():
    if not os.path.exists(TEMP_FILE):
        print(f"No temporary jobs file found ({TEMP_FILE}). Nothing to merge.")
        return

    try:
        with open(TEMP_FILE, "r", encoding="utf-8") as f:
            new_jobs = json.load(f)
        print(f"Loaded {len(new_jobs)} new/updated jobs from {TEMP_FILE}.")
    except Exception as e:
        print(f"Error reading {TEMP_FILE}: {e}")
        return

    # 1. Discard local database changes to avoid merge conflicts during pull
    print("Discarding local database changes before pull...")
    run_cmd(["git", "checkout", "HEAD", "--", "all_jobs_*.json", "role_index.json"])
    # Also discard jobs_by_role folder changes if it exists
    if os.path.exists("jobs_by_role"):
        run_cmd(["git", "checkout", "HEAD", "--", "jobs_by_role/"])

    # 2. Pull latest changes from remote
    print("Pulling latest changes from origin main...")
    run_cmd(["git", "pull", "origin", "main"])

    # 3. Import storage and merge jobs
    print("Merging new jobs into the latest database state...")
    os.environ["IS_MERGING_TEMP"] = "1"
    try:
        import storage
        stored_count = storage.store_jobs_batch(new_jobs)
        print(f"Successfully merged {stored_count} new jobs into database.")
    except Exception as e:
        print(f"Error during merge: {e}")
        return

    # 4. Clean up temp file
    try:
        os.remove(TEMP_FILE)
        print(f"Removed temporary file {TEMP_FILE}.")
    except Exception as e:
        print(f"Error removing {TEMP_FILE}: {e}")

if __name__ == "__main__":
    main()
