#!/usr/bin/env python3
"""Render Food-AI KG JSON as an interactive HTML graph.

- Input: KG JSON produced by this repo (e.g. data/processed/kg_yogurt_diabetes.json)
- Output: an interactive HTML file rendered with PyVis (vis.js)

Usage:
  python3 scripts/render_kg_pyvis.py \
    --input data/processed/kg_yogurt_diabetes.json \
    --output data/processed/kg_yogurt_diabetes.html

Notes:
- This script builds a NetworkX MultiDiGraph first, then uses pyvis.Network.from_nx.
- Best viewed by opening the generated HTML in a browser.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import networkx as nx
from pyvis.network import Network


def _node_id(node_type: str, name_or_id: str) -> str:
    return f"{node_type}:{name_or_id}"


def build_nx_from_kg_json(path: Path) -> nx.MultiDiGraph:
    d: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    G = nx.MultiDiGraph()

    def add_node(node_id: str, node_type: str, label: str, **attrs: Any) -> None:
        if G.has_node(node_id):
            return
        attrs = dict(attrs)
        attrs.setdefault("type", node_type)
        attrs.setdefault("label", label)
        G.add_node(node_id, **attrs)

    # Nodes: normalize into typed IDs to avoid collisions
    for name, obj in (d.get("strains") or {}).items():
        add_node(_node_id("strain", name), "strain", name, **(obj or {}))

    for name, obj in (d.get("food_products") or {}).items():
        add_node(_node_id("food", name), "food_product", name, **(obj or {}))

    for name, obj in (d.get("populations") or {}).items():
        add_node(_node_id("pop", name), "population", name, **(obj or {}))

    for name, obj in (d.get("outcomes") or {}).items():
        add_node(_node_id("out", name), "outcome", name, **(obj or {}))

    for pmid, obj in (d.get("evidences") or {}).items():
        title = (obj or {}).get("title") or pmid
        add_node(_node_id("pmid", pmid), "evidence", str(title), **(obj or {}))

    def claim_endpoint(t: str, n: str) -> str:
        if t == "food_product":
            return _node_id("food", n)
        if t == "strain":
            return _node_id("strain", n)
        if t == "population":
            return _node_id("pop", n)
        if t == "outcome":
            return _node_id("out", n)
        return _node_id(t or "entity", n)

    # Edges: claims as subject -> object
    for claim_key, c in (d.get("claims") or {}).items():
        st = c.get("subject_type")
        sn = c.get("subject_name")
        ot = c.get("object_type")
        on = c.get("object_name")
        if not (st and sn and ot and on):
            continue

        u = claim_endpoint(st, sn)
        v = claim_endpoint(ot, on)

        if not G.has_node(u):
            add_node(u, st, sn, name=sn)
        if not G.has_node(v):
            add_node(v, ot, on, name=on)

        predicate = c.get("predicate") or "rel"
        direction = c.get("direction")
        evidence_ref = c.get("evidence_ref")

        title_bits = [predicate]
        if direction:
            title_bits.append(f"direction={direction}")
        if evidence_ref:
            title_bits.append(f"PMID={evidence_ref}")

        G.add_edge(
            u,
            v,
            key=str(claim_key),
            predicate=predicate,
            direction=direction,
            effect_size=c.get("effect_size"),
            p_value=c.get("p_value"),
            evidence_ref=evidence_ref,
            evidence_snippet=c.get("evidence_snippet"),
            title=" | ".join(title_bits),
            label=predicate,
        )

        # Optional: connect involved nodes to evidence node for quick navigation
        if evidence_ref:
            ev_node = _node_id("pmid", str(evidence_ref))
            if G.has_node(ev_node):
                G.add_edge(u, ev_node, key=f"supported_by:{claim_key}:u", label="supported_by", title="supported_by")
                G.add_edge(v, ev_node, key=f"supported_by:{claim_key}:v", label="supported_by", title="supported_by")

    return G


def render_pyvis(
    G: nx.MultiDiGraph,
    output_html: Path,
    height: str = "900px",
    width: str = "100%",
) -> None:
    # notebook=False generates a standalone HTML.
    net = Network(height=height, width=width, directed=True, notebook=False)

    # Physics tuned for small/medium graphs; user can toggle in UI.
    net.force_atlas_2based(
        gravity=-50,
        central_gravity=0.01,
        spring_length=140,
        spring_strength=0.08,
        damping=0.4,
        overlap=0.5,
    )

    # Map node type to colors (pyvis uses hex strings)
    color_map = {
        "food_product": "#4C78A8",
        "strain": "#72B7B2",
        "population": "#F58518",
        "outcome": "#E45756",
        "evidence": "#54A24B",
    }

    # pyvis.from_nx won't preserve MultiDiGraph edge keys well, and we want richer tooltips.
    for node_id, attrs in G.nodes(data=True):
        ntype = attrs.get("type", "entity")
        label = attrs.get("label") or node_id

        # Tooltip: keep it readable
        title = attrs.get("title")
        if not title:
            # show a few common fields if present
            if ntype == "evidence":
                pmid = attrs.get("pmid")
                journal = attrs.get("journal")
                year = attrs.get("year")
                title = f"PMID: {pmid}\n{journal or ''} {year or ''}".strip()
            else:
                title = ntype

        net.add_node(
            node_id,
            label=str(label),
            title=str(title),
            color=color_map.get(ntype, "#999999"),
        )

    for u, v, _k, attrs in G.edges(keys=True, data=True):
        net.add_edge(
            u,
            v,
            label=str(attrs.get("label") or ""),
            title=str(attrs.get("title") or ""),
            arrows="to",
        )

    # Add UI controls (physics, node/edge styling, etc.)
    net.show_buttons(filter_=["physics", "interaction", "layout"])

    output_html.parent.mkdir(parents=True, exist_ok=True)
    net.write_html(str(output_html))


def main() -> int:
    parser = argparse.ArgumentParser(description="Render KG JSON to interactive HTML (PyVis)")
    parser.add_argument("--input", "-i", type=Path, required=True, help="KG JSON path")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output HTML path")
    parser.add_argument("--height", type=str, default="900px", help="Canvas height, e.g. 900px")
    parser.add_argument("--width", type=str, default="100%", help="Canvas width, e.g. 100%")
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(args.input)

    G = build_nx_from_kg_json(args.input)
    render_pyvis(G, args.output, height=args.height, width=args.width)

    print(f"nodes={G.number_of_nodes()} edges={G.number_of_edges()}")
    print(f"wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
