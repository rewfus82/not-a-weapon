"""
Batch smoke test for the combine evaluator.

Runs a curated spread of combinations chosen to probe the distribution: a real
weapon, an absurd janky weapon, food -> trinket, a tool, and a dud. Prints each
gadget plus a category tally so you can see at a glance whether the model is
(wrongly) defaulting everything to WEAPON.

Run:  ANTHROPIC_API_KEY=sk-ant-... python ai/smoke.py
"""

from __future__ import annotations

import os
import random
import sys
from collections import Counter

from combine_eval import resolve, _print_gadget, Category  # noqa: E402

try:
    import anthropic
except ImportError:
    sys.exit("Install deps first:  pip install anthropic pydantic")

# Deliberately mixed: only ~half should plausibly be weapons.
COMBOS: list[list[str]] = [
    ["m16", "anchovies"],                     # plausible weapon (gummed up)
    ["spaghetti", "nerf_gun", "co2_canister"],# absurd -> janky weapon w/ backfire
    ["ketchup", "feathers", "spatula"],       # food/fluff -> trinket, not a weapon
    ["magnet", "backpack"],                   # tool -> utility, not a weapon
    ["potato", "zip_ties"],                   # nonsense -> dud
    ["beehive", "grenade", "magnet"],         # clever -> rare weapon
    ["pixie_stix", "wire_hanger", "zip_ties"],# harmless contraption
    ["vacuum", "chainsaw", "backpack"],       # utility (loot harvester)
]


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("BYOK: set ANTHROPIC_API_KEY=sk-ant-... and re-run.")
    random.seed(42)  # stable glitch rolls so the run is reproducible
    client = anthropic.Anthropic()
    seed = 7777

    tally: Counter[str] = Counter()
    for ids in COMBOS:
        print("  >>> " + " + ".join(ids))
        try:
            g = resolve(client, ids, seed)
        except Exception as e:  # noqa: BLE001
            print(f"      ! {e}\n")
            continue
        _print_gadget(g)
        cat = g.category.value if isinstance(g.category, Category) else str(g.category)
        tally[cat] += 1

    print("category tally:", dict(tally))
    weapons = tally.get("WEAPON", 0)
    total = sum(tally.values())
    if total:
        print(f"WEAPON share: {weapons}/{total}  "
              f"({'good — weapons are the exception' if weapons <= total // 2 else 'still weapon-heavy; tune the prompt'})")


if __name__ == "__main__":
    main()
