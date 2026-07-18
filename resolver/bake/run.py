"""Bake runner: one structured-output call per combo -> ScaffoldSet, retry
ladder on refusal/transport failure, resumable append-only JSONL, adaptive
top-up for combos whose scaffolds show real interpretive width.

Rates are logged; the *reason* a call failed is never asked, classified, or
recorded (standing rule: log rates, ablate by item swap, never chase the
reason). This is offline tooling — never the runtime hot path.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from resolver.bake.schema import (
    BakeRecord, Depth, ScaffoldSet, combo_id, contract_fingerprint,
)
from resolver.contract import EffectKind, GadgetDraft, Target
from resolver.items import Build
from resolver.prompt import slot_line

# ScaffoldSet is three drafts plus adaptive thinking; starve it and the JSON
# truncates mid-token (same failure mode MAX_TOKENS=8000 fixed for one draft).
MAX_TOKENS = 16000

BAKE_PROMPT: str = (
    Path(__file__).parent.parent / "prompts" / "bake_prompt.txt"
).read_text(encoding="utf-8").strip()

_TEMPLATE = """BUILD
  delivery: {delivery}
  damage:   {damage}
  utility:  {utility}
  modifier: {modifier}

LOCKED DELIVERY FORM: {form}

Give the three readings of this build: shallow, medium, deep. Trace every
effect back to a stated property of the specific objects above. Compose
within the locked delivery form."""

_TOP_UP_SUFFIX = """

ALREADY HAVE (from an earlier pass over this same build):
{existing}

Read the build differently: another three readings — shallow, medium, deep —
built on different properties or a different arrangement than the ones above.
Do not repeat those compositions or names."""


def render_bake_message(build: Build) -> str:
    slots = dict(build.slots())
    return _TEMPLATE.format(
        delivery=slot_line(slots["delivery"]),
        damage=slot_line(slots["damage"]),
        utility=slot_line(slots["utility"]),
        modifier=slot_line(slots["modifier"]),
        form=build.delivery.value,
    )


def _shape_line(depth: Depth, draft: GadgetDraft) -> str:
    kinds = ", ".join(f"{e.kind.value}@{e.target.value}"
                      for stage in draft.stages for e in stage.effects)
    return f"- {depth.value.lower()} \"{draft.name}\": {kinds}"


def render_top_up_message(build: Build, record: BakeRecord) -> str:
    existing = "\n".join(_shape_line(d, record.scaffolds[d][0]) for d in Depth)
    return render_bake_message(build) + _TOP_UP_SUFFIX.format(existing=existing)


def palette(draft: GadgetDraft) -> frozenset[tuple[EffectKind, Target]]:
    return frozenset((e.kind, e.target) for stage in draft.stages for e in stage.effects)


TOP_UP_WIDTH = 3  # top up only maximal-width combos (placeholder threshold;
                  # the report shows the width distribution to tune it on evidence)


def width(record: BakeRecord) -> int:
    """Distinct (kind, target) palettes among the base scaffolds (resolved
    records only). Palettes, not stage structure: depth mandates structural
    growth, so structure always differs; palettes differ only when the depths
    read the items differently."""
    return len({palette(record.scaffolds[d][0]) for d in Depth})


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _call_ladder(client, models: list[str], user: str):
    """Try each model in order; first parseable ScaffoldSet wins. Returns
    (scaffold_set | None, model | None, usage). Failure reasons are never
    recorded — rates only."""
    usage = {"input_tokens": 0, "output_tokens": 0}
    for model in models:
        try:
            response = client.messages.parse(
                model=model,
                max_tokens=MAX_TOKENS,
                system=BAKE_PROMPT,
                messages=[{"role": "user", "content": user}],
                output_format=ScaffoldSet,
            )
        except Exception:  # noqa: BLE001 - next rung; the reason is deliberately dropped
            continue
        used = getattr(response, "usage", None)
        if used is not None:
            usage["input_tokens"] += used.input_tokens
            usage["output_tokens"] += used.output_tokens
        if response.parsed_output is not None:
            return response.parsed_output, model, usage
    return None, None, usage


def bake_combo(client, models: list[str], build: Build) -> BakeRecord:
    scaffold_set, model, usage = _call_ladder(client, models, render_bake_message(build))
    if scaffold_set is None:
        return BakeRecord(combo_id=combo_id(build), status="unresolved",
                          contract_fingerprint=contract_fingerprint(),
                          baked_at=_now(), usage=usage)
    record = BakeRecord(
        combo_id=combo_id(build), status="resolved",
        contract_fingerprint=contract_fingerprint(),
        model=model, baked_at=_now(), usage=usage,
        scaffolds={Depth.SHALLOW: [scaffold_set.shallow],
                   Depth.MEDIUM: [scaffold_set.medium],
                   Depth.DEEP: [scaffold_set.deep]},
    )
    if width(record) >= TOP_UP_WIDTH:  # one extra call max at pilot scale
        extra, _, more = _call_ladder(client, models, render_top_up_message(build, record))
        for key, value in more.items():
            record.usage[key] = record.usage.get(key, 0) + value
        if extra is not None:
            record.scaffolds[Depth.SHALLOW].append(extra.shallow)
            record.scaffolds[Depth.MEDIUM].append(extra.medium)
            record.scaffolds[Depth.DEEP].append(extra.deep)
    return record


def load_records(path: Path) -> dict[str, BakeRecord]:
    if not path.exists():
        return {}
    out: dict[str, BakeRecord] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = BakeRecord.model_validate_json(line)
            out[record.combo_id] = record
    return out


def append_record(path: Path, record: BakeRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(record.model_dump_json() + "\n")


def write_records(path: Path, records: dict[str, BakeRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(r.model_dump_json() + "\n" for r in records.values()),
                    encoding="utf-8")


def run_wave(client, models: list[str], builds: dict[str, Build], path: Path,
             retry_unresolved: bool = False) -> dict[str, int]:
    """Resumable: existing combo_ids are skipped (a crash or a later wave is
    just a re-run); with retry_unresolved, unresolved lines are re-attempted
    and replaced, never duplicated. Appends after every combo — crash-safe."""
    existing = load_records(path)
    stats = {"attempted": 0, "resolved": 0, "unresolved": 0, "skipped": 0, "topped_up": 0}
    for cid, build in builds.items():
        prior = existing.get(cid)
        if prior is not None and not (retry_unresolved and prior.status == "unresolved"):
            stats["skipped"] += 1
            continue
        record = bake_combo(client, models, build)
        stats["attempted"] += 1
        stats[record.status] += 1
        if record.status == "resolved" and len(record.scaffolds[Depth.SHALLOW]) > 1:
            stats["topped_up"] += 1
        existing[cid] = record
        if prior is None:
            append_record(path, record)
        else:
            write_records(path, existing)
    return stats
