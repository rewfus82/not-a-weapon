"""The junk catalog, behaviour-first. Every item carries a functional verb; the
absurdity lives in *combining* verbs, not in the items being jokes. Each item
declares the layer(s) it can feed (roles), affinity tags (interaction-bearing;
see resolver.interactions.TAXONOMY), and — for mechanisms — the base delivery
FORM it locks. Guns + real ammo share a `caliber` so a matching pair reads as
coherent. See docs/superpowers/specs/2026-07-12-item-catalog-and-behavior-taxonomy-design.md.

Association-cloud conventions (spec: 2026-07-12-association-clouds-design.md):
ordered obvious -> non-obvious -> chainable; lines embody the item's tags and
verb, never contradict them; no digits or magnitudes (caliber names excepted);
real register — cartoon register is a per-item repair applied only on live
refusal evidence, never pre-emptively. Shape is pinned by tests/test_associations.py.
"""
from __future__ import annotations

from dataclasses import dataclass

from resolver.contract import Delivery, EffectKind, Role, Flag, MELEE_DELIVERIES


@dataclass(frozen=True)
class BaseUse:
    """The solo action an item performs with no craft: one delivery, one
    effect — the same behavior it contributes to a craft (the governing
    rule). `armed=True` marks a payload inert until ignited (its patch
    fires on ON_TRIGGER, not on impact)."""
    delivery: Delivery
    effect: EffectKind
    armed: bool = False


@dataclass(frozen=True)
class Item:
    name: str
    # ordered obvious -> non-obvious -> chainable (optional; LLM-path flavor)
    associations: tuple[str, ...] = ()
    roles: frozenset[Role] = frozenset()
    verb: str = ""
    tags: frozenset[str] = frozenset()
    delivery: Delivery | None = None
    caliber: str | None = None
    flags: frozenset[Flag] = frozenset()
    base_use: BaseUse | None = None

    def describe(self) -> str:
        if self.associations:
            return ", ".join(self.associations)
        parts = [self.verb] if self.verb else []
        parts.extend(sorted(self.tags))
        return ", ".join(p for p in parts if p)


M, MOD, SUB = Role.MECHANISM, Role.MODIFIER, Role.SUBSTANCE
WIELD, FIRE, AMMO, LOAD, BASE = (
    Flag.WIELDABLE, Flag.FIREARM, Flag.AMMUNITION, Flag.LOADABLE, Flag.BASE_WEAPON,
)
_GUN = frozenset({WIELD, FIRE, BASE})
_MELEE = frozenset({WIELD})


