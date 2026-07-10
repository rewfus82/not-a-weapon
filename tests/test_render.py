from resolver.contract import (
    Category, Delivery, Effect, EffectKind, GadgetDraft, ResolvedGadget, Stage, Tier, Trigger,
)
from resolver.render import RunResult, render_run, render_fallback_summary


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


def test_render_marks_fallback_slots_with_tag_and_reason():
    results = [
        RunResult("fan+duck", _resolved("Plan B", Tier.RARE, Category.WEAPON, False), 1, 3,
                  source="fallback", reason="RuntimeError: no GadgetDraft (stop_reason='refusal')"),
        RunResult("fan+duck", _resolved("Live One", Tier.RARE, Category.WEAPON, False), 2, 3),
    ]
    out = render_run(results)
    assert out.count("[fallback]") == 1          # only the fallback slot is tagged
    assert "RuntimeError: no GadgetDraft" in out # its reason is shown
    assert "Plan B" in out and "Live One" in out


def test_fallback_summary_reports_rate_including_zero_builds():
    results = [
        RunResult("broom+oil", _resolved("A", Tier.DUD, Category.WEAPON, False), 1, 1),
        RunResult("fan+duck", _resolved("B", Tier.RARE, Category.WEAPON, False), 1, 3,
                  source="fallback", reason="x"),
        RunResult("fan+duck", _resolved("C", Tier.RARE, Category.WEAPON, False), 2, 3,
                  source="fallback", reason="x"),
        RunResult("fan+duck", _resolved("D", Tier.RARE, Category.WEAPON, False), 3, 3),
    ]
    summary = render_fallback_summary(results)
    assert summary.startswith("fallbacks:")
    assert "broom+oil 0/1" in summary            # zero-fallback build still shown, no percent
    assert "fan+duck 2/3 (67%)" in summary       # round(100*2/3) == 67
