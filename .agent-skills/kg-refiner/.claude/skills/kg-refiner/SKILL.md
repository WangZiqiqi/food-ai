---
name: kg-refiner
description: "Knowledge graph refinement tools for analyzing graph quality, detecting suspicious entities or conflicts, and applying cautious entity-level fixes with backups."
---

# KG Refiner

Use this skill when maintaining or auditing the Food-AI knowledge graph. The refiner is intended for controlled graph-quality work, not for ordinary read-only question answering.

## Principles

1. **Safety first**: graph-modifying commands create backups before writing.
2. **Incremental changes**: inspect the graph before applying any fix.
3. **Traceability**: changes should be explainable in terms of affected claims and PMIDs.
4. **Conservatism**: do not merge entities only because names are superficially similar.
5. **Scientific caution**: conflicting evidence may reflect real literature heterogeneity and should often be preserved.

## Workflow

1. Run `analyze_graph.py` to inspect graph size and entity distributions.
2. Run `detect_issues.py` to list suspicious entities, duplicate candidates, and conflicting claim directions.
3. Use `get_entity_info.py` to inspect a specific entity and its connected claims.
4. Use `modify_graph.py` only for well-justified fixes such as merge, rename, retype, delete orphan, set display name, or mark out of scope.
5. Re-run analysis after modification.

## Tools

### `analyze_graph.py`

```bash
python analyze_graph.py
```

Returns graph-level statistics, node distributions, top foods, top outcomes, and other summary counts.

### `detect_issues.py`

```bash
python detect_issues.py
```

Detects suspicious entity types, likely duplicate names, and subject-outcome pairs with conflicting directions.

### `get_entity_info.py`

```bash
python get_entity_info.py yogurt food
```

Returns entity metadata and connected claims.

### `modify_graph.py`

Supported operations include:

```bash
python modify_graph.py merge <entity_a> <entity_b> <entity_type> <target_name>
python modify_graph.py rename <old_name> <entity_type> <new_name>
python modify_graph.py retype <entity_name> <old_type> <new_type>
python modify_graph.py delete_orphan <entity_name> <entity_type>
python modify_graph.py set_name <entity_name> <entity_type> <display_name>
python modify_graph.py mark_out_of_scope <entity_name> <entity_type> <reason>
```

Use destructive operations only after inspecting connected claims.

## Decision rules

Safe examples:

- Singular/plural normalization when evidence semantics are identical.
- Dose-arm label cleanup when all claims clearly refer to the same canonical entity.
- Deleting an entity only if it is truly orphaned.

Unsafe examples:

- Merging a food with a bioactive compound when the paper distinguishes them.
- Merging a product formulation into a generic food if formulation details are outcome-critical.
- Treating a real scientific disagreement as a data error.
