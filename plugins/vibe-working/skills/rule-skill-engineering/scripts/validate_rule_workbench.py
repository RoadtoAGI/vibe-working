#!/usr/bin/env python3
"""Validate a rule-skill-engineering workbench JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SOURCE_KINDS = {
    "primary_authority",
    "project_rule",
    "user_requirement",
    "existing_artifact",
    "design_choice",
}
STRENGTHS = {"hard_constraint", "execution_strategy", "heuristic"}
RULE_STATUSES = {"active", "absorbed", "supporting", "discarded"}
RELATIONS = {"equivalent", "shared_invariant", "adjacent"}
CLUSTER_DECISIONS = {"merge", "abstract", "keep_separate"}
SURFACES = {
    "frontmatter",
    "skill_body",
    "reference",
    "script",
    "project_rule",
    "project_doc",
    "discarded",
}
CHECK_STATUSES = {"open", "pass", "fail", "not_applicable"}
REQUIRED_CHECKS = {
    "authority_traceability",
    "rule_closure",
    "merge_safety",
    "abstraction_preservation",
    "ssot_uniqueness",
    "runtime_reachability",
    "structural_validation",
    "behavior_positive",
    "behavior_boundary",
    "behavior_conflict",
}


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, path: str, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def object(self, value: Any, path: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            self.error(path, "must be an object")
            return {}
        return value

    def array(self, value: Any, path: str, *, nonempty: bool = False) -> list[Any]:
        if not isinstance(value, list):
            self.error(path, "must be an array")
            return []
        if nonempty and not value:
            self.error(path, "must not be empty")
        return value

    def text(self, value: Any, path: str) -> str:
        if not isinstance(value, str) or not value.strip():
            self.error(path, "must be a non-empty string")
            return ""
        return value.strip()

    def enum(self, value: Any, path: str, allowed: set[str]) -> str:
        text = self.text(value, path)
        if text and text not in allowed:
            self.error(path, f"must be one of {sorted(allowed)}")
        return text

    def text_array(
        self, value: Any, path: str, *, nonempty: bool = False, unique: bool = False
    ) -> list[str]:
        items = self.array(value, path, nonempty=nonempty)
        result = [self.text(item, f"{path}[{index}]") for index, item in enumerate(items)]
        clean = [item for item in result if item]
        if unique and len(clean) != len(set(clean)):
            self.error(path, "must contain unique strings")
        return clean


def unique_id_map(
    validation: Validation, items: list[Any], path: str
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(items):
        item = validation.object(value, f"{path}[{index}]")
        item_id = validation.text(item.get("id"), f"{path}[{index}].id")
        if not item_id:
            continue
        if item_id in result:
            validation.error(f"{path}[{index}].id", f"duplicate id {item_id!r}")
        else:
            result[item_id] = item
    return result


def validate_target(validation: Validation, value: Any) -> None:
    target = validation.object(value, "target")
    for field in ("name", "purpose", "deliverable", "owner"):
        validation.text(target.get(field), f"target.{field}")
    validation.text_array(target.get("consumers"), "target.consumers", nonempty=True, unique=True)


def validate_sources(validation: Validation, values: Any) -> dict[str, dict[str, Any]]:
    sources = validation.array(values, "sources", nonempty=True)
    source_map = unique_id_map(validation, sources, "sources")
    for index, value in enumerate(sources):
        source = validation.object(value, f"sources[{index}]")
        validation.enum(source.get("kind"), f"sources[{index}].kind", SOURCE_KINDS)
        validation.text(source.get("locator"), f"sources[{index}].locator")
        validation.text(source.get("authority"), f"sources[{index}].authority")
        validation.text_array(
            source.get("claims"), f"sources[{index}].claims", nonempty=True, unique=True
        )
    return source_map


def validate_rules(
    validation: Validation, values: Any, source_ids: set[str]
) -> dict[str, dict[str, Any]]:
    rules = validation.array(values, "rules", nonempty=True)
    rule_map = unique_id_map(validation, rules, "rules")
    for index, value in enumerate(rules):
        rule = validation.object(value, f"rules[{index}]")
        prefix = f"rules[{index}]"
        for field in (
            "decision",
            "trigger",
            "action",
            "acceptance",
            "rationale",
            "authority",
            "scope",
            "owner",
        ):
            validation.text(rule.get(field), f"{prefix}.{field}")
        validation.enum(rule.get("strength"), f"{prefix}.strength", STRENGTHS)
        status = validation.enum(rule.get("status"), f"{prefix}.status", RULE_STATUSES)
        linked_sources = validation.text_array(
            rule.get("source_ids"), f"{prefix}.source_ids", nonempty=True, unique=True
        )
        for source_id in linked_sources:
            if source_id not in source_ids:
                validation.error(f"{prefix}.source_ids", f"unknown source id {source_id!r}")
        validation.text_array(rule.get("depends_on"), f"{prefix}.depends_on", unique=True)
        validation.text_array(rule.get("exceptions"), f"{prefix}.exceptions", unique=True)
        replacement = rule.get("replaced_by")
        if status == "absorbed":
            validation.text(replacement, f"{prefix}.replaced_by")
        elif replacement is not None:
            validation.error(f"{prefix}.replaced_by", "must be null unless status is absorbed")

    rule_ids = set(rule_map)
    for index, value in enumerate(rules):
        rule = validation.object(value, f"rules[{index}]")
        prefix = f"rules[{index}]"
        rule_id = rule.get("id")
        dependencies = rule.get("depends_on", [])
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if not isinstance(dependency, str):
                    continue  # The field validation above already reports this value.
                if dependency not in rule_ids:
                    validation.error(f"{prefix}.depends_on", f"unknown rule id {dependency!r}")
                if dependency == rule_id:
                    validation.error(f"{prefix}.depends_on", "a rule cannot depend on itself")
        replacement = rule.get("replaced_by")
        if isinstance(replacement, str) and replacement:
            if replacement not in rule_ids:
                validation.error(f"{prefix}.replaced_by", f"unknown rule id {replacement!r}")
            elif replacement == rule_id:
                validation.error(f"{prefix}.replaced_by", "a rule cannot replace itself")
            elif rule_map[replacement].get("status") in {"absorbed", "discarded"}:
                validation.error(
                    f"{prefix}.replaced_by", "must point to an active or supporting rule"
                )
    return rule_map


def validate_clusters(
    validation: Validation, values: Any, rules: dict[str, dict[str, Any]]
) -> None:
    clusters = validation.array(values, "clusters")
    unique_id_map(validation, clusters, "clusters")
    valid_pairs = {
        ("equivalent", "merge"),
        ("shared_invariant", "abstract"),
        ("adjacent", "keep_separate"),
    }
    for index, value in enumerate(clusters):
        cluster = validation.object(value, f"clusters[{index}]")
        prefix = f"clusters[{index}]"
        members = validation.text_array(
            cluster.get("member_rule_ids"), f"{prefix}.member_rule_ids", nonempty=True, unique=True
        )
        if len(members) < 2:
            validation.error(f"{prefix}.member_rule_ids", "must contain at least two rule ids")
        for member in members:
            if member not in rules:
                validation.error(f"{prefix}.member_rule_ids", f"unknown rule id {member!r}")
        relation = validation.enum(cluster.get("relation"), f"{prefix}.relation", RELATIONS)
        decision = validation.enum(
            cluster.get("decision"), f"{prefix}.decision", CLUSTER_DECISIONS
        )
        if relation and decision and (relation, decision) not in valid_pairs:
            validation.error(prefix, f"invalid relation/decision combination {relation}/{decision}")
        validation.text(cluster.get("rationale"), f"{prefix}.rationale")
        result_rule_id = cluster.get("result_rule_id")
        invariant = cluster.get("invariant")
        if decision in {"merge", "abstract"}:
            result = validation.text(result_rule_id, f"{prefix}.result_rule_id")
            if result and result not in rules:
                validation.error(f"{prefix}.result_rule_id", f"unknown rule id {result!r}")
            elif result and rules[result].get("status") not in {"active", "supporting"}:
                validation.error(
                    f"{prefix}.result_rule_id", "must point to an active or supporting rule"
                )
        elif result_rule_id is not None:
            validation.error(f"{prefix}.result_rule_id", "must be null for keep_separate")
        if relation == "shared_invariant":
            validation.text(invariant, f"{prefix}.invariant")
        elif invariant is not None:
            validation.error(
                f"{prefix}.invariant", "must be null unless relation is shared_invariant"
            )


def validate_placements(
    validation: Validation, values: Any, rules: dict[str, dict[str, Any]]
) -> None:
    placements = validation.array(values, "placements", nonempty=True)
    placed: set[str] = set()
    for index, value in enumerate(placements):
        placement = validation.object(value, f"placements[{index}]")
        prefix = f"placements[{index}]"
        rule_id = validation.text(placement.get("rule_id"), f"{prefix}.rule_id")
        surface = validation.enum(placement.get("surface"), f"{prefix}.surface", SURFACES)
        validation.text(placement.get("locator"), f"{prefix}.locator")
        validation.text(placement.get("reason"), f"{prefix}.reason")
        if rule_id:
            if rule_id not in rules:
                validation.error(f"{prefix}.rule_id", f"unknown rule id {rule_id!r}")
            elif rule_id in placed:
                validation.error(f"{prefix}.rule_id", "each rule must have exactly one placement")
            placed.add(rule_id)
            status = rules.get(rule_id, {}).get("status")
            if status == "discarded" and surface != "discarded":
                validation.error(f"{prefix}.surface", "discarded rules require discarded surface")
            if status != "discarded" and surface == "discarded":
                validation.error(f"{prefix}.surface", "only discarded rules use discarded surface")
    missing = set(rules) - placed
    if missing:
        validation.error("placements", f"missing rule ids {sorted(missing)}")


def validate_checks(validation: Validation, values: Any, *, final: bool) -> None:
    checks = validation.array(values, "checks", nonempty=True)
    seen: set[str] = set()
    for index, value in enumerate(checks):
        check = validation.object(value, f"checks[{index}]")
        prefix = f"checks[{index}]"
        name = validation.text(check.get("name"), f"{prefix}.name")
        if name in seen:
            validation.error(f"{prefix}.name", f"duplicate check {name!r}")
        seen.add(name)
        status = validation.enum(check.get("status"), f"{prefix}.status", CHECK_STATUSES)
        validation.text_array(check.get("evidence"), f"{prefix}.evidence", nonempty=True)
        if final and status not in {"pass", "not_applicable"}:
            validation.error(f"{prefix}.status", "final validation requires pass or not_applicable")
    missing = REQUIRED_CHECKS - seen
    extra = seen - REQUIRED_CHECKS
    if missing:
        validation.error("checks", f"missing required checks {sorted(missing)}")
    if extra:
        validation.error("checks", f"unknown checks {sorted(extra)}")


def validate_document(document: Any, *, require_final: bool) -> list[str]:
    validation = Validation()
    root = validation.object(document, "$")
    if root.get("schema_version") != "1.0":
        validation.error("schema_version", "must equal '1.0'")
    phase = validation.enum(root.get("phase"), "phase", {"draft", "final"})
    if require_final and phase != "final":
        validation.error("phase", "--final requires phase to be 'final'")

    validate_target(validation, root.get("target"))
    sources = validate_sources(validation, root.get("sources"))
    rules = validate_rules(validation, root.get("rules"), set(sources))
    validate_clusters(validation, root.get("clusters"), rules)
    validate_placements(validation, root.get("placements"), rules)
    validate_checks(validation, root.get("checks"), final=require_final or phase == "final")
    return validation.errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbench", type=Path, help="Path to rule-workbench JSON")
    parser.add_argument(
        "--final", action="store_true", help="Require phase=final and all checks closed"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with args.workbench.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.workbench}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read JSON: {exc}", file=sys.stderr)
        return 2

    errors = validate_document(document, require_final=args.final)
    if errors:
        print(f"INVALID: {args.workbench} ({len(errors)} error(s))", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    mode = "final" if args.final else document.get("phase", "draft")
    print(
        f"VALID: {args.workbench} "
        f"(mode={mode}, rules={len(document.get('rules', []))}, "
        f"clusters={len(document.get('clusters', []))})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
