from types import SimpleNamespace

from resolver.bake.dedup import (
    Rename, dedup_wave, iter_scaffolds, load_registry, normalize, save_registry,
)
from resolver.bake.schema import BakeRecord, Depth, contract_fingerprint
from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Target, Trigger

LADDER = ["claude-sonnet-5"]


class FakeMessages:
    def __init__(self, names):
        self.names = list(names)
        self.captured = []

    def parse(self, **kwargs):
        self.captured.append(kwargs)
        name = self.names.pop(0)
        parsed = None if name is None else Rename(name=name)
        return SimpleNamespace(parsed_output=parsed, stop_reason="end_turn")


class FakeClient:
    def __init__(self, names):
        self.messages = FakeMessages(names)


def _draft(name):
    return GadgetDraft(name=name, description="flavor", logic="trace", stages=[
        Stage(trigger=Trigger.ON_HIT,
              effects=[Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=1.0)]),
    ])


def _record(cid, names3):
    return BakeRecord(
        combo_id=cid, status="resolved", contract_fingerprint=contract_fingerprint(),
        baked_at="t", scaffolds={d: [_draft(n)] for d, n in zip(Depth, names3)},
    )


def test_normalize_folds_case_punctuation_and_whitespace():
    # punctuation strips without leaving a space; whitespace collapses; casefold applies
    assert normalize("Load-Bearing  Argument!") == normalize("LOADBEARING argument")
    assert normalize("The  Bouncer") == "the bouncer"
    assert normalize("Mk. II") == normalize("mk ii")


def test_iter_scaffolds_yields_first_baked_order():
    records = [_record("c1", ["a", "b", "c"]), _record("c2", ["d", "e", "f"])]
    owners = [owner for owner, _ in iter_scaffolds(records)]
    assert owners == [
        ("c1", "SHALLOW", 0), ("c1", "MEDIUM", 0), ("c1", "DEEP", 0),
        ("c2", "SHALLOW", 0), ("c2", "MEDIUM", 0), ("c2", "DEEP", 0),
    ]


def test_first_baked_keeps_the_name_and_loser_is_renamed():
    records = [_record("c1", ["Same Name", "b", "c"]), _record("c2", ["Same Name", "e", "f"])]
    registry = {}
    events = dedup_wave(records, registry, FakeClient(["Fresh Name"]), LADDER)
    assert records[0].scaffolds[Depth.SHALLOW][0].name == "Same Name"
    assert records[1].scaffolds[Depth.SHALLOW][0].name == "Fresh Name"
    assert events == [{"owner": ["c2", "SHALLOW", 0], "old": "Same Name",
                       "new": "Fresh Name", "outcome": "renamed"}]
    assert registry[normalize("Same Name")]["owner"] == ["c1", "SHALLOW", 0]
    assert registry[normalize("Fresh Name")]["owner"] == ["c2", "SHALLOW", 0]


def test_registry_from_an_earlier_wave_wins():
    registry = {normalize("Old Glory"): {"owner": ["old", "DEEP", 0], "display": "Old Glory"}}
    records = [_record("c1", ["Old Glory", "b", "c"])]
    dedup_wave(records, registry, FakeClient(["New Name"]), LADDER)
    assert records[0].scaffolds[Depth.SHALLOW][0].name == "New Name"
    assert registry[normalize("Old Glory")]["owner"] == ["old", "DEEP", 0]


def test_rename_touches_only_the_name():
    records = [_record("c1", ["Dup", "b", "c"]), _record("c2", ["Dup", "e", "f"])]
    before = records[1].scaffolds[Depth.SHALLOW][0].model_dump()
    dedup_wave(records, {}, FakeClient(["Renamed"]), LADDER)
    after = records[1].scaffolds[Depth.SHALLOW][0].model_dump()
    assert after["name"] == "Renamed"
    assert {k: v for k, v in after.items() if k != "name"} == \
        {k: v for k, v in before.items() if k != "name"}


def test_suffix_fallback_after_two_colliding_rename_attempts():
    records = [_record("c1", ["Dup", "b", "c"]), _record("c2", ["Dup", "e", "f"])]
    # both rename attempts return names that are already taken
    events = dedup_wave(records, {}, FakeClient(["Dup", "b"]), LADDER)
    assert events[0]["outcome"] == "suffixed"
    new = records[1].scaffolds[Depth.SHALLOW][0].name
    assert new.startswith("Dup") and new != "Dup"


def test_refused_rename_call_counts_as_a_failed_attempt():
    records = [_record("c1", ["Dup", "b", "c"]), _record("c2", ["Dup", "e", "f"])]
    events = dedup_wave(records, {}, FakeClient([None, None]), LADDER)
    assert events[0]["outcome"] == "suffixed"


def test_registry_round_trips(tmp_path):
    path = tmp_path / "names.json"
    registry = {"x": {"owner": ["c", "DEEP", 0], "display": "X"}}
    save_registry(path, registry)
    assert load_registry(path) == registry
    assert load_registry(tmp_path / "missing.json") == {}
