"""
Spatial Bounding Box Merger and Deduplication.
Merges detections across multi-pass OCR runs using Intersection over Union (IoU)
and spatial proximity.
"""
from typing import List, Tuple
from ..schema.job_schema import OCRBoundingBox


class OCRMerger:
    @staticmethod
    def calculate_iou(box_a: List[float], box_b: List[float]) -> float:
        """Calculate IoU of two bounding boxes [x1, y1, x2, y2]."""
        x_a = max(box_a[0], box_b[0])
        y_a = max(box_a[1], box_b[1])
        x_b = min(box_a[2], box_b[2])
        y_b = min(box_a[3], box_b[3])

        inter_area = max(0.0, x_b - x_a) * max(0.0, y_b - y_a)
        if inter_area == 0.0:
            return 0.0

        box_a_area = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        box_b_area = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        union_area = box_a_area + box_b_area - inter_area
        return inter_area / union_area if union_area > 0 else 0.0

    @classmethod
    def merge_bounding_boxes(
        cls,
        boxes: List[OCRBoundingBox],
        orig_shape: Tuple[int, int],
        iou_threshold: float = 0.40
    ) -> List[OCRBoundingBox]:
        """
        Merge overlapping detections from different passes.
        Preserves higher confidence detections and sorts from top to bottom (reading order).
        """
        if not boxes:
            return []

        # Sort by confidence descending
        sorted_by_conf = sorted(boxes, key=lambda b: b.confidence, reverse=True)
        unique_boxes: List[OCRBoundingBox] = []

        for candidate in sorted_by_conf:
            is_dup = False
            for existing in unique_boxes:
                # Check IoU
                iou = cls.calculate_iou(candidate.rect, existing.rect)
                if iou >= iou_threshold:
                    is_dup = True
                    break
                # Check text exact similarity in nearly identical vertical position
                if candidate.text.lower() == existing.text.lower() and abs(candidate.relative_top - existing.relative_top) < 0.03:
                    is_dup = True
                    break

            if not is_dup:
                unique_boxes.append(candidate)

        # Sort spatially top-to-bottom, then left-to-right (natural reading order)
        sorted_reading_order = sorted(unique_boxes, key=lambda b: (round(b.relative_top, 2), b.rect[0]))
        return sorted_reading_order

    @staticmethod
    def get_full_text(boxes: List[OCRBoundingBox]) -> str:
        """Combine sorted OCR boxes into a unified text document."""
        return "\n".join(b.text for b in boxes if b.text.strip())
