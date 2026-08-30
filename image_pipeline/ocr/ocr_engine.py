"""
Multi-pass OCR Engine for Job Posters.
Preserves bounding box coordinates, polygon vertices, confidence scores,
and spatial layout positions for downstream semantic analysis.
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from ..schema.job_schema import OCRBoundingBox
from ..preprocessing.preprocessor import ImagePreprocessor
from ..config import OCR_MIN_CONFIDENCE

# Lazy-loaded OCR engine instance
_OCR_INSTANCE = None


def get_ocr_engine():
    global _OCR_INSTANCE
    if _OCR_INSTANCE is None:
        try:
            # Primary: RapidOCR ONNX runtime (PaddleOCR PP-OCRv4 ONNX model)
            from rapidocr_onnxruntime import RapidOCR
            _OCR_INSTANCE = RapidOCR()
        except ImportError:
            try:
                # Fallback: standard PaddleOCR
                from paddleocr import PaddleOCR
                _OCR_INSTANCE = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            except Exception as e:
                print(f"⚠️ Warning: Could not initialize local OCR engine: {e}")
                _OCR_INSTANCE = None
    return _OCR_INSTANCE


class OCREngine:
    def __init__(self, min_confidence: float = OCR_MIN_CONFIDENCE):
        self.min_confidence = min_confidence
        self.engine = get_ocr_engine()

    def run_single_image(self, img: np.ndarray, orig_shape: Tuple[int, int]) -> List[OCRBoundingBox]:
        """
        Run OCR on a single image array and normalize coordinates back to original image dimensions.
        orig_shape: (orig_height, orig_width)
        """
        if self.engine is None or img is None:
            return []

        orig_h, orig_w = orig_shape
        curr_h, curr_w = img.shape[:2]
        scale_x = orig_w / float(curr_w) if curr_w > 0 else 1.0
        scale_y = orig_h / float(curr_h) if curr_h > 0 else 1.0

        boxes: List[OCRBoundingBox] = []

        try:
            # RapidOCR call returns (results, elapse)
            result = self.engine(img)
            if isinstance(result, tuple):
                items = result[0]
            else:
                items = result

            if not items:
                return []

            for item in items:
                # item format: [box_points, text, confidence]
                if len(item) < 3:
                    continue
                raw_box = item[0]
                text = str(item[1]).strip()
                try:
                    conf = float(item[2])
                except (ValueError, TypeError):
                    conf = 0.5

                if conf < self.min_confidence or len(text) == 0:
                    continue

                # Scale box points back to original image coordinates
                scaled_box = []
                x_coords, y_coords = [], []
                for pt in raw_box:
                    sx = pt[0] * scale_x
                    sy = pt[1] * scale_y
                    scaled_box.append([round(sx, 1), round(sy, 1)])
                    x_coords.append(sx)
                    y_coords.append(sy)

                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                relative_top = y_min / orig_h if orig_h > 0 else 0.0

                boxes.append(
                    OCRBoundingBox(
                        text=text,
                        confidence=round(conf, 3),
                        box=scaled_box,
                        rect=[round(x_min, 1), round(y_min, 1), round(x_max, 1), round(y_max, 1)],
                        relative_top=round(relative_top, 3)
                    )
                )
        except Exception as e:
            # print(f"OCR execution warning: {e}")
            pass

        return boxes

    def run_multipass(self, image_input) -> List[OCRBoundingBox]:
        """
        Execute multi-pass OCR on:
        1. Original image
        2. Upscaled 2x (for small text & badges)
        3. CLAHE contrast enhanced
        4. Sharpened
        Then merge and deduplicate spatially.
        """
        if isinstance(image_input, str):
            img = ImagePreprocessor.load_image(image_input)
        else:
            img = image_input

        if img is None:
            return []

        orig_shape = (img.shape[0], img.shape[1])
        variants = ImagePreprocessor.generate_variants(img)

        all_boxes: List[OCRBoundingBox] = []

        # Run primary pass on original
        all_boxes.extend(self.run_single_image(variants.get("original", img), orig_shape))

        # Run pass on upscaled for small fonts
        if "upscaled" in variants:
            all_boxes.extend(self.run_single_image(variants["upscaled"], orig_shape))

        # Run pass on CLAHE contrast enhanced
        if "clahe" in variants:
            all_boxes.extend(self.run_single_image(variants["clahe"], orig_shape))

        # Merge results
        from .merger import OCRMerger
        merged_boxes = OCRMerger.merge_bounding_boxes(all_boxes, orig_shape)
        return merged_boxes
