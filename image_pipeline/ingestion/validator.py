"""
Image validation module.
Verifies format, dimensions, corruption, and minimum size requirements.
"""
from typing import Tuple, Optional
from PIL import Image
from ..config import MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT, MAX_IMAGE_DIMENSION


class ImageValidator:
    @staticmethod
    def validate(image_path: str) -> Tuple[bool, Optional[str], Optional[Tuple[int, int]]]:
        """
        Validate image file.
        Returns: (is_valid, error_reason, (width, height))
        """
        try:
            with Image.open(image_path) as img:
                img.verify()

            # Re-open after verify to inspect dimensions
            with Image.open(image_path) as img:
                w, h = img.size
                if w < MIN_IMAGE_WIDTH or h < MIN_IMAGE_HEIGHT:
                    return False, f"Image too small ({w}x{h} < {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT})", (w, h)
                if w > MAX_IMAGE_DIMENSION or h > MAX_IMAGE_DIMENSION:
                    return True, "Large image, will be resized", (w, h)
                return True, None, (w, h)
        except Exception as e:
            return False, f"Invalid or corrupted image: {str(e)}", None
