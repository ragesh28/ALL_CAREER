"""
Company Resolver with Multi-Stage Lookup Pipeline:
1. Input Normalization & Candidate Phrase Extraction
2. Curated Brand Aliases Lookup
3. Exact SQLite Indexed Lookup
4. Fast SQLite FTS5 Prefix Candidate Retrieval (5-25 rows)
5. RapidFuzz Re-ranking on Candidate Set ONLY (Never full DB scan)
6. Confidence Classification (High, Medium, Low / Uncertain)
"""
import re
from typing import Dict, Any, List, Optional
from rapidfuzz import fuzz

from .config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW, FTS5_CANDIDATE_LIMIT
from .normalizer import CompanyNormalizer
from .database import CompanyDatabase


class CompanyResolver:
    def __init__(self, db: Optional[CompanyDatabase] = None):
        self.db = db or CompanyDatabase()

    def _extract_candidate_phrases(self, ocr_text: str) -> List[str]:
        """
        Extract meaningful potential company candidate lines/phrases from OCR text.
        Extracts:
        1. Clean individual lines
        2. Context phrases after prepositions ("at [Company]", "for [Company]", "in [Company]")
        3. Word n-grams (1 to 4 words)
        Filters out pure generic words, emails, phone numbers, and noise.
        """
        if not ocr_text:
            return []

        lines = [line.strip() for line in ocr_text.split("\n") if line.strip()]
        candidates = []
        seen = set()

        def add_candidate(phrase: str):
            cleaned = CompanyNormalizer.clean_whitespace(phrase)
            norm = CompanyNormalizer.normalize_name(cleaned, strip_legal_suffix=False)
            if norm and len(norm) >= 2 and not CompanyNormalizer.is_generic_word(norm):
                if norm not in seen:
                    seen.add(norm)
                    candidates.append(cleaned)

        for line in lines:
            # Skip obvious non-company patterns (dates, phones, emails, urls)
            if re.search(r'(@|https?://|www\.|\+91|\b\d{6}\b)', line):
                continue

            # 1. Add full cleaned line
            add_candidate(line)

            # 2. Check context after prepositions (e.g. "Walk in interview at TCS Chennai" -> "TCS")
            prep_matches = re.findall(r'\b(?:at|for|by|join|with|welcome to)\s+([A-Za-z0-9&\s\.\-]{2,40})', line, re.IGNORECASE)
            for match in prep_matches:
                # Take up to the next generic word or punctuation
                words = match.split()
                for length in range(len(words), 0, -1):
                    sub_phrase = " ".join(words[:length])
                    add_candidate(sub_phrase)

            # 3. Add sliding window n-grams (1, 2, 3 words) from line
            words = line.split()
            if len(words) > 1:
                for w_len in range(1, min(4, len(words) + 1)):
                    for i in range(len(words) - w_len + 1):
                        ngram = " ".join(words[i:i + w_len])
                        add_candidate(ngram)

        return candidates

    def resolve_candidate(self, query: str) -> Dict[str, Any]:
        """
        Execute multi-stage resolution on a single candidate name:
        Exact -> Alias -> FTS5 -> RapidFuzz.
        """
        cleaned_query = CompanyNormalizer.clean_whitespace(query)
        normalized_query = CompanyNormalizer.normalize_name(cleaned_query, strip_legal_suffix=True)
        query_tokens = CompanyNormalizer.get_search_tokens(normalized_query)

        if not normalized_query or CompanyNormalizer.is_generic_word(normalized_query):
            return {
                "matched": False,
                "company_name": None,
                "cin": None,
                "confidence": 0.0,
                "match_type": "rejected_generic",
                "candidates": []
            }

        # ── Stage 1: Curated Brand Aliases Lookup (O(1)) ──
        alias_match = self.db.lookup_alias(query)
        if alias_match:
            return {
                "matched": True,
                "company_name": alias_match["canonical_name"],
                "cin": alias_match.get("cin"),
                "confidence": 0.99,
                "match_type": "alias_exact",
                "matched_alias": alias_match["alias"],
                "candidate_count": 1
            }

        # ── Stage 2: Exact Normalized SQLite Index Lookup (O(1) B-Tree) ──
        exact_match = self.db.exact_lookup(normalized_query)
        if exact_match:
            return {
                "matched": True,
                "company_name": exact_match["company_name"],
                "cin": exact_match["cin"],
                "confidence": 1.0,
                "match_type": "exact",
                "registered_state": exact_match.get("registered_state"),
                "company_status": exact_match.get("company_status"),
                "candidate_count": 1
            }

        # ── Stage 3: FTS5 Candidate Retrieval (Fast SQLite Prefix Match) ──
        fts_candidates = self.db.search_fts5(query_tokens, limit=FTS5_CANDIDATE_LIMIT)
        if not fts_candidates:
            # Try single character prefix if query token has at least 3 chars
            if query_tokens:
                fts_candidates = self.db.search_fts5([query_tokens[0][:4]], limit=FTS5_CANDIDATE_LIMIT)

        if not fts_candidates:
            return {
                "matched": False,
                "company_name": None,
                "cin": None,
                "confidence": 0.0,
                "match_type": "unknown_company",
                "candidates": []
            }

        # ── Stage 4: RapidFuzz Re-Ranking on Candidates ONLY ──
        scored_candidates = []
        for cand in fts_candidates:
            cand_norm = cand["normalized_name"]
            
            # Compute multiple fuzzy metrics
            ratio_score = fuzz.ratio(normalized_query, cand_norm)
            wratio_score = fuzz.WRatio(normalized_query, cand_norm)
            token_sort_score = fuzz.token_sort_ratio(normalized_query, cand_norm)
            token_set_score = fuzz.token_set_ratio(normalized_query, cand_norm)
            partial_score = fuzz.partial_ratio(normalized_query, cand_norm)

            # Check primary brand word (first word) for single-word queries
            first_word_score = 0.0
            cand_words = cand_norm.split()
            if cand_words:
                first_word_score = fuzz.ratio(normalized_query, cand_words[0])

            # Composite similarity score (0 to 100)
            composite_score = max(
                ratio_score,
                wratio_score,
                token_sort_score * 0.95,
                token_set_score * 0.90,
                partial_score * 0.95 if len(normalized_query) >= 5 else 0,
                first_word_score
            )

            scored_candidates.append({
                "company_name": cand["company_name"],
                "normalized_name": cand["normalized_name"],
                "cin": cand["cin"],
                "registered_state": cand.get("registered_state"),
                "company_status": cand.get("company_status"),
                "similarity": round(composite_score, 2),
                "confidence": round(composite_score / 100.0, 3)
            })

        # Sort candidates by similarity descending
        scored_candidates.sort(key=lambda x: x["similarity"], reverse=True)
        top_candidates = scored_candidates[:3]
        best = top_candidates[0] if top_candidates else None

        if not best:
            return {
                "matched": False,
                "company_name": None,
                "cin": None,
                "confidence": 0.0,
                "match_type": "unknown_company",
                "candidates": []
            }

        best_conf = best["confidence"]

        # ── Stage 5: Confidence Thresholding ──
        if best_conf >= CONFIDENCE_HIGH:
            return {
                "matched": True,
                "company_name": best["company_name"],
                "cin": best["cin"],
                "confidence": best_conf,
                "match_type": "fuzzy_high",
                "similarity": best["similarity"],
                "candidate_count": len(fts_candidates),
                "registered_state": best.get("registered_state"),
                "candidates": top_candidates
            }
        elif best_conf >= CONFIDENCE_MEDIUM:
            return {
                "matched": True,
                "company_name": best["company_name"],
                "cin": best["cin"],
                "confidence": best_conf,
                "match_type": "fuzzy_medium",
                "similarity": best["similarity"],
                "candidate_count": len(fts_candidates),
                "registered_state": best.get("registered_state"),
                "candidates": top_candidates
            }
        else:
            return {
                "matched": False,
                "company_name": None,
                "cin": None,
                "confidence": best_conf,
                "match_type": "uncertain",
                "similarity": best["similarity"],
                "candidate_count": len(fts_candidates),
                "candidates": top_candidates
            }

    def find_company(self, ocr_text: str) -> Dict[str, Any]:
        """
        Main entry point: find genuine registered company entity from OCR text.
        Tests candidate phrases extracted from the text in order of relevance.
        """
        if not ocr_text:
            return {
                "matched": False,
                "company_name": None,
                "cin": None,
                "confidence": 0.0,
                "match_type": "empty_input",
                "candidates": []
            }

        candidates = self._extract_candidate_phrases(ocr_text)
        best_result = None

        for cand in candidates:
            res = self.resolve_candidate(cand)
            if res.get("matched") and res.get("confidence", 0) >= CONFIDENCE_MEDIUM:
                return res
            if not best_result or res.get("confidence", 0) > best_result.get("confidence", 0):
                best_result = res

        return best_result or {
            "matched": False,
            "company_name": None,
            "cin": None,
            "confidence": 0.0,
            "match_type": "unknown_company",
            "candidates": []
        }
