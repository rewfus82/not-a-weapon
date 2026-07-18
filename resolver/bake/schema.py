"""Bake schema: what one bake call returns and what the library stores.

The scaffold body reuses GadgetDraft: fit/fill rescales every draft, so the
numbers a model emits are formally *relative weights* — "no magnitudes" is
enforced by the deriver (derive.py), not the schema. Depth is the bake-side
instruction axis; tiers are derived per depth band at read time.
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from resolver.contract import Delivery, EffectKind, GadgetDraft, Target, Trigger
from resolver.items import Build

CONTRACT_VERSION = "v1"


class Depth(str, Enum):
    SHALLOW = "SHALLOW"  # the DUD/COMMON reading
    MEDIUM = "MEDIUM"    # the workmanlike reading — UNCOMMON/RARE
    DEEP = "DEEP"        # chained, reactive — EPIC/LEGENDARY


class ScaffoldSet(BaseModel):
    """Model-facing structured output: named fields, not a list, so "exactly
    one scaffold per depth" holds by construction."""
    shallow: GadgetDraft
    medium: GadgetDraft
    deep: GadgetDraft


class BakeRecord(BaseModel):
    combo_id: str
    status: Literal["resolved", "unresolved"]
    contract_version: str = CONTRACT_VERSION
    contract_fingerprint: str
    model: str | None = None  # the ladder model that produced the base set
    baked_at: str = ""        # ISO timestamp, UTC
    usage: dict[str, int] = Field(default_factory=dict)
    scaffolds: dict[Depth, list[GadgetDraft]] = Field(default_factory=dict)


_EMPTY = "-"


def combo_id(build: Build) -> str:
    """Canonical, role-sensitive id: same items in different slots are
    different combos, matching Build."""
    slots = dict(build.slots())

    def name(key: str) -> str:
        item = slots[key]
        return item.name if item is not None else _EMPTY

    return (f"d:{name('delivery')}|dmg:{name('damage')}"
            f"|u:{name('utility')}|m:{name('modifier')}")


def _fingerprint(families: dict[str, list[str]]) -> str:
    payload = json.dumps({k: sorted(v) for k, v in sorted(families.items())})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def contract_fingerprint() -> str:
    """Stable hash of the enum vocabulary the scaffolds were baked against.
    A mismatch on read means deterministic re-validation through repair —
    never a re-bake."""
    return _fingerprint({
        "delivery": [d.value for d in Delivery],
        "effect": [k.value for k in EffectKind],
        "trigger": [t.value for t in Trigger],
        "target": [t.value for t in Target],
    })
