"""
This Is Not A Weapon — INTUITION test harness.

The core question this proves: when you combine junk, does the result feel like
what a player would EXPECT — following the items' real associations literally and
cleverly (punny, absurd, "obvious in hindsight") — instead of generic junk?

The key idea: a player doesn't think "beehive = [organic, swarm]". They think
"beehive = furious bees, do-not-disturb, ticking time bomb, the swarm seeks
warmth". So we give each item that *association cloud*, and ask the model to
compose results by reasoning from it. The model already shares those associations
with the player — that shared knowledge is what makes it feel intuitive on both
ends. The output still maps to the engine's real deliveries/effects.

Run:  ANTHROPIC_API_KEY=sk-ant-... python ai/combine_eval.py
"""

from __future__ import annotations

import os
import sys

try:
    import anthropic
    from pydantic import BaseModel, Field
except ImportError:
    sys.exit("Install deps first:  pip install anthropic pydantic")

# Wittier model for the feel test (judging the ceiling). Drop to claude-haiku-4-5
# for production once the prompt is dialed in.
MODEL = "claude-sonnet-5"

# --- items as ASSOCIATION CLOUDS (what the player actually thinks) -----------
ITEMS: dict[str, list[str]] = {
    "m16":            ["a real military rifle", "spits bullets fast", "magazine-fed", "lethal"],
    "nerf_gun":       ["a kid's toy", "fires soft foam darts", "harmless", "bright plastic"],
    "grenade":        ["explodes", "you throw it and run", "shrapnel everywhere", "pull the pin"],
    "chainsaw":       ["a roaring blade", "cuts through anything", "horror-movie icon", "you have to get close"],
    "bear_trap":      ["snaps shut on a leg", "hidden on the ground", "vicious steel jaws", "holds you in place"],
    "anchovies":      ["tiny salty fish", "smells revolting", "packed in oily brine", "canned"],
    "ketchup":        ["red goopy sauce", "squirts everywhere", "looks like blood", "sticky mess"],
    "spaghetti":      ["long sticky strands", "gooey and tangling", "a wet mess", "looks like guts or wires"],
    "feathers":       ["light and fluffy", "float on the air", "tickle", "completely harmless"],
    "pixie_stix":     ["pure sugar dust", "a hyperactive sugar rush", "comes in a paper straw", "powder"],
    "potato":         ["dense and starchy", "the classic spud-gun ammo", "muffles a gun barrel like a movie silencer", "lumpy"],
    "beehive":        ["full of furious bees", "do not disturb", "a ticking time bomb", "the swarm seeks warmth"],
    "magnet":         ["pulls metal toward it", "sticks to the fridge", "an invisible field", "attracts"],
    "boomerang":      ["you throw it and it comes back", "curved hunting tool", "returns to your hand", "whirls through the air"],
    "fishing_rod":    ["casts a line way out", "reels the catch back in", "hook and bait", "drags things toward you"],
    "pringles":       ["a cardboard tube", "pops when you open it", "a perfect barrel shape", "stackable chips"],
    "co2_canister":   ["pressurized gas", "a propellant that powers a blast", "freezing cold when it vents", "metal cylinder"],
    "vacuum":         ["sucks everything in", "loud motor", "a hose and a bag", "hoovers it all up"],
    "leaf_blower":    ["blasts a cone of air", "shoves everything away", "loud yard tool", "a gale from a nozzle"],
    "fire_extinguisher": ["sprays a freezing CO2 cloud", "a pressurized blast", "puts fires out cold", "billowing white fog"],
    "gasoline":       ["highly flammable liquid", "reeking fumes", "one spark and WHOOSH", "fuel"],
    "car_battery":    ["heavy lead box", "twelve volts", "acid sloshing inside", "jump-starts a dead engine"],
    "jumper_cables":  ["conduct raw electricity", "clamp onto terminals", "arc and spark", "connect two things"],
    "ice_pack":       ["freezing cold", "numbs on contact", "a squishy gel pack", "frostbite"],
    "taser":          ["a crackling electric shock", "stuns you stiff", "two probes on wires", "high voltage"],
    "bandages":       ["patch you up", "first aid", "stop the bleeding", "gauze and tape"],
    "super_ball":     ["bounces off everything wildly", "dense rubber", "ricochets around a room", "absurdly high-energy"],
    "marbles":        ["scatter across the floor", "you slip and wipe out on them", "little glass spheres", "roll everywhere"],
    "propane_tank":   ["pressurized fuel", "goes up in a fireball", "a heavy steel cylinder", "BBQ bomb"],
    "duct_tape":      ["sticks to anything", "fixes everything", "binds things together", "the universal solution"],
    "boombox":        ["blares loud music", "everyone turns to look", "draws a crowd", "thumping bass"],
    "raw_meat":       ["bait", "every predator wants it", "drips and reeks", "irresistible to the hungry"],
}


# --- output (maps to what the engine can actually execute) -------------------
class Effect(BaseModel):
    kind: str = Field(description="One of: damage, slow, snare, knockback, explode, burn, pierce, spawn, freeze, chain, collect, heal, shield, speed")
    detail: str = Field("", description="Short note on how this effect manifests, in the item's flavor.")


