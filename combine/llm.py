"""The LLM resolver (Sonnet) — the primary brain; deterministic is the fallback.

The model reasons FREELY about what the junk becomes, but it may only emit the
engine's vocabulary (enforced by the Gadget schema via structured output). It is
shown ONLY the associations the player can currently see (insight-gated), and the
current era's rule-licensing, so its output is always legible AND era-correct.

Requires the optional `anthropic` dependency and a caller-supplied client (BYOK).
The client is duck-typed (`client.messages.parse(...)`), so tests inject a fake.
"""

from __future__ import annotations

import os

from .grammar import Build
from .items import Item
from .lucidity import Awakening, MismatchPolicy
from .schema import Delivery, EffectKind, Gadget, GadgetDraft

# Haiku is the cheap/fast POC default. NOTE: switch back to Sonnet
# (COMBINE_MODEL=claude-sonnet-4-6) for the shipped/authored catalog or whenever
# max wit matters — Sonnet keeps sharper names + tighter normalize/era-discipline.
MODEL = os.environ.get("COMBINE_MODEL", "claude-haiku-4-5")

_DELIVERIES = " | ".join(d.value for d in Delivery)
_EFFECTS = " | ".join(k.value for k in EffectKind)

# what each primitive MECHANICALLY does — so the model picks by behavior, not by vibe
_EFFECT_GLOSS = """Effect meanings (these are MECHANICS, not flavor — pick the one whose real behavior matches):
  damage = direct HP loss
  slow = reduced move speed for a time      snare = rooted in place briefly
  knockback = shoved away                   explode = area burst of damage
  burn = damage over time (fire/acid)       pierce = the shot passes through several enemies
  spawn = releases homing sub-things (bees, sparks, darts)
  collect = vacuums loot / pulls things toward you, NO damage  <- use this for a magnet's pull, NOT chain
  freeze = near-freezes an enemy (frozen enemies take bonus damage)
  chain = damage ARCS to nearby enemies (lightning ONLY — not "links" or "pulls")
  heal = restores YOUR HP   shield = a temporary damage-absorbing shield on YOU   speed = a temporary move-speed boost to YOU
A gadget with NO damaging effect (no damage/explode/burn/spawn/chain) is harmless — a tool, not a weapon."""

# natural chassis hint per delivery item (kept in sync with resolver.SHAPE by test)
from .resolver import SHAPE  # noqa: E402

SYSTEM = f"""You are the imagination of someone trapped in a glitching simulation
who can MacGyver ordinary junk into improvised gear. The player hands you a BUILD:
items placed into named slots. You decide what it BECOMES.

THE SLOTS ARE INSTRUCTIONS. Each slot tells you the ROLE the player intends, and
that role OVERRIDES the item's default reading:
- delivery : the chassis — HOW it's used / deployed. This item defines the form.
- damage   : the business end — what does the hurting.
- utility  : a NON-damage behavior — signal, lure, control, area-deny.
- modifier : a twist on the whole thing — an element, homing, a suppressor, etc.
A beehive in `damage` is the killing swarm; in `utility` it's area denial. Same
item, different slot, different result.

THE GOLDEN RULE — intuitive, literal, clever:
Follow the items' associations LITERALLY and CLEVERLY. The result must be
surprising, a little absurd, often punny, but OBVIOUS IN HINDSIGHT — a
groan-and-grin, "of course that's what those make." If it feels arbitrary or you
can't trace it to the parts, you failed. Reason ONLY from the associations given;
those are what the player can currently perceive. Do not invent traits.

CATEGORY — be honest about what it is:
- WEAPON: deals real damage (damage / explode / burn / a damaging swarm), even if
  it ALSO controls. A trap that snares AND deals 20 damage + a bee swarm is a WEAPON.
- CONTROL: disables or impedes WITHOUT meaningful damage (snare / slow / knockback /
  freeze only, no damage).
- UTILITY / TRINKET: harmless — collects, lures, or merely exists.
Most builds are NOT weapons, and an empty damage slot is almost never a weapon —
but do NOT under-call WEAPON when the thing clearly hurts.

OUTPUT — compose, don't pick from a list:
- chassis  : one delivery primitive ({_DELIVERIES}). Take it from the delivery
  item's nature.
- stages   : an ORDERED list. Each stage is a trigger + effects, in the sequence
  they happen (e.g. a trap: on_trigger -> snare, then startle, then swarm).
- effects  : only these primitives ({_EFFECTS}). Nothing else can be rendered.
- params   : OPTIONAL numeric delivery-behavior tuning (NOT effects). Only meaningful
  for the RETURN (boomerang) chassis today: {{"range": how far out before it turns
  (80-600, default 300), "curve": how wide it arcs (0-800, default 260),
  "return_speed": how fast it comes back (200-1200, default 600)}}. Bend these from
  the parts — a light/floaty part widens + slows the loop, a propellant/spring
  tightens + speeds it, a heavy part shortens it. Omit params for any other chassis.

{_EFFECT_GLOSS}

- name/description/logic: free, witty text. `logic` names the exact association(s)
  and slot(s) you followed — the 'aha'.
- ALWAYS emit at least one stage containing at least one effect, unless the result
  is a genuine DUD (category dud, no effects). Never return empty stages otherwise.

You may only ever use the delivery and effect primitives listed above. If you
imagine something outside them, express it by choosing the CLOSEST primitives and
putting the wild idea in the name/description."""


