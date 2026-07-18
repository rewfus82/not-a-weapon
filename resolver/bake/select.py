"""Deterministic stratified combo selection for a bake wave.

Seeded and reproducible: the exact selection is written to JSON and reviewed
before any money moves. Strata are targets, not hard guarantees (some cells,
e.g. high-coherence 4-item, may be unreachable); the achieved distribution
is visible in the selection file and the wave report.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from resolver.bake.schema import combo_id
from resolver.coherence import coherence
from resolver.harness import PROBE_BUILDS
from resolver.items import CATALOG, Build, Item
from resolver.router import C_HIGH, C_LOW

# Always-selected refusal hot-spots: the six live-validated probes plus the
# 9/9-refused live build. The exact powder item of that build was never
# recorded (HANDOFF: "a powder item"); fertilizer (powder + ignition) is the
# most refusal-prone reconstruction. The spec's fan+duck pin is unbuildable —
# the rubber duck left the catalog in the 2026-07-12 rewrite; its successor
# probe_whimsical is already pinned.
PINNED_BUILDS: dict[str, Build] = {
    **PROBE_BUILDS,
    "pinned_extinguisher": Build(
        delivery_item=CATALOG["fire extinguisher"],
        damage_item=CATALOG["sack of fertilizer"],
        utility_item=CATALOG["industrial fan"],
        modifier_item=CATALOG["roman candle"],
    ),
}

SHAPE_QUOTAS: dict[int, float] = {2: 0.4, 3: 0.4, 4: 0.2}
_SLOTS = ("damage", "utility", "modifier")


def chassis_eligible(item: Item) -> bool:
    """Mirrors Build.delivery: an item can chair the delivery slot iff it
    locks a form or has a base use to inherit one from."""
    return item.delivery is not None or item.base_use is not None


def _tercile(c: float) -> int:
    if c <= C_LOW:
        return 0
    if c >= C_HIGH:
        return 2
    return 1


def _shape(build: Build) -> int:
    return sum(1 for _, item in build.slots() if item is not None)


def _random_build(rng: random.Random, shape: int, must_include: Item | None = None) -> Build:
    chassis = sorted((i for i in CATALOG.values() if chassis_eligible(i)), key=lambda i: i.name)
    pool = sorted(CATALOG.values(), key=lambda i: i.name)
    if must_include is not None and chassis_eligible(must_include) and rng.random() < 0.5:
        delivery = must_include
    else:
        delivery = rng.choice(chassis)
    picks = rng.sample([i for i in pool if i.name != delivery.name], shape - 1)
    if (must_include is not None and must_include.name != delivery.name
            and all(p.name != must_include.name for p in picks)):
        picks[0] = must_include
    slots: dict[str, Item | None] = dict.fromkeys(_SLOTS, None)
    for slot, item in zip(rng.sample(_SLOTS, len(picks)), picks):
        slots[slot] = item
    return Build(delivery_item=delivery, damage_item=slots["damage"],
                 utility_item=slots["utility"], modifier_item=slots["modifier"])


def select_combos(n: int = 300, seed: int = 20260717) -> list[Build]:
    rng = random.Random(seed)
    chosen: dict[str, Build] = {}

    def add(build: Build) -> bool:
        cid = combo_id(build)
        if cid in chosen or len(chosen) >= n:
            return False
        chosen[cid] = build
        return True

    for build in PINNED_BUILDS.values():
        add(build)

    def covered() -> set[str]:
        return {item.name for b in chosen.values() for _, item in b.slots() if item is not None}

    # coverage: every catalog item (every association cloud) gets exercised
    shapes, weights = list(SHAPE_QUOTAS), list(SHAPE_QUOTAS.values())
    for item in sorted(CATALOG.values(), key=lambda i: i.name):
        if item.name in covered():
            continue
        for _ in range(200):
            build = _random_build(rng, rng.choices(shapes, weights)[0], must_include=item)
            in_build = {i.name for _, i in build.slots() if i is not None}
            if item.name in in_build and add(build):
                break

    # strata fill over the remainder: (shape, coherence tercile) cells
    remainder = n - len(chosen)
    targets: dict[tuple[int, int], int] = {}
    for shape, frac in SHAPE_QUOTAS.items():
        per_shape = round(frac * remainder)
        for t in range(3):
            targets[(shape, t)] = per_shape // 3 + (1 if t < per_shape % 3 else 0)
    filled = dict.fromkeys(targets, 0)
    attempts = 0
    while len(chosen) < n and attempts < 200 * n:
        attempts += 1
        open_shapes = sorted({s for (s, t) in targets if filled[(s, t)] < targets[(s, t)]})
        if not open_shapes:
            break
        build = _random_build(rng, rng.choice(open_shapes))
        cell = (_shape(build), _tercile(coherence(build)))
        if cell in targets and filled[cell] < targets[cell] and add(build):
            filled[cell] += 1

    # top-off: unreachable cells must not shrink the wave
    while len(chosen) < n and attempts < 400 * n:
        attempts += 1
        add(_random_build(rng, rng.choices(shapes, weights)[0]))
    return list(chosen.values())


def write_selection(builds: list[Build], path: Path, seed: int) -> None:
    payload = {
        "seed": seed,
        "n": len(builds),
        "combos": [
            {"combo_id": combo_id(b),
             "slots": {slot: (item.name if item is not None else None)
                       for slot, item in b.slots()}}
            for b in builds
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_selection(path: Path) -> dict[str, Build]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, Build] = {}
    for entry in payload["combos"]:
        slots = entry["slots"]

        def item(key: str) -> Item | None:
            return CATALOG[slots[key]] if slots[key] else None

        out[entry["combo_id"]] = Build(
            delivery_item=CATALOG[slots["delivery"]], damage_item=item("damage"),
            utility_item=item("utility"), modifier_item=item("modifier"),
        )
    return out
