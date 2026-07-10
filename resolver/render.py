"""Human-readable output. Groups by build, then tier, so a person can eyeball
depth across tiers and variety within a tier in one scroll (not raw JSON).
"""
from __future__ import annotations

from dataclasses import dataclass

from resolver.contract import ResolvedGadget

_BAR = "=" * 60


@dataclass
class RunResult:
    build_key: str
    resolved: ResolvedGadget
    run_index: int
    run_total: int
    source: str = "llm"
    reason: str | None = None


def _render_effect(effect) -> str:
    bits = [effect.kind.value, f"a={effect.amount:g}"]
    if effect.duration:
        bits.append(f"d={effect.duration:g}")
    if effect.radius:
        bits.append(f"r={effect.radius:g}")
    if effect.count:
        bits.append(f"n={effect.count}")
    line = " ".join(bits)
    if effect.note:
        line += f'  "{effect.note}"'
    return line


def _render_one(result: RunResult) -> str:
    rg = result.resolved
    tag = "  [fallback]" if result.source == "fallback" else ""
    lines = [
        f"--- {rg.tier.value} ---  ({rg.category.value}, harmless={rg.harmless})  "
        f"[run {result.run_index}/{result.run_total}]{tag}",
        f"  name:  {rg.draft.name}",
        f"  logic: {rg.draft.logic}",
    ]
    if result.source == "fallback" and result.reason:
        lines.append(f"  fallback: {result.reason}")
    lines.append("  stages:")
    for stage in rg.draft.stages:
        lines.append(f"    {stage.trigger.value}:")
        for effect in stage.effects:
            lines.append(f"      {_render_effect(effect)}")
    return "\n".join(lines)


def render_run(results: list[RunResult]) -> str:
    out: list[str] = []
    seen: set[str] = set()
    for result in results:
        key = result.build_key
        if key not in seen:
            seen.add(key)
            rg = result.resolved
            out.append("")
            out.append(_BAR)
            out.append(f"BUILD: {key}   [delivery: {rg.delivery.value}, color: {rg.color}]")
            out.append(_BAR)
        out.append("")
        out.append(_render_one(result))
    return "\n".join(out).strip() + "\n"
