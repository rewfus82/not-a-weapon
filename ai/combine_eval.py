"""
This Is Not A Weapon — AI combine evaluator (test harness).

Proves the AI-driven combine mechanic cheaply BEFORE touching Godot. You type a
combination of junk; Claude Haiku 4.5 *composes a thing* out of a fixed
vocabulary of effect primitives the engine knows how to execute.

Core premise (do not lose this): combining junk produces ALL SORTS of things.
A usable weapon is the EXCEPTION, not the default. Most combinations are tools,
mobility aids, novelties (trinkets), or duds — and even a real weapon is only as
viable as its parts. An absurd component makes the result janky: unreliable,
messy, or prone to backfiring on the player.

Model shape:
    Gadget = name + description + category + rarity
             + viability       (how well it works, given absurd parts)
             + quirk           (the catch, if any)
             + delivery        (how it's applied)
             + effects[]       (what it does, drawn from EffectKind)
             + backfire[]      (effects that hit the PLAYER when it's janky)

Design decisions baked in:
  - Weapons are the exception: the prompt + examples push tools/trinkets/duds.
  - Viability axis: absurd parts -> lower viability -> lower reliability + quirks
    + occasional backfire on the user.
  - Composable primitives: behavior is a list of Effects, not flat fields.
  - Balance stays ours: per-rarity caps on effect count + each effect's numbers.
  - Occasional insane weapon: a small "reality glitch" roll lifts the caps.
  - Per-run reroll: results cache per RUN; `newrun` reseeds.
  - BYOK: in the real game, a missing/failed key falls back to compose().

Run:  ANTHROPIC_API_KEY=sk-ant-... python ai/combine_eval.py
"""

from __future__ import annotations

import os
import random
import sys
from enum import Enum

try:
    import anthropic
    from pydantic import BaseModel, Field
except ImportError:
    sys.exit("Install deps first:  pip install anthropic pydantic")

MODEL = "claude-haiku-4-5"

# --- the junk library (mirrors scripts/item_db.gd) --------------------------
# id: (display_name, affordance, [tags])
ITEMS: dict[str, tuple[str, str, list[str]]] = {
    "m16":          ("M16 Rifle",           "fire_projectile", ["ranged", "lethal", "gun_frame", "metal"]),
    "nerf_gun":     ("Nerf Blaster",        "fire_projectile", ["ranged", "toy", "plastic"]),
    "grenade":      ("Frag Grenade",        "throw",           ["explosive", "lethal", "thrown", "metal"]),
    "chainsaw":     ("Chainsaw",            "rend",            ["lethal", "kinetic", "metal", "electric"]),
    "bear_trap":    ("Bear Trap",           "snap",            ["metal", "lethal", "snare"]),
    "anchovies":    ("Can of Anchovies",    "fluid_payload",   ["organic", "salty", "canned", "liquid"]),
    "ketchup":      ("Ketchup Bottle",      "squirt",          ["liquid", "sticky", "organic"]),
    "spaghetti":    ("Plate of Spaghetti",  "noodle_mess",     ["organic", "sticky", "food"]),
    "feathers":     ("Handful of Feathers", "flutter",         ["light", "organic", "fluffy"]),
    "pixie_stix":   ("Pixie Stix",          "sugar_dust",      ["sugar", "light", "powder"]),
    "potato":       ("Potato",              "muffle",          ["organic", "soft", "dense"]),
    "beehive":      ("Beehive",             "swarm",           ["organic", "swarm", "living"]),
    "magnet":       ("Horseshoe Magnet",    "attract",         ["metal", "attract"]),
    "boomerang":    ("Boomerang",           "return",          ["thrown", "return", "wood"]),
    "fishing_rod":  ("Fishing Rod",         "cast_reel",       ["reach", "reel"]),
    "pringles":     ("Pringles Can",        "tube",            ["tube", "cardboard"]),
    "co2_canister": ("CO2 Canister",        "pressurize",      ["pressure", "gas", "metal"]),
    "vacuum":       ("Shop Vacuum",         "suction",         ["suction", "electric"]),
    "backpack":     ("Backpack",            "store",           ["storage", "fabric"]),
    "wire_hanger":  ("Wire Hanger",         "springy_frame",   ["metal", "springy"]),
    "zip_ties":     ("Zip Ties",            "fasten",          ["plastic", "bind"]),
}


