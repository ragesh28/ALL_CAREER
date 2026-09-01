"""
High-Recall Job and Hiring Signal Detector.
Evaluates OCR text using a weighted scoring model to filter out non-job images
before invoking multimodal AI.
"""
from typing import Dict, List, Tuple
from ..config import MIN_JOB_SIGNAL_SCORE


JOB_SIGNALS = {
    "walk_in": {
        "score": 5,
        "keywords": [
            "walk-in", "walk in", "walkin", "walk-in interview", "walk in interview",
            "walkin interview", "walk-in drive", "walk in drive", "walkin drive",
            "walking interview", "walking drive", "direct walkin", "walk-in-interview",
            "spot offer", "spot offers", "spot selection", "selection drive", "recruitment drive",
            "mega walk-in", "mega walk in", "mega job fair", "job fair", "open drive"
        ]
    },
    "interview": {
        "score": 3,
        "keywords": [
            "interview", "interviews", "face to face", "f2f interview",
            "virtual interview", "drive on", "interview scheduled", "interview venue",
            "placement drive", "written test", "technical round", "hr round", "venue", "timing"
        ]
    },
    "hiring": {
        "score": 2,
        "keywords": [
            "we are hiring", "we're hiring", "hiring now", "hiring", "urgently hiring",
            "urgent hiring", "join our team", "join the team", "career opportunity",
            "career opportunities", "job opportunity", "job openings", "job opening",
            "open positions", "immediate openings", "immediate opening", "hiring alert",
            "wanted", "looking for", "invites applications", "now hiring", "immediate joining"
        ]
    },
    "vacancy": {
        "score": 2,
        "keywords": [
            "vacancy", "vacancies", "multiple vacancies", "openings for", "positions open",
            "requirements", "requirement", "job role", "job description", "roles"
        ]
    },
    "qualifications": {
        "score": 2,
        "keywords": [
            "qualification", "qualifications", "eligibility", "experience", "fresher",
            "freshers", "graduates", "diploma", "b.tech", "b.e", "salary", "ctc",
            "take-home salary", "take home salary", "shift details"
        ]
    },
    "application": {
        "score": 1,
        "keywords": [
            "apply now", "apply", "register now", "send resume", "share your resume",
            "share cv", "submit resume", "forward resume", "contact hr", "send your cv",
            "mail resume", "whatsapp resume", "hr email", "contact us", "contact for registration"
        ]
    }
}


class JobSignalDetector:
    @classmethod
    def evaluate(
        cls,
        text: str,
        has_role: bool = False,
        has_location: bool = False,
        has_company: bool = False,
        has_datetime: bool = False,
        min_threshold: int = MIN_JOB_SIGNAL_SCORE
    ) -> Tuple[bool, int, List[str]]:
        """
        Calculates cumulative weighted score for the OCR text.
        Returns: (is_job_candidate, total_score, matched_signals_list)
        """
        if not text:
            return False, 0, []

        low_text = " " + text.lower() + " "
        compact_text = low_text.replace(" ", "").replace("-", "").replace("\n", "").replace("_", "")
        total_score = 0
        matched_signals = []

        # 1. Evaluate keyword groups (standard & glued/compact)
        for signal_category, data in JOB_SIGNALS.items():
            category_score = data["score"]
            for kw in data["keywords"]:
                kw_compact = kw.replace(" ", "").replace("-", "")
                if kw in low_text or (len(kw_compact) >= 5 and kw_compact in compact_text):
                    total_score += category_score
                    matched_signals.append(f"{signal_category}:{kw} (+{category_score})")
                    break  # Count each category once

        # 2. Add structural entity bonuses
        if has_role:
            total_score += 2
            matched_signals.append("entity:role (+2)")
        if has_location:
            total_score += 2
            matched_signals.append("entity:location (+2)")
        if has_company:
            total_score += 2
            matched_signals.append("entity:company (+2)")
        if has_datetime:
            total_score += 2
            matched_signals.append("entity:datetime (+2)")

        is_candidate = total_score >= min_threshold
        return is_candidate, total_score, matched_signals
