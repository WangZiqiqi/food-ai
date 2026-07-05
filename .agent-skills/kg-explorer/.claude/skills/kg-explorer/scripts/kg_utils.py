#!/usr/bin/env python3
"""Shared utilities for inspecting the final Food-AI knowledge graph."""

import json
import pickle
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()

ENV_KG_PICKLE_PATH = os.getenv("FOOD_AI_KG_PICKLE_PATH")
ENV_KG_JSON_PATH = os.getenv("FOOD_AI_KG_JSON_PATH")
ENV_EMBEDDINGS_PATH = os.getenv("FOOD_AI_EMBEDDINGS_PATH")


def find_project_root() -> Path:
    """Find the repository root from this nested skill script path."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").exists() and (candidate / "data").exists():
            return candidate
    return Path.cwd()


PROJECT_ROOT = find_project_root()

# Default paper-facing graph bundle. Environment variables can still override these paths.
DEFAULT_KG_PATH = Path(ENV_KG_PICKLE_PATH) if ENV_KG_PICKLE_PATH else PROJECT_ROOT / "data/processed/final_graph/food_ai_graph.pkl"
DEFAULT_KG_JSON_PATH = Path(ENV_KG_JSON_PATH) if ENV_KG_JSON_PATH else PROJECT_ROOT / "data/processed/final_graph/food_ai_graph_networkx.json"
DEFAULT_EMBEDDINGS_PATH = Path(ENV_EMBEDDINGS_PATH) if ENV_EMBEDDINGS_PATH else PROJECT_ROOT / "data/processed/final_graph/claim_embeddings_bge_m3.json"


class KGDataStore:
    """translated note - translated note (V3 - NetworkX pickle)"""
    _instance = None
    _kg_graph: Optional[Any] = None  # NetworkX graph
    _kg_data: Optional[Dict] = None  # JSON format for backward compatibility
    _embeddings_data: Optional[Dict] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_kg_graph(self, kg_path: Optional[Path] = None):
        """translated note NetworkX translated note(translated note)- V3"""
        if self._kg_graph is None:
            path = kg_path or self._find_kg_pickle_path()
            with open(path, 'rb') as f:
                self._kg_graph = pickle.load(f)
        return self._kg_graph

    def get_kg(self, kg_path: Optional[Path] = None) -> Dict:
        """translated note JSON translated note(translated note)- translated note"""
        if self._kg_data is None:
            path = kg_path or self._find_kg_json_path()
            with open(path, 'r', encoding='utf-8') as f:
                self._kg_data = json.load(f)
        return self._kg_data

    def get_embeddings(self, embeddings_path: Optional[Path] = None) -> Dict:
        """translated note(translated note)"""
        if self._embeddings_data is None:
            path = embeddings_path or self._find_embeddings_path()
            with open(path, 'r') as f:
                self._embeddings_data = json.load(f)
        return self._embeddings_data

    def _find_kg_pickle_path(self) -> Path:
        """Return the frozen paper-facing NetworkX pickle path."""
        if DEFAULT_KG_PATH.exists():
            return DEFAULT_KG_PATH
        raise FileNotFoundError(f"Knowledge graph pickle not found: {DEFAULT_KG_PATH}")

    def _find_kg_json_path(self) -> Path:
        """Return the frozen paper-facing NetworkX JSON path."""
        if DEFAULT_KG_JSON_PATH.exists():
            return DEFAULT_KG_JSON_PATH
        raise FileNotFoundError(f"Knowledge graph JSON not found: {DEFAULT_KG_JSON_PATH}")

    def _find_embeddings_path(self) -> Path:
        """Return the frozen paper-facing claim embedding path."""
        if DEFAULT_EMBEDDINGS_PATH.exists():
            return DEFAULT_EMBEDDINGS_PATH
        raise FileNotFoundError(f"Embeddings file not found: {DEFAULT_EMBEDDINGS_PATH}")

    def clear_cache(self):
        """translated note(translated note)"""
        self._kg_graph = None
        self._kg_data = None
        self._embeddings_data = None


# translated note
data_store = KGDataStore()


def normalize_entity_name(name: str) -> str:
    """Normalize entity name for lookup in the knowledge graph.
    Only replaces spaces with underscores; hyphens are preserved
    to match how node IDs are stored (e.g. 'probiotic-containing_beverages').
    """
    return name.lower().replace(" ", "_")


def get_claim_by_id(G, claim_id: str) -> Optional[Dict]:
    """V3: translated note claim_id translated note NetworkX translated note claim translated note"""
    if claim_id in G.nodes:
        node_data = G.nodes[claim_id]
        if node_data.get("node_type") == "claim":
            return dict(node_data)
    return None


def get_claim_by_key(kg: Dict, claim_key: str) -> Optional[Dict]:
    """V2 translated note: translated note claim_key translated note claim translated note"""
    for node in kg.get("nodes", []):
        if node.get("node_type") == "claim" and node.get("claim_key") == claim_key:
            return node
    return None


def get_evidence_by_pmid(kg: Dict, pmid: str) -> Optional[Dict]:
    """V2 translated note: translated note PMID translated note evidence translated note"""
    for node in kg.get("nodes", []):
        if node.get("node_type") == "evidence" and node.get("pmid") == pmid:
            return node
    return None


def find_claims_by_entity(G, entity_name: str, entity_type: str,
                          direction: str = "both") -> Dict[str, List]:
    """
    V3: translated note NetworkX translated note claims

    Returns:
        {
            "as_subject": [...],  # translated note subject translated note claims
            "as_object": [...]    # translated note object translated note claims
        }
    """
    entity_node_id = f"{entity_type}_{normalize_entity_name(entity_name)}"
    as_subject = []
    as_object = []

    if entity_node_id not in G.nodes:
        return {"as_subject": [], "as_object": []}

    if direction in ["both", "subject"]:
        # translated note subject: entity -> claim
        for claim_id in G.successors(entity_node_id):
            claim_data = G.nodes[claim_id]
            if claim_data.get("node_type") == "claim":
                as_subject.append(dict(claim_data))

    if direction in ["both", "object"]:
        # translated note object: claim -> entity
        for claim_id in G.predecessors(entity_node_id):
            claim_data = G.nodes[claim_id]
            if claim_data.get("node_type") == "claim":
                as_object.append(dict(claim_data))

    return {"as_subject": as_subject, "as_object": as_object}


def get_entity_by_name(G, entity_name: str, entity_type: str) -> Optional[Dict]:
    """V3: translated note NetworkX translated note"""
    entity_node_id = f"{entity_type}_{normalize_entity_name(entity_name)}"
    if entity_node_id in G.nodes:
        return dict(G.nodes[entity_node_id])
    return None


def format_claim_for_display(claim: Dict, include_snippet: bool = True) -> Dict:
    """V3: translated note claim translated note - translated note evidence_list"""
    result = {
        "claim_id": claim.get("claim_id"),
        "claim_text": claim.get("claim_text"),
        "subject": claim.get("subject_name"),
        "object": claim.get("object_name"),
        "direction": claim.get("direction"),
        "evidence_count": claim.get("evidence_count", 0),
        "confidence_score": claim.get("confidence_score", 0),
    }

    # V3 translated note: evidence_list
    evidence_list = claim.get("evidence_list", [])
    if evidence_list:
        result["evidence_list"] = evidence_list
        result["primary_pmid"] = evidence_list[0].get("pmid") if evidence_list else None

    # translated note effect_size translated note p_value(translated note evidence translated note)
    if evidence_list:
        first_ev = evidence_list[0]
        if first_ev.get("effect_size"):
            result["effect_size"] = first_ev["effect_size"]
        if first_ev.get("p_value"):
            result["p_value"] = first_ev["p_value"]

    if include_snippet and evidence_list and evidence_list[0].get("evidence_snippet"):
        snippet = evidence_list[0]["evidence_snippet"]
        result["snippet"] = snippet[:200] + "..." if len(snippet) > 200 else snippet

    return result