def _era_licensing(awakening: Awakening) -> str:
    policy = awakening.mismatch_policy()
    if policy is MismatchPolicy.NORMALIZE:
        return ("You are ASLEEP. The simulation still enforces its rules: if an item "
                "sits in a slot that fights its nature, QUIETLY IGNORE that item and "
                "resolve the boring, expected thing — smooth the anomaly over. Keep "
                "results mundane and literal.")
    if policy is MismatchPolicy.PENALIZE:
        return ("You are WAKING. Off-nature placements now WORK, but jankily — weaker, "
                "funnier, clearly 'a tool, not a proper weapon'. Honor the absurdity, "
                "at reduced effectiveness.")
    return ("You are LUCID. The rules are yours to break. Off-nature, rule-defying "
            "placements should give the BEST, wildest results. Go for the groan-and-grin; "
            "reality bends to the joke.")


def _item_line(slot: str, item: Item, insight: int) -> str:
    assoc = "; ".join(item.visible_text(insight)) or "(you can't read this yet)"
    hint = ""
    if slot == "delivery":
        hint = f"  [natural form: {SHAPE.get(item.id, Delivery.PROJECTILE).value}]"
    return f"- {slot}: {item.name} — {assoc}{hint}"


def build_user_message(build: Build, awakening: Awakening) -> str:
    """The per-build message. Only insight-visible associations appear here."""
    insight = awakening.insight
    lines = [
        f"AWAKENING: {awakening.era.value} (insight {insight}). {_era_licensing(awakening)}",
        "",
        "BUILD:",
    ]
    for p in build.placements():
        lines.append(_item_line(p.slot, p.item, insight))
    lines.append("")
    lines.append("Compose the gadget. Reason from the associations and the slots.")
    return "\n".join(lines)


def llm_resolve(build: Build, awakening: Awakening, client: object, attempts: int = 3) -> Gadget:
    """Call the model with structured output; return the parsed Gadget (unclamped).

    `resolve()` clamps the result; this function stays a thin transport so the
    prompt and the parse are what tests inspect. Retries once by default: the model
    occasionally emits a schema-invalid gadget (e.g. empty stages), and a fresh
    sample usually fixes it before `resolve()` would fall back to deterministic.
    """
    user = build_user_message(build, awakening)
    color = build.delivery.color if build.delivery is not None else "#b0b0b0"
    last_exc: Exception | None = None
    for _ in range(max(1, attempts)):
        try:
            resp = client.messages.parse(
                model=MODEL,
                max_tokens=1500,
                system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
                output_format=GadgetDraft,
            )
            draft = getattr(resp, "parsed_output", None)
            if draft is not None:
                return draft.to_gadget(color)  # code sets color, not the model
            last_exc = RuntimeError(f"no parseable gadget (stop={getattr(resp, 'stop_reason', '?')})")
        except Exception as exc:  # noqa: BLE001 - retry on any transport/parse failure
            last_exc = exc
    raise last_exc if last_exc else RuntimeError("llm_resolve failed")
