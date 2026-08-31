"""
Deterministic Date and Time Detector for Walk-in & Recruitment Posters.
Normalizes single dates, date ranges, and time intervals into standardized formats.
"""
import re
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from ..schema.job_schema import TimeWindow


class DateTimeDetector:
    # Month mapping
    MONTH_MAP = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
        "nov": 11, "november": 11, "dec": 12, "december": 12
    }

    # Date range patterns (e.g. "28th to 30th August 2026", "28 - 30 Aug", "28th & 29th Aug")
    DATE_RANGE_REGEX = re.compile(
        r'\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:to|-|&|and)\s*(\d{1,2})(?:st|nd|rd|th)?\s*([A-Za-z]{3,9})(?:\s*(\d{4}))?\b',
        re.IGNORECASE
    )

    # Single date patterns (e.g. "29th August 2026", "29 Aug", "29Aug2026", "29-08-2026", "29/08/2026")
    SINGLE_DATE_WORD_REGEX = re.compile(
        r'\b(\d{1,2})(?:st|nd|rd|th)?\s*([A-Za-z]{3,9})(?:\s*(\d{4}))?\b',
        re.IGNORECASE
    )
    SINGLE_DATE_NUMERIC_REGEX = re.compile(
        r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b'
    )

    # Time window regex (e.g. "09:30 AM to 03:30 PM", "10:00 AM - 1:00 PM", "10 AM - 4 PM", "9:30AM - 5:00PM")
    TIME_RANGE_REGEX = re.compile(
        r'\b(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:to|-|till)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b',
        re.IGNORECASE
    )

    @classmethod
    def parse_time(cls, text: str) -> TimeWindow:
        """Extract start and end time window."""
        match = cls.TIME_RANGE_REGEX.search(text)
        if match:
            start_raw, end_raw = match.group(1).strip(), match.group(2).strip()
            # If start missing am/pm, infer from end
            if not re.search(r'(am|pm)', start_raw, re.IGNORECASE) and re.search(r'pm', end_raw, re.IGNORECASE):
                # If start is 9, 10, 11 it's likely AM
                val = int(start_raw.split(":")[0])
                if val in [8, 9, 10, 11]:
                    start_raw += " AM"
                else:
                    start_raw += " PM"
            return TimeWindow(start=start_raw.upper(), end=end_raw.upper())
        return TimeWindow()

    @classmethod
    def parse_dates(cls, text: str, current_year: int = 2026) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract start date and optional end date.
        Returns: (start_date_str, end_date_str)
        """
        # 1. Check Date Range (e.g. 28th to 30th August 2026)
        range_match = cls.DATE_RANGE_REGEX.search(text)
        if range_match:
            d1 = int(range_match.group(1))
            d2 = int(range_match.group(2))
            month_str = range_match.group(3).lower()
            yr = int(range_match.group(4)) if range_match.group(4) else current_year
            month_num = cls.MONTH_MAP.get(month_str)

            if month_num:
                start_iso = f"{yr:04d}-{month_num:02d}-{d1:02d}"
                end_iso = f"{yr:04d}-{month_num:02d}-{d2:02d}"
                return start_iso, end_iso

        # 2. Check Single Word Date (e.g. 29th August 2026)
        word_match = cls.SINGLE_DATE_WORD_REGEX.search(text)
        if word_match:
            d = int(word_match.group(1))
            month_str = word_match.group(2).lower()
            yr = int(word_match.group(3)) if word_match.group(3) else current_year
            month_num = cls.MONTH_MAP.get(month_str)
            if month_num and 1 <= d <= 31:
                start_iso = f"{yr:04d}-{month_num:02d}-{d:02d}"
                return start_iso, None

        # 3. Check Numeric Date (e.g. 29/08/2026 or 29-08-2026)
        num_match = cls.SINGLE_DATE_NUMERIC_REGEX.search(text)
        if num_match:
            d = int(num_match.group(1))
            m = int(num_match.group(2))
            y = int(num_match.group(3))
            if y < 100:
                y += 2000
            if 1 <= m <= 12 and 1 <= d <= 31:
                start_iso = f"{y:04d}-{m:02d}-{d:02d}"
                return start_iso, None

        return None, None

    @classmethod
    def detect_date_time(cls, text: str) -> Dict[str, Any]:
        """Detect both date and time from text."""
        start_date, end_date = cls.parse_dates(text)
        time_window = cls.parse_time(text)
        return {
            "date": start_date,
            "end_date": end_date,
            "time": time_window
        }
