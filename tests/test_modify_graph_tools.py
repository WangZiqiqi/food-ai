import json
import os
import pickle
import subprocess
import sys
from pathlib import Path

import networkx as nx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODIFY_GRAPH = (
    PROJECT_ROOT
    / ".agent-skills"
    / "kg-refiner"
    / ".claude"
    / "skills"
    / "kg-refiner"
    / "scripts"
    / "modify_graph.py"
)


def run_modify_graph(tmp_path, *args):
    env = os.environ.copy()
    env["FOOD_AI_REFINER_KG_PATH"] = str(tmp_path / "graph.pkl")
    result = subprocess.run(
        [sys.executable, str(MODIFY_GRAPH), *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_modify_graph_retype_preserves_claim_edges(tmp_path):
    graph_path = tmp_path / "graph.pkl"
    graph = nx.DiGraph()
    graph.add_node("food_male_sex", node_type="food", entity_type="food", name="male_sex")
    graph.add_node(
        "claim_1",
        node_type="claim",
        subject_name="male_sex",
        subject_type="food",
        object_name="cholesterol",
        object_type="outcome",
        direction="neutral",
    )
    graph.add_node("outcome_cholesterol", node_type="outcome", entity_type="outcome", name="cholesterol")
    graph.add_edge("food_male_sex", "claim_1")
    graph.add_edge("claim_1", "outcome_cholesterol")
    pickle.dump(graph, open(graph_path, "wb"))

    result = run_modify_graph(tmp_path, "retype", "male_sex", "food", "population")

    updated = pickle.load(open(graph_path, "rb"))
    assert result["success"] is True
    assert "food_male_sex" not in updated.nodes
    assert "population_male_sex" in updated.nodes
    assert updated.has_edge("population_male_sex", "claim_1")
    assert updated.nodes["claim_1"]["subject_type"] == "population"


def test_modify_graph_delete_orphan_removes_disconnected_entity(tmp_path):
    graph_path = tmp_path / "graph.pkl"
    graph = nx.DiGraph()
    graph.add_node("food_placeholder", node_type="food", entity_type="food", name="placeholder")
    pickle.dump(graph, open(graph_path, "wb"))

    result = run_modify_graph(tmp_path, "delete_orphan", "placeholder", "food")

    updated = pickle.load(open(graph_path, "rb"))
    assert result["success"] is True
    assert "food_placeholder" not in updated.nodes


def test_modify_graph_set_name_updates_display_name_and_claim_text(tmp_path):
    graph_path = tmp_path / "graph.pkl"
    graph = nx.DiGraph()
    graph.add_node("strain_bifidobacterium_infantis", node_type="strain", entity_type="strain", name="bifidobacterium_infantis")
    graph.add_node(
        "claim_1",
        node_type="claim",
        subject_name="bifidobacterium_infantis",
        subject_type="strain",
        object_name="gut_health",
        object_type="outcome",
        direction="positive",
    )
    graph.add_edge("strain_bifidobacterium_infantis", "claim_1")
    pickle.dump(graph, open(graph_path, "wb"))

    result = run_modify_graph(tmp_path, "set_name", "bifidobacterium_infantis", "strain", "Bifidobacterium infantis")

    updated = pickle.load(open(graph_path, "rb"))
    assert result["success"] is True
    assert updated.nodes["strain_bifidobacterium_infantis"]["display_name"] == "Bifidobacterium infantis"
    assert updated.nodes["claim_1"]["subject_name"] == "Bifidobacterium infantis"


def test_modify_graph_mark_out_of_scope_flags_connected_claims(tmp_path):
    graph_path = tmp_path / "graph.pkl"
    graph = nx.DiGraph()
    graph.add_node("food_caffeine", node_type="food", entity_type="food", name="caffeine")
    graph.add_node(
        "claim_1",
        node_type="claim",
        subject_name="caffeine",
        subject_type="food",
        object_name="performance",
        object_type="outcome",
        direction="positive",
    )
    graph.add_edge("food_caffeine", "claim_1")
    pickle.dump(graph, open(graph_path, "wb"))

    result = run_modify_graph(tmp_path, "mark_out_of_scope", "caffeine", "food", "domain_drift")

    updated = pickle.load(open(graph_path, "rb"))
    assert result["success"] is True
    assert updated.nodes["food_caffeine"]["quality_status"] == "out_of_scope"
    assert updated.nodes["claim_1"]["quality_flags"] == ["entity_out_of_scope:food:caffeine"]
