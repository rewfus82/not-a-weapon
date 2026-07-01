"""The awakening model — one meter, two effects.

The player slowly realizes they're in a simulation. A single `Awakening.level`
(0..1) drives BOTH:
  - insight  : how deep into each item's association cloud they can see, and
  - lucidity : how much the simulation's rules have loosened.

The rules-loosening is expressed as a mismatch policy that a slot placement is
run through. Early the simulation silently NORMALIZES absurd builds (papers over
the glitch). In the middle, off-nature placements are PENALIZED (they work, but
weak and janky). Late, they are REWARDED (breaking the rules is the point).
Same action across the run, three meanings — the ramp IS the story.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Era(str, Enum):
    ASLEEP = "asleep"
    STIRRING = "stirring"
    WAKING = "waking"
    LUCID = "lucid"


class MismatchPolicy(str, Enum):
    NORMALIZE = "normalize"  # absurd placement is silently corrected to the boring thing
    PENALIZE = "penalize"    # off-nature works, but weaker / jankier
    REWARD = "reward"        # off-nature can beat on-nature


# insight tier granted per era (also the max reveal-tier the player can read)
_ERA_INSIGHT: dict[Era, int] = {
    Era.ASLEEP: 0,
    Era.STIRRING: 1,
    Era.WAKING: 2,
    Era.LUCID: 3,
}


@dataclass(frozen=True)
class Awakening:
    """Single progression meter. Everything else derives from `level`."""

    level: float  # 0..1

    def __post_init__(self) -> None:
        if not 0.0 <= self.level <= 1.0:
            raise ValueError(f"awakening level must be in [0, 1], got {self.level!r}")

    @property
    def era(self) -> Era:
        if self.level < 0.25:
            return Era.ASLEEP
        if self.level < 0.50:
            return Era.STIRRING
        if self.level < 0.75:
            return Era.WAKING
        return Era.LUCID

    @property
    def insight(self) -> int:
        """Max association tier the player can read right now (0..3)."""
        return _ERA_INSIGHT[self.era]

    @property
    def lucidity(self) -> float:
        return self.level

    def mismatch_policy(self) -> MismatchPolicy:
        if self.level < 0.25:
            return MismatchPolicy.NORMALIZE
        if self.level < 0.75:
            return MismatchPolicy.PENALIZE
        return MismatchPolicy.REWARD
