"""
Role detector that integrates with the hierarchical RoleTaxonomy.
"""
from typing import List
from ..schema.job_schema import RoleResult
from ..taxonomy.role_taxonomy import RoleTaxonomyResolver


class RoleDetector:
    @staticmethod
    def detect_roles(text: str) -> List[RoleResult]:
        """Extract all matching roles from OCR text."""
        raw_roles = RoleTaxonomyResolver.find_all_roles(text)
        results = []
        for r in raw_roles:
            results.append(
                RoleResult(
                    name=r["name"],
                    canonical=r["canonical"],
                    category=r["category"],
                    sector=r["sector"],
                    confidence=r["confidence"]
                )
            )
        return results
