"""Deterministic fallback resolver: keeps the whole pipeline functional with
no API key. Composes a real (if simple) draft from the build's items: base
delivery from the chassis, effects derived from substance/mechanism tags,
overlays unlocked at RARE+ from modifier tags. Its signature matches the LLM
resolver's `resolve`, so the harness can swap them freely.
"""
from __future__ import annotations

from resolver.clamp import TIER_BUDGET
from resolver.contract import (
    Delivery, Effect, EffectKind, GadgetDraft, Role, Stage, Target, Tier, Trigger,
    default_target, tier_at_least,
)
from resolver.items import Build
from resolver.interactions import effects_for


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


def substance_stages(effects: list[Effect], armed: bool) -> list[Stage]:
    """A substance chassis is a thrown container that bursts on impact —
    armed payloads burst inert and fire on ignition (ON_TRIGGER)."""
    if armed:
        return [
            Stage(trigger=Trigger.ON_IMPACT, effects=[], note="burst"),
            Stage(trigger=Trigger.ON_TRIGGER, effects=effects, note="armed patch"),
        ]
    return [Stage(trigger=Trigger.ON_IMPACT, effects=effects, note="burst")]


def _stages_for(build: Build, effects: list[Effect]) -> list[Stage]:
    """Mechanism chassis hit (ON_HIT); a substance chassis is a thrown
    container that bursts (ON_IMPACT) — armed payloads burst inert and
    fire on ignition (ON_TRIGGER); a self-kit chassis is used on yourself
    (ON_USE, everything lands on the wielder)."""
    chassis = build.delivery_item
    if chassis.delivery is Delivery.SELF:
        for e in effects:
            e.target = Target.SELF
        return [Stage(trigger=Trigger.ON_USE, effects=effects, note="self-kit")]
    if chassis.delivery is None and chassis.base_use is not None:
        return substance_stages(effects, chassis.base_use.armed)
    return [Stage(trigger=Trigger.ON_HIT, effects=effects, note="composed")]


def resolve(build: Build, tier: Tier) -> GadgetDraft:
    tag_union = frozenset().union(
        *(it.tags for _, it in build.slots() if it is not None)
    ) if any(it for _, it in build.slots()) else frozenset()

    base_effects = effects_for(tag_union) or [EffectKind.DAMAGE]
    # base: strongest single effect at DUD; more of the chain deeper
    take = 1 if tier is Tier.DUD else (2 if not tier_at_least(tier, Tier.RARE) else len(base_effects))
    chosen = base_effects[:take]

    # §6: every build at a tier spends the same budget — it splits across the
    # composed effects (overlays ride at half a base share). Overlays only
    # unlock at RARE+; a kind the base chain already has is skipped.
    parts: list[tuple[EffectKind, float, str]] = [(k, 1.0, "base") for k in chosen]
    if tier_at_least(tier, Tier.RARE):
        for k in _overlays(build):
            if k in chosen:
                continue
            parts.append((k, 0.5, "overlay"))
    budget = TIER_BUDGET[tier]
    total_weight = sum(w for _, w, _ in parts)
    effects = [
        Effect(kind=k, target=default_target(k), amount=budget * w / total_weight, note=note)
        for k, w, note in parts
    ]

    name_bits = " + ".join(it.name for _, it in build.slots() if it is not None)
    return GadgetDraft(
        name=f"Improvised {build.delivery_item.name.title()}",
        description=f"{name_bits}, composed by the simulation.",
        logic=(
            f"Base delivery: {build.delivery.value}. "
            f"Effects from tags {sorted(tag_union)}: "
            f"{[e.kind.value for e in effects]}."
        ),
        stages=_stages_for(build, effects),
    )
