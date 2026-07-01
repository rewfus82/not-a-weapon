"""Interactive combine bench — the acceptance-test playground.

Fill the slot grid, set how awake you are, and see what the junk becomes: the
gadget, its ordered stages, the logic readback, and the compiled engine form.
Runs on the deterministic resolver with no key; set ANTHROPIC_API_KEY to route
through Sonnet instead (BYOK).

    python -m combine.harness

Commands:
    delivery=bear_trap damage=beehive utility=fireworks modifier=dry_ice
    awake 0.9            # set the awakening meter (0..1)
    items                # list the junk + what you can currently read
    clear                # empty the bench
    quit
"""

from __future__ import annotations

import os
import sys

from .compile import to_engine
from .grammar import Build, validate_build
from .items import CATALOG, SLOTS
from .lucidity import Awakening
from .resolver import resolve


def _make_client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
    except ImportError:
        print("  (anthropic not installed; staying deterministic. `pip install anthropic`)")
        return None
    return anthropic.Anthropic()


def _print_gadget(build: Build, awakening: Awakening, client) -> None:
    problems = validate_build(build)
    if problems:
        print("  ! " + "; ".join(problems))
        return
    where = "Sonnet" if client is not None else "deterministic"
    try:
        g = resolve(build, awakening, client=client)
    except Exception as exc:  # noqa: BLE001 - surface any transport error to the bench
        print(f"  ! resolve failed ({where}): {exc}")
        return
    print(f"\n  {g.name}   [{g.category.value} | chassis={g.chassis.value}]   ({where})")
    print(f'  "{g.description}"')
    for st in g.stages:
        seq = "  ".join(
            e.kind.value
            + (f"({int(e.amount)})" if e.amount else "")
            + (f" x{e.count}" if e.count else "")
            + (f" {e.duration:g}s" if e.duration else "")
            for e in st.effects
        )
        print(f"    {st.trigger.value}: {seq}")
    extra = []
    if g.homing:
        extra.append("homing")
    if g.harmless:
        extra.append("harmless")
    if extra:
        print("    (" + ", ".join(extra) + ")")
    print(f"  logic: {g.logic}")
    print(f"  -> engine.delivery={to_engine(g)['delivery']}\n")


def _list_items(insight: int) -> None:
    print(f"  (insight {insight} — you can read these traits)")
    for iid, item in CATALOG.items():
        seen = "; ".join(item.visible_text(insight))
        redacted = item.hidden_count(insight)
        tail = f"   +{redacted} hidden" if redacted else ""
        print(f"    {iid:14} {item.name:20} {seen}{tail}")


def _parse_slots(tokens: list[str]) -> Build:
    kw: dict = {}
    for tok in tokens:
        tok = tok.strip().strip(",").strip()  # tolerate comma-separated pairs
        if not tok:
            continue
        if "=" not in tok:
            raise ValueError(f"expected slot=item, got {tok!r}")
        slot, iid = tok.split("=", 1)
        slot = slot.strip().lower()
        iid = iid.strip().strip(",").strip().lower()
        if slot not in SLOTS:
            raise ValueError(f"unknown slot {slot!r} (use {', '.join(SLOTS)})")
        if iid not in CATALOG:
            raise ValueError(f"unknown item {iid!r} (try 'items')")
        kw[slot] = CATALOG[iid]
    return Build(**kw)


def main() -> None:
    # model + flavor text can contain unicode; never let a stock Windows console crash on it
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    client = _make_client()
    awakening = Awakening(1.0)
    print("This Is Not A Weapon — combine bench")
    print("  routing:", "Sonnet (BYOK)" if client else "deterministic (set ANTHROPIC_API_KEY for Sonnet)")
    print("  try: delivery=bear_trap damage=beehive utility=fireworks modifier=dry_ice")
    print("  commands: awake <0..1> · items · clear · quit\n")
    build = Build()
    while True:
        try:
            raw = input(f"[{awakening.era.value}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not raw:
            continue
        head, *rest = raw.split()
        low = head.lower()
        if low in ("quit", "exit", "q"):
            return
        if low == "items":
            _list_items(awakening.insight)
            continue
        if low == "clear":
            build = Build()
            print("  bench cleared.")
            continue
        if low == "awake":
            try:
                awakening = Awakening(float(rest[0]))
            except (IndexError, ValueError) as exc:
                print(f"  ! {exc}")
                continue
            print(f"  awakening = {awakening.level} ({awakening.era.value}, insight {awakening.insight}, "
                  f"rules: {awakening.mismatch_policy().value})")
            continue
        try:
            build = _parse_slots(raw.split())
        except ValueError as exc:
            print(f"  ! {exc}")
            continue
        _print_gadget(build, awakening, client)


if __name__ == "__main__":
    sys.exit(main())
