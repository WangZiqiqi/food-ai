from food_ai.batch_review import compare_extraction_batches
from food_ai.build_quality import summarize_extraction_quality
from food_ai.entity_validator import EntityValidator
from food_ai.refine_candidates import (
    extract_refine_candidates_from_review,
    select_refine_candidates,
)


def test_food_validator_rejects_non_food_placeholders():
    validator = EntityValidator()

    result = validator.validate_food_name("male_sex")

    assert result.is_valid is False
    assert result.entity_type == "food"


def test_batch_quality_report_flags_suspicious_foods_and_warnings():
    payload = {
        "total": 2,
        "success": 2,
        "error": 0,
        "merged_claims_count": 2,
        "results": [
            {
                "pmid": "1",
                "success": True,
                "warnings": ["Skipped suspicious food entity 'male_sex'"],
                "claims": [],
            },
            {
                "pmid": "2",
                "success": True,
                "warnings": [],
                "claims": [{"subject": "yogurt", "object": "cholesterol", "direction": "positive"}],
            },
        ],
        "merged_claims": [
            {
                "claim_id": "c1",
                "subject_type": "food",
                "subject_name": "male_sex",
                "object_type": "outcome",
                "object_name": "cholesterol",
            },
            {
                "claim_id": "c2",
                "subject_type": "food",
                "subject_name": "black_tea_10_percent_kombucha",
                "object_type": "outcome",
                "object_name": "glucose",
            },
        ],
    }

    report = summarize_extraction_quality(payload)

    assert report["summary"]["articles_with_warnings"] == 1
    assert report["summary"]["suspicious_food_entities"] == 1
    assert report["summary"]["over_specific_food_entities"] == 1
    assert report["review_recommendation"]["should_run_batch_review"] is True


def test_batch_delta_review_detects_new_suspicious_entities():
    baseline_payload = {
        "total": 1,
        "success": 1,
        "error": 0,
        "merged_claims_count": 1,
        "results": [{"pmid": "1", "success": True, "warnings": [], "claims": [{"subject": "yogurt"}]}],
        "merged_claims": [
            {
                "claim_id": "c1",
                "subject_type": "food",
                "subject_name": "yogurt",
                "object_type": "outcome",
                "object_name": "cholesterol",
            }
        ],
    }
    current_payload = {
        "total": 2,
        "success": 2,
        "error": 0,
        "merged_claims_count": 2,
        "results": [
            {"pmid": "1", "success": True, "warnings": [], "claims": [{"subject": "yogurt"}]},
            {"pmid": "2", "success": True, "warnings": [], "claims": [{"subject": "male_sex"}]},
        ],
        "merged_claims": [
            {
                "claim_id": "c1",
                "subject_type": "food",
                "subject_name": "yogurt",
                "object_type": "outcome",
                "object_name": "cholesterol",
            },
            {
                "claim_id": "c2",
                "subject_type": "food",
                "subject_name": "male_sex",
                "object_type": "outcome",
                "object_name": "glucose",
            },
        ],
    }

    report = compare_extraction_batches(current_payload=current_payload, baseline_payload=baseline_payload)

    assert report["delta_summary"]["new_claims"] == 1
    assert report["delta_summary"]["new_foods"] == 1
    assert report["newly_suspicious_foods"] == ["male_sex"]
    assert report["review_recommendation"]["should_run_batch_review"] is True


def test_refine_candidate_extraction_and_selection():
    review_raw = """
## Issues Found

### ISSUE-001: [duplicate] - kombucha
- **Severity**: major
- **Entity**: kombucha (food)
- **Current State**: duplicate variants exist
- **Expected State**: use one canonical food node
- **Evidence**: string overlap and same neighbor pattern
- **PMIDs Affected**: 123, 456
- **Suggested Action**: merge
- **Confidence**: high

### ISSUE-002: [naming] - male_sex
- **Severity**: critical
- **Entity**: male_sex (food)
- **Current State**: placeholder is classified as food
- **Expected State**: should not stay as a food node
- **Evidence**: blacklist match
- **PMIDs Affected**: 789
- **Suggested Action**: preserve
- **Confidence**: high
"""

    candidates = extract_refine_candidates_from_review(review_raw)
    selected = select_refine_candidates(candidates, limit=1)

    assert len(candidates) == 2
    assert candidates[0]["issue_id"] == "ISSUE-001"
    assert candidates[0]["suggested_action"] == "merge"
    assert candidates[1]["entity_name"] == "male_sex"
    assert selected[0]["issue_id"] == "ISSUE-001"


def test_refine_candidate_action_normalizes_retype_and_delete_orphan():
    review_raw = """
### ISSUE-001: [misclassification] - male_sex
- **Severity**: critical
- **Entity**: male_sex (food)
- **Suggested Action**: update_type
- **Confidence**: high

### ISSUE-002: [orphan] - placeholder
- **Severity**: minor
- **Entity**: placeholder (food)
- **Suggested Action**: delete orphan
- **Confidence**: high

### ISSUE-003: [naming] - bifidobacterium_infantis
- **Severity**: minor
- **Entity**: bifidobacterium_infantis (strain)
- **Suggested Action**: title case
- **Confidence**: high

### ISSUE-004: [domain] - caffeine
- **Severity**: major
- **Entity**: caffeine (food)
- **Suggested Action**: mark out of scope
- **Confidence**: high
"""

    candidates = extract_refine_candidates_from_review(review_raw)

    assert candidates[0]["suggested_action"] == "retype"
    assert candidates[0]["raw_suggested_action"] == "update_type"
    assert candidates[1]["suggested_action"] == "delete_orphan"
    assert candidates[2]["suggested_action"] == "set_name"
    assert candidates[3]["suggested_action"] == "mark_out_of_scope"
