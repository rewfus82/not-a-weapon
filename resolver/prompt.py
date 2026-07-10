"""Loads the hardened, jargon-free system prompt and renders the per-build
user message. The prompt is data (a text file), not code, so it can be
iterated between test runs without touching Python.
"""
from __future__ import annotations

from pathlib import Path

from resolver.contract import Tier
from resolver.items import Build

_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.txt"
SYSTEM_PROMPT: str = _PROMPT_PATH.read_text(encoding="utf-8").strip()

_TEMPLATE = """BUILD
  delivery: {delivery}
  damage:   {damage}
  utility:  {utility}
  modifier: {modifier}

LOCKED DELIVERY FORM: {form}
TARGET TIER: {tier}

Resolve this build to the target tier. Trace every effect back to a stated
property of the specific objects above. Compose within the locked delivery form."""


def _slot_line(item) -> str:
    if item is None:
        return "empty"
    return f"{item.name} — {', '.join(item.associations)}"


def render_user_message(build: Build, tier: Tier) -> str:
    slots = dict(build.slots())
    return _TEMPLATE.format(
        delivery=_slot_line(slots["delivery"]),
        damage=_slot_line(slots["damage"]),
        utility=_slot_line(slots["utility"]),
        modifier=_slot_line(slots["modifier"]),
        form=build.delivery.value,
        tier=tier.value,
    )
