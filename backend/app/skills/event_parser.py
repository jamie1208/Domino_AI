"""Conservative offline event parsing for Domino AI.

Rule-based fallback only: neither LLM nor public-data lookup is performed here.
Never infer risk severity from earthquake magnitude, duration, or location.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas import Scenario

_NATURAL = ("地震", "颱風", "洪水", "earthquake", "typhoon", "flood")
_SUPPLY = ("斷料", "缺料", "供應中斷", "物流中斷", "supply chain", "supply disruption")
_POLICY = ("關稅", "出口限制", "出口管制", "tariff", "export control")
_DURATION = re.compile(r"(?<![\d.])(\d{1,4})\s*(?:天|日|days?\b)", re.I)
_MAGNITUDE = re.compile(r"(?:地震\s*)?(?:規模\s*|magnitude\s*|M\s*)(\d{1,2}(?:\.\d+)?)", re.I)


@dataclass(frozen=True)
class EventParseDetails:
    """Auxiliary interpretations; not official Scenario fields or model inputs."""

    earthquake_magnitude: float | None = None
    missing_required: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class EventParserSkill:
    def run(self, scenario: Scenario) -> Scenario:
        """Fill only safe absent fields and preserve all user-provided fields."""
        text = scenario.description
        lowered = text.casefold()
        updates: dict[str, object] = {}

        if scenario.event_type == "unknown":
            # A disaster + supply interruption is primarily a disaster event.
            if any(term in lowered for term in _NATURAL):
                updates["event_type"] = "natural_disaster"
            elif any(term in lowered for term in _POLICY):
                updates["event_type"] = "economic_policy"
            elif any(term in lowered for term in _SUPPLY):
                updates["event_type"] = "supply_chain"

        if scenario.duration_days is None:
            match = _DURATION.search(text)
            if match:
                duration = int(match.group(1))
                if 0 <= duration <= 3650:
                    updates["duration_days"] = duration

        # model_copy(update=...) bypasses Pydantic validation; explicitly
        # validate the merged data for safe and stable API contracts.
        return Scenario.model_validate({**scenario.model_dump(), **updates})

    def inspect(self, scenario: Scenario) -> EventParseDetails:
        """Return optional extracted details and important missing fields.

        This method never modifies the Scenario or feeds magnitude to the
        deterministic risk engine as a surrogate for severity.
        """
        parsed = self.run(scenario)
        magnitude = None
        notes: list[str] = []
        if parsed.event_type == "natural_disaster" and ("地震" in scenario.description or "earthquake" in scenario.description.casefold()):
            match = _MAGNITUDE.search(scenario.description)
            if match:
                value = float(match.group(1))
                if 0 <= value <= 10:
                    magnitude = value
                else:
                    notes.append("地震規模超出支援範圍，需人工確認")
        missing: list[str] = []
        if parsed.event_type == "unknown":
            missing.append("event_type")
        if parsed.severity is None:
            missing.append("severity")
        if not parsed.seed_nodes:
            missing.append("seed_nodes")
        if not parsed.region:
            missing.append("region")
        if not parsed.product:
            missing.append("product")
        return EventParseDetails(
            earthquake_magnitude=magnitude,
            missing_required=tuple(missing),
            notes=tuple(notes),
        )
