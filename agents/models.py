"""
KG Refinement Pipeline - Pydantic Models
translated note pydantic-ai translated note
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class Issue(BaseModel):
    """translated note"""
    issue_id: str = Field(description="translated note,translated note ISSUE-001")
    type: Literal[
        "misclassification",
        "duplicate",
        "over_specific",
        "experimental_condition",
        "naming",
        "conflict",
        "other"
    ] = Field(description="translated note")
    severity: Literal["critical", "major", "minor"] = Field(description="translated note")
    entity_name: str = Field(description="translated note")
    entity_type: str = Field(description="translated note")
    current_state: str = Field(description="translated note")
    expected_state: str = Field(description="translated note")
    evidence: str = Field(description="translated note")
    pmids_affected: List[str] = Field(default_factory=list, description="translated notePMIDtranslated note")
    suggested_action: Literal["merge", "rename", "delete", "update_type", "normalize", "review"] = Field(
        description="translated note"
    )
    action_details: Optional[dict] = Field(default=None, description="translated note")
    confidence: Literal["high", "medium", "low"] = Field(description="translated note")


class Pattern(BaseModel):
    """translated note"""
    pattern: str = Field(description="translated note")
    affected_entities: List[str] = Field(description="translated note")
    recommendation: str = Field(description="translated note")


class ReviewSummary(BaseModel):
    """translated note"""
    total_nodes: int = Field(description="translated note")
    total_claims: int = Field(description="claim translated note")
    overall_health: Literal["good", "fair", "poor"] = Field(description="translated note")
    critical_issues_count: int = Field(description="translated note")
    major_issues_count: int = Field(description="translated note")
    minor_issues_count: int = Field(description="translated note")


class Statistics(BaseModel):
    """translated note"""
    misclassifications: int = Field(default=0)
    duplicates: int = Field(default=0)
    over_specific_variants: int = Field(default=0)
    conflicts: int = Field(default=0)
    naming_issues: int = Field(default=0)


class ReviewReport(BaseModel):
    """translated note - translated note pydantic-ai result_type"""
    review_summary: ReviewSummary = Field(description="translated note")
    issues: List[Issue] = Field(default_factory=list, description="translated note")
    patterns_identified: List[Pattern] = Field(default_factory=list, description="translated note")
    statistics: Statistics = Field(default_factory=Statistics, description="translated note")


class RefinementDecision(BaseModel):
    """translated note"""
    needs_refinement: bool = Field(description="translated note")
    priority: Optional[Literal["P0", "P1", "P2", "none"]] = Field(default="none", description="translated note")
    reasoning: str = Field(description="translated note")
    auto_fixable: bool = Field(description="translated note")
    issues_to_fix: List[str] = Field(default_factory=list, description="translated noteissue_idtranslated note")
    issues_to_skip: List[str] = Field(default_factory=list, description="translated noteissue_idtranslated note")


class FixedIssue(BaseModel):
    """translated note"""
    issue_id: str = Field(description="translated noteID")
    action_taken: str = Field(description="translated note")
    result: Literal["success", "failed", "partial"] = Field(description="translated note")
    backup_file: Optional[str] = Field(default=None, description="translated note")
    details: str = Field(description="translated note")


class RefinementReport(BaseModel):
    """translated note"""
    analysis_summary: str = Field(description="translated note")
    issues_fixed: List[FixedIssue] = Field(default_factory=list, description="translated note")
    verification: str = Field(description="translated note")
    remaining_issues: str = Field(description="translated note")
