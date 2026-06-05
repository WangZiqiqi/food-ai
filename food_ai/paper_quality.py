#!/usr/bin/env python3
"""
PubMed translated note - translated note
translated note
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import re
from pathlib import Path

from food_ai.sjr_loader import SJRJournalData


class StudyTypeScore(Enum):
    """translated note"""
    RCT = 10                    # translated note (translated note)
    META_ANALYSIS = 10          # Meta translated note
    SYSTEMATIC_REVIEW = 9       # translated note
    COHORT = 7                  # translated note
    CASE_CONTROL = 6            # translated note
    CROSS_SECTIONAL = 5         # translated note
    OBSERVATIONAL = 5           # translated note
    REVIEW = 4                  # translated note
    CASE_REPORT = 3             # translated note
    IN_VITRO = 2                # translated note
    ANIMAL_STUDY = 2            # translated note
    UNKNOWN = 0


@dataclass
class QualityMetrics:
    """translated note"""
    # translated note (25%)
    study_type_score: float = 0.0
    study_type_detail: str = "unknown"
    
    # translated note (20%)
    sample_size_score: float = 0.0
    sample_size: int = 0
    
    # translated note (20%)
    journal_score: float = 0.0
    journal_tier: str = "unknown"  # top, high, medium, low
    
    # translated note (15%)
    institution_score: float = 0.0
    top_institution_count: int = 0
    
    # translated note (20%)
    funding_score: float = 0.0
    funding_type: str = "unknown"  # government, non_profit, industry, mixed, none
    
    # translated note (0-10)
    total_score: float = 0.0
    
    # translated note
    grade: str = "F"  # A+, A, A-, B+, B, B-, C+, C, C-, D, F
    
    def to_dict(self) -> Dict[str, Any]:
        """translated note"""
        return {
            "study_type_score": self.study_type_score,
            "study_type_detail": self.study_type_detail,
            "sample_size_score": self.sample_size_score,
            "sample_size": self.sample_size,
            "journal_score": self.journal_score,
            "journal_tier": self.journal_tier,
            "institution_score": self.institution_score,
            "top_institution_count": self.top_institution_count,
            "funding_score": self.funding_score,
            "funding_type": self.funding_type,
            "total_score": round(self.total_score, 2),
            "grade": self.grade
        }


class PaperQualityAssessor:
    """
    translated note - translated note
    
    translated note:
    1. translated note (25%): translated note
    2. translated note (20%): translated note
    3. translated note (20%): translated note
    4. translated note (15%): translated note
    5. translated note (20%): translated note
    """
    
    # translated note
    WEIGHTS = {
        "study_type": 0.25,
        "sample_size": 0.20,
        "journal": 0.20,
        "institution": 0.15,
        "funding": 0.20
    }
    
    # translated note (translated note)
    JOURNAL_TIERS = {
        # translated note (IF > 20 translated note)
        "top": {
            "journals": {
                "Nature", "Science", "Cell", "Lancet", "NEJM", "JAMA", "BMJ",
                "Nature Medicine", "Nature Food", "Nature Microbiology",
                "Cell Metabolism", "Gut", "Microbiome", "Diabetes Care"
            },
            "score": 10.0
        },
        # translated note (IF 10-20)
        "high": {
            "journals": {
                "American Journal of Clinical Nutrition", "Journal of Nutrition",
                "Clinical Nutrition", "Nutrition Reviews", "Obesity Reviews",
                "Diabetologia", "Diabetes", "Gastroenterology",
                "American Journal of Gastroenterology", "Alimentary Pharmacology & Therapeutics"
            },
            "score": 8.0
        },
        # translated note (IF 5-10)
        "medium": {
            "journals": {
                "Nutrients", "Food & Function", "Journal of Functional Foods",
                "Beneficial Microbes", "Journal of Dairy Science",
                "European Journal of Nutrition", "Nutrition Journal"
            },
            "score": 6.0
        }
    }
    
    # translated note (translated note)
    TOP_INSTITUTIONS = {
        # translated note
        "Harvard", "MIT", "Stanford", "Johns Hopkins", "UCSF", "UCLA", "Yale",
        "Princeton", "Columbia", "University of Pennsylvania", "Cornell",
        "University of Michigan", "University of Washington", "Duke",
        "University of California", "UC ", "Mayo Clinic", "Cleveland Clinic",
        # translated note
        "Oxford", "Cambridge", "Imperial College", "UCL", "King's College",
        "University of Edinburgh", "University of Manchester",
        # translated note
        "ETH Zurich", "Karolinska", "University of Copenhagen",
        "Max Planck", "Pasteur Institute",
        # translated note
        "Chinese Academy of Sciences", "Tsinghua", "Peking University",
        "Fudan", "Zhejiang University", "Shanghai Jiao Tong", "Nanjing University",
        "University of Chinese Academy of Sciences", "China Agricultural University",
        # translated note
        "University of Tokyo", "Kyoto University", "Osaka University",
        # translated note
        "University of Toronto", "McGill", "University of Melbourne",
        "University of Sydney", "National University of Singapore"
    }
    
    # translated note
    FUNDING_CATEGORIES = {
        "government": {
            "keywords": [
                "NIH", "NSF", "USDA", "CDC", "FDA", "HHS",
                "National Natural Science Foundation of China", "NSFC",
                "National Key Research", "Ministry of Science",
                "MRC", "Wellcome Trust", "ERC", "Horizon Europe",
                "Japan Society for the Promotion", "JSPS",
                "Canadian Institutes of Health", "CIHR",
                "Australian Research Council", "ARC",
                "Medical Research Council", "Biotechnology and Biological Sciences"
            ],
            "score": 10.0,
            "type": "government"
        },
        "non_profit": {
            "keywords": [
                "Foundation", "Society", "Association", "Trust",
                "Bill & Melinda Gates", "Howard Hughes",
                "American Heart Association", "Diabetes Association",
                "Cancer Research", "Alzheimer's Association"
            ],
            "score": 8.0,
            "type": "non_profit"
        },
        "industry": {
            "keywords": [
                "Inc.", "Corp.", "Corporation", "Ltd.", "Limited",
                "Company", "Pharma", "Pharmaceutical", "Biotech",
                "Dairy", "Yogurt", "Probiotic", "Industry", "Commercial"
            ],
            "score": 3.0,
            "type": "industry"
        },
        "academic": {
            "keywords": [
                "University", "College", "Institute", "Research Center",
                "Scholarship", "Fellowship"
            ],
            "score": 7.0,
            "type": "academic"
        }
    }
    
    def __init__(self, sjr_data: Optional[SJRJournalData] = None):
        self.metrics_cache: Dict[str, QualityMetrics] = {}
        # translated note SJR translated note(translated note,translated note)
        self.sjr_data = sjr_data if sjr_data else SJRJournalData()
    
    def assess(self, article: Dict[str, Any]) -> QualityMetrics:
        """
        translated note
        """
        pmid = article.get("pmid", "unknown")
        
        # 1. translated note
        study_type_score, study_type_detail = self._score_study_type(article)
        
        # 2. translated note
        sample_size_score, sample_size = self._score_sample_size(article)
        
        # 3. translated note
        journal_score, journal_tier = self._score_journal(article)
        
        # 4. translated note
        institution_score, top_count = self._score_institution(article)
        
        # 5. translated note
        funding_score, funding_type = self._score_funding(article)
        
        # translated note
        total_score = (
            study_type_score * self.WEIGHTS["study_type"] +
            sample_size_score * self.WEIGHTS["sample_size"] +
            journal_score * self.WEIGHTS["journal"] +
            institution_score * self.WEIGHTS["institution"] +
            funding_score * self.WEIGHTS["funding"]
        )
        
        # translated note
        grade = self._score_to_grade(total_score)
        
        metrics = QualityMetrics(
            study_type_score=study_type_score,
            study_type_detail=study_type_detail,
            sample_size_score=sample_size_score,
            sample_size=sample_size,
            journal_score=journal_score,
            journal_tier=journal_tier,
            institution_score=institution_score,
            top_institution_count=top_count,
            funding_score=funding_score,
            funding_type=funding_type,
            total_score=total_score,
            grade=grade
        )
        
        self.metrics_cache[pmid] = metrics
        return metrics
    
    def _score_study_type(self, article: Dict) -> tuple:
        """translated note (0-10) + translated note"""
        pub_types = article.get("publication_types", [])
        type_names = [pt.get("name", "").lower() for pt in pub_types]
        
        # translated note
        if any("randomized controlled trial" in t for t in type_names):
            return StudyTypeScore.RCT.value, "RCT"
        elif any("meta-analysis" in t for t in type_names):
            return StudyTypeScore.META_ANALYSIS.value, "Meta-analysis"
        elif any("systematic review" in t for t in type_names):
            return StudyTypeScore.SYSTEMATIC_REVIEW.value, "Systematic review"
        elif any("cohort" in t for t in type_names):
            return StudyTypeScore.COHORT.value, "Cohort study"
        elif any("case-control" in t for t in type_names):
            return StudyTypeScore.CASE_CONTROL.value, "Case-control study"
        elif any("cross-sectional" in t for t in type_names):
            return StudyTypeScore.CROSS_SECTIONAL.value, "Cross-sectional"
        elif any("review" in t for t in type_names):
            return StudyTypeScore.REVIEW.value, "Review"
        elif any("case report" in t for t in type_names):
            return StudyTypeScore.CASE_REPORT.value, "Case report"
        elif any("in vitro" in t for t in type_names):
            return StudyTypeScore.IN_VITRO.value, "In vitro"
        elif any("animal" in t for t in type_names):
            return StudyTypeScore.ANIMAL_STUDY.value, "Animal study"
        
        return StudyTypeScore.UNKNOWN.value, "Unknown"
    
    def _score_sample_size(self, article: Dict) -> tuple:
        """translated note (0-10) + translated note"""
        abstract = article.get("abstract", "")
        title = article.get("title", "")
        
        # translated note
        patterns = [
            r'[nN]\s*=\s*(\d{2,})',
            r'(\d{2,})\s*(?:subjects|participants|patients|volunteers|individuals)',
            r'total\s+of\s+(\d{2,})',
            r'(\d{2,})\s+(?:men|women|children|adults|subjects)',
            r'enrolled\s+(\d{2,})',
            r'recruited\s+(\d{2,})',
            r'sample\s+size\s+(?:of\s+)?(\d{2,})',
        ]
        
        sample_size = 0
        text_to_search = f"{title} {abstract}"
        
        for pattern in patterns:
            matches = re.findall(pattern, text_to_search, re.IGNORECASE)
            if matches:
                # translated note(translated note)
                sizes = [int(m) for m in matches if int(m) < 100000]  # translated note
                if sizes:
                    sample_size = max(sizes)
                    break
        
        # translated note
        study_type = self._detect_study_type(article)
        
        if study_type in ["RCT", "Meta-analysis", "Systematic review"]:
            # translated note,translated note
            if sample_size >= 1000:
                return 10.0, sample_size
            elif sample_size >= 500:
                return 9.0, sample_size
            elif sample_size >= 200:
                return 8.0, sample_size
            elif sample_size >= 100:
                return 7.0, sample_size
            elif sample_size >= 50:
                return 5.0, sample_size
            elif sample_size > 0:
                return 3.0, sample_size
        else:
            # translated note
            if sample_size >= 500:
                return 10.0, sample_size
            elif sample_size >= 200:
                return 8.0, sample_size
            elif sample_size >= 100:
                return 7.0, sample_size
            elif sample_size >= 50:
                return 5.0, sample_size
            elif sample_size > 0:
                return 3.0, sample_size
        
        return 0.0, sample_size
    
    def _detect_study_type(self, article: Dict) -> str:
        """translated note"""
        pub_types = article.get("publication_types", [])
        type_names = [pt.get("name", "").lower() for pt in pub_types]
        
        if any("randomized" in t for t in type_names):
            return "RCT"
        elif any("meta-analysis" in t for t in type_names):
            return "Meta-analysis"
        elif any("systematic review" in t for t in type_names):
            return "Systematic review"
        return "Other"
    
    def _score_journal(self, article: Dict) -> tuple:
        """translated note (0-10) + translated note - translated note SJR translated note"""
        journal = article.get("journal", "")
        
        if not journal:
            return 0.0, "unknown"
        
        # translated note SJR translated note
        score, tier, sjr_value = self.sjr_data.get_score(journal)
        
        # translated note SJR translated note article translated note
        article['_sjr_value'] = sjr_value
        
        return score, tier
    
    def _score_institution(self, article: Dict) -> tuple:
        """translated note (0-10) + translated note"""
        # translated note
        authors_full = article.get("authors_full", [])
        all_affiliations = []
        
        for author in authors_full:
            affils = author.get("affiliations", [])
            all_affiliations.extend(affils)
        
        # translated note
        if not all_affiliations:
            all_affiliations = article.get("author_affiliations", [])
        
        if not all_affiliations:
            return 0.0, 0
        
        # translated note
        top_count = 0
        for affil in all_affiliations:
            for inst in self.TOP_INSTITUTIONS:
                if inst.lower() in affil.lower():
                    top_count += 1
                    break
        
        # translated note
        if top_count >= 5:
            return 10.0, top_count
        elif top_count >= 3:
            return 9.0, top_count
        elif top_count >= 2:
            return 8.0, top_count
        elif top_count >= 1:
            return 6.0, top_count
        else:
            return 3.0, top_count
    
    def _score_funding(self, article: Dict) -> tuple:
        """translated note (0-10) + translated note"""
        grants = article.get("grants", [])
        
        if not grants:
            return 5.0, "none"  # translated note
        
        # translated note
        categories = {"government": 0, "non_profit": 0, "industry": 0, "academic": 0}
        
        for grant in grants:
            agency = grant.get("agency", "")
            agency_lower = agency.lower()
            
            for category, info in self.FUNDING_CATEGORIES.items():
                for keyword in info["keywords"]:
                    if keyword.lower() in agency_lower:
                        categories[category] += 1
                        break
        
        # translated note
        total = sum(categories.values())
        if total == 0:
            return 5.0, "unknown"
        
        # translated note,translated note
        if categories["industry"] > 0:
            if categories["government"] > 0 or categories["non_profit"] > 0:
                # translated note,translated note
                return 6.0, "mixed"
            else:
                # translated note
                return 3.0, "industry"
        
        # translated note
        if categories["government"] > 0:
            return 10.0, "government"
        
        # translated note
        if categories["non_profit"] > 0:
            return 8.0, "non_profit"
        
        # translated note
        if categories["academic"] > 0:
            return 7.0, "academic"
        
        return 5.0, "unknown"
    
    def _score_to_grade(self, score: float) -> str:
        """translated note (translated note)"""
        if score >= 9.0:
            return "A+"
        elif score >= 8.5:
            return "A"
        elif score >= 8.0:
            return "A-"
        elif score >= 7.5:
            return "B+"
        elif score >= 7.0:
            return "B"
        elif score >= 6.5:
            return "B-"
        elif score >= 6.0:
            return "C+"
        elif score >= 5.5:
            return "C"
        elif score >= 5.0:
            return "C-"
        elif score >= 3.0:
            return "D"
        else:
            return "F"
    
    def should_include(self, article: Dict, min_grade: str = "C") -> bool:
        """translated note"""
        metrics = self.assess(article)
        
        grade_order = {
            "A+": 12, "A": 11, "A-": 10,
            "B+": 9, "B": 8, "B-": 7,
            "C+": 6, "C": 5, "C-": 4,
            "D": 3, "F": 2
        }
        
        return grade_order.get(metrics.grade, 0) >= grade_order.get(min_grade, 5)
    
    def batch_assess(self, articles: List[Dict]) -> List[Dict]:
        """translated note"""
        results = []
        for article in articles:
            metrics = self.assess(article)
            article["quality_metrics"] = metrics.to_dict()
            results.append(article)
        
        # translated note
        results.sort(key=lambda x: x["quality_metrics"]["total_score"], reverse=True)
        return results


def filter_by_quality(articles: List[Dict], min_grade: str = "C", min_score: float = 0.0) -> List[Dict]:
    """translated note"""
    assessor = PaperQualityAssessor()
    filtered = []
    
    for article in articles:
        metrics = assessor.assess(article)
        
        if assessor.should_include(article, min_grade) and metrics.total_score >= min_score:
            article["quality_metrics"] = metrics.to_dict()
            filtered.append(article)
    
    filtered.sort(key=lambda x: x["quality_metrics"]["total_score"], reverse=True)
    return filtered


if __name__ == "__main__":
    # translated note
    test_article = {
        "pmid": "123456",
        "title": "Test Article",
        "publication_types": [{"name": "Randomized Controlled Trial"}],
        "abstract": "A total of 250 subjects were enrolled in this study.",
        "journal": "Nature Medicine",
        "authors_full": [
            {"name": "John Doe", "affiliations": ["Harvard Medical School"]}
        ],
        "grants": [{"agency": "NIH", "grant_id": "R01DK12345"}]
    }
    
    assessor = PaperQualityAssessor()
    metrics = assessor.assess(test_article)
    
    print("translated note:", metrics.study_type_score, f"({metrics.study_type_detail})")
    print("translated note:", metrics.sample_size_score, f"(n={metrics.sample_size})")
    print("translated note:", metrics.journal_score, f"({metrics.journal_tier})")
    print("translated note:", metrics.institution_score, f"(translated note: {metrics.top_institution_count})")
    print("translated note:", metrics.funding_score, f"({metrics.funding_type})")
    print("translated note:", metrics.total_score)
    print("translated note:", metrics.grade)
