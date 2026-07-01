"""The output contract: only engine-executable primitives, well-formed gadgets."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from combine.schema import (
    Category,
    Delivery,
    Effect,
    EffectKind,
    Gadget,
    Stage,
    Trigger,
)


def _weapon(**over) -> Gadget:
    base = dict(
        name="Test Gun",
        category=Category.WEAPON,
        chassis=Delivery.PROJECTILE,
        stages=[Stage(trigger=Trigger.ON_HIT, effects=[Effect(kind=EffectKind.DAMAGE, amount=10)])],
    )
    base.update(over)
    return Gadget(**base)


def test_valid_gadget_builds():
    g = _weapon()
    assert g.chassis is Delivery.PROJECTILE
    assert g.has(EffectKind.DAMAGE)
    assert not g.has(EffectKind.BURN)


def test_all_effects_flattens_stages():
    g = _weapon(stages=[
        Stage(trigger=Trigger.ON_HIT, effects=[Effect(kind=EffectKind.DAMAGE, amount=5)]),
        Stage(trigger=Trigger.ON_EXPIRE, effects=[Effect(kind=EffectKind.EXPLODE, radius=90)]),
    ])
    kinds = {e.kind for e in g.all_effects()}
    assert kinds == {EffectKind.DAMAGE, EffectKind.EXPLODE}


def test_unknown_effect_kind_rejected():
    with pytest.raises(ValidationError):
        Effect(kind="turn_into_a_chicken")  # not in the capability contract


def test_unknown_delivery_rejected():
    with pytest.raises(ValidationError):
        _weapon(chassis="stream_of_flame")


def test_non_dud_requires_a_stage():
    with pytest.raises(ValidationError):
        _weapon(stages=[])


def test_dud_may_have_no_stages():
    g = Gadget(name="Wet Sock", category=Category.DUD, chassis=Delivery.MELEE, stages=[])
    assert g.category is Category.DUD
    assert g.all_effects() == []


def test_projectile_speed_is_clamped_by_schema():
    with pytest.raises(ValidationError):
        _weapon(projectile_speed=99999.0)


def test_json_round_trip():
    g = _weapon(description="pew", logic="gun goes in damage")
    restored = Gadget.model_validate_json(g.model_dump_json())
    assert restored == g
