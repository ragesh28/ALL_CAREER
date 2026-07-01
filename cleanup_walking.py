"""
Cleanup script: Remove walking_interview field from all stored job JSON files.
Only removes the field - NEVER deletes any jobs.
Run once to clean existing data. Safe to re-run.
"""
import os
import sys
import json
import glob

# Fix encoding on Windows
sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = os.path.dirname(os.path.abspath(__file__))

def cleanup_walking_field():
    """Remove walking_interview key from every job in all_jobs_*.json and jobs_by_role/*.json"""
    patterns = [
        os.path.join(WORKSPACE, "all_jobs_*.json"),
        os.path.join(WORKSPACE, "jobs_by_role", "*.json"),
    ]
    
    total_cleaned = 0
    files_modified = 0
    
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    jobs = json.load(f)
                
                if not isinstance(jobs, list):
                    continue
                
                original_count = len(jobs)
                modified = False
                for job in jobs:
                    if "walking_interview" in job:
                        del job["walking_interview"]
                        total_cleaned += 1
                        modified = True
                
                # Safety check: NEVER reduce job count
                assert len(jobs) == original_count, f"Job count changed in {filepath}! Aborting."
                
                if modified:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(jobs, f, separators=(',', ':'))
                    files_modified += 1
                    print(f"  Cleaned {os.path.basename(filepath)} ({original_count} jobs intact)")
                    
            except Exception as e:
                print(f"  Error processing {os.path.basename(filepath)}: {e}")
    
    print(f"\n{'='*50}")
    print(f"  Files modified:     {files_modified}")
    print(f"  Fields removed:     {total_cleaned}")
    print(f"  Jobs deleted:       0 (safety guaranteed)")
    print(f"{'='*50}")

if __name__ == "__main__":
    print("Removing walking_interview field from all stored jobs...\n")
    cleanup_walking_field()
    print("\nDone! The walking_interview field has been removed from all jobs.")
