import os
import json
import subprocess
import sys
import glob

TEMP_FILE = "temp_new_jobs.json"

def run_cmd(args):
    print(f"Running: {' '.join(args)}")
    res = subprocess.run(args, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error: {res.stderr}")
    else:
        if res.stdout.strip():
            print(res.stdout.strip())
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

    if not new_jobs:
        print("No jobs to merge.")
        return

    # Count sources in temp file
    temp_sources = {}
    for j in new_jobs:
        src = j.get("source") or j.get("platform") or "unknown"
        temp_sources[src] = temp_sources.get(src, 0) + 1
    print(f"Temp file sources: {temp_sources}")

    # 1. Discard local database changes to avoid merge conflicts during pull
    print("\nStep 1: Discarding local database changes before pull...")
    # Use glob to expand filenames explicitly since subprocess list mode
    # might not expand wildcards correctly on all platforms
    chunk_files = glob.glob("all_jobs_*.json")
    if chunk_files:
        run_cmd(["git", "checkout", "HEAD", "--"] + chunk_files + ["role_index.json"])
    else:
        run_cmd(["git", "checkout", "HEAD", "--", "role_index.json"])
    
    if os.path.exists("jobs_by_role"):
        role_files = glob.glob("jobs_by_role/*.json")
        if role_files:
            run_cmd(["git", "checkout", "HEAD", "--"] + role_files)

    # 2. Pull latest changes from remote
    print("\nStep 2: Pulling latest changes from origin main...")
    run_cmd(["git", "pull", "origin", "main"])

    # 3. Verify current state of database
    chunk_files_after = sorted(glob.glob("all_jobs_*.json"))
    total_before = 0
    for f in chunk_files_after:
        try:
            data = json.load(open(f, encoding="utf-8"))
            total_before += len(data)
        except:
            pass
    print(f"\nDatabase state after pull: {total_before} total jobs in {len(chunk_files_after)} chunks")

    # 4. Force-reload storage module to clear any cached state
    print("\nStep 3: Merging new jobs into the latest database state...")
    os.environ["IS_MERGING_TEMP"] = "1"
    
    # Remove storage from sys.modules to force a fresh import
    if "storage" in sys.modules:
        del sys.modules["storage"]
    if "role_classifier" in sys.modules:
        del sys.modules["role_classifier"]
    
    try:
        import storage
        stored_count = storage.store_jobs_batch(new_jobs)
        print(f"Successfully merged {stored_count} new jobs into database.")
    except Exception as e:
        print(f"Error during merge: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Verify final state
    chunk_files_final = sorted(glob.glob("all_jobs_*.json"))
    total_after = 0
    sources_after = {}
    for f in chunk_files_final:
        try:
            data = json.load(open(f, encoding="utf-8"))
            total_after += len(data)
            for j in data:
                src = j.get("source") or j.get("platform") or "unknown"
                sources_after[src] = sources_after.get(src, 0) + 1
        except:
            pass
    print(f"\nFinal database state: {total_after} total jobs (+{total_after - total_before} new)")
    print(f"Final sources: {dict(sorted(sources_after.items(), key=lambda x: -x[1]))}")
    
    # Check that our target portals made it in
    for portal in ["workindia", "internshala", "glassdoor"]:
        count = sources_after.get(portal, 0)
        temp_count = temp_sources.get(portal, 0)
        status = "OK" if count > 0 else ("MISSING!" if temp_count > 0 else "none in temp")
        print(f"  {portal}: {count} in DB, {temp_count} in temp file -> {status}")

    # 6. Clean up temp file
    try:
        os.remove(TEMP_FILE)
        print(f"\nRemoved temporary file {TEMP_FILE}.")
    except Exception as e:
        print(f"Error removing {TEMP_FILE}: {e}")

if __name__ == "__main__":
    main()
