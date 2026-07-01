"""The LLM path — contract-tested with a fake client (no API key, no network).

We can't unit-test the model's creativity, but we CAN pin the contract around it:
the prompt only leaks VISIBLE associations, structured output is used, and the
result is clamped before it can reach the engine.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from combine.grammar import Build
from combine.items import CATALOG
from combine.llm import SYSTEM, build_user_message, llm_resolve
from combine.lucidity import Awakening
from combine.resolver import clamp_gadget, resolve
from combine.schema import Category, Delivery, Effect, EffectKind, Gadget, GadgetDraft, Stage, Trigger


def _b(**slots) -> Build:
    return Build(**{k: CATALOG[v] for k, v in slots.items()})


class _FakeClient:
    """Records the parse() kwargs and returns a canned parsed_output."""

    def __init__(self, gadget: Gadget | None):
        self.sink: dict = {}
        outer = self

        class _Messages:
            def parse(self, **kwargs):
                outer.sink.update(kwargs)
                return SimpleNamespace(parsed_output=gadget, stop_reason="end_turn")

        self.messages = _Messages()


def _draft(**over) -> GadgetDraft:
    """A canned LLM output (no color — the model never sets color anymore)."""
    base = dict(
        name="Apiary Snare",
        category=Category.WEAPON,
        chassis=Delivery.PLACED,
        stages=[Stage(trigger=Trigger.ON_TRIGGER,
                      effects=[Effect(kind=EffectKind.DAMAGE, amount=9999.0)])],
        logic="delivery=bear_trap -> trap",
    )
    base.update(over)
    return GadgetDraft(**base)


def _canned(**over) -> Gadget:
    """A full Gadget (with color) for testing code paths that take a Gadget directly."""
    return _draft(**over).to_gadget("#8f9196")


# --- the visible-associations guard (the legibility north star) --------------

def test_prompt_hides_associations_above_insight():
    build = _b(delivery="bear_trap", damage="beehive")
    asleep = build_user_message(build, Awakening(0.0))   # insight 0
    lucid = build_user_message(build, Awakening(1.0))    # insight 3
    assert "a papery lump" in asleep          # beehive tier-0 reading
    assert "furious bees" not in asleep       # tier-1 trait must be hidden
    assert "furious bees" in lucid            # ...and visible once awake


def test_prompt_carries_slot_names_and_era_licensing():
    msg = build_user_message(_b(delivery="bear_trap", damage="beehive"), Awakening(1.0))
    assert "delivery:" in msg and "damage:" in msg
    assert "LUCID" in msg
    assert "natural form: placed" in msg      # delivery item's chassis hint


def test_system_prompt_enumerates_the_vocabulary():
    for token in ("projectile", "placed", "cone", "beam"):
        assert token in SYSTEM
    for token in ("damage", "snare", "spawn", "freeze"):
        assert token in SYSTEM


# --- transport + delegation + clamp ------------------------------------------

def test_resolve_with_client_uses_llm_and_clamps():
    client = _FakeClient(_draft())
    g = resolve(_b(delivery="bear_trap", damage="beehive"), Awakening(1.0), client=client)
    # the model asked for 9999 damage; the clamp brings it inside the contract
    dmg = next(e.amount for e in g.all_effects() if e.kind is EffectKind.DAMAGE)
    assert dmg <= 60.0
    # and it actually went through structured output (color-free draft schema)
    assert client.sink["output_format"] is GadgetDraft
    assert client.sink["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_resolve_without_client_stays_deterministic():
    # no client => no network; deterministic floor answers
    g = resolve(_b(delivery="bear_trap", damage="beehive"), Awakening(1.0))
    assert g.chassis is Delivery.PLACED


def test_missing_parsed_output_raises():
    with pytest.raises(RuntimeError):
        llm_resolve(_b(delivery="bear_trap"), Awakening(1.0), _FakeClient(None))


def test_harmless_is_derived_not_trusted():
    # model claims harmless but stuffed in a DAMAGE effect -> we treat it as armed
    g = _draft(category=Category.TRINKET, harmless=True,
               stages=[Stage(trigger=Trigger.ON_HIT,
                             effects=[Effect(kind=EffectKind.DAMAGE, amount=30.0)])])
    out = resolve(_b(delivery="mop"), Awakening(1.0), client=_FakeClient(g))
    assert out.harmless is False

    # a genuinely damage-free "weapon" is derived harmless AND downgraded out of WEAPON
    g2 = _draft(category=Category.WEAPON, harmless=False,
                stages=[Stage(trigger=Trigger.ON_HIT,
                              effects=[Effect(kind=EffectKind.SNARE, duration=2.0)])])
    out2 = resolve(_b(delivery="mop"), Awakening(1.0), client=_FakeClient(g2))
    assert out2.harmless is True
    assert out2.category is Category.CONTROL


def test_resolve_falls_back_to_deterministic_on_llm_error():
    class _BoomClient:
        class _M:
            def parse(self, **kwargs):
                raise RuntimeError("boom")
        def __init__(self):
            self.messages = self._M()

    # no strict flag -> a broken LLM must not crash the combine
    g = resolve(_b(delivery="bear_trap", damage="beehive"), Awakening(1.0), client=_BoomClient())
    assert g.chassis is Delivery.PLACED  # the deterministic floor answered


def test_clamp_floors_dead_effects():
    g = _canned(stages=[Stage(trigger=Trigger.ON_HIT, effects=[
        Effect(kind=EffectKind.KNOCKBACK, amount=8.0),
        Effect(kind=EffectKind.SLOW, amount=0.0, duration=0.0),
    ])])
    clamp_gadget(g)
    kb = next(e for e in g.all_effects() if e.kind is EffectKind.KNOCKBACK)
    sl = next(e for e in g.all_effects() if e.kind is EffectKind.SLOW)
    assert kb.amount >= 80.0     # a knockback of 8 would be imperceptible
    assert sl.duration >= 1.5    # a slow with no duration does nothing


def test_llm_retries_once_then_succeeds():
    good = _draft()

    class _Flaky:
        def __init__(self):
            self.calls = 0
            outer = self

            class _M:
                def parse(self, **kwargs):
                    outer.calls += 1
                    if outer.calls == 1:
                        raise RuntimeError("transient")
                    return SimpleNamespace(parsed_output=good, stop_reason="end_turn")

            self.messages = _M()

    client = _Flaky()
    out = llm_resolve(_b(delivery="bear_trap"), Awakening(1.0), client)
    assert out.name == good.name  # draft converted to a Gadget (with code-set color)
    assert client.calls == 2


def test_strict_mode_surfaces_llm_errors():
    class _BoomClient:
        class _M:
            def parse(self, **kwargs):
                raise RuntimeError("boom")
        def __init__(self):
            self.messages = self._M()

    with pytest.raises(RuntimeError):
        resolve(_b(delivery="bear_trap"), Awakening(1.0), client=_BoomClient(), strict=True)
