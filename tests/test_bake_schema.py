from resolver.bake.schema import (
    CONTRACT_VERSION, BakeRecord, Depth, ScaffoldSet,
    combo_id, contract_fingerprint, _fingerprint,
)
from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Target, Trigger
from resolver.items import CATALOG, Build


def _draft(name="Fake"):
    return GadgetDraft(
        name=name, description="d", logic="l",
        stages=[Stage(trigger=Trigger.ON_HIT, effects=[
            Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=2.0),
        ])],
    )


def test_combo_id_canonical_format():
    build = Build(delivery_item=CATALOG["baseball bat"],
                  modifier_item=CATALOG["car battery"])
    assert combo_id(build) == "d:baseball bat|dmg:-|u:-|m:car battery"


def test_combo_id_is_role_sensitive():
    a = Build(delivery_item=CATALOG["baseball bat"], damage_item=CATALOG["car battery"])
    b = Build(delivery_item=CATALOG["baseball bat"], modifier_item=CATALOG["car battery"])
    assert combo_id(a) != combo_id(b)


def test_fingerprint_is_stable_and_hex():
    fp = contract_fingerprint()
    assert fp == contract_fingerprint()
    assert len(fp) == 64 and int(fp, 16) >= 0


def test_fingerprint_changes_when_vocabulary_changes():
    base = {"delivery": ["SWING"], "effect": ["DAMAGE"], "trigger": ["ON_HIT"], "target": ["STRUCK"]}
    widened = {**base, "effect": ["DAMAGE", "TELEPORT"]}
    assert _fingerprint(base) != _fingerprint(widened)


def test_fingerprint_ignores_token_order():
    a = {"delivery": ["SWING", "SLAM"], "effect": [], "trigger": [], "target": []}
    b = {"delivery": ["SLAM", "SWING"], "effect": [], "trigger": [], "target": []}
    assert _fingerprint(a) == _fingerprint(b)


def test_scaffold_set_has_one_draft_per_depth():
    s = ScaffoldSet(shallow=_draft("a"), medium=_draft("b"), deep=_draft("c"))
    assert [s.shallow.name, s.medium.name, s.deep.name] == ["a", "b", "c"]


def test_bake_record_round_trips_through_json():
    record = BakeRecord(
        combo_id="d:baseball bat|dmg:-|u:-|m:car battery",
        status="resolved",
        contract_fingerprint=contract_fingerprint(),
        model="claude-sonnet-5",
        baked_at="2026-07-17T00:00:00+00:00",
        usage={"input_tokens": 100, "output_tokens": 200},
        scaffolds={Depth.SHALLOW: [_draft()], Depth.MEDIUM: [_draft()], Depth.DEEP: [_draft()]},
    )
    line = record.model_dump_json()
    assert BakeRecord.model_validate_json(line) == record
    assert record.contract_version == CONTRACT_VERSION == "v1"


def test_unresolved_record_defaults_to_empty_scaffolds():
    record = BakeRecord(combo_id="x", status="unresolved",
                        contract_fingerprint=contract_fingerprint(), baked_at="t")
    assert record.scaffolds == {} and record.model is None and record.usage == {}
