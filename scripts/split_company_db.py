"""
Split large company database file into < 45MB chunks for GitHub compatibility,
and provide fast integrity-verified reassembly.
"""
import os
import sys
import hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

CHUNK_SIZE_BYTES = 44 * 1024 * 1024  # 44 MB per chunk (strictly under GitHub 50MB/100MB limits)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SOURCE_DB = DATA_DIR / "company_names.db"
CHUNKS_DIR = DATA_DIR / "company_names_chunks"


def calculate_sha256(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(4 * 1024 * 1024):
            sha.update(chunk)
    return sha.hexdigest()


def split_database(source_file: Path = SOURCE_DB, output_dir: Path = CHUNKS_DIR) -> list:
    if not source_file.exists():
        raise FileNotFoundError(f"Source database not found at {source_file}")

    output_dir.mkdir(parents=True, exist_ok=True)
    total_size = source_file.stat().st_size
    full_sha = calculate_sha256(source_file)

    print(f"📦 Splitting: {source_file.name} ({total_size / (1024*1024):.2f} MB)")
    print(f"   SHA-256: {full_sha}")

    part_num = 0
    chunk_files = []

    with open(source_file, "rb") as src:
        while True:
            chunk_data = src.read(CHUNK_SIZE_BYTES)
            if not chunk_data:
                break
            part_filename = f"company_names.part{part_num:02d}"
            part_path = output_dir / part_filename
            with open(part_path, "wb") as dst:
                dst.write(chunk_data)
            chunk_size_mb = len(chunk_data) / (1024 * 1024)
            print(f"   Created chunk: {part_filename} ({chunk_size_mb:.2f} MB)")
            chunk_files.append(part_path)
            part_num += 1

    # Save manifest
    manifest_path = output_dir / "manifest.json"
    import json
    manifest = {
        "source_filename": source_file.name,
        "total_size_bytes": total_size,
        "sha256": full_sha,
        "chunk_count": len(chunk_files),
        "chunk_size_bytes": CHUNK_SIZE_BYTES,
        "chunks": [p.name for p in chunk_files]
    }
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

    print(f"✅ Splitting Complete: {len(chunk_files)} chunks created in {output_dir}")
    print(f"   Manifest saved to {manifest_path}")
    return chunk_files


def reassemble_database(chunks_dir: Path = CHUNKS_DIR, target_file: Path = SOURCE_DB) -> bool:
    import json
    manifest_path = chunks_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"⚠️ Warning: No manifest found at {manifest_path}")
        # Find parts by glob
        parts = sorted(chunks_dir.glob("company_names.part*"))
        if not parts:
            print(f"❌ Error: No chunk parts found in {chunks_dir}")
            return False
        expected_sha = None
    else:
        with open(manifest_path, "r", encoding="utf-8") as mf:
            manifest = json.load(mf)
        parts = [chunks_dir / name for name in manifest["chunks"]]
        expected_sha = manifest.get("sha256")

    print(f"🔄 Reassembling database from {len(parts)} chunks into {target_file.name}...")
    target_file.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target_file.with_suffix(".tmp_reassemble")

    with open(temp_target, "wb") as out_f:
        for p in parts:
            if not p.exists():
                raise FileNotFoundError(f"Missing chunk: {p}")
            with open(p, "rb") as in_f:
                while chunk := in_f.read(4 * 1024 * 1024):
                    out_f.write(chunk)

    # Verify SHA-256 if available
    actual_sha = calculate_sha256(temp_target)
    if expected_sha and actual_sha != expected_sha:
        temp_target.unlink(missing_ok=True)
        raise ValueError(f"Integrity check failed! Expected {expected_sha}, got {actual_sha}")

    if target_file.exists():
        target_file.unlink()
    temp_target.rename(target_file)
    print(f"✅ Reassembly Successful: {target_file.name} ({target_file.stat().st_size / (1024*1024):.2f} MB)")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reassemble":
        reassemble_database()
    else:
        split_database()
