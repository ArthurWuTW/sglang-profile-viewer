from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# Precedence: lower number = higher priority.
STRATEGY_ORDER = ("exact", "qualified_exact", "regex", "contains", "contains_any")
_STRATEGY_PRIORITY = {s: i for i, s in enumerate(STRATEGY_ORDER)}

_MISSING = object()


@dataclass(frozen=True)
class MappingRule:
    id: str
    display_name: str
    category: str
    strategy: str
    patterns: tuple
    confidence: str = "medium"
    framework: Optional[str] = None
    source: Optional[dict] = None
    description: Optional[str] = None
    order: int = 0
    sglang_version: Optional[dict] = None
    git_commit: Optional[list] = None


def _as_pattern_list(value: Any) -> tuple:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(v) for v in value)
    return (str(value),)


def _parse_match(match: dict) -> tuple[str, tuple]:
    """Return (strategy, patterns) from a match dict.

    Supported keys: exact, qualified_exact, regex, contains (all must match),
    contains_any (at least one must match).
    """
    if not isinstance(match, dict) or not match:
        raise ValueError("mapping rule 'match' must be a non-empty dict")
    if "exact" in match:
        return "exact", _as_pattern_list(match["exact"])
    if "qualified_exact" in match:
        return "qualified_exact", _as_pattern_list(match["qualified_exact"])
    if "regex" in match:
        return "regex", _as_pattern_list(match["regex"])
    if "contains" in match:
        return "contains", _as_pattern_list(match["contains"])
    if "contains_any" in match:
        return "contains_any", _as_pattern_list(match["contains_any"])
    raise ValueError(f"mapping rule 'match' has no recognized strategy: {match}")


def _parse_rule(raw: dict, order: int) -> MappingRule:
    for key in ("id", "display_name", "category", "match"):
        if key not in raw:
            raise ValueError(f"mapping rule missing required key '{key}': {raw}")
    strategy, patterns = _parse_match(raw["match"])
    if not patterns:
        raise ValueError(f"mapping rule '{raw['id']}' has empty patterns")
    # Pre-compile regexes to fail fast on bad patterns.
    if strategy == "regex":
        for p in patterns:
            re.compile(p)
    source = raw.get("source")
    if source is not None and not isinstance(source, dict):
        raise ValueError(f"mapping rule '{raw['id']}' source must be a dict")
    return MappingRule(
        id=str(raw["id"]),
        display_name=str(raw["display_name"]),
        category=str(raw["category"]),
        strategy=strategy,
        patterns=patterns,
        confidence=str(raw.get("confidence", "medium")).lower(),
        framework=raw.get("framework"),
        source=source,
        description=raw.get("description"),
        order=order,
        sglang_version=raw.get("sglang_version"),
        git_commit=raw.get("git_commit"),
    )


def _iter_mapping_files(mappings_dir: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.yaml", "*.yml"):
        files.extend(mappings_dir.rglob(pattern))
    # base.yaml first, then the rest in deterministic path order.
    files.sort(key=lambda p: (0 if p.name == "base.yaml" else 1, str(p)))
    return files


def load_mappings(mappings_dir: Path) -> "SemanticMapper":
    """Load all YAML mapping rules under ``mappings_dir`` into a mapper."""
    rules: list[MappingRule] = []
    if mappings_dir is not None and mappings_dir.exists():
        for path in _iter_mapping_files(mappings_dir):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except (OSError, yaml.YAMLError) as exc:
                logger.warning("Failed to load mapping file %s: %s", path, exc)
                continue
            if data is None:
                continue
            if isinstance(data, dict) and "rules" in data:
                data = data["rules"]
            if not isinstance(data, list):
                logger.warning("Mapping file %s is not a list of rules", path)
                continue
            for raw in data:
                if not isinstance(raw, dict):
                    continue
                try:
                    rules.append(_parse_rule(raw, order=len(rules)))
                except ValueError as exc:
                    logger.warning("Skipping invalid mapping rule in %s: %s", path, exc)
    else:
        logger.warning(
            "Mappings directory %s not found; semantic mapping unavailable",
            mappings_dir,
        )
    return SemanticMapper(rules)


class SemanticMapper:
    """Deterministic raw-name -> semantic rule classifier.

    Precedence (documented, not file-order dependent):
        exact > qualified_exact > regex > contains / contains_any
    Within the same strategy, the rule with the lowest load order wins.
    """

    def __init__(self, rules: list[MappingRule]):
        self.rules = rules
        self._by_strategy: dict[str, list[MappingRule]] = {}
        for r in rules:
            self._by_strategy.setdefault(r.strategy, []).append(r)
        for strategy, rs in self._by_strategy.items():
            rs.sort(key=lambda r: r.order)
        self._by_id: dict[str, MappingRule] = {r.id: r for r in rules}
        self._cache: dict[str, Optional[MappingRule]] = {}

    def rule_by_id(self, rule_id: Optional[str]) -> Optional[MappingRule]:
        if rule_id is None:
            return None
        return self._by_id.get(rule_id)

    @staticmethod
    def _matches(rule: MappingRule, name: str) -> bool:
        if rule.strategy == "exact":
            return any(name == p for p in rule.patterns)
        if rule.strategy == "qualified_exact":
            # Matches the qualified name exactly, or the same name with
            # template arguments appended: "sglang::store_kvcache<...>".
            # Kernel names are often prefixed with the return type ("void ").
            base = name
            for prefix in ("void ", "const "):
                if base.startswith(prefix):
                    base = base[len(prefix):]
                    break
            return any(base == p or base.startswith(p + "<") for p in rule.patterns)
        if rule.strategy == "regex":
            return any(re.search(p, name) for p in rule.patterns)
        if rule.strategy == "contains":
            # All patterns must be present.
            return all(p in name for p in rule.patterns)
        if rule.strategy == "contains_any":
            return any(p in name for p in rule.patterns)
        return False

    def classify(self, name: str) -> Optional[MappingRule]:
        cached = self._cache.get(name, _MISSING)
        if cached is not _MISSING:
            return cached
        rule: Optional[MappingRule] = None
        for strategy in STRATEGY_ORDER:
            for r in self._by_strategy.get(strategy, ()):
                if self._matches(r, name):
                    rule = r
                    break
            if rule is not None:
                break
        self._cache[name] = rule
        return rule