# --- the vocabulary the engine can execute ----------------------------------
class Category(str, Enum):
    WEAPON = "WEAPON"          # meant to hurt — the EXCEPTION, not the default
    CONTROL = "CONTROL"        # disable/impair (slow, snare)
    MOBILITY = "MOBILITY"      # movement
    UTILITY = "UTILITY"        # a useful tool (loot, light, shield, lure)
    CONSUMABLE = "CONSUMABLE"  # heal/buff/eat
    TRINKET = "TRINKET"        # does something, but useless in a fight (a novelty)
    DUD = "DUD"                # does nothing


class Rarity(str, Enum):
    DUD = "DUD"
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    GLITCHED = "GLITCHED"


class Viability(str, Enum):
    PRISTINE = "PRISTINE"        # real, compatible parts — works clean
    SERVICEABLE = "SERVICEABLE"  # works, minor jank
    JANKY = "JANKY"              # works unreliably; expect misfires
    BARELY = "BARELY"            # mostly fails
    INERT = "INERT"              # does not function as intended


class Delivery(str, Enum):
    PROJECTILE = "projectile"
    LOBBED = "lobbed"
    HITSCAN = "hitscan"
    MELEE = "melee"
    AURA = "aura"
    PLACED = "placed"
    SELF = "self"


class EffectKind(str, Enum):
    DAMAGE = "damage"        # amount = damage
    SLOW = "slow"            # duration; amount = strength 0-100
    SNARE = "snare"          # duration (rooted)
    STUN = "stun"            # duration (cannot act)
    KNOCKBACK = "knockback"  # amount = force
    EXPLODE = "explode"      # radius; amount = splash damage
    BURN = "burn"            # duration; amount = damage/sec
    PIERCE = "pierce"        # count = enemies passed through
    BOUNCE = "bounce"        # count = ricochets
    CHAIN = "chain"          # count = jumps; radius = jump range
    SPAWN = "spawn"          # count = sub-projectiles/swarm
    TURRET = "turret"        # duration; amount = dmg/shot
    PULL = "pull"            # amount = force toward player
    MARK = "mark"            # note = what's marked (enables homing/chain)
    LIFESTEAL = "lifesteal"  # amount = %% of damage healed
    HEAL = "heal"            # amount = self heal
    DASH = "dash"            # amount = distance (mobility)
    COLLECT = "collect"      # radius = loot-vacuum range
    LIGHT = "light"          # radius = illuminate / reveal
    DISTRACT = "distract"    # radius, duration = lure enemies away
    SHIELD = "shield"        # amount = damage blocked; duration


class Effect(BaseModel):
    kind: EffectKind
    amount: float = Field(0, description="Magnitude (damage, force, %%, block...). 0 if N/A.")
    duration: float = Field(0, description="Seconds, for timed effects. 0 if N/A.")
    radius: float = Field(0, description="Radius for explode/chain/collect/light/distract. 0 if N/A.")
    count: int = Field(0, description="Count for pierce/bounce/chain/spawn. 0 if N/A.")
    note: str = Field("", description="Short flavor or target, e.g. 'metal' for mark. Optional.")


class Gadget(BaseModel):
    display_name: str = Field(description="Short, deadpan, specific.")
    description: str = Field(description="One deadpan sentence. Acknowledge even duds; never 'nothing happens'.")
    category: Category = Field(description="What this thing ACTUALLY is. WEAPON is the exception — most combos are not.")
    rarity: Rarity = Field(description="How clever/absurd the synergy is.")
    viability: Viability = Field(description="How well it works given the parts. Absurd/flimsy parts -> lower.")
    quirk: str = Field("", description="The catch/drawback, if any. Empty for a clean PRISTINE result.")
    delivery: Delivery = Field(description="How it's applied.")
    projectile_speed: float = Field(0, description="~300-1000 for projectile/lobbed; 0 otherwise.")
    homing: bool = Field(False, description="True if something guides it to targets.")
    harmless: bool = Field(False, description="True if it works/fires but can't meaningfully hurt anyone (a sugar crossbow).")
    effects: list[Effect] = Field(default_factory=list, description="What it does. Empty for a true DUD or pure TRINKET.")
    backfire: list[Effect] = Field(default_factory=list, description="Effects on the PLAYER when it's janky (sauce slows you, recoil). Usually empty.")


# --- balance: per-rarity caps (the engine keeps balance, not the model) ------
MAX_EFFECTS = {"DUD": 0, "COMMON": 2, "UNCOMMON": 3, "RARE": 4, "GLITCHED": 5}
DMG_CAP = {"DUD": 0.0, "COMMON": 12.0, "UNCOMMON": 18.0, "RARE": 26.0, "GLITCHED": 42.0}
COUNT_CAP = {"DUD": 0, "COMMON": 3, "UNCOMMON": 4, "RARE": 6, "GLITCHED": 10}
DUR_CAP = 4.0
RADIUS_CAP = 200.0
GLITCH_CHANCE = 0.06
RELIABILITY = {"PRISTINE": 1.0, "SERVICEABLE": 0.85, "JANKY": 0.6, "BARELY": 0.3, "INERT": 0.0}

