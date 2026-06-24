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

Controls: **WASD/arrows** move · **mouse** aim · **left-click** use the equipped gadget.
On the right: click items into the **pot** (max 3), hit **Combine**, then fire it in the
test chamber. Toggle **Tier 1/2/3** to feel the progression gating.

### Things to try

| Combine | Tier | Result |
|---|---|---|
| M16 + Can of Anchovies | 1 | Anchovy Rifle (the first crack) |
| M16 + Pringles Can | 2 | Scoped M16 (a modifier) |
| Ketchup + Spatula + Feathers | 2 | Gunk Lobber (harmless slow) |
| Beehive + Frag Grenade + Magnet | 3 | Swarm Mine (homing splash) |
| Bear Trap + Boomerang + Fishing Rod | 3 | Retriever (snare) |
| Backpack + Chainsaw + Shop Vacuum | 3 | Harvester (auto-collect loot) |
| Pixie Stix + Wire Hanger + Zip Ties | 3 | a crossbow that fires, harmlessly |

Also try a **special at the wrong tier** (e.g. the Swarm Mine on Tier 1) to see the
simulation refuse — and a nonsense combo to see a *dud* get acknowledged instead of ignored.

## Layout

```
project.godot        # Godot project config; main scene = scenes/Main.tscn
scenes/Main.tscn     # root Node2D -> scripts/main.gd
scripts/
  item.gd            # Item: id, slots, affordance, tags, color
  item_db.gd         # the junk library (~21 items)
  gadget.gd          # Gadget: the resolved effect profile
  resolver.gd        # SPECIALS (authored) over compose() (generic engine) + tier gating
  main.gd            # test chamber: world state, draw, combine UI, tier toggle
```

## Next steps (when the verb feels good)

- More effect categories wired into combat (Mobility/dash, Consumable/heal).
- A few more authored specials to seed the escalation curve.
- Replace squares with a flat-icon item style; Kenney CC0 packs for the world/UI.
- Eventually: the same resolver behind a 3D body. It doesn't care how it's rendered.
