import pytest

from resolver.bake.derive import BUDGET_LOW, DEPTH_TIERS, JITTER, derive_instance
from resolver.bake.schema import Depth
from resolver.clamp import OVER_BUDGET_FACTOR, TIER_BUDGET, total_cost
from resolver.contract import (
    Category, Effect, EffectKind, GadgetDraft, Stage, Target, Tier, Trigger,
)
from resolver.items import CATALOG, Build

BUILD = Build(delivery_item=CATALOG["baseball bat"], modifier_item=CATALOG["car battery"])


def _scaffold():
    # float-only, two stages: proportions are what the scaffold carries
    return GadgetDraft(
        name="Scaffold", description="d", logic="l",
        stages=[
            Stage(trigger=Trigger.ON_HIT, effects=[
                Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=3.0),
                Effect(kind=EffectKind.KNOCKBACK, target=Target.STRUCK, amount=1.0, duration=1.0),
            ]),
            Stage(trigger=Trigger.ON_KILL, effects=[
                Effect(kind=EffectKind.HEAL, target=Target.SELF, amount=1.0),
            ]),
        ],
    )


def test_depth_bands_cover_all_six_tiers_exactly_once():
    assert DEPTH_TIERS == {
        Depth.SHALLOW: (Tier.DUD, Tier.COMMON),
        Depth.MEDIUM: (Tier.UNCOMMON, Tier.RARE),
        Depth.DEEP: (Tier.EPIC, Tier.LEGENDARY),
    }


def test_same_seed_gives_identical_instance():
    a = derive_instance(_scaffold(), BUILD, Tier.RARE, seed=42)
    b = derive_instance(_scaffold(), BUILD, Tier.RARE, seed=42)
    assert a.draft.model_dump() == b.draft.model_dump()
    assert (a.tier, a.category, a.harmless) == (b.tier, b.category, b.harmless)


def test_different_seeds_give_different_magnitudes():
    a = derive_instance(_scaffold(), BUILD, Tier.RARE, seed=1)
    b = derive_instance(_scaffold(), BUILD, Tier.RARE, seed=2)
    assert a.draft.model_dump() != b.draft.model_dump()


@pytest.mark.parametrize("tier", list(Tier))
def test_cost_lands_in_the_seeded_band_at_every_tier(tier):
    for seed in range(10):
        out = derive_instance(_scaffold(), BUILD, tier, seed=seed)
        total = total_cost(out.draft)
        assert total <= TIER_BUDGET[tier] * OVER_BUDGET_FACTOR + 1e-9
        assert total >= TIER_BUDGET[tier] * BUDGET_LOW - 1e-9


def test_count_heavy_scaffold_never_exceeds_the_cap():
    draft = GadgetDraft(name="Counts", description="d", logic="l", stages=[
        Stage(trigger=Trigger.ON_HIT, effects=[
            Effect(kind=EffectKind.CHAIN, target=Target.STRUCK, amount=1.0, count=100),
        ]),
    ])
    out = derive_instance(draft, BUILD, Tier.DUD, seed=0)
    assert total_cost(out.draft) <= TIER_BUDGET[Tier.DUD] * OVER_BUDGET_FACTOR + 1e-9


def test_self_chassis_scaffold_is_repaired():
    kit = Build(delivery_item=CATALOG["adrenaline shot"])
    draft = GadgetDraft(name="Kit", description="d", logic="l", stages=[
        Stage(trigger=Trigger.ON_IMPACT, effects=[
            Effect(kind=EffectKind.SPEED, target=Target.STRUCK, amount=2.0),
        ]),
    ])
    out = derive_instance(draft, kit, Tier.COMMON, seed=7)
    assert out.draft.stages[0].trigger is Trigger.ON_USE
    assert all(e.target is Target.SELF for s in out.draft.stages for e in s.effects)


def test_zero_cost_scaffold_passes_through():
    draft = GadgetDraft(name="Empty", description="d", logic="l", stages=[])
    out = derive_instance(draft, BUILD, Tier.LEGENDARY, seed=3)
    assert out.draft.stages == [] and out.category is Category.DUD


def test_input_draft_is_never_mutated():
    draft = _scaffold()
    before = draft.model_dump()
    derive_instance(draft, BUILD, Tier.EPIC, seed=9)
    assert draft.model_dump() == before


def test_jitter_stays_inside_its_band():
    # after fit, per-effect *proportions* deviate from the scaffold's by at
    # most the jitter ratio ((1+J)/(1-J)); a plain rescale would keep them exact
    scaffold = _scaffold()
    out = derive_instance(scaffold, BUILD, Tier.RARE, seed=11)
    base = scaffold.stages[0].effects
    got = out.draft.stages[0].effects
    ratio = (got[0].amount / got[1].amount) / (base[0].amount / base[1].amount)
    band = (1 + JITTER) / (1 - JITTER)
    assert 1 / band - 1e-9 <= ratio <= band + 1e-9