class Gadget(BaseModel):
    name: str = Field(description="Short, evocative, ideally punny — follows directly from the items.")
    category: str = Field(description="WEAPON, CONTROL, MOBILITY, UTILITY, TRINKET, or DUD. WEAPON is the exception.")
    delivery: str = Field(description="One of: projectile, lobbed, cone, beam, melee, return, aura, placed, turret, decoy, self")
    effects: list[Effect] = Field(default_factory=list, description="The composed behavior. May be empty for a pure trinket/dud.")
    description: str = Field(description="One deadpan, clever sentence describing what it does.")
    logic: str = Field(description="The 'aha': one sentence naming the item association(s) you followed to get here.")


SYSTEM = """You are the imagination of a survivor in a glitching simulation who can
MacGyver ordinary junk into improvised gear. Given 2-3 items, decide what they
BECOME when combined.

THE GOLDEN RULE — intuitive, literal, clever:
A player holds a small cloud of associations for each item (what it's made of,
what it does, what it reminds them of). The result MUST follow those associations
LITERALLY and CLEVERLY — surprising and a little absurd, often punny, but obvious
in hindsight. The target reaction is a groan-and-grin: "of COURSE that's what a
beehive + grenade makes." If the result feels arbitrary, generic, or doesn't
clearly trace back to the parts, you have FAILED. Predictability is a feature:
a player who knows the items should be able to half-guess the result.

You are given each item's associations. Reason FROM them. Worked examples of the
right thinking:
- Beehive {furious bees, do-not-disturb, ticking bomb, swarm seeks warmth} +
  Grenade {explodes, throw and run, shrapnel} -> "Apiary Mine": lob it; the blast
  scatters a swarm of enraged, heat-seeking bees that chase the nearest warm body.
  (The bees ARE the shrapnel, and they seek heat.) delivery=lobbed,
  effects=[spawn (homing bees), explode].
- Spaghetti {sticky strands, tangling, wet mess} + Leaf Blower {blasts a cone of
  air} -> "Pasta Cannon": hoses a cone of sticky strands that tangle and bog down
  whatever they touch. delivery=cone, effects=[slow, snare].
- Potato {muffles a barrel like a movie silencer} + M16 {rifle} -> "Spudpressor":
  a quieter rifle (the potato is a suppressor). delivery=projectile, effects=[damage].
  The potato changes the gun's CHARACTER, it doesn't add bees.

RULES:
- Most combinations are NOT weapons. A thing that merely exists, or is silly and
  useless, is a TRINKET. Reach for WEAPON only when something genuinely dangerous
  is involved. Harmless parts -> harmless result, and that's correct.
- Follow the DOMINANT items. Don't bolt unrelated effects on; let the parts' real
  nature decide the delivery AND the effects. Do NOT default to "projectile + damage".
- Be specific and witty in the name and description. The `logic` field must name
  the exact association(s) you followed.

ENGINE VOCABULARY (only use these):
delivery: projectile | lobbed | cone | beam | melee | return | aura | placed | turret | decoy | self
effects:  damage | slow | snare | knockback | explode | burn | pierce | spawn | freeze | chain | collect | heal | shield | speed
"""


def resolve(client: anthropic.Anthropic, item_ids: list[str]) -> Gadget:
    lines = []
    for iid in item_ids:
        lines.append("- %s: %s" % (iid, "; ".join(ITEMS[iid])))
    user = "Combine these items. Reason from their associations.\n\n" + "\n".join(lines)
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=800,
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_format=Gadget,
    )
    if resp.parsed_output is None:
        raise RuntimeError(f"No parseable output (stop_reason={resp.stop_reason}).")
    return resp.parsed_output


def _lookup(token: str) -> str | None:
    token = token.strip().lower().replace(" ", "_").replace("-", "_")
    if token in ITEMS:
        return token
    for iid in ITEMS:
        if token in iid:
            return iid
    return None


def _print(g: Gadget) -> None:
    print(f"\n  {g.name}   [{g.category} | {g.delivery}]")
    print(f"  \"{g.description}\"")
    for e in g.effects:
        print(f"    - {e.kind}{(': ' + e.detail) if e.detail else ''}")
    print(f"  logic: {g.logic}\n")


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("BYOK: set ANTHROPIC_API_KEY=sk-ant-... and re-run.")
    client = anthropic.Anthropic()
    print("This Is Not A Weapon — intuition test  (model: %s)" % MODEL)
    print("Type 2-3 items, comma-separated.  Commands: items / quit")
    print("Try:  beehive, grenade   ·   spaghetti, leaf_blower   ·   potato, m16\n")

    while True:
        try:
            raw = input("combine> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); return
        if not raw:
            continue
        if raw in ("quit", "exit", "q"):
            return
        if raw == "items":
            for iid, assoc in ITEMS.items():
                print(f"  {iid:18} {', '.join(assoc[:2])}…")
            continue
        ids: list[str] = []
        for tok in raw.split(","):
            iid = _lookup(tok)
            if iid is None:
                print(f"  ? unknown item: '{tok.strip()}' (try 'items')")
                ids = []
                break
            ids.append(iid)
        if not ids:
            continue
        try:
            print("  ...working out what you just built...")
            g = resolve(client, ids)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {e}")
            continue
        _print(g)


if __name__ == "__main__":
    main()
