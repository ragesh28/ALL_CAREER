"""
Location detector for Indian job flyers.
Extracts canonical city, state, district, IT corridors, PIN codes, and venue address.
"""
import re
from typing import Optional, List
from ..schema.job_schema import LocationResult, OCRBoundingBox
from ..taxonomy.location_taxonomy import LocationTaxonomyResolver


class LocationDetector:
    # 6-digit Indian Postal PIN code pattern (e.g. 600001, 560100, 500081, 400001)
    PINCODE_PATTERN = re.compile(r'\b[1-9][0-9]{2}\s?[0-9]{3}\b')

    # Venue introduction keywords
    VENUE_PREFIXES = [
        "venue:", "interview venue:", "walk-in venue:", "walkin venue:",
        "location:", "address:", "interview location:", "drive location:",
        "reporting venue:", "venue address:"
    ]

    @classmethod
    def extract_venue(cls, text: str) -> Optional[str]:
        """Extract multi-line venue block from text if explicit venue keyword exists."""
        lines = text.split("\n")
        for i, line in enumerate(lines):
            low = line.lower().strip()
            for prefix in cls.VENUE_PREFIXES:
                if prefix in low:
                    # Collect following 1-3 lines
                    venue_lines = [line.split(":", 1)[-1].strip() if ":" in line else line]
                    for next_idx in range(i + 1, min(i + 4, len(lines))):
                        next_l = lines[next_idx].strip()
                        if next_l and not any(k in next_l.lower() for k in ["date:", "time:", "role:", "contact:", "salary:"]):
                            venue_lines.append(next_l)
                        else:
                            break
                    cleaned = ", ".join([l for l in venue_lines if l]).strip(" ,-")
                    if len(cleaned) >= 5:
                        return cleaned
        return None

    @classmethod
    def detect_location(
        cls,
        text: str,
        boxes: Optional[List[OCRBoundingBox]] = None
    ) -> LocationResult:
        """
        Detect canonical Indian city, state, locality, PIN code, and venue.
        """
        if not text:
            return LocationResult()

        # 1. Resolve taxonomy city / state / locality
        tax_res = LocationTaxonomyResolver.resolve_location(text)
        
        # 2. Extract PIN code
        pincode = None
        pin_match = cls.PINCODE_PATTERN.search(text)
        if pin_match:
            pincode = pin_match.group(0).replace(" ", "")

        # 3. Extract venue
        venue = cls.extract_venue(text)

        if tax_res:
            return LocationResult(
                city=tax_res["city"],
                state=tax_res["state"],
                district=tax_res["district"],
                locality=tax_res.get("locality"),
                venue=venue,
                pincode=pincode,
                confidence=tax_res["confidence"]
            )
        elif venue or pincode:
            return LocationResult(
                venue=venue,
                pincode=pincode,
                confidence=0.60
            )

        return LocationResult()
