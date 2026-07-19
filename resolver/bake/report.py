"""Per-wave statistical report: a library this size is never hand-QA'd.
Everything here is read-only over the frozen records; the derive sweep uses
a fixed report seed so two runs of the report agree byte-for-byte.
"""
from __future__ import annotations

import hashlib
from collections import Counter

from resolver.bake.dedup import iter_scaffolds
from resolver.bake.derive import DEPTH_TIERS, derive_instance
from resolver.bake.run import width
from resolver.bake.schema import BakeRecord, Depth
from resolver.bake.select import PINNED_BUILDS
from resolver.bake.schema import combo_id as _combo_id
from resolver.clamp import TIER_BUDGET, total_cost
from resolver.contract import Tier
from resolver.items import Build

REPORT_SEED = 20260717

# $ per million tokens (input, output). 2026-07 list prices — verify against
# the current pricing page before reading a pilot's dollar figure as truth.
PRICE_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
}


def instance_seed(cid: str, depth: str, index: int, tier: Tier) -> int:
    digest = hashlib.sha256(
        f"{cid}|{depth}|{index}|{tier.value}|{REPORT_SEED}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big")


def _dollars(records: list[BakeRecord]) -> float:
    total = 0.0
    for record in records:
        price_in, price_out = PRICE_PER_MTOK.get(record.model or "", (0.0, 0.0))
        total += record.usage.get("input_tokens", 0) / 1e6 * price_in
        total += record.usage.get("output_tokens", 0) / 1e6 * price_out
    return total


def wave_report(records: list[BakeRecord], builds: dict[str, Build],
                rename_events: list[dict], wave: str) -> str:
    resolved = [r for r in records if r.status == "resolved"]
    unresolved = [r for r in records if r.status == "unresolved"]
    pinned_ids = {_combo_id(b): key for key, b in PINNED_BUILDS.items()}
    lines: list[str] = [f"# Bake report — {wave}", ""]

    lines += [f"- combos: {len(records)}",
              f"- unresolved: {len(unresolved)}/{len(records)}"]
    for record in unresolved:
        tag = pinned_ids.get(record.combo_id, "")
        lines.append(f"  - `{record.combo_id}`" + (f" (pinned: {tag})" if tag else ""))
    pinned_unresolved = [r for r in unresolved if r.combo_id in pinned_ids]
    lines.append(f"- pinned unresolved: {len(pinned_unresolved)}/{len(pinned_ids)}")

    widths = Counter(width(r) for r in resolved)
    topped = sum(1 for r in resolved if len(r.scaffolds[Depth.SHALLOW]) > 1)
    lines += ["", "## Width / top-up",
              *(f"- width {w}: {widths.get(w, 0)}" for w in (1, 2, 3)),
              f"- topped up: {topped}"]

    suffixed = sum(1 for e in rename_events if e["outcome"] == "suffixed")
    lines += ["", "## Names",
              f"- renames: {len(rename_events)}",
              f"- suffixed: {suffixed}"]
    for event in rename_events:
        if event["outcome"] == "suffixed":
            lines.append(f"  - FLAG suffixed: {event['old']!r} -> {event['new']!r} ({event['owner']})")

    lines += ["", "## Derive sweep (fixed report seed)"]
    ratios: list[tuple[float, str]] = []
    per_tier: dict[Tier, list[float]] = {t: [] for t in Tier}
    categories: Counter = Counter()
    harmless_count = 0
    total_instances = 0
    for record in resolved:
        build = builds[record.combo_id]
        for (cid, depth_value, index), draft in iter_scaffolds([record]):
            for tier in DEPTH_TIERS[Depth(depth_value)]:
                seed = instance_seed(cid, depth_value, index, tier)
                instance = derive_instance(draft, build, tier, seed)
                ratio = (total_cost(instance.draft) / TIER_BUDGET[tier]
                         if TIER_BUDGET[tier] else 0.0)
                ratios.append((ratio, f"{instance.draft.name} [{tier.value}]"))
                per_tier[tier].append(ratio)
                categories[instance.category.value] += 1
                harmless_count += instance.harmless
                total_instances += 1
    for tier in Tier:
        values = per_tier[tier]
        if values:
            lines.append(f"- {tier.value}: n={len(values)} "
                         f"cost/budget mean={sum(values) / len(values):.3f} "
                         f"min={min(values):.3f} max={max(values):.3f}")
        else:
            lines.append(f"- {tier.value}: n=0")
    lines += ["", "### Categories",
              *(f"- {cat}: {count}" for cat, count in sorted(categories.items()))]
    if total_instances:
        lines.append(f"- harmless: {harmless_count}/{total_instances}")

    outliers = max(1, len(ratios) // 100)
    ranked = sorted(ratios)
    lines += ["", "### Outliers by cost share",
              *(f"- low: {name} ({ratio:.3f})" for ratio, name in ranked[:outliers]),
              *(f"- high: {name} ({ratio:.3f})" for ratio, name in ranked[-outliers:])]

    tokens_in = sum(r.usage.get("input_tokens", 0) for r in records)
    tokens_out = sum(r.usage.get("output_tokens", 0) for r in records)
    dollars = _dollars(records)
    per_combo = dollars / len(records) if records else 0.0
    lines += ["", "## Cost",
              f"- input tokens: {tokens_in}",
              f"- output tokens: {tokens_out}",
              f"- total: ${dollars:.2f} (prices from PRICE_PER_MTOK — verify before trusting)",
              f"- $/combo: ${per_combo:.4f}"]
    return "\n".join(lines) + "\n"
