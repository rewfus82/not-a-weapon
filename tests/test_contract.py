import pytest
from pydantic import ValidationError

from resolver.contract import (
    Delivery, EffectKind, Target, Trigger, Category, Tier,
    Effect, Stage, GadgetDraft, ResolvedGadget, default_target,
    LETHAL_KINDS, CONTROL_KINDS, SELF_KINDS, UTILITY_KINDS, MELEE_DELIVERIES,
)


def test_enums_cover_the_contract_vocabulary():
    assert {d.value for d in Delivery} == {
        "HITSCAN", "PROJECTILE", "LOBBED", "BEAM", "THROWN", "SPRAY", "PLACED",
        "SWING", "THRUST", "SLAM", "WHIP", "GUARD", "SELF", "DASH",
    }
    assert {e.value for e in EffectKind} == {
        "DAMAGE", "BURN", "EXPLODE", "PIERCE", "CHAIN",
        "KNOCKBACK", "LAUNCH", "STAGGER", "SNARE", "SLOW", "FREEZE",
        "HEAL", "SHIELD", "SPEED", "SUMMON", "LURE",
    }
    assert {t.value for t in Trigger} == {
        "ON_USE", "ON_HIT", "ON_IMPACT", "ON_TRIGGER", "ON_EXPIRE", "ON_KILL", "ON_BLOCK",
    }
    assert {t.value for t in Tier} == {
        "DUD", "COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY",
    }


def test_gadget_draft_exposes_only_model_owned_fields():
    # The model may NOT emit delivery, tier, category, harmless, color, params.
    assert set(GadgetDraft.model_fields) == {"name", "description", "logic", "stages"}


def test_valid_draft_round_trips():
    draft = GadgetDraft(
        name="Last Call",
        description="A broom with a grudge.",
        logic="bristles hold the oil; the sweep flings it.",
        stages=[Stage(trigger=Trigger.ON_HIT, effects=[Effect(kind=EffectKind.BURN, target=Target.STRUCK, amount=14, duration=3)])],
    )
    assert draft.stages[0].effects[0].kind is EffectKind.BURN


def test_schema_rejects_off_contract_effect_kind():
    with pytest.raises(ValidationError):
        Stage(trigger=Trigger.ON_HIT, effects=[Effect(kind="TELEPORT", target=Target.STRUCK, amount=1)])


def test_schema_rejects_off_contract_trigger():
    with pytest.raises(ValidationError):
        Stage(trigger="ON_SNEEZE", effects=[])


def test_family_sets_partition_the_effect_kinds():
    families = LETHAL_KINDS | CONTROL_KINDS | SELF_KINDS | UTILITY_KINDS
    assert families == set(EffectKind)
    assert EffectKind.SUMMON in LETHAL_KINDS  # a summoned swarm can hurt -> lethal
    assert Delivery.SWING in MELEE_DELIVERIES


def test_resolved_gadget_carries_code_owned_fields():
    draft = GadgetDraft(name="x", description="", logic="", stages=[])
    rg = ResolvedGadget(
        draft=draft, delivery=Delivery.SWING, tier=Tier.DUD,
        category=Category.DUD, harmless=True, color="amber", params={},
    )
    assert rg.delivery is Delivery.SWING and rg.harmless is True


def test_roles_and_flags_exist():
    from resolver.contract import Role, Flag
    assert {r.value for r in Role} == {"MECHANISM", "MODIFIER", "SUBSTANCE"}
    assert {f.value for f in Flag} == {
        "WIELDABLE", "FIREARM", "AMMUNITION", "LOADABLE", "BASE_WEAPON"
    }


def test_tier_order_is_monotonic_and_total():
    from resolver.contract import TIER_ORDER
    assert set(TIER_ORDER) == set(Tier)
    assert TIER_ORDER[Tier.DUD] < TIER_ORDER[Tier.LEGENDARY]


def test_tier_at_least():
    from resolver.contract import tier_at_least
    assert tier_at_least(Tier.RARE, Tier.UNCOMMON) is True
    assert tier_at_least(Tier.COMMON, Tier.RARE) is False
    assert tier_at_least(Tier.RARE, Tier.RARE) is True


def test_target_enum_covers_the_contract():
    assert {t.value for t in Target} == {"SELF", "STRUCK"}


def test_effect_requires_a_target():
    with pytest.raises(ValidationError):
        Effect(kind=EffectKind.DAMAGE, amount=1)


def test_effect_rejects_negative_amount():
    with pytest.raises(ValidationError):
        Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=-1)


def test_default_target_is_self_only_for_the_self_family():
    for kind in (EffectKind.HEAL, EffectKind.SHIELD, EffectKind.SPEED):
        assert default_target(kind) is Target.SELF
    for kind in (EffectKind.DAMAGE, EffectKind.SNARE, EffectKind.LURE, EffectKind.SUMMON):
        assert default_target(kind) is Target.STRUCK
