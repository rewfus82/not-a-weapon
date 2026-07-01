"""Batch eval for dialing in the resolver + prompt.

Runs a fixed set of representative builds through the resolver in one shot and
prints a scannable report with soft PASS/FAIL checks, so the prompt can be tuned
by reading many outputs at once instead of typing builds one at a time.

Routing (BYOK):
  - ANTHROPIC_API_KEY in the env, OR a gitignored `.anthropic_key` file at the
    repo root  ->  Sonnet.
  - neither  ->  the deterministic floor (structure-only; still useful for regression).

    python -m combine.eval            # auto-routes (LLM if a key is found)
    python -m combine.eval --det      # force deterministic regardless of key

Checks are SOFT (reported, never a hard failure): the LLM legitimately varies
chassis/flavor run to run, so this is a tuning lens, not CI. Structural
regression lives in the pytest suite.
"""

from __future__ import annotations

import os
import sys

from .grammar import Build
from .items import CATALOG
from .lucidity import Awakening
from .resolver import resolve
from .schema import Category, EffectKind, Gadget

# name, awakening level, slot->item, soft expectations
CASES: list[dict] = [
    {"name": "flagship / lucid", "awake": 1.0,
     "slots": {"delivery": "bear_trap", "damage": "beehive", "utility": "fireworks", "modifier": "dry_ice"},
     "expect": {"armed": True, "has": ["spawn"]}},
    {"name": "flagship / asleep (normalize)", "awake": 0.15,
     "slots": {"delivery": "bear_trap", "damage": "beehive", "utility": "fireworks", "modifier": "dry_ice"},
     "expect": {"armed": True}},
    {"name": "bee-bomb / lucid", "awake": 1.0,
     "slots": {"delivery": "beehive", "damage": "grenade", "utility": "co2_canister"},
     "expect": {"armed": True, "has": ["explode"]}},
    {"name": "bee-bomb / asleep (normalize)", "awake": 0.15,
     "slots": {"delivery": "beehive", "damage": "grenade"},
     "expect": {"armed": True, "lacks": ["spawn"]}},   # bees should be smoothed away
    {"name": "mop tool (no damage)", "awake": 1.0,
     "slots": {"delivery": "mop", "utility": "magnet", "modifier": "feathers"},
     "expect": {"armed": False, "not_weapon": True}},
    {"name": "all off-nature / lucid", "awake": 1.0,
     "slots": {"delivery": "salami", "damage": "feathers", "utility": "dish_soap"},
     "expect": {"not_weapon": True}},
    {"name": "salami absurd / lucid", "awake": 1.0,
     "slots": {"delivery": "salami", "damage": "dish_soap", "utility": "handgun", "modifier": "pencil"},
     "expect": {}},
    {"name": "salami absurd / asleep", "awake": 0.15,
     "slots": {"delivery": "salami", "damage": "dish_soap", "utility": "handgun", "modifier": "pencil"},
     "expect": {}},
    {"name": "leaf blower spray", "awake": 1.0,
     "slots": {"delivery": "leaf_blower", "damage": "handgun"},
     "expect": {"armed": True}},
    {"name": "magnet homing gun", "awake": 1.0,
     "slots": {"delivery": "handgun", "damage": "handgun", "modifier": "magnet"},
     "expect": {"armed": True, "homing": True}},
    {"name": "potato-suppressed rifle", "awake": 1.0,
     "slots": {"delivery": "m16", "damage": "m16", "modifier": "potato"},
     "expect": {"armed": True}},
    {"name": "flaming mop", "awake": 1.0,
     "slots": {"delivery": "mop", "damage": "gasoline"},
     "expect": {"armed": True, "has": ["burn"]}},
    {"name": "boombox lure", "awake": 1.0,
     "slots": {"delivery": "boombox", "utility": "beehive"},
     "expect": {}},
    {"name": "spaghetti tangle spray", "awake": 1.0,
     "slots": {"delivery": "leaf_blower", "utility": "spaghetti"},
     "expect": {"not_weapon": True}},
]


def _build(slots: dict) -> Build:
    return Build(**{k: CATALOG[v] for k, v in slots.items()})


def _checks(g: Gadget, expect: dict) -> list[str]:
    out: list[str] = []
    kinds = {e.kind.value for e in g.all_effects()}
    if "armed" in expect:
        ok = (g.category is not Category.DUD and not g.harmless) if expect["armed"] else g.harmless
        out.append(("armed" if expect["armed"] else "harmless") + (" ✓" if ok else " ✗"))
    if expect.get("not_weapon"):
        out.append("not-weapon " + ("✓" if g.category is not Category.WEAPON else "✗"))
    if expect.get("homing"):
        out.append("homing " + ("✓" if g.homing else "✗"))
    for k in expect.get("has", []):
        out.append(f"has:{k} " + ("✓" if k in kinds else "✗"))
    for k in expect.get("lacks", []):
        out.append(f"no:{k} " + ("✓" if k not in kinds else "✗"))
    return out


def _resolve_key() -> str | None:
    k = os.environ.get("ANTHROPIC_API_KEY")
    if k:
        return k.strip()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in (".anthropic_key", os.path.join(".secrets", "anthropic_key")):
        p = os.path.join(root, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                return fh.read().strip()
    return None


def _make_client(force_det: bool):
    if force_det:
        return None
    key = _resolve_key()
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        print("  (anthropic not installed — staying deterministic)")
        return None
    return anthropic.Anthropic(api_key=key)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    client = _make_client("--det" in sys.argv)
    where = "Sonnet (BYOK)" if client is not None else "deterministic"
    print(f"combine eval — routing: {where} — {len(CASES)} cases\n")
    fails = 0
    for c in CASES:
        build = _build(c["slots"])
        awake = Awakening(c["awake"])
        slot_str = " ".join(f"{k}={v}" for k, v in c["slots"].items())
        print(f"● {c['name']}  [awake {c['awake']} · {awake.era.value}]")
        print(f"  {slot_str}")
        try:
            g = resolve(build, awake, client=client, strict=True)
        except Exception as exc:  # noqa: BLE001 - report and keep going through the batch
            print(f"  ! resolve failed: {exc}\n")
            fails += 1
            continue
        print(f"  -> {g.name}  [{g.category.value} | {g.chassis.value}]"
              + ("  (homing)" if g.homing else "") + ("  (harmless)" if g.harmless else ""))
        for st in g.stages:
            seq = " ".join(e.kind.value + (f"{int(e.amount)}" if e.amount else "") for e in st.effects)
            print(f"     {st.trigger.value}: {seq}")
        if g.logic:
            print(f"     logic: {g.logic}")
        checks = _checks(g, c["expect"])
        if checks:
            print("     checks: " + "  ".join(checks))
            fails += sum(1 for ch in checks if ch.endswith("✗"))
        print()
    print(f"done. soft-check failures: {fails}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
