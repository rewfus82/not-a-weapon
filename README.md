# This Is Not A Weapon

> Code name: **not-a-weapon**. A 2D top-down prototype.

You're an entity in a simulated reality. You start to notice you can **combine random
everyday junk** to make weird things — most of which are not weapons. As your grasp on
reality shatters, the simulation's rules loosen and you can combine more freely.

This repo is currently a **graybox**: squares and text, no art. The only goal right now
is to answer one question — *is the combine verb fun?*

## Core design (the part that makes or breaks it)

- **Items carry functions, not just materials.** Each item has `slots` it can fill,
  an `affordance` (its human verb), and `tags`. A Pringles can is a *tube* → a scope.
- **Combining outputs an effect profile, not "a weapon."** Results land in a category:
  `DAMAGE`, `CONTROL`, `MOBILITY`, `UTILITY`, `CONSUMABLE`, or `DUD`. A pixie-stix
  crossbow really fires — it's just harmless. That's a feature.
- **Gadget grammar = Delivery + Payload + Behavior/Targeting.** The resolver composes
  filled slots, so players can invent gadgets we never authored and they still make sense.
- **Two layers:** hand-authored `SPECIALS` (the jokes + story beats) override a generic
  `compose()` engine that makes *any* combination respond.
- **Progression = unlocking slots, not recipes.** Tier 1: swap ammo in a real gun.
  Tier 2: add modifiers to weapons. Tier 3: build anything from anything. The tier is
  literally how loose the simulation's grip on reality is.

## Run it

1. Install **Godot 4.x** (standard build, GDScript — no C#/.NET needed): <https://godotengine.org/download>
2. Open Godot → **Import** → select this folder's `project.godot` → **Import & Edit**.
3. Press **F5** (Play). The main scene is `scenes/Main.tscn`.

### The loop

**Scavenge → Wave → repeat (harder).** Each cycle: a **BUILD phase** (loot junk by
walking into the HOUSE/CAR/DUMPSTER/CORPSE PILE, combine on the bench, equip — a
countdown ticks to the next wave, or press **SPACE** to start early), then a **WAVE
phase** (zombies chase you; fight with what you built; kills drop more junk). Survive
to keep going; **die** and you restart with **R**.

Controls: **WASD/arrows** move · **mouse** aim · **left-click** fire · **SPACE** start
wave early · **R** restart on death.

On the right: click owned items into the **bench** (max 3), then either **COMBINE**
(build a new weapon — consumes the junk) or **MODIFY** (augment your *equipped*
weapon with the junk: a Pringles can adds pierce, a magnet adds homing, CO2 adds
speed). You start with a Rusty Pistol and a little junk; everything else you scavenge.

**Components drive the weapon.** Delivery comes from the parts — a gun fires
projectiles, a chainsaw is **melee** (arc swing + knockback), a grenade is **lobbed**
(explodes), a bear trap is **placed**, a vacuum is a passive **aura**. Effects compose
from tags: explosive→splash, sticky→slow, swarm→spawned homing bees, tube→pierce,
electric→burn. So `chainsaw + magnet` plays nothing like `M16 + pringles`.

## Layout

```
project.godot        # Godot project config; main scene = scenes/Main.tscn
scenes/Main.tscn     # root Node2D -> scripts/main.gd
scripts/
  item.gd            # Item: id, slots, affordance, tags, color
  item_db.gd         # the junk library (~21 items)
  gadget.gd          # Gadget: the resolved effect profile
  resolver.gd        # SPECIALS (authored) over compose() (generic engine) + tier gating
  main.gd            # zombie-wave loop: phases, enemies, scavenging, crafting, juice
```

## Next steps (when the verb feels good)

- More effect categories wired into combat (Mobility/dash, Consumable/heal).
- A few more authored specials to seed the escalation curve.
- Replace squares with a flat-icon item style; Kenney CC0 packs for the world/UI.
- Eventually: the same resolver behind a 3D body. It doesn't care how it's rendered.
