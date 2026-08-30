"""
Perceptual Image Hashing and Deduplication.
Uses pHash, dHash, and MD5 for ultra-fast duplicate detection of poster flyers.
"""
import hashlib
from typing import Tuple, Optional, Set
from PIL import Image
import imagehash


class ImageHasher:
    @staticmethod
    def compute_hashes(image_input) -> Tuple[str, str, str]:
        """
        Compute perceptual hash (pHash), difference hash (dHash), and MD5.
        Accepts file path or PIL Image.
        Returns: (phash_str, dhash_str, md5_str)
        """
        if isinstance(image_input, str):
            with open(image_input, "rb") as f:
                content = f.read()
                md5_str = hashlib.md5(content).hexdigest()
            img = Image.open(image_input)
        else:
            img = image_input
            md5_str = ""

        ph = str(imagehash.phash(img))
        dh = str(imagehash.dhash(img))
        return ph, dh, md5_str

    @staticmethod
    def is_duplicate(
        hash_a: str,
        hash_b: str,
        threshold: int = 6
    ) -> bool:
        """
        Compare two perceptual hash strings using Hamming distance.
        If distance <= threshold (default 6), images are visual duplicates.
        """
        if not hash_a or not hash_b:
            return False
        if hash_a == hash_b:
            return True
        try:
            h1 = imagehash.hex_to_hash(hash_a)
            h2 = imagehash.hex_to_hash(hash_b)
            return (h1 - h2) <= threshold
        except Exception:
            return False


class DuplicateTracker:
    """In-memory and persistent tracker for seen poster images."""
    def __init__(self, threshold: int = 6):
        self.threshold = threshold
        self.seen_phashes: Set[str] = set()
        self.seen_md5s: Set[str] = set()

    def check_and_add(self, phash: str, md5_str: Optional[str] = None) -> bool:
        """
        Returns True if duplicate, False if unique (and adds to tracker).
        """
        if md5_str and md5_str in self.seen_md5s:
            return True

        for existing_ph in self.seen_phashes:
            if ImageHasher.is_duplicate(existing_ph, phash, self.threshold):
                return True

        if phash:
            self.seen_phashes.add(phash)
        if md5_str:
            self.seen_md5s.add(md5_str)
        return False
