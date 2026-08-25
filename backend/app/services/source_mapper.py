from __future__ import annotations

from typing import Any, Optional

from .semantic_mapper import MappingRule, SemanticMapper


class SourceMapper:
    """Resolves a semantic mapping rule to its SGLang source-code reference.

    Answers: "If I see this event in the profiler, where in SGLang should I look?"
    """

    def __init__(self, mapper: SemanticMapper):
        self._mapper = mapper

    def for_rule_id(self, rule_id: Optional[str]) -> Optional[dict[str, Any]]:
        rule = self._mapper.rule_by_id(rule_id)
        if rule is None or not rule.source:
            return None
        src = dict(rule.source)
        src["ruleId"] = rule.id
        if rule.framework:
            src.setdefault("framework", rule.framework)
        return src

    def for_event(self, event) -> Optional[dict[str, Any]]:
        return self.for_rule_id(getattr(event, "rule_id", None))
