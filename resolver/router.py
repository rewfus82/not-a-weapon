"""The cost lever: pick deterministic vs. LLM from (coherence, tier). Sensible
combos and all low tiers are free; LLM spend concentrates on the absurd frontier.
"""
from __future__ import annotations

from resolver.contract import Tier, tier_at_least
from resolver.coherence import coherence
from resolver.items import Build

# Spec says ~0.66; 0.67 keeps a 2/3-coherent build (one disconnected pair in a
# 3-item build) in the middle band — 0.66 would misclassify it as coherent.
C_HIGH: float = 0.67
C_LOW: float = 0.33


def route(build: Build, tier: Tier) -> str:
    if tier in (Tier.DUD, Tier.COMMON):
        return "deterministic"
    c = coherence(build)
    if c >= C_HIGH:
        return "deterministic"
    if c <= C_LOW:
        return "llm" if tier_at_least(tier, Tier.UNCOMMON) else "deterministic"
    return "llm" if tier_at_least(tier, Tier.RARE) else "deterministic"
