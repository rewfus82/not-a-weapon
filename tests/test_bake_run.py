from types import SimpleNamespace

from resolver.bake.run import (
    BAKE_PROMPT, TOP_UP_WIDTH, bake_combo, load_records, palette,
    render_bake_message, run_wave, width, write_records,
)
from resolver.bake.schema import BakeRecord, Depth, ScaffoldSet, combo_id, contract_fingerprint
from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Target, Trigger
from resolver.items import CATALOG, Build

BUILD = Build(delivery_item=CATALOG["baseball bat"], modifier_item=CATALOG["car battery"])
LADDER = ["claude-sonnet-5", "claude-sonnet-5", "claude-opus-4-8"]


class FakeMessages:
    """One canned outcome per parse() call: a ScaffoldSet (success), None
    (refusal), or an Exception (transport error)."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.models_used = []
        self.captured = []

    def parse(self, **kwargs):
        self.captured.append(kwargs)
        self.models_used.append(kwargs["model"])
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        stop = "refusal" if outcome is None else "end_turn"
        return SimpleNamespace(parsed_output=outcome, stop_reason=stop,
                               usage=SimpleNamespace(input_tokens=100, output_tokens=200))


class FakeClient:
    def __init__(self, outcomes):
        self.messages = FakeMessages(outcomes)


def _draft(name, kind=EffectKind.DAMAGE, target=Target.STRUCK):
    return GadgetDraft(name=name, description="d", logic="l", stages=[
        Stage(trigger=Trigger.ON_HIT,
              effects=[Effect(kind=kind, target=target, amount=1.0)]),
    ])


def _narrow_set():
    # all three depths read the same (kind, target) palette -> width 1
    return ScaffoldSet(shallow=_draft("a"), medium=_draft("b"), deep=_draft("c"))


def _wide_set():
    # three pairwise-distinct palettes -> width 3
    return ScaffoldSet(
        shallow=_draft("a", EffectKind.DAMAGE),
        medium=_draft("b", EffectKind.SNARE),
        deep=_draft("c", EffectKind.HEAL, Target.SELF),
    )


def test_bake_message_lists_slots_without_a_tier_line():
    msg = render_bake_message(BUILD)
    assert "baseball bat" in msg and "car battery" in msg
    assert "LOCKED DELIVERY FORM: SWING" in msg
    assert "TIER" not in msg.replace("LOCKED DELIVERY", "")


def test_bake_combo_resolved_record():
    client = FakeClient([_narrow_set()])
    record = bake_combo(client, LADDER, BUILD)
    assert record.status == "resolved" and record.combo_id == combo_id(BUILD)
    assert record.model == "claude-sonnet-5"
    assert record.contract_fingerprint == contract_fingerprint()
    assert [len(record.scaffolds[d]) for d in Depth] == [1, 1, 1]
    assert record.usage == {"input_tokens": 100, "output_tokens": 200}
    call = client.messages.captured[0]
    assert call["system"] == BAKE_PROMPT and call["output_format"] is ScaffoldSet
    assert "temperature" not in call and "top_p" not in call and "top_k" not in call


def test_ladder_escalates_past_refusal_and_transport_error():
    client = FakeClient([None, RuntimeError("boom"), _narrow_set()])
    record = bake_combo(client, LADDER, BUILD)
    assert record.status == "resolved" and record.model == "claude-opus-4-8"
    assert client.messages.models_used == LADDER


def test_exhausted_ladder_records_unresolved_without_reasons():
    client = FakeClient([None, None, None])
    record = bake_combo(client, LADDER, BUILD)
    assert record.status == "unresolved" and record.scaffolds == {}
    assert record.model is None
    # rates only: no reason text anywhere in the stored line
    assert "refusal" not in record.model_dump_json()


def test_width_signal_counts_distinct_palettes():
    assert palette(_draft("x")) == frozenset({(EffectKind.DAMAGE, Target.STRUCK)})
    narrow = bake_combo(FakeClient([_narrow_set()]), LADDER, BUILD)
    assert width(narrow) == 1
    wide = bake_combo(FakeClient([_wide_set(), _wide_set()]), LADDER, BUILD)
    assert width(wide) == TOP_UP_WIDTH


def test_wide_combo_gets_exactly_one_top_up_call():
    client = FakeClient([_wide_set(), _wide_set()])
    record = bake_combo(client, LADDER, BUILD)
    assert len(client.messages.captured) == 2
    assert [len(record.scaffolds[d]) for d in Depth] == [2, 2, 2]
    assert record.usage == {"input_tokens": 200, "output_tokens": 400}
    top_up_msg = client.messages.captured[1]["messages"][0]["content"]
    assert "ALREADY HAVE" in top_up_msg and "a" in top_up_msg


def test_narrow_combo_gets_no_top_up_call():
    client = FakeClient([_narrow_set()])
    bake_combo(client, LADDER, BUILD)
    assert len(client.messages.captured) == 1


def test_failed_top_up_keeps_the_base_scaffolds():
    client = FakeClient([_wide_set(), None, None, None])
    record = bake_combo(client, LADDER, BUILD)
    assert record.status == "resolved"
    assert [len(record.scaffolds[d]) for d in Depth] == [1, 1, 1]


def test_run_wave_skips_existing_and_appends_new(tmp_path):
    path = tmp_path / "scaffolds.jsonl"
    first = bake_combo(FakeClient([_narrow_set()]), LADDER, BUILD)
    write_records(path, {first.combo_id: first})
    other = Build(delivery_item=CATALOG["crowbar"])
    client = FakeClient([_narrow_set()])
    stats = run_wave(client, LADDER, {combo_id(BUILD): BUILD, combo_id(other): other}, path)
    assert stats["skipped"] == 1 and stats["attempted"] == 1
    assert client.messages.models_used == ["claude-sonnet-5"]
    assert set(load_records(path)) == {combo_id(BUILD), combo_id(other)}


def test_retry_unresolved_replaces_the_line(tmp_path):
    path = tmp_path / "scaffolds.jsonl"
    dead = bake_combo(FakeClient([None, None, None]), LADDER, BUILD)
    write_records(path, {dead.combo_id: dead})
    stats = run_wave(FakeClient([_narrow_set()]), LADDER,
                     {combo_id(BUILD): BUILD}, path, retry_unresolved=True)
    records = load_records(path)
    assert stats["attempted"] == 1
    assert len(records) == 1 and records[combo_id(BUILD)].status == "resolved"


def test_run_wave_without_retry_flag_keeps_unresolved(tmp_path):
    path = tmp_path / "scaffolds.jsonl"
    dead = bake_combo(FakeClient([None, None, None]), LADDER, BUILD)
    write_records(path, {dead.combo_id: dead})
    stats = run_wave(FakeClient([]), LADDER, {combo_id(BUILD): BUILD}, path)
    assert stats["skipped"] == 1 and load_records(path)[combo_id(BUILD)].status == "unresolved"
