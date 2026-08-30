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
            "spot offer", "spot offers", "selection drive", "recruitment drive"
        ]
    },
    "interview": {
        "score": 3,
        "keywords": [
            "interview", "interviews", "face to face interview", "f2f interview",
            "virtual interview", "drive on", "interview scheduled", "interview venue",
            "placement drive", "job fair", "mega job fair", "campus drive"
        ]
    },
    "hiring": {
        "score": 2,
        "keywords": [
            "we are hiring", "we're hiring", "hiring now", "hiring", "urgently hiring",
            "urgent hiring", "join our team", "join the team", "career opportunity",
            "career opportunities", "job opportunity", "job openings", "job opening",
            "open positions", "immediate openings", "immediate opening", "hiring alert",
            "wanted", "looking for", "invites applications", "now hiring"
        ]
    },
    "vacancy": {
        "score": 2,
        "keywords": [
            "vacancy", "vacancies", "multiple vacancies", "openings for", "positions open",
            "requirements", "requirement", "job role", "job description"
        ]
    },
    "application": {
        "score": 1,
        "keywords": [
            "apply now", "apply", "register now", "send resume", "share your resume",
            "share cv", "submit resume", "forward resume", "contact hr", "send your cv",
            "mail resume", "whatsapp resume", "hr email", "contact us"
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
        total_score = 0
        matched_signals = []

        # 1. Evaluate keyword groups
        for signal_category, data in JOB_SIGNALS.items():
            category_score = data["score"]
            for kw in data["keywords"]:
                if f" {kw} " in low_text or f"\n{kw}\n" in low_text or f"\n{kw} " in low_text or f" {kw}\n" in low_text or kw in low_text:
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
