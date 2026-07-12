"""Deterministic fallback resolver: keeps the whole pipeline functional with
no API key. Composes a real (if simple) draft from the build's items: base
delivery from the chassis, effects derived from substance/mechanism tags,
overlays unlocked at RARE+ from modifier tags. Its signature matches the LLM
resolver's `resolve`, so the harness can swap them freely.
"""
from __future__ import annotations

from resolver.contract import (
    Effect, EffectKind, GadgetDraft, Role, Stage, Tier, Trigger, tier_at_least,
)
from resolver.items import Build
from resolver.interactions import effects_for

_TIER_SEED: dict[Tier, float] = {
    Tier.DUD: 2.0, Tier.COMMON: 6.0, Tier.UNCOMMON: 10.0,
    Tier.RARE: 18.0, Tier.EPIC: 30.0, Tier.LEGENDARY: 45.0,
}


def _role_items(build: Build, role: Role):
    return [it for _, it in build.slots() if it is not None and role in it.roles]


def _overlays(build: Build) -> list[EffectKind]:
    overlays: list[EffectKind] = []
    mods = _role_items(build, Role.MODIFIER)
    for m in mods:
        if "electrical" in m.tags:
            overlays.append(EffectKind.CHAIN)
        if "powder" in m.tags or ("pressurized-gas" in m.tags and "flammable" in m.tags):
            overlays.append(EffectKind.EXPLODE)
    if any("sharp" in it.tags for _, it in build.slots() if it is not None):
        overlays.append(EffectKind.PIERCE)
    # de-dup, stable order
    seen, out = set(), []
    for k in overlays:
        if k not in seen:
            seen.add(k); out.append(k)
    return out


def resolve(build: Build, tier: Tier) -> GadgetDraft:
    seed = _TIER_SEED[tier]
    tag_union = frozenset().union(
        *(it.tags for _, it in build.slots() if it is not None)
    ) if any(it for _, it in build.slots()) else frozenset()

    base_effects = effects_for(tag_union) or [EffectKind.DAMAGE]
    # base: strongest single effect at DUD; more of the chain deeper
    take = 1 if tier is Tier.DUD else (2 if not tier_at_least(tier, Tier.RARE) else len(base_effects))
    chosen = base_effects[:take]

    effects = [Effect(kind=k, amount=seed, note="base") for k in chosen]
    # overlays only unlock at RARE+
    if tier_at_least(tier, Tier.RARE):
        for k in _overlays(build):
            effects.append(Effect(kind=k, amount=seed * 0.5, note="overlay"))

    name_bits = " + ".join(it.name for _, it in build.slots() if it is not None)
    return GadgetDraft(
        name=f"Improvised {build.delivery_item.name.title()}",
        description=f"{name_bits}, composed by the simulation.",
        logic=(
            f"Base delivery: {build.delivery.value}. "
            f"Effects from tags {sorted(tag_union)}: "
            f"{[e.kind.value for e in effects]}."
        ),
        stages=[Stage(trigger=Trigger.ON_HIT, effects=effects, note="composed")],
    )
