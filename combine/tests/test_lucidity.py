"""The single awakening meter and its two effects (insight + rule-loosening)."""

from __future__ import annotations

import pytest

from combine.lucidity import Awakening, Era, MismatchPolicy


def test_level_bounds_enforced():
    with pytest.raises(ValueError):
        Awakening(-0.1)
    with pytest.raises(ValueError):
        Awakening(1.1)


@pytest.mark.parametrize("level,era", [
    (0.0, Era.ASLEEP), (0.24, Era.ASLEEP),
    (0.25, Era.STIRRING), (0.49, Era.STIRRING),
    (0.5, Era.WAKING), (0.74, Era.WAKING),
    (0.75, Era.LUCID), (1.0, Era.LUCID),
])
def test_era_thresholds(level, era):
    assert Awakening(level).era is era


@pytest.mark.parametrize("level,insight", [
    (0.0, 0), (0.25, 1), (0.5, 2), (0.75, 3), (1.0, 3),
])
def test_insight_tracks_era(level, insight):
    assert Awakening(level).insight == insight


@pytest.mark.parametrize("level,policy", [
    (0.0, MismatchPolicy.NORMALIZE),
    (0.2, MismatchPolicy.NORMALIZE),
    (0.25, MismatchPolicy.PENALIZE),
    (0.5, MismatchPolicy.PENALIZE),
    (0.74, MismatchPolicy.PENALIZE),
    (0.75, MismatchPolicy.REWARD),
    (1.0, MismatchPolicy.REWARD),
])
def test_mismatch_policy_by_era(level, policy):
    assert Awakening(level).mismatch_policy() is policy