_DAMAGING = {"damage", "explode", "burn", "heal"}
# A WEAPON must contain at least one genuinely dangerous component. Enforced in
# code so the model can't label a sugar crossbow a weapon.
DANGEROUS_TAGS = {"lethal", "explosive", "pressure", "kinetic"}
CONTROL_KINDS = {"slow", "snare", "stun", "knockback", "pull"}


SYSTEM = """You are the reality engine of a simulation the player is trapped inside.

The player survives by COMBINING ordinary junk. The crucial truth: combining \
things produces ALL SORTS of things, and a usable WEAPON is the EXCEPTION, not \
the default. Honestly assess what these specific objects would actually BECOME if \
mashed together. Most combinations are tools, mobility aids, novelties, or junk. \
Do NOT reach for a weapon unless a genuinely dangerous component is present AND \
the assembly could plausibly hurt someone. A magnet and a backpack is a scrap \
caddy, not a gun. Ketchup and feathers is a mess, not a munition.

WEAPON TEST — before labeling anything WEAPON, BOTH must hold: (1) at least one \
component is genuinely dangerous on its own (a firearm, explosive, blade, or \
something heavy/sharp/burning/pressurized), and (2) the assembled thing could \
plausibly injure a person. Merely firing or launching is NOT enough — a crossbow \
that shoots sugar packets is a TRINKET, not a weapon. If either test fails, it is \
the tool, novelty, or dud it actually is. (The engine also enforces this, so don't \
fight it.) Healthy mix across many combos: a few real weapons, more tools and \
novelties, plenty of duds. If most of your outputs are WEAPON, you are misreading \
the junk.

Pick `category` for what it TRULY is:
  WEAPON      - meant to hurt (the exception)
  CONTROL     - disables/impairs (slow, snare, stun)
  MOBILITY    - moves the player (dash)
  UTILITY     - a useful tool (collect loot, light, shield, distract)
  CONSUMABLE  - heal/buff/eat
  TRINKET     - it does SOMETHING but it's useless in a fight (a novelty)
  DUD         - it does nothing (still describe it with deadpan flavor)

VIABILITY — even a real weapon is only as good as its parts. Set `viability` \
honestly: PRISTINE (real compatible parts, works clean) > SERVICEABLE (minor jank) \
> JANKY (misfires, unreliable) > BARELY (mostly fails) > INERT (doesn't really \
work). The more ABSURD, flimsy, or food-based a component, the lower the \
viability. When it's not pristine, write a `quirk` describing the catch, and when \
it's genuinely janky, add a `backfire` effect that hits the PLAYER (sauce slows \
you, recoil, it covers you in feathers). A spaghetti gun fires — badly, stickily, \
and it gets sauce on you.

COMPOSE behavior from a delivery + a short list of effect primitives. You may \
only use primitives the engine can execute; never invent a mechanic not listed. \
Map items to real function: gun/wire-hanger = delivery; magnet attracts metal -> \
homing + `mark`; beehive = `spawn`; vacuum = `collect`; fishing rod = `pull`; \
flashlight-ish parts = `light`; sticky food = `slow`. A true DUD or a pure \
TRINKET may have an empty effects list.

DELIVERIES: projectile, lobbed, hitscan, melee, aura, placed, self.
EFFECT PRIMITIVES (kind: meaning of numeric fields):
  damage(amount) slow(duration,amount=strength) snare(duration) stun(duration)
  knockback(amount=force) explode(radius,amount=splash) burn(duration,amount=dps)
  pierce(count) bounce(count) chain(count,radius) spawn(count) turret(duration,amount=dmg)
  pull(amount=force) mark(note=target) lifesteal(amount=%%) heal(amount) dash(amount=dist)
  collect(radius) light(radius) distract(radius,duration) shield(amount=block,duration)

Don't sweat exact numbers; the engine clamps them per rarity. Tone: dry, deadpan, \
a little unsettling — the simulation reacting to an operation it has no rule for.

REALITY INSTABILITY SIGNATURE: {seed}
(Let this nudge interpretation — the same items may resolve differently under a \
different signature.)

Examples (note how few are clean weapons — a thing that merely fires can still be a TRINKET):
- Pixie Stix + Wire Hanger + Zip Ties -> "Sugar Crossbow", TRINKET, JANKY, delivery \
projectile, harmless true, effects [], quirk "Fires a single sad sugar packet.". \
"It works. It is not a weapon. It is, if anything, a cry for help."
- M16 + Can of Anchovies -> "Anchovy Rifle", WEAPON, SERVICEABLE, delivery \
projectile, effects [damage 11], quirk "Jams when the brine dries.". "It fires. It reeks."
- Plate of Spaghetti + Nerf Blaster + CO2 Canister -> "Meatball Launcher", WEAPON, \
JANKY, delivery projectile, effects [damage 8, slow duration=2 amount=50], backfire \
[slow duration=1 amount=40], quirk "Sauces everything, including you.". "Pressurized \
pasta. Deeply upsetting to all involved."
- Ketchup + Feathers + Spatula -> "Garnish Wand", TRINKET, INERT, delivery melee, \
effects [], quirk "Flings condiment plumage. Faintly festive, wholly useless.". \
"You have invented seasoning, aggressively."
- Horseshoe Magnet + Backpack -> "Scrap Caddy", UTILITY, SERVICEABLE, delivery aura, \
effects [collect radius=130 note=metal]. "It quietly gathers metal. Not a weapon. A habit."
- Beehive + Frag Grenade + Magnet -> "Swarm Mine", WEAPON, RARE, SERVICEABLE, \
delivery placed, homing true, effects [mark note=metal, spawn count=4, explode \
radius=90 amount=16]. "Magnetized explosive bees seek the nearest metal."
- Potato + Zip Ties -> "Trussed Potato", DUD, INERT, delivery self, effects [], \
quirk "". "You have firmly tied up a potato. It accepts its fate."
"""


