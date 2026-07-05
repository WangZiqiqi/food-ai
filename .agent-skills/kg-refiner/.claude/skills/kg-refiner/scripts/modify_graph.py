#!/usr/bin/env python3
"""
KG Refiner - translated note
translated note(translated note, translated note)
translated note
"""

import json
import pickle
import shutil
import os
import tempfile
from pathlib import Path
from datetime import datetime


KG_PATH = os.getenv("FOOD_AI_REFINER_KG_PATH") or os.getenv("FOOD_AI_KG_PICKLE_PATH") or "data/processed/final_graph/food_ai_graph.pkl"


def backup_graph():
    """translated note"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = KG_PATH.replace('.pkl', f'_backup_{timestamp}.pkl')
    shutil.copy(KG_PATH, backup_path)
    return backup_path


def save_graph_safely(G):
    """
    Atomically save the graph and verify it can be loaded back before replacing the target file.
    """
    kg_path = Path(KG_PATH)
    fd, temp_path = tempfile.mkstemp(prefix=kg_path.stem + "_", suffix=".pkl", dir=str(kg_path.parent))
    os.close(fd)

    try:
        with open(temp_path, 'wb') as f:
            pickle.dump(G, f)

        # Verify the written pickle is readable before replacing the original.
        with open(temp_path, 'rb') as f:
            pickle.load(f)

        os.replace(temp_path, KG_PATH)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def merge_entities(entity_a: str, entity_b: str, target_name: str, entity_type: str = "food"):
    """
    translated note target_name.

    translated note(translated note entity_a/entity_b translated note):
      - target_name translated note.
      - translated note source(entity_a translated note entity_b)translated note normalized node id translated note target node id translated note,
        translated note claims translated note target,translated note source translated note.
      - translated note source translated note node id translated note target node id,translated note,translated note.

    translated note:
      merge probiotic_supplement_capsule probiotic_supplement probiotic_supplement food
      -> translated note probiotic_supplement_capsule translated note claims translated note probiotic_supplement,
        translated note probiotic_supplement_capsule;probiotic_supplement translated note.
    """
    backup_path = backup_graph()

    with open(KG_PATH, 'rb') as f:
        G = pickle.load(f)

    node_a = f"{entity_type}_{entity_a.lower().replace(' ', '_')}"
    node_b = f"{entity_type}_{entity_b.lower().replace(' ', '_')}"
    node_target = f"{entity_type}_{target_name.lower().replace(' ', '_')}"

    if node_a not in G.nodes and node_b not in G.nodes:
        print(json.dumps({
            "success": False,
            "error": f"Neither {entity_a} nor {entity_b} found ({entity_type})"
        }))
        return

    # translated note
    if node_target not in G.nodes:
        sources_existing = [
            s for s in (entity_a, entity_b)
            if f"{entity_type}_{s.lower().replace(' ', '_')}" in G.nodes
        ]
        G.add_node(
            node_target,
            node_type=entity_type,
            name=target_name,
            entity_type=entity_type,
            merged_from=sources_existing,
        )

    transferred_details: list[str] = []

    def absorb(source_node: str) -> int:
        """translated note source_node translated note claim translated note node_target,translated note source_node."""
        if source_node == node_target or source_node not in G.nodes:
            return 0

        local = 0
        for successor in list(G.successors(source_node)):
            if G.nodes[successor].get("node_type") != "claim":
                continue
            claim_data = G.nodes[successor]
            old_subject = claim_data.get("subject_name")
            claim_data["subject_name"] = target_name
            claim_data["claim_text"] = (
                f"{target_name} has {claim_data.get('direction')} effect on "
                f"{claim_data.get('object_name')}"
            )
            if G.has_edge(source_node, successor):
                G.remove_edge(source_node, successor)
            G.add_edge(node_target, successor)
            transferred_details.append(f"{successor}: subject {old_subject} -> {target_name}")
            local += 1

        for predecessor in list(G.predecessors(source_node)):
            if G.nodes[predecessor].get("node_type") != "claim":
                continue
            claim_data = G.nodes[predecessor]
            old_object = claim_data.get("object_name")
            claim_data["object_name"] = target_name
            claim_data["claim_text"] = (
                f"{claim_data.get('subject_name')} has {claim_data.get('direction')} effect on "
                f"{target_name}"
            )
            if G.has_edge(predecessor, source_node):
                G.remove_edge(predecessor, source_node)
            G.add_edge(predecessor, node_target)
            transferred_details.append(f"{predecessor}: object {old_object} -> {target_name}")
            local += 1

        G.remove_node(source_node)
        return local

    total = 0
    total += absorb(node_a)
    total += absorb(node_b)

    save_graph_safely(G)

    print(json.dumps({
        "success": True,
        "backup_created": backup_path,
        "merged": {
            "entity_a": entity_a,
            "entity_b": entity_b,
            "target_name": target_name,
            "target_node": node_target,
        },
        "claims_transferred": total,
        "details": transferred_details[:10],
    }, indent=2, ensure_ascii=False))


def delete_entity(entity_name: str, entity_type: str):
    """translated note(translated note)"""
    # translated note
    backup_path = backup_graph()

    with open(KG_PATH, 'rb') as f:
        G = pickle.load(f)

    node_id = f"{entity_type}_{entity_name.lower().replace(' ', '_')}"

    if node_id not in G.nodes:
        print(json.dumps({"success": False, "error": f"Entity {entity_name} not found"}))
        return

    # translated noteclaims
    connected_claims = list(G.successors(node_id)) + list(G.predecessors(node_id))

    if connected_claims:
        print(json.dumps({
            "success": False,
            "error": f"Entity has {len(connected_claims)} connected claims, cannot delete",
            "connected_claims": connected_claims[:5]
        }))
        return

    G.remove_node(node_id)

    save_graph_safely(G)

    print(json.dumps({
        "success": True,
        "backup_created": backup_path,
        "deleted": {"name": entity_name, "type": entity_type}
    }, indent=2))


def delete_orphan_entity(entity_name: str, entity_type: str):
    """translated note;translated note claim,translated note."""
    delete_entity(entity_name, entity_type)


def rename_entity(old_name: str, new_name: str, entity_type: str):
    """translated note"""
    # translated note
    backup_path = backup_graph()

    with open(KG_PATH, 'rb') as f:
        G = pickle.load(f)

    old_node = f"{entity_type}_{old_name.lower().replace(' ', '_')}"
    new_node = f"{entity_type}_{new_name.lower().replace(' ', '_')}"

    if old_node not in G.nodes:
        print(json.dumps({"success": False, "error": f"Entity {old_name} not found"}))
        return

    if new_node in G.nodes:
        print(json.dumps({"success": False, "error": f"Target name {new_name} already exists"}))
        return

    # translated note/translated note
    G.add_node(new_node, **G.nodes[old_node])
    G.nodes[new_node]['name'] = new_name

    out_edges = list(G.out_edges(old_node, data=True))
    in_edges = list(G.in_edges(old_node, data=True))

    for _, target, edge_data in out_edges:
        G.add_edge(new_node, target, **edge_data)

    for source, _, edge_data in in_edges:
        G.add_edge(source, new_node, **edge_data)

    G.remove_node(old_node)

    # translated noteclaims
    updated_claims = []
    for node_id, data in G.nodes(data=True):
        if data.get('node_type') == 'claim':
            updated = False
            if data.get('subject_name') == old_name:
                data['subject_name'] = new_name
                updated = True
            if data.get('object_name') == old_name:
                data['object_name'] = new_name
                updated = True
            if updated:
                # translated noteclaim_text
                data['claim_text'] = f"{data.get('subject_name')} has {data.get('direction')} effect on {data.get('object_name')}"
                updated_claims.append(node_id)

    save_graph_safely(G)

    print(json.dumps({
        "success": True,
        "backup_created": backup_path,
        "renamed": {"from": old_name, "to": new_name},
        "claims_updated": len(updated_claims)
    }, indent=2))


def retype_entity(entity_name: str, old_type: str, new_type: str):
    """translated note."""
    backup_path = backup_graph()

    with open(KG_PATH, 'rb') as f:
        G = pickle.load(f)

    normalized_name = entity_name.lower().replace(' ', '_')
    old_node = f"{old_type}_{normalized_name}"
    new_node = f"{new_type}_{normalized_name}"

    if old_node not in G.nodes:
        print(json.dumps({"success": False, "error": f"Entity {entity_name} ({old_type}) not found"}))
        return

    old_attrs = dict(G.nodes[old_node])
    if new_node not in G.nodes:
        old_attrs["node_type"] = new_type
        old_attrs["entity_type"] = new_type
        old_attrs["name"] = normalized_name
        old_attrs["retyped_from"] = old_type
        G.add_node(new_node, **old_attrs)

    out_edges = list(G.out_edges(old_node, data=True))
    in_edges = list(G.in_edges(old_node, data=True))
    updated_claims = []

    for _, target, edge_data in out_edges:
        G.add_edge(new_node, target, **edge_data)
        if G.nodes[target].get("node_type") == "claim":
            G.nodes[target]["subject_type"] = new_type
            G.nodes[target]["subject_name"] = normalized_name
            G.nodes[target]["claim_text"] = (
                f"{G.nodes[target].get('subject_name')} has "
                f"{G.nodes[target].get('direction')} effect on "
                f"{G.nodes[target].get('object_name')}"
            )
            updated_claims.append(target)

    for source, _, edge_data in in_edges:
        G.add_edge(source, new_node, **edge_data)
        if G.nodes[source].get("node_type") == "claim":
            G.nodes[source]["object_type"] = new_type
            G.nodes[source]["object_name"] = normalized_name
            G.nodes[source]["claim_text"] = (
                f"{G.nodes[source].get('subject_name')} has "
                f"{G.nodes[source].get('direction')} effect on "
                f"{G.nodes[source].get('object_name')}"
            )
            updated_claims.append(source)

    G.remove_node(old_node)
    save_graph_safely(G)

    print(json.dumps({
        "success": True,
        "backup_created": backup_path,
        "retyped": {"name": normalized_name, "from": old_type, "to": new_type},
        "claims_updated": len(set(updated_claims))
    }, indent=2, ensure_ascii=False))


def set_entity_name(entity_name: str, entity_type: str, display_name: str):
    """translated note claim translated note,translated note node id."""
    backup_path = backup_graph()

    with open(KG_PATH, 'rb') as f:
        G = pickle.load(f)

    node_id = f"{entity_type}_{entity_name.lower().replace(' ', '_')}"
    if node_id not in G.nodes:
        print(json.dumps({"success": False, "error": f"Entity {entity_name} ({entity_type}) not found"}))
        return

    old_display_name = G.nodes[node_id].get("name", entity_name)
    G.nodes[node_id]["name"] = display_name
    G.nodes[node_id]["display_name"] = display_name

    updated_claims = []
    for claim_id, data in G.nodes(data=True):
        if data.get("node_type") != "claim":
            continue
        updated = False
        if data.get("subject_type") == entity_type and data.get("subject_name") in {entity_name, old_display_name}:
            data["subject_name"] = display_name
            updated = True
        if data.get("object_type") == entity_type and data.get("object_name") in {entity_name, old_display_name}:
            data["object_name"] = display_name
            updated = True
        if updated:
            data["claim_text"] = (
                f"{data.get('subject_name')} has {data.get('direction')} effect on {data.get('object_name')}"
            )
            updated_claims.append(claim_id)

    save_graph_safely(G)

    print(json.dumps({
        "success": True,
        "backup_created": backup_path,
        "renamed_display": {"entity": entity_name, "type": entity_type, "display_name": display_name},
        "claims_updated": len(updated_claims)
    }, indent=2, ensure_ascii=False))


def mark_out_of_scope(entity_name: str, entity_type: str, reason: str = "out_of_scope"):
    """translated note KG translated note."""
    backup_path = backup_graph()

    with open(KG_PATH, 'rb') as f:
        G = pickle.load(f)

    node_id = f"{entity_type}_{entity_name.lower().replace(' ', '_')}"
    if node_id not in G.nodes:
        print(json.dumps({"success": False, "error": f"Entity {entity_name} ({entity_type}) not found"}))
        return

    G.nodes[node_id]["quality_status"] = "out_of_scope"
    G.nodes[node_id]["out_of_scope_reason"] = reason

    connected_claims = list(G.successors(node_id)) + list(G.predecessors(node_id))
    claim_ids = []
    for claim_id in connected_claims:
        if G.nodes[claim_id].get("node_type") != "claim":
            continue
        flags = list(G.nodes[claim_id].get("quality_flags", []))
        flag = f"entity_out_of_scope:{entity_type}:{entity_name}"
        if flag not in flags:
            flags.append(flag)
        G.nodes[claim_id]["quality_flags"] = flags
        claim_ids.append(claim_id)

    save_graph_safely(G)

    print(json.dumps({
        "success": True,
        "backup_created": backup_path,
        "marked_out_of_scope": {"name": entity_name, "type": entity_type, "reason": reason},
        "claims_flagged": len(claim_ids)
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:", file=sys.stderr)
        print("  python modify_graph.py merge <entity_a> <entity_b> <target_name> [entity_type]", file=sys.stderr)
        print("  python modify_graph.py delete <entity_name> <entity_type>", file=sys.stderr)
        print("  python modify_graph.py delete_orphan <entity_name> <entity_type>", file=sys.stderr)
        print("  python modify_graph.py rename <old_name> <new_name> <entity_type>", file=sys.stderr)
        print("  python modify_graph.py retype <entity_name> <old_type> <new_type>", file=sys.stderr)
        print("  python modify_graph.py set_name <entity_name> <entity_type> <display_name>", file=sys.stderr)
        print("  python modify_graph.py mark_out_of_scope <entity_name> <entity_type> [reason]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "merge" and len(sys.argv) >= 5:
        merge_entities(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "food")
    elif command == "delete" and len(sys.argv) >= 4:
        delete_entity(sys.argv[2], sys.argv[3])
    elif command == "delete_orphan" and len(sys.argv) >= 4:
        delete_orphan_entity(sys.argv[2], sys.argv[3])
    elif command == "rename" and len(sys.argv) >= 5:
        rename_entity(sys.argv[2], sys.argv[3], sys.argv[4])
    elif command in {"retype", "update_type"} and len(sys.argv) >= 5:
        retype_entity(sys.argv[2], sys.argv[3], sys.argv[4])
    elif command == "set_name" and len(sys.argv) >= 5:
        set_entity_name(sys.argv[2], sys.argv[3], sys.argv[4])
    elif command == "mark_out_of_scope" and len(sys.argv) >= 4:
        mark_out_of_scope(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "out_of_scope")
    else:
        print("Invalid command or arguments", file=sys.stderr)
        sys.exit(1)
