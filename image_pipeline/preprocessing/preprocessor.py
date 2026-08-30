"""
Multi-pass Image Preprocessor.
Generates image variants to maximize OCR recall across diverse flyer fonts,
backgrounds, tiny text, and contrast levels.
"""
from typing import Dict, List, Tuple, Optional
import cv2
import numpy as np


class ImagePreprocessor:
    @staticmethod
    def load_image(image_path: str) -> Optional[np.ndarray]:
        """Load image into OpenCV BGR numpy array."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                # Handle non-ASCII / Unicode paths on Windows
                stream = open(image_path, "rb")
                bytes_data = bytearray(stream.read())
                numpy_array = np.asarray(bytes_data, dtype=np.uint8)
                img = cv2.imdecode(numpy_array, cv2.IMREAD_UNCHANGED)
                stream.close()
            return img
        except Exception:
            return None

    @classmethod
    def generate_variants(cls, img: np.ndarray, upscale_factor: float = 2.0) -> Dict[str, np.ndarray]:
        """
        Generate multiple image variants for multi-pass OCR:
        1. original
        2. upscaled_2x: cubic interpolation for small/tiny text
        3. clahe: contrast-limited adaptive histogram equalization
        4. sharpened: unsharp mask kernel
        5. threshold: adaptive gaussian thresholding for low-contrast text
        """
        variants = {}
        if img is None:
            return variants

        # 1. Original
        variants["original"] = img.copy()

        # Convert to Grayscale if color
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        variants["grayscale"] = gray

        # 2. 2x Upscaled
        h, w = img.shape[:2]
        if w < 1600 or h < 1600:
            new_w, new_h = int(w * upscale_factor), int(h * upscale_factor)
            variants["upscaled"] = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

        # 3. CLAHE Contrast Enhanced
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        variants["clahe"] = clahe.apply(gray)

        # 4. Sharpened
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        variants["sharpened"] = cv2.filter2D(img, -1, kernel)

        # 5. Adaptive Threshold (Binarized)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        variants["threshold"] = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        return variants

    @classmethod
    def crop_regions(cls, img: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Crop important semantic regions:
        - top_header: top 35% (usually contains company name and logo)
        - bottom_footer: bottom 35% (usually contains venue, phone, email, and dates)
        """
        h, w = img.shape[:2]
        regions = {
            "top_header": img[0:int(h * 0.35), 0:w],
            "bottom_footer": img[int(h * 0.65):h, 0:w]
        }
        return regions