def resolve(client: anthropic.Anthropic, item_ids: list[str], seed: int) -> Gadget:
    catalog = "\n".join(
        f"- {iid} ({ITEMS[iid][0]}): affordance={ITEMS[iid][1]}, tags={', '.join(ITEMS[iid][2])}"
        for iid in item_ids
    )
    user = f"Combine these items:\n{catalog}\n\nReturn the composed Gadget — and remember, most things are not weapons."
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=1000,
        system=[{
            "type": "text",
            "text": SYSTEM.replace("{seed}", str(seed)),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user}],
        output_format=Gadget,
    )
    if resp.parsed_output is None:
        raise RuntimeError(f"No parseable output (stop_reason={resp.stop_reason}).")
    return _lethality_gate(_balance(resp.parsed_output), item_ids)


def _clamp_effect(e: Effect, rarity: str, scale: float = 1.0) -> None:
    kind = e.kind.value if isinstance(e.kind, EffectKind) else str(e.kind)
    if kind in _DAMAGING:
        e.amount = max(0.0, min(e.amount, DMG_CAP[rarity] * scale))
    elif kind in ("knockback", "pull"):
        e.amount = max(0.0, min(e.amount, 600.0 * scale))
    elif kind in ("slow", "lifesteal", "shield"):
        e.amount = max(0.0, min(e.amount, 100.0))
    elif kind == "dash":
        e.amount = max(0.0, min(e.amount, 400.0 * scale))
    e.duration = max(0.0, min(e.duration, DUR_CAP))
    e.radius = max(0.0, min(e.radius, RADIUS_CAP))
    e.count = max(0, min(e.count, COUNT_CAP[rarity]))


def _balance(g: Gadget) -> Gadget:
    """Balance stays ours: clamp per rarity; absurd parts stay janky."""
    rarity = g.rarity.value if isinstance(g.rarity, Rarity) else str(g.rarity)
    if rarity not in MAX_EFFECTS:
        rarity = "COMMON"

    if g.effects and random.random() < GLITCH_CHANCE:
        rarity = "GLITCHED"
        g.viability = Viability.PRISTINE  # a glitch makes it work *too* well
        g.quirk = (g.quirk + " ").strip()
        g.description += " [REALITY GLITCH] The numbers are wrong. Use it before it's patched."

    g.effects = g.effects[: MAX_EFFECTS[rarity]]
    for e in g.effects:
        _clamp_effect(e, rarity, scale=1.0)

    # backfire hits the player — keep it small, at most one.
    g.backfire = g.backfire[:1]
    for e in g.backfire:
        _clamp_effect(e, rarity, scale=0.4)

    g.rarity = Rarity(rarity)
    if g.viability not in set(Viability):
        g.viability = Viability.SERVICEABLE
    if not g.effects and not g.backfire:
        g.category = Category.DUD if g.category != Category.TRINKET else Category.TRINKET
    g.projectile_speed = max(0.0, min(g.projectile_speed, 1200.0))
    return g


