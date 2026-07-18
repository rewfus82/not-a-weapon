"""Global name dedup: bake calls are stateless (no exclusion lists in
prompts — they break prompt caching, cannot scale, and parallel calls would
still collide); uniqueness is enforced by this post-wave pass against a
persistent registry. First-baked keeps the name. Only the name field is
ever touched — composition is immutable once baked. The pass rewrites
scaffolds.jsonl and names.json; the git diff is the rename audit.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel

from resolver.bake.schema import BakeRecord, Depth
from resolver.contract import GadgetDraft

RENAME_ATTEMPTS = 2
RENAME_MAX_TOKENS = 1000

RENAME_PROMPT = (
    "You are renaming one gadget in a stylized video game so its name is "
    "unique. You will see the gadget's current name, description, and logic, "
    "plus names that are already taken. Give it a new name with the same "
    "character: something a person would grin at, no mechanic-words, clearly "
    "different from every taken name. Change only the name."
)


class Rename(BaseModel):
    name: str


Owner = tuple[str, str, int]  # (combo_id, depth value, alternate index)


def normalize(name: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", name.casefold())
    return re.sub(r"\s+", " ", cleaned).strip()


def iter_scaffolds(records: list[BakeRecord]) -> Iterator[tuple[Owner, GadgetDraft]]:
    """Canonical first-baked order: record (JSONL line) order, then depth
    order SHALLOW -> MEDIUM -> DEEP, then alternate index."""
    for record in records:
        for depth in Depth:
            for index, draft in enumerate(record.scaffolds.get(depth, [])):
                yield (record.combo_id, depth.value, index), draft


def load_registry(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_registry(path: Path, registry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")


def _rename_message(draft: GadgetDraft, taken: list[str]) -> str:
    lines = "\n".join(f"- {name}" for name in taken)
    return (f"Current name: {draft.name}\n"
            f"Description: {draft.description}\n"
            f"Logic: {draft.logic}\n\n"
            f"Taken names:\n{lines}\n\n"
            "Give the new unique name.")


def _try_rename(client, models: list[str], draft: GadgetDraft, taken: list[str]) -> str | None:
    """One rename attempt down the ladder; None if nothing parseable came back.
    Reasons are never recorded."""
    for model in models:
        try:
            response = client.messages.parse(
                model=model,
                max_tokens=RENAME_MAX_TOKENS,
                system=RENAME_PROMPT,
                messages=[{"role": "user", "content": _rename_message(draft, taken)}],
                output_format=Rename,
            )
        except Exception:  # noqa: BLE001 - next rung
            continue
        if response.parsed_output is not None:
            return response.parsed_output.name
    return None


def _suffixed(name: str, registry: dict) -> str:
    mark = 2
    while normalize(f"{name} Mk {mark}") in registry:
        mark += 1
    return f"{name} Mk {mark}"


def dedup_wave(records: list[BakeRecord], registry: dict, client, models: list[str]) -> list[dict]:
    """Detect collisions (wave-internal and against the registry), rename the
    losers, register every final name. Mutates draft names and the registry
    in place; returns the rename events for the report."""
    events: list[dict] = []
    for owner, draft in iter_scaffolds(records):
        key = normalize(draft.name)
        claimed = registry.get(key)
        if claimed is None:
            registry[key] = {"owner": list(owner), "display": draft.name}
            continue
        if tuple(claimed["owner"]) == owner:
            continue  # this scaffold already owns the name (re-run of the pass)
        old = draft.name
        taken = [claimed["display"]]
        outcome = "suffixed"
        for _ in range(RENAME_ATTEMPTS):
            candidate = _try_rename(client, models, draft, taken)
            if candidate is None:
                continue
            if normalize(candidate) not in registry:
                draft.name = candidate
                outcome = "renamed"
                break
            taken.append(candidate)
        if outcome == "suffixed":
            draft.name = _suffixed(old, registry)
        registry[normalize(draft.name)] = {"owner": list(owner), "display": draft.name}
        events.append({"owner": list(owner), "old": old,
                       "new": draft.name, "outcome": outcome})
    return events
