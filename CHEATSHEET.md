# Combine Cheat Sheet (dev reference)

How the bench works:
- **BUILD** = junk → a new weapon (delivery + effects come from the parts' tags).
- **MOD** = equipped weapon + junk → augments it (Pringles add pierce, magnet adds homing…).
- **LOAD** = junk → ammo for the equipped weapon (the loaded round *alters the shot*).

Debug: every run auto-stocks all items. **G** = top up items · **T** = add every special below to your arsenal · **SPACE** = pause.

---

## Authored special combos (exact recipes)

Build these *exact* item sets to get the named result. Everything else is generic composition.

| Items | → Weapon | Does |
|---|---|---|
| Can of Anchovies + M16 Rifle | **Anchovy Rifle** | full-auto, fishy |
| Beehive + Frag Grenade + Horseshoe Magnet | **Swarm Mine** | placed; homing explosive bees |
| CO2 Canister + Nerf Blaster + Plate of Spaghetti | **Meatball Launcher** | fast sticky rounds (damage + slow) |
| Backpack + Chainsaw + Shop Vacuum | **Harvester** | aura: vacuums loot + shreds nearby |
| Bear Trap + Boomerang + Fishing Rod | **Retriever** | placed trap: snare + damage |
| Fireworks + Pringles Can | **Roman Candle** | spawns flaming sparks (spawn + burn) |
| Bottle of Glue + Frag Grenade | **Sticky Bomb** | lobbed: explode + slow |
| Beehive + CO2 Canister | **Bee Cannon** | fast homing bee swarm |
| Can of Anchovies + Beehive | **Chum Swarm** | homing bees + damage |
| Horseshoe Magnet + Bag of Marbles | **Bearing Storm** | homing piercing rounds |
| Propane Tank + Wire Hanger | **Bottle Rocket** | lobbed: big explosion |
| Chainsaw + CO2 Canister | **Buzzsaw Launcher** | piercing high-damage projectile |
| Jerry Can of Gas + Spray Paint | **Flamethrower** | cone: burn + knockback |
| Car Battery + Taser | **Arc Lance** | beam: damage + burn |
| Car Battery + Jumper Cables | **Chain Lightning** | chains between enemies |
| Ice Pack + Nail Gun | **Frost Driver** | freeze, then shatter |

---

## Tag reference (drives generic combos)

A combination's **delivery** comes from the first matching tag; its **effects** from every tag present.

### Delivery (how it's used)
| If parts have… | Delivery |
|---|---|
| `gun_frame` / `ranged` | projectile (aim + fire) |
| `beam` | beam (hold, hitscan line) |
| `aerosol` / `scatter` | cone (short-range spray fan) |
| `explosive` / `thrown` | lobbed (arcs, explodes) |
| `return` | boomerang (out and back) |
| `kinetic` / `flat` | melee (swing, continuous) |
| `snare` | placed (trap) |
| `suction` / `storage` | aura (passive field) |

### Effects (what it does)
| Tag | Effect |
|---|---|
| `lethal` / `kinetic` / `heavy` | + damage |
| `explosive` | splash explosion |
| `sticky` | slow on hit |
| `snare` / `stun` | root/snare |
| `electric` / `flammable` / `caustic` / `spicy` / `poison` | burn (damage over time) |
| `swarm` | spawn homing bees |
| `attract` | homing |
| `tube` / `sharp` | pierce (passes through) |
| `pressure` | faster + harder |
| `blunt` | knockback |
| `cold` | freeze (near-stop + shatter) |
| `conductive` | chain lightning |
| *(no dangerous tag)* | harmless contraption |

### Ammo (LOAD junk → the round behaves differently)
| Tag | Round |
|---|---|
| `light` / `fluffy` / `powder` / `sugar` | harmless, fast then drags to a stop |
| `canned` / `metal` / `rubber` | ricochets off walls |
| `lethal` / `dense` / `heavy` | hits harder |
| `sticky` | slows on hit |
| `explosive` | bursts on impact |
| `electric` / `flammable` / `caustic` / `spicy` / `poison` | burning rounds |
| `attract` | homing rounds |
| `sharp` | piercing rounds |
| `cold` | freezing rounds |
| `conductive` | chaining rounds |

---

*Note: this is hand-maintained and may drift as content is added. The live source of
truth is `scripts/resolver.gd` (tables + SPECIALS) and `scripts/item_db.gd` (items).*