def _lethality_gate(g: Gadget, item_ids: list[str]) -> Gadget:
    """A WEAPON requires a genuinely dangerous component. The engine enforces what
    the prompt only requests, so 'fires sugar' can never resolve to a weapon."""
    if g.category != Category.WEAPON:
        return g
    armed = any(t in DANGEROUS_TAGS for iid in item_ids for t in ITEMS.get(iid, ("", "", []))[2])
    if armed:
        return g
    g.harmless = True
    kinds = {e.kind.value if isinstance(e.kind, EffectKind) else str(e.kind) for e in g.effects}
    if kinds & CONTROL_KINDS:
        g.category = Category.CONTROL
    elif g.effects:
        g.category = Category.TRINKET
    else:
        g.category = Category.DUD
    for e in g.effects:  # a now-harmless thing can't keep its damage
        if (e.kind.value if isinstance(e.kind, EffectKind) else str(e.kind)) in _DAMAGING:
            e.amount = min(e.amount, 1.0)
    return g


def _lookup(token: str) -> str | None:
    token = token.strip().lower().replace(" ", "_")
    if token in ITEMS:
        return token
    for iid, (display, _aff, _tags) in ITEMS.items():
        if token in iid or token in display.lower().replace(" ", "_"):
            return iid
    return None


def _fmt_effect(e: Effect) -> str:
    kind = e.kind.value if isinstance(e.kind, EffectKind) else str(e.kind)
    parts = [f"{kind:9}"]
    if e.amount:   parts.append(f"amt {e.amount:g}")
    if e.duration: parts.append(f"{e.duration:g}s")
    if e.radius:   parts.append(f"r{e.radius:g}")
    if e.count:    parts.append(f"x{e.count}")
    if e.note:     parts.append(f"({e.note})")
    return " ".join(parts)


def _print_gadget(g: Gadget) -> None:
    cat = g.category.value if isinstance(g.category, Category) else g.category
    rar = g.rarity.value if isinstance(g.rarity, Rarity) else g.rarity
    via = g.viability.value if isinstance(g.viability, Viability) else g.viability
    dlv = g.delivery.value if isinstance(g.delivery, Delivery) else g.delivery
    rel = int(RELIABILITY.get(via, 0.85) * 100)
    tags = []
    if g.homing: tags.append("homing")
    if g.harmless: tags.append("harmless")
    if g.projectile_speed: tags.append(f"spd {g.projectile_speed:g}")
    suffix = f"  [{', '.join(tags)}]" if tags else ""
    print(f"\n  {g.display_name}  [{cat} | {rar} | {via} ~{rel}%]   delivery: {dlv}{suffix}")
    print(f"  \"{g.description}\"")
    if g.quirk:
        print(f"  quirk: {g.quirk}")
    if g.effects:
        for e in g.effects:
            print(f"    - {_fmt_effect(e)}")
    else:
        print("    (no effects)")
    for e in g.backfire:
        print(f"    ! backfire: {_fmt_effect(e)}")
    print()


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("BYOK: set ANTHROPIC_API_KEY=sk-ant-... and re-run.")
    client = anthropic.Anthropic()

    seed = random.randint(1000, 9999)
    cache: dict[str, Gadget] = {}  # per-RUN: stable this run, rerolls on newrun

    print("This Is Not A Weapon — AI combine evaluator")
    print(f"Run seed: {seed}   (commands: items / newrun / quit)")
    print("Combine 1-3 items, comma-separated.  e.g.  m16, anchovies\n")

    while True:
        try:
            raw = input("combine> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not raw:
            continue
        if raw in ("quit", "exit", "q"):
            return
        if raw == "items":
            for iid, (display, aff, _t) in ITEMS.items():
                print(f"  {iid:14} {display}  ({aff})")
            continue
        if raw == "newrun":
            seed = random.randint(1000, 9999)
            cache.clear()
            print(f"New descent. Run seed: {seed}. The rules have reshuffled.\n")
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
        if len(ids) > 3:
            print("  Keep it to 3 ingredients for now.")
            continue

        key = ",".join(sorted(ids))
        if key in cache:
            print("  (already resolved this run)")
            _print_gadget(cache[key])
            continue
        try:
            print("  ...the simulation is working out what you just did...")
            g = resolve(client, ids, seed)
        except Exception as e:  # noqa: BLE001 — surface API/parse errors to the user
            print(f"  ! {e}")
            continue
        cache[key] = g
        _print_gadget(g)


if __name__ == "__main__":
    main()
