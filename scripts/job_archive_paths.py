"""Paths for the numbered job archives shared by scrapers and the catalog."""

from pathlib import Path

ARCHIVE_DIRECTORY = Path("data/job_archives")
ARCHIVE_PREFIX = "all_jobs_"


def archive_chunk_number(path):
    return int(Path(path).stem.removeprefix(ARCHIVE_PREFIX))


def archive_chunks(root):
    root = Path(root)
    # A scrape started before the move can still leave a numbered root file.
    paths = [
        path
        for directory in (root / ARCHIVE_DIRECTORY, root)
        for path in directory.glob(f"{ARCHIVE_PREFIX}*.json")
        if path.stem.removeprefix(ARCHIVE_PREFIX).isdecimal() and path.is_file()
    ]
    return sorted(paths, key=lambda path: (archive_chunk_number(path), path.parent == root, path.name))
