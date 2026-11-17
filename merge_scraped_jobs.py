"""Replay the scraper journal on current Git data and save the checkpoint."""
import argparse
import os
from pathlib import Path
import subprocess

from scripts.job_archive_paths import ARCHIVE_DIRECTORY


TEMP_FILE = Path("temp_new_jobs.json")
SHARD_PATHS = ("data/jobs", "data/index", ARCHIVE_DIRECTORY.as_posix())
JOB_PATHS = (*SHARD_PATHS, ":(glob)all_jobs_*.json", "role_index.json", "jobs_by_role")


def git(*args):
    return subprocess.run(["git", *args], check=True, text=True, stdout=subprocess.PIPE).stdout


def merge_checkpoint(message=None, checkpoint_paths=()):
    import storage

    jobs = storage.read_saved_jobs(TEMP_FILE) if TEMP_FILE.is_file() else []
    if not jobs and not message:
        print("No pending jobs to merge.")
        return

    branch = git("branch", "--show-current").strip()
    if not branch:
        raise RuntimeError("A scraper must run on a checked-out branch to save progress")
    if jobs:
        # Rebuild the generated files from the journal after bringing in other
        # scrapers' commits. Checkpoint and debug files stay in the worktree.
        paths = [path for path in JOB_PATHS if git("ls-files", "--", path)]
        if paths:
            git("restore", "--source=HEAD", "--staged", "--worktree", "--", *paths)
        untracked = git("ls-files", "--others", "--exclude-standard", "-z", "--", *SHARD_PATHS)
        for path in untracked.rstrip("\0").split("\0") if untracked else []:
            Path(path).unlink()

    git("pull", "--rebase", "--autostash", "origin", branch)
    if git("diff", "--name-only", "--diff-filter=U"):
        raise RuntimeError("Scraper files conflicted with another commit")

    if jobs:
        storage.archived_keys(refresh=True)
        previous = os.environ.get("IS_MERGING_TEMP")
        os.environ["IS_MERGING_TEMP"] = "1"
        try:
            storage.store_jobs_batch(jobs)
        finally:
            if previous is None:
                os.environ.pop("IS_MERGING_TEMP")
            else:
                os.environ["IS_MERGING_TEMP"] = previous
        expected = {storage.archive_key(job) for job in jobs}
        if not expected.issubset(storage.archived_keys()):
            raise RuntimeError("Some journaled jobs are missing from the archive")
        print(f"Verified {len(expected)} journaled jobs in the archive.")

    if message:
        paths = [path for path in (*SHARD_PATHS, *checkpoint_paths)
                 if Path(path).exists() or git("ls-files", "--", path)]
        if paths:
            git("add", "-A", "--", *paths)
        if git("diff", "--cached", "--name-only"):
            git("commit", "-m", message)
        # The checkpoint only counts as saved once the same commit, with its
        # job records, reaches GitHub. A racing push leaves the journal intact.
        git("push", "origin", f"HEAD:refs/heads/{branch}")
        print(f"Checkpoint is saved at {git('rev-parse', '--short', 'HEAD').strip()}.")

    TEMP_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit-message")
    parser.add_argument("checkpoint_paths", nargs="*")
    args = parser.parse_args()
    merge_checkpoint(args.commit_message, args.checkpoint_paths)
