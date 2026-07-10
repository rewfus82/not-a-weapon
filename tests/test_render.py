from resolver.contract import (
    Category, Delivery, Effect, EffectKind, GadgetDraft, ResolvedGadget, Stage, Tier, Trigger,
)
from resolver.render import RunResult, render_run


def _resolved(name, tier, category, harmless):
    draft = GadgetDraft(
        name=name, description="flavor", logic="the trace",
        stages=[Stage(trigger=Trigger.ON_HIT, effects=[Effect(kind=EffectKind.BURN, amount=14, duration=3, note="grease")])],
    )
    return ResolvedGadget(
        draft=draft, delivery=Delivery.SWING, tier=tier,
        category=category, harmless=harmless, color="amber", params={},
    )


def test_render_groups_by_build_and_shows_both_axes():
    results = [
        RunResult("broom+oil", _resolved("Damp Sweep", Tier.DUD, Category.WEAPON, False), 1, 1),
        RunResult("broom+oil", _resolved("Last Call", Tier.LEGENDARY, Category.WEAPON, False), 1, 3),
        RunResult("broom+oil", _resolved("Second Round", Tier.LEGENDARY, Category.WEAPON, False), 2, 3),
    ]
    out = render_run(results)
    assert "broom+oil" in out
    assert "SWING" in out and "amber" in out
    assert "DUD" in out and "LEGENDARY" in out       # depth across tiers
    assert "Damp Sweep" in out and "Last Call" in out
    assert "the trace" in out                        # logic is shown
    assert "BURN" in out                             # staged effect is shown
    assert "[run 2/3]" in out                        # variety-within-tier instances labelled


def test_render_prints_build_header_once_per_build():
    results = [
        RunResult("broom+oil", _resolved("A", Tier.DUD, Category.WEAPON, False), 1, 1),
        RunResult("broom+oil", _resolved("B", Tier.COMMON, Category.WEAPON, False), 1, 1),
    ]
    out = render_run(results)
    assert out.count("BUILD: broom+oil") == 1
