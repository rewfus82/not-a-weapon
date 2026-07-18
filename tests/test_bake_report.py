from resolver.bake.report import instance_seed, wave_report
from resolver.bake.schema import BakeRecord, Depth, contract_fingerprint
from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Target, Tier, Trigger
from resolver.items import CATALOG, Build


def _draft(name, kind=EffectKind.DAMAGE):
    return GadgetDraft(name=name, description="d", logic="l", stages=[
        Stage(trigger=Trigger.ON_HIT,
              effects=[Effect(kind=kind, target=Target.STRUCK, amount=2.0)]),
    ])


def _resolved(cid, kinds):
    return BakeRecord(
        combo_id=cid, status="resolved", contract_fingerprint=contract_fingerprint(),
        model="claude-sonnet-5", baked_at="t",
        usage={"input_tokens": 1000, "output_tokens": 1000},
        scaffolds={d: [_draft(f"{cid}-{d.value}", k)] for d, k in zip(Depth, kinds)},
    )


BUILD = Build(delivery_item=CATALOG["baseball bat"])
RECORDS = [
    _resolved("c1", [EffectKind.DAMAGE, EffectKind.DAMAGE, EffectKind.DAMAGE]),  # width 1
    _resolved("c2", [EffectKind.DAMAGE, EffectKind.SNARE, EffectKind.HEAL]),     # width 3
    BakeRecord(combo_id="c3", status="unresolved",
               contract_fingerprint=contract_fingerprint(), baked_at="t",
               usage={"input_tokens": 500, "output_tokens": 0}),
]
BUILDS = {"c1": BUILD, "c2": BUILD, "c3": BUILD}
EVENTS = [{"owner": ["c2", "SHALLOW", 0], "old": "x", "new": "y", "outcome": "suffixed"}]


def test_instance_seed_is_deterministic_and_distinct():
    a = instance_seed("c1", "SHALLOW", 0, Tier.DUD)
    assert a == instance_seed("c1", "SHALLOW", 0, Tier.DUD)
    assert a != instance_seed("c1", "SHALLOW", 0, Tier.COMMON)
    assert a != instance_seed("c2", "SHALLOW", 0, Tier.DUD)


def test_report_is_deterministic():
    assert wave_report(RECORDS, BUILDS, EVENTS, "wave1") == \
        wave_report(RECORDS, BUILDS, EVENTS, "wave1")


def test_report_carries_the_headline_stats():
    md = wave_report(RECORDS, BUILDS, EVENTS, "wave1")
    assert "wave1" in md
    assert "unresolved: 1/3" in md
    assert "width 1: 1" in md and "width 3: 1" in md
    assert "renames: 1" in md and "suffixed: 1" in md
    assert "input tokens: 2500" in md and "output tokens: 2000" in md
    assert "$" in md  # a dollar figure is present


def test_report_covers_all_six_tiers():
    md = wave_report(RECORDS, BUILDS, EVENTS, "wave1")
    for tier in Tier:
        assert tier.value in md
