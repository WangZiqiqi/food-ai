"""
translated note
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class CompletenessLevel(Enum):
    """translated note"""
    COMPLETE = "complete"           # translated note
    PARTIAL = "partial"             # translated note
    MINIMAL = "minimal"             # translated note
    INSUFFICIENT = "insufficient"   # translated note


@dataclass
class ExtractionAssessment:
    """translated note"""
    pmid: str
    overall_level: CompletenessLevel
    
    # translated note
    has_strain_info: bool
    has_dose_info: bool
    has_duration_info: bool
    has_sample_size: bool
    has_effect_size: bool
    has_full_text: bool
    
    # translated note
    missing_fields: List[str]
    
    # translated note
    recommendation: str


def assess_claim_quality(claim: Dict[str, Any]) -> Dict[str, bool]:
    """translated note claim translated note"""
    return {
        "has_strain_info": claim.get("subject_name") and any(
            s in claim["subject_name"].lower() 
            for s in ["lactobacillus", "bifidobacterium", "streptococcus"]
        ),
        "has_dose_info": claim.get("dose") is not None,
        "has_duration_info": (
            claim.get("dose") and 
            claim["dose"].get("duration_days") is not None
        ),
        "has_effect_size": claim.get("effect_size") is not None,
        "has_p_value": claim.get("p_value") is not None,
    }


def assess_evidence_quality(evidence: Dict[str, Any]) -> Dict[str, bool]:
    """translated note"""
    return {
        "has_sample_size": evidence.get("sample_size") is not None,
        "has_study_type": (
            evidence.get("study_type") and 
            evidence["study_type"] != "unknown"
        ),
        "has_pmcid": evidence.get("pmcid") is not None,
        "has_funding_info": bool(evidence.get("funding_sources")),
    }


def assess_kg_quality(kg_dict: Dict[str, Any]) -> List[ExtractionAssessment]:
    """translated note
    
    Returns:
        translated note
    """
    assessments = []
    
    evidences = kg_dict.get("evidences", {})
    claims = kg_dict.get("claims", {})
    
    for pmid, evidence in evidences.items():
        # translated note claims
        article_claims = [
            c for c in claims.values() 
            if c.get("evidence_ref") == pmid
        ]
        
        # translated note evidence translated note
        evidence_quality = assess_evidence_quality(evidence)
        
        # translated note claims translated note
        claim_qualities = [assess_claim_quality(c) for c in article_claims]
        
        # translated note
        missing_fields = []
        
        if not evidence_quality["has_sample_size"]:
            missing_fields.append("sample_size")
        if not evidence_quality["has_study_type"]:
            missing_fields.append("study_type")
        if not evidence_quality["has_pmcid"]:
            missing_fields.append("pmcid/full_text")
            
        # translated note claims translated note
        has_strain_info = any(cq["has_strain_info"] for cq in claim_qualities) if claim_qualities else False
        has_dose_info = any(cq["has_dose_info"] for cq in claim_qualities) if claim_qualities else False
        has_duration_info = any(cq["has_duration_info"] for cq in claim_qualities) if claim_qualities else False
        has_effect_size = any(cq["has_effect_size"] for cq in claim_qualities) if claim_qualities else False
        
        if not has_strain_info:
            missing_fields.append("strain_details")
        if not has_dose_info:
            missing_fields.append("dose")
        if not has_duration_info:
            missing_fields.append("duration")
        
        # translated note
        score = 0
        if evidence_quality["has_sample_size"]: score += 1
        if evidence_quality["has_study_type"]: score += 1
        if evidence_quality["has_pmcid"]: score += 1
        if has_strain_info: score += 1
        if has_dose_info: score += 1
        if has_duration_info: score += 1
        if has_effect_size: score += 1
        
        if score >= 6:
            level = CompletenessLevel.COMPLETE
            recommendation = "translated note,translated note"
        elif score >= 4:
            level = CompletenessLevel.PARTIAL
            recommendation = "translated note,translated note"
        elif score >= 2:
            level = CompletenessLevel.MINIMAL
            recommendation = "translated note,translated note"
        else:
            level = CompletenessLevel.INSUFFICIENT
            recommendation = "translated note,translated note"
        
        assessment = ExtractionAssessment(
            pmid=pmid,
            overall_level=level,
            has_strain_info=has_strain_info,
            has_dose_info=has_dose_info,
            has_duration_info=has_duration_info,
            has_sample_size=evidence_quality["has_sample_size"],
            has_effect_size=has_effect_size,
            has_full_text=evidence_quality["has_pmcid"],
            missing_fields=missing_fields,
            recommendation=recommendation
        )
        
        assessments.append(assessment)
    
    return assessments


def print_assessment_report(assessments: List[ExtractionAssessment]):
    """translated note"""
    print("\n" + "=" * 60)
    print("translated note")
    print("=" * 60)
    
    for assessment in assessments:
        print(f"\nPMID: {assessment.pmid}")
        print(f"  translated note: {assessment.overall_level.value.upper()}")
        print(f"  translated note: {', '.join(assessment.missing_fields) if assessment.missing_fields else 'translated note'}")
        print(f"  translated note: {assessment.recommendation}")
        print(f"  translated note:")
        print(f"    - translated note: {'✓' if assessment.has_strain_info else '✗'}")
        print(f"    - translated note: {'✓' if assessment.has_dose_info else '✗'}")
        print(f"    - translated note: {'✓' if assessment.has_duration_info else '✗'}")
        print(f"    - translated note: {'✓' if assessment.has_sample_size else '✗'}")
        print(f"    - translated note: {'✓' if assessment.has_effect_size else '✗'}")
        print(f"    - translated note: {'✓' if assessment.has_full_text else '✗'}")
    
    # translated note
    print("\n" + "-" * 60)
    print("translated note:")
    total = len(assessments)
    complete = sum(1 for a in assessments if a.overall_level == CompletenessLevel.COMPLETE)
    partial = sum(1 for a in assessments if a.overall_level == CompletenessLevel.PARTIAL)
    minimal = sum(1 for a in assessments if a.overall_level == CompletenessLevel.MINIMAL)
    insufficient = sum(1 for a in assessments if a.overall_level == CompletenessLevel.INSUFFICIENT)
    
    print(f"  translated note: {total} translated note")
    print(f"  translated note: {complete} ({complete/total*100:.1f}%)")
    print(f"  translated note: {partial} ({partial/total*100:.1f}%)")
    print(f"  translated note: {minimal} ({minimal/total*100:.1f}%)")
    print(f"  translated note: {insufficient} ({insufficient/total*100:.1f}%)")
    
    # translated note
    need_full_text = [a.pmid for a in assessments if not a.has_full_text and a.missing_fields]
    if need_full_text:
        print(f"\n  translated note: {', '.join(need_full_text)}")
    
    print("=" * 60)
