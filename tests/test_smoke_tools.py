import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KG_EXPLORER = PROJECT_ROOT / ".agent-skills" / "kg-explorer" / ".claude" / "skills" / "kg-explorer" / "scripts"
KG_REFINER = PROJECT_ROOT / ".agent-skills" / "kg-refiner" / ".claude" / "skills" / "kg-refiner" / "scripts"


def run_json_script(script_path: Path, *args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_get_claim_details_smoke():
    data = run_json_script(KG_EXPLORER / "get_claim_details.py", "407221a36b7d")
    assert data["found"] is True
    assert data["subject"]["name"] == "yogurt"
    assert data["object"]["name"] == "ldl_cholesterol"


def test_vector_search_lexical_smoke():
    data = run_json_script(
        KG_EXPLORER / "vector_search.py",
        "yogurt effect on diabetes",
        "--top_k",
        "3",
        "--mode",
        "lexical",
    )
    assert data["search_mode"] == "lexical_fallback"
    assert len(data["results"]) == 3


def test_explore_neighbors_smoke():
    data = run_json_script(
        KG_EXPLORER / "explore_neighbors.py",
        "yogurt",
        "food",
        "--direction",
        "subject",
    )
    assert data["entity"] == "yogurt"
    assert data["as_subject_count"] >= 1


def test_search_entities_smoke():
    data = run_json_script(
        KG_EXPLORER / "search_entities.py",
        "yogurt",
        "--top-k",
        "5",
    )
    assert len(data["results"]) >= 1
    assert any(item["name"] == "yogurt" for item in data["results"])


def test_search_by_pmid_smoke():
    data = run_json_script(KG_EXPLORER / "search_by_pmid.py", "21289226")
    assert data["claim_count"] >= 1
    assert any("fasting_serum_glucose" in claim["claim_text"] for claim in data["claims"])


def test_compare_claims_smoke():
    data = run_json_script(
        KG_EXPLORER / "compare_claims.py",
        "407221a36b7d",
        "01e523949fe7",
    )
    assert data["found_claims"] == 2
    assert data["shared_object"] is True


def test_analyze_graph_smoke():
    data = run_json_script(KG_REFINER / "analyze_graph.py")
    assert data["total_nodes"] >= 800
    assert data["total_claims"] >= 400


def test_detect_issues_smoke():
    data = run_json_script(KG_REFINER / "detect_issues.py")
    assert "summary" in data
    assert data["summary"]["duplicate_candidates_count"] >= 0