_ITEMS: list[Item] = [
    # ---- Layer 1 · Mechanism · Ballistic (fast, flat) ----
    Item("m16 rifle",
         associations=(
             "a military service rifle",
             "fires 5.56 on full auto; does exactly what a rifle does",
         ),
         roles=frozenset({M}), verb="fire-auto",
         tags=frozenset(), delivery=Delivery.HITSCAN, caliber="5.56", flags=_GUN,
         base_use=BaseUse(Delivery.HITSCAN, EffectKind.DAMAGE)),
    Item(".22 pistol",
         associations=(
             "a small-bore .22 target pistol",
             "quiet, light, and exactly as boring as it looks",
         ),
         roles=frozenset({M}), verb="fire",
         tags=frozenset(), delivery=Delivery.HITSCAN, caliber=".22", flags=_GUN,
         base_use=BaseUse(Delivery.HITSCAN, EffectKind.DAMAGE)),
    Item("9mm pistol",
         associations=(
             "a standard 9mm sidearm",
             "does exactly what a pistol does; nothing clever about it",
         ),
         roles=frozenset({M}), verb="fire",
         tags=frozenset(), delivery=Delivery.HITSCAN, caliber="9mm", flags=_GUN,
         base_use=BaseUse(Delivery.HITSCAN, EffectKind.DAMAGE)),
    Item("revolver",
         associations=(
             "a .357 six-shooter",
             "heavy trigger, big noise, no surprises",
         ),
         roles=frozenset({M}), verb="fire",
         tags=frozenset(), delivery=Delivery.HITSCAN, caliber=".357", flags=_GUN,
         base_use=BaseUse(Delivery.HITSCAN, EffectKind.DAMAGE)),
    Item(".30-06 hunting rifle",
         associations=(
             "a bolt-action .30-06 hunting rifle",
             "slow, deliberate, and accurate at long range",
         ),
         roles=frozenset({M}), verb="fire",
         tags=frozenset(), delivery=Delivery.HITSCAN, caliber=".30-06", flags=_GUN,
         base_use=BaseUse(Delivery.HITSCAN, EffectKind.DAMAGE)),
    Item("nail gun",
         associations=(
             "a construction tool that spits framing nails",
             "meant to be pressed against wood, but the safety tip is long gone",
             "each nail flies flat and pins whatever it hits",
             "whatever coats the nails goes wherever the nails go",
         ),
         roles=frozenset({M}), verb="drive-nails",
         tags=frozenset({"sharp"}), delivery=Delivery.PROJECTILE, flags=_MELEE,
         base_use=BaseUse(Delivery.PROJECTILE, EffectKind.PIERCE)),

    # ---- Layer 1 · Mechanism · Spread (cone of many) ----
    Item("pump shotgun",
         associations=(
             "a pump-action 12ga shotgun",
             "wide, loud, and short-ranged; exactly what it looks like",
         ),
         roles=frozenset({M}), verb="fire-spread",
         tags=frozenset({"scatter"}), delivery=Delivery.SPRAY, caliber="12ga", flags=_GUN,
         base_use=BaseUse(Delivery.SPRAY, EffectKind.DAMAGE)),

    # ---- Layer 1 · Mechanism · Stream (continuous cone/jet) ----
    Item("fire extinguisher",
         associations=(
             "a red steel bottle under serious pressure",
             "vents a freezing white cone that blankets everything in front of it",
             "the blast shoves lightweight things backward and kills open flames",
             "empty, it's still a heavy steel club — and punctured, it takes off like a rocket",
         ),
         roles=frozenset({M}), verb="cone-blast",
         tags=frozenset({"pressurized-gas", "cold"}), delivery=Delivery.SPRAY,
         base_use=BaseUse(Delivery.SPRAY, EffectKind.FREEZE)),
    Item("pressure washer",
         associations=(
             "a motor that turns a garden trickle into a cutting jet",
             "the stream hits hard enough to strip paint and peel bark",
             "knocks light things over and pushes heavy things back",
             "whatever you feed the intake comes out the nozzle at paint-stripping speed",
         ),
         roles=frozenset({M}), verb="jet",
         tags=frozenset({"liquid"}), delivery=Delivery.BEAM,
         base_use=BaseUse(Delivery.BEAM, EffectKind.KNOCKBACK)),
    Item("industrial fan",
         associations=(
             "a man-high drum fan on a rolling frame",
             "kicks out a steady lane of wind that shoves loose junk downrange",
             "planted in a doorway, nothing light gets through against the airflow",
             "anything airborne — mist, powder, fog, sparks — rides the lane to the far end",
         ),
         roles=frozenset({M}), verb="blow",
         # "heavy", not "electrical": an electrical tag would edge with the garden
         # hose (electrical+liquid) and collapse swamp_cooler's middle band (C=2/3).
         tags=frozenset({"wind", "heavy"}), delivery=Delivery.PLACED,
         base_use=BaseUse(Delivery.PLACED, EffectKind.KNOCKBACK)),
    Item("garden hose",
         associations=(
             "a long rubber hose that sprays wherever you point it",
             "soaks the ground into mud and puddles",
             "kink it and let go for a single hard spurt",
             "a wet floor plus anything electrical is everyone's problem at once",
         ),
         roles=frozenset({M}), verb="spray-water",
         tags=frozenset({"liquid"}), delivery=Delivery.SPRAY,
         base_use=BaseUse(Delivery.SPRAY, EffectKind.KNOCKBACK)),

    # ---- Layer 1 · Mechanism · Arc (lobbed, indirect) ----
    Item("t-shirt cannon",
         associations=(
             "a stadium souvenir cannon that lobs whatever fits down the barrel",
             "a puff of compressed gas sends the payload in a high arc",
             "doesn't care what the payload is, only that it fits",
             "load something that splashes, shatters, or burns and it delivers that downrange",
         ),
         roles=frozenset({M}), verb="launch",
         tags=frozenset({"pressurized-gas"}), delivery=Delivery.LOBBED,
         base_use=BaseUse(Delivery.LOBBED, EffectKind.STAGGER)),
    Item("roman candle",
         associations=(
             "a cardboard tube that spits burning stars one at a time",
             "each star pops loud and glows bright enough to read by",
             "the stars keep burning wherever they land",
             "every star is a flying ignition source for anything flammable it touches",
         ),
         roles=frozenset({M, MOD}), verb="lob-sparks",
         tags=frozenset({"flammable", "ignition", "light-source", "loud"}),
         delivery=Delivery.LOBBED,
         base_use=BaseUse(Delivery.LOBBED, EffectKind.BURN)),

    # ---- Layer 1 · Mechanism · Thrown (single-arc object) ----
    Item("glass bottle",
         associations=(
             "an empty glass bottle, ready to be filled",
             "shatters on the first hard knock into a burst of sharp shards",
             "holds a pour of whatever liquid you have on hand",
             "thrown full, it breaks on impact and splashes its contents over everything nearby",
         ),
         roles=frozenset({M}), verb="smash",
         tags=frozenset({"brittle", "container"}), delivery=Delivery.THROWN,
         base_use=BaseUse(Delivery.THROWN, EffectKind.PIERCE)),
    Item("cinder block",
         associations=(
             "a two-handed slab of concrete",
             "everything it lands on stays landed on",
             "awkward to throw far, devastating to drop close",
             "crushes brittle things flat and pins whatever it doesn't crush",
         ),
         roles=frozenset({M}), verb="hurl",
         tags=frozenset({"heavy", "blunt"}), delivery=Delivery.THROWN,
         base_use=BaseUse(Delivery.THROWN, EffectKind.DAMAGE)),

    # ---- Layer 1 · Mechanism · Beam (instant sustained line) ----
    Item("salvaged laser cutter",
         associations=(
             "an industrial cutting head pulled off its gantry, trigger wired by hand",
             "projects a thin line of light that scorches a seam across whatever it crosses",
             "steady hands turn it into a slow knife at a distance",
             "anything flammable along the line starts smoking before the beam even finishes passing",
         ),
         roles=frozenset({M}), verb="cut",
         tags=frozenset({"light-source"}), delivery=Delivery.BEAM,
         base_use=BaseUse(Delivery.BEAM, EffectKind.BURN)),

    # ---- Layer 1 · Mechanism · Melee (contact) ----
    Item("crowbar",
         associations=(
             "a bent steel bar with a flattened claw",
             "swings mean and pries meaner",
             "finds the gap in anything — doors, crates, armor plates",
             "wedged into a seam, it turns your whole body weight into leverage",
         ),
         roles=frozenset({M}), verb="pry-&-swing",
         tags=frozenset({"blunt"}), delivery=Delivery.SWING, flags=_MELEE,
         base_use=BaseUse(Delivery.SWING, EffectKind.DAMAGE)),
    Item("sledgehammer",
         associations=(
             "a slab of steel on a long handle",
             "too slow to swing twice, too heavy to need to",
             "the follow-through carries into walls, floors, and whatever's behind the target",
             "one full swing turns brittle things into gravel",
         ),
         roles=frozenset({M}), verb="smash",
         tags=frozenset({"blunt", "heavy"}), delivery=Delivery.SLAM, flags=_MELEE,
         base_use=BaseUse(Delivery.SLAM, EffectKind.DAMAGE)),
    Item("fire axe",
         associations=(
             "a heavy axe head on a long haft, made for cutting through doors",
             "bites deep and sticks where it lands",
             "the spike on the back punches holes the blade can't",
             "momentum does the work — whatever it hits, it hits committed",
         ),
         roles=frozenset({M}), verb="chop",
         tags=frozenset({"sharp"}), delivery=Delivery.SWING, flags=_MELEE,
         base_use=BaseUse(Delivery.SWING, EffectKind.PIERCE)),
    Item("machete",
         associations=(
             "a long flat blade made for clearing brush",
             "light enough to swing all day, fast enough to swing twice",
             "slices in arcs rather than chops",
             "whatever's smeared on the blade ends up in every cut",
         ),
         roles=frozenset({M}), verb="slash",
         tags=frozenset({"sharp"}), delivery=Delivery.SWING, flags=_MELEE,
         base_use=BaseUse(Delivery.SWING, EffectKind.PIERCE)),
    Item("screwdriver",
         associations=(
             "a palm-sized steel spike with a handle",
             "goes exactly where you push it, no farther",
             "punches through sheet metal if you lean in",
             "jammed into a moving part, it stops the whole machine",
         ),
         roles=frozenset({M}), verb="stab",
         tags=frozenset({"sharp"}), delivery=Delivery.THRUST, flags=_MELEE,
         base_use=BaseUse(Delivery.THRUST, EffectKind.PIERCE)),
    Item("baseball bat",
         associations=(
             "a solid wooden bat with real swing weight",
             "the sweet spot sends things flying instead of just breaking them",
             "flexes a hair on impact and gives the hit a spring",
             "anything small and hard becomes a line drive if you can toss it up first",
         ),
         roles=frozenset({M}), verb="clobber",
         tags=frozenset({"blunt", "heavy", "springy"}), delivery=Delivery.SWING, flags=_MELEE,
         base_use=BaseUse(Delivery.SWING, EffectKind.DAMAGE)),
    Item("power drill",
         associations=(
             "a cordless drill with a fresh bit",
             "chews through wood, plastic, and thin steel",
             "the torque wrenches your wrist if the bit binds",
             "pressed against anything, it doesn't stop at the surface",
         ),
         roles=frozenset({M}), verb="bore",
         tags=frozenset({"sharp"}), delivery=Delivery.THRUST, flags=_MELEE,
         base_use=BaseUse(Delivery.THRUST, EffectKind.PIERCE)),
    Item("angle grinder",
         associations=(
             "a spinning abrasive disc on a motor",
             "throws a rooster tail of sparks off bare metal",
             "doesn't cut so much as eat its way through",
             "the spark stream is an ignition source you can aim",
         ),
         roles=frozenset({M}), verb="grind",
         tags=frozenset({"sharp"}), delivery=Delivery.SWING, flags=_MELEE,
         base_use=BaseUse(Delivery.SWING, EffectKind.PIERCE)),
    Item("chainsaw",
         associations=(
             "a motorized chain of cutting teeth",
             "announces itself from a block away",
             "pulls itself into the cut once it bites",
             "the noise alone empties a room before the blade arrives",
         ),
         roles=frozenset({M}), verb="saw",
         tags=frozenset({"sharp", "loud"}), delivery=Delivery.SWING, flags=_MELEE,
         base_use=BaseUse(Delivery.SWING, EffectKind.PIERCE)),
    Item("weed whacker",
         associations=(
             "a spinning line on the end of a long shaft",
             "stings and shreds anything soft inside a wide arc",
             "keeps threats at a full pole's length",
             "swap the trimmer line for wire or chain and the sting becomes a bite",
         ),
         roles=frozenset({M}), verb="whip",
         tags=frozenset({"long-reach"}), delivery=Delivery.WHIP, flags=_MELEE,
         base_use=BaseUse(Delivery.WHIP, EffectKind.DAMAGE)),
    Item("riot shield",
         associations=(
             "a clear polymer wall with a handle",
             "turns anything thrown or swung at you",
             "leaning in, it's a pushing weapon in its own right",
             "whatever splashes against the front stays on the front — not on you",
         ),
         roles=frozenset({M}), verb="block",
         tags=frozenset({"protective"}), delivery=Delivery.GUARD, flags=_MELEE,
         base_use=BaseUse(Delivery.GUARD, EffectKind.SHIELD)),

    # ---- Layer 1 · Mechanism · Placed ----
    Item("bear trap",
         associations=(
             "a spring-loaded steel jaw staked to the ground",
             "waits under leaves or trash until something steps in",
             "snaps shut hard enough to hold what it catches",
             "anything lured, herded, or knocked onto it does the work for you",
         ),
         roles=frozenset({M}), verb="snap",
         tags=frozenset({"sharp"}), delivery=Delivery.PLACED,
         base_use=BaseUse(Delivery.PLACED, EffectKind.SNARE)),

    Item("airhorn",
         associations=(
             "a pocket air canister with a trumpet that makes ears ring",
             "one blast turns every head on the block",
             "wedge the button down and it screams until the can dies",
             "set it where you aren't, and everything comes running to where you aren't",
         ),
         roles=frozenset({M}), verb="blare",
         tags=frozenset({"loud"}), delivery=Delivery.PLACED,
         base_use=BaseUse(Delivery.PLACED, EffectKind.LURE)),

    # ---- Layer 1 · Mechanism · Self / mobility ----
    Item("leaf blower",
         associations=(
             "a backpack motor that throws a hard lane of wind",
             "shoves loose junk, dust, and mist wherever it points",
             "braced against your own body, the recoil is a push you can ride",
             "anything drifting in the air — spray, smoke, sparks — rides the wind lane downrange",
         ),
         roles=frozenset({M}), verb="gust",
         tags=frozenset({"wind"}), delivery=Delivery.DASH,
         base_use=BaseUse(Delivery.DASH, EffectKind.KNOCKBACK)),
    Item("adrenaline shot",
         associations=(
             "a spring-loaded autoinjector of pure hurry",
             "your legs stop asking questions for a little while",
             "pain arrives later, all at once, with interest",
             "everything else you're carrying gets used faster while it lasts",
         ),
         roles=frozenset({M, SUB}), verb="inject",
         tags=frozenset({"stimulant"}), delivery=Delivery.SELF,
         base_use=BaseUse(Delivery.SELF, EffectKind.SPEED)),
    Item("first-aid kit",
         associations=(
             "gauze, splints, and stims in a plastic clamshell",
             "closes wounds well enough to keep moving",
             "works on the move if you don't mind the stitching",
             "buys back the mistakes the rest of this loadout will cause",
         ),
         roles=frozenset({MOD}), verb="patch",
         tags=frozenset({"restorative"}), delivery=Delivery.SELF,
         base_use=BaseUse(Delivery.SELF, EffectKind.HEAL)),

    # ---- Layer 2 · Modifier / energizer (overlay + effect transform) ----
    Item("propane tank",
         associations=(
             "a squat steel tank of liquid propane under pressure",
             "hisses out a heavier-than-air cloud when the valve cracks",
             "the tank itself flies when ruptured",
             "a leaking cloud finds every spark in the room the hard way",
         ),
         roles=frozenset({MOD, SUB}), verb="fuel-bomb",
         tags=frozenset({"pressurized-gas", "flammable"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.DAMAGE)),
    Item("sack of fertilizer",
         associations=(
             "a heavy sack of pellet fertilizer",
             "grows crops on the label, wears a hazard diamond on the back",
             "burns fast and mean once something sets it off",
             "packed in with anything else that burns, the burn becomes a blast",
         ),
         roles=frozenset({MOD, SUB}), verb="detonate",
         tags=frozenset({"powder", "ignition"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.BURN, armed=True)),
    Item("car battery",
         associations=(
             "dead-weight heavy",
             "holds a charge that arcs across a gap",
             "leaks corrosive acid",
             "a hard enough knock cracks the case and spills the acid",
         ),
         roles=frozenset({MOD, SUB}), verb="electrify",
         tags=frozenset({"electrical", "heavy", "corrosive"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.DAMAGE)),
    Item("jumper cables",
         associations=(
             "a pair of thick copper clamps on long insulated leads",
             "the clamps bite onto anything and hold",
             "bridge them to a live source and the far ends carry the charge",
             "anything conductive they're clipped to becomes part of the circuit",
         ),
         roles=frozenset({MOD}), verb="jolt",
         tags=frozenset({"electrical"}),
         base_use=BaseUse(Delivery.THRUST, EffectKind.SNARE)),
    Item("defibrillator",
         associations=(
             "a portable unit with two paddles and one job",
             "builds a charge with a rising whine, then dumps it all at once",
             "the jolt clenches every muscle it crosses",
             "delivered through anything conductive — rails, puddles, chain link — it travels",
         ),
         roles=frozenset({MOD, SUB}), verb="shock",
         tags=frozenset({"electrical"}),
         base_use=BaseUse(Delivery.THRUST, EffectKind.DAMAGE)),
    Item("taser",
         associations=(
             "a palm-sized stunner with a crackling arc between two prongs",
             "the arc snaps and pops even before it touches anything",
             "a touch locks up whatever muscle it finds",
             "held against metal or wet ground, the crackle keeps traveling",
         ),
         roles=frozenset({MOD, SUB}), verb="stun",
         tags=frozenset({"electrical"}), flags=frozenset({WIELD}),
         base_use=BaseUse(Delivery.THRUST, EffectKind.STAGGER)),

    # ---- Layer 3 · Substance / payload (needs a delivery to come out) ----
    Item("jerrycan of gasoline",
         associations=(
             "a jerrycan of gasoline, sloshing and sharp-smelling",
             "splashes wide, soaks in, and stays",
             "the fumes catch before the liquid does",
             "one spark anywhere on the spill claims the whole spill",
         ),
         roles=frozenset({SUB}), verb="fuel",
         tags=frozenset({"liquid", "flammable", "ignition"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.BURN, armed=True)),
    Item("jug of motor oil",
         associations=(
             "a jug of motor oil — slick, viscous, impossible to get traction on",
             "clings in a dark film to whatever it coats",
             "flammable once something gets it hot enough",
             "poured across a floor it turns the whole stretch into a skating rink",
         ),
         roles=frozenset({SUB}), verb="slick",
         tags=frozenset({"liquid", "flammable", "slippery"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.SLOW)),
    Item("jar of thermite",
         associations=(
             "a jar of dull grey powder that looks like nothing",
             "nearly impossible to light — and nearly impossible to put out once lit",
             "burns hot enough to eat through steel plate",
             "poured onto a surface first, it turns any ignition into a cutting charge",
         ),
         roles=frozenset({SUB}), verb="burn-through",
         tags=frozenset({"powder", "ignition"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.BURN, armed=True)),
    Item("road flare",
         associations=(
             "a stick that strikes to a furious red flame",
             "burns wet or dry, wind be damned",
             "bright enough to blind night eyes and mark positions",
             "an open flame you can hold, plant, or throw at anything that wants lighting",
         ),
         roles=frozenset({SUB}), verb="ignite",
         tags=frozenset({"ignition", "light-source", "flammable"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.BURN)),
    Item("can of hairspray",
         associations=(
             "a can of hairspray under pressure",
             "sprays a fine sticky mist that hangs in the air",
             "the propellant is flammable",
             "a mist plus a spark becomes a gout of flame",
         ),
         roles=frozenset({SUB}), verb="spritz",
         tags=frozenset({"flammable", "pressurized-gas"}),
         base_use=BaseUse(Delivery.SPRAY, EffectKind.SNARE)),
    Item("tub of pool chlorine",
         associations=(
             "a tub of pool-shock granules with a bleachy reek",
             "eats color, fabric, and skin given time",
             "the dust alone stings eyes and throats",
             "given something to react with, the granules boil into stinging fog",
         ),
         roles=frozenset({SUB}), verb="corrode",
         tags=frozenset({"corrosive", "powder"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.BURN)),
    Item("jug of ammonia cleaner",
         associations=(
             "a jug of ammonia cleaner that clears your sinuses from across the room",
             "the fumes sting eyes shut and chase people out of small spaces",
             "slicks and strips whatever it's poured over",
             "in a closed room the fumes do more work than the liquid",
         ),
         roles=frozenset({SUB}), verb="fume",
         tags=frozenset({"corrosive", "liquid"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.BURN)),
    Item("jug of bleach",
         associations=(
             "a jug of household bleach",
             "ruins everything it splashes — cloth, color, skin",
             "the smell alone announces it",
             "an open pan of it makes a room hostile to stay in",
         ),
         roles=frozenset({SUB}), verb="bleach",
         tags=frozenset({"corrosive", "liquid"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.BURN)),
    Item("dewar of liquid nitrogen",
         associations=(
             "a steel dewar of liquid so cold it smokes",
             "a splash freezes surfaces white on contact",
             "what it soaks turns brittle as glass",
             "frozen brittle, things that used to bend now shatter",
         ),
         roles=frozenset({SUB}), verb="freeze",
         tags=frozenset({"cold", "liquid"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.FREEZE)),
    Item("block of dry ice",
         associations=(
             "a block of dry ice, smoking in open air",
             "burns bare skin with cold instead of heat",
             "sublimates into a heavy ground-hugging fog",
             "dropped in water it fogs a whole corridor in moments",
         ),
         roles=frozenset({SUB}), verb="chill",
         tags=frozenset({"cold"}),
         base_use=BaseUse(Delivery.PLACED, EffectKind.FREEZE)),
    Item("bucket of wet cement",
         associations=(
             "a bucket of wet cement, heavy and slopping",
             "clings to boots and drags every step",
             "sets hard on its own schedule, and nothing renegotiates",
             "whatever's standing in it when it cures is furniture now",
         ),
         roles=frozenset({SUB}), verb="set",
         tags=frozenset({"sticky", "liquid"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.SNARE)),
    Item("can of expanding foam",
         associations=(
             "a can of gap-filler foam",
             "a thin bead swells to a fat, sticky loaf",
             "cures from tacky to rock in place",
             "sprayed into a mechanism or a doorway, it becomes the new mechanism",
         ),
         roles=frozenset({SUB}), verb="foam",
         tags=frozenset({"sticky"}),
         base_use=BaseUse(Delivery.SPRAY, EffectKind.SNARE)),
    Item("crate of overripe produce",
         associations=(
             "a crate of produce past its best days",
             "bursts into slick pulp at the slightest violence",
             "the pulp is half slip, half glue",
             "anything driven through it comes out wearing it",
         ),
         roles=frozenset({SUB}), verb="gum-up",
         tags=frozenset({"slippery", "sticky"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.SLOW)),

    # ---- Feeders · Ammo — real (AMMUNITION · caliber-matched) ----
    Item(".22 rounds",
         associations=(
             "a box of .22 rounds",
             "inert until a matching firearm feeds them",
         ),
         roles=frozenset({SUB}), verb="round",
         tags=frozenset(), caliber=".22", flags=frozenset({AMMO})),
    Item("9mm rounds",
         associations=(
             "a box of 9mm rounds",
             "inert until a matching firearm feeds them",
         ),
         roles=frozenset({SUB}), verb="round",
         tags=frozenset(), caliber="9mm", flags=frozenset({AMMO})),
    Item(".357 rounds",
         associations=(
             "a box of .357 rounds",
             "inert until a matching revolver feeds them",
         ),
         roles=frozenset({SUB}), verb="round",
         tags=frozenset(), caliber=".357", flags=frozenset({AMMO})),
    Item("5.56 rounds",
         associations=(
             "a box of 5.56 rounds",
             "inert until a matching rifle feeds them",
         ),
         roles=frozenset({SUB}), verb="round",
         tags=frozenset(), caliber="5.56", flags=frozenset({AMMO})),
    Item("12-gauge shells",
         associations=(
             "a box of 12-gauge shells",
             "inert until a matching shotgun feeds them",
         ),
         roles=frozenset({SUB}), verb="shell",
         tags=frozenset({"scatter"}), caliber="12ga", flags=frozenset({AMMO})),
    Item(".30-06 rounds",
         associations=(
             "a box of .30-06 rounds",
             "inert until a matching rifle feeds them",
         ),
         roles=frozenset({SUB}), verb="round",
         tags=frozenset(), caliber=".30-06", flags=frozenset({AMMO})),

    # ---- Feeders · Ammo — improvised (LOADABLE, small + numerous) ----
    Item("box of nails",
         associations=(
             "a hardware-store box of loose nails",
             "each one is a small sharp problem for whoever's downrange",
             "they tumble and scatter rather than fly true",
             "fired or flung in a handful, they turn one hit into many small punctures",
         ),
         roles=frozenset({SUB}), verb="improvised-round",
         tags=frozenset({"scatter", "sharp"}), flags=frozenset({LOAD}),
         base_use=BaseUse(Delivery.PLACED, EffectKind.PIERCE)),
    Item("tin of ball bearings",
         associations=(
             "a tin of dense steel spheres",
             "heavier than they look; they hit like thrown weights",
             "spilled underfoot, they take feet out from under people",
             "launched in a spread they dent everything in a cone",
         ),
         roles=frozenset({SUB}), verb="improvised-round",
         tags=frozenset({"scatter", "heavy"}), flags=frozenset({LOAD}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.DAMAGE)),
    Item("bag of marbles",
         associations=(
             "a bag of glass marbles",
             "roll forever on any hard floor",
             "underfoot they're a slapstick disaster",
             "scattered ahead of a chase, they end the chase",
         ),
         roles=frozenset({SUB}), verb="improvised-round",
         tags=frozenset({"scatter", "slippery"}), flags=frozenset({LOAD}),
         base_use=BaseUse(Delivery.PLACED, EffectKind.SLOW)),
    Item("bag of gravel",
         associations=(
             "a heavy bag of loose gravel",
             "flung, it's a wave of stinging grit",
             "spread thin, it makes every step loud and unsure",
             "loaded into anything that launches, it becomes a wide, ugly cone",
         ),
         roles=frozenset({SUB}), verb="improvised-round",
         tags=frozenset({"scatter"}), flags=frozenset({LOAD}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.DAMAGE)),
]

CATALOG: dict[str, Item] = {item.name: item for item in _ITEMS}

# Optional per-item tint for the playground; unknown items default to "grey".
_COLOR_BY_ITEM: dict[str, str] = {}


@dataclass
class Build:
    delivery_item: Item
    damage_item: Item | None = None
    utility_item: Item | None = None
    modifier_item: Item | None = None

    @property
    def delivery(self) -> Delivery:
        d = self.delivery_item.delivery
        if d is not None:
            return d
        bu = self.delivery_item.base_use
        if bu is None:
            raise ValueError(f"{self.delivery_item.name!r} cannot be a delivery chassis")
        return bu.delivery

    @property
    def color(self) -> str:
        return _COLOR_BY_ITEM.get(self.delivery_item.name, "grey")

    def slots(self) -> list[tuple[str, Item | None]]:
        return [
            ("delivery", self.delivery_item),
            ("damage", self.damage_item),
            ("utility", self.utility_item),
            ("modifier", self.modifier_item),
        ]


DEFAULT_BUILDS: dict[str, Build] = {
    # grounded, coherent: blunt melee + heavy shock modifier
    "broom_bat": Build(
        delivery_item=CATALOG["baseball bat"],
        modifier_item=CATALOG["car battery"],
    ),
    # coherent firearm: gun + matching-caliber ammo (C should be ~1)
    "gun_ammo": Build(
        delivery_item=CATALOG["m16 rifle"],
        damage_item=CATALOG["5.56 rounds"],
    ),
    # absurd: the Swamp Cooler — placed wind lane + shock modifier + water feed
    "swamp_cooler": Build(
        delivery_item=CATALOG["industrial fan"],
        modifier_item=CATALOG["car battery"],
        utility_item=CATALOG["garden hose"],
    ),
}


def params_for(delivery: Delivery) -> dict[str, float]:
    """Per-delivery-family renderer params (v0 stubs; feel-tuned later)."""
    if delivery in MELEE_DELIVERIES:
        return {"reach": 150.0, "arc": 90.0, "commit": 0.4, "sweep_targets": 2.0}
    if delivery is Delivery.GUARD:
        return {"block_arc": 120.0, "parry_window": 0.3}
    if delivery in (Delivery.SELF, Delivery.DASH):
        return {"distance": 300.0, "self_duration": 3.0}
    # ranged / thrown / placed / spray / beam / hitscan / projectile / lobbed
    return {"range": 800.0, "projectile_speed": 1200.0, "spread": 10.0, "homing": 0.0}
