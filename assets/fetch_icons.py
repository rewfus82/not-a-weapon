"""Fetch CC-BY item icons from game-icons.net (via the game-icons/icons repo).

Maps each in-game item id -> a game-icons SVG (with fallbacks), validates the
pick against the real index, downloads to assets/icons/<id>.svg, and writes an
attribution file. game-icons.net icons are CC-BY 3.0 — attribution required.

    python assets/fetch_icons.py
"""

from __future__ import annotations

import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(HERE, "icons")
RAW = "https://raw.githubusercontent.com/game-icons/icons/master/"
DEFAULT = "delapouite/cog.svg"

# item id -> candidate icon paths (first one that exists in the index wins)
MAPPING: dict[str, list[str]] = {
    "m16": ["sbed/rifle.svg", "delapouite/kalashnikov.svg"],
    "nerf_gun": ["john-colburn/pistol-gun.svg", "delapouite/ray-gun.svg"],
    "grenade": ["lorc/grenade.svg"],
    "chainsaw": ["delapouite/chainsaw.svg"],
    "bear_trap": ["lorc/gift-trap.svg", "caro-asercion/venus-flytrap.svg"],
    "anchovies": ["delapouite/canned-fish.svg"],
    "ketchup": ["delapouite/ketchup.svg"],
    "spaghetti": ["delapouite/fast-noodles.svg"],
    "feathers": ["lorc/feather.svg"],
    "pixie_stix": ["delapouite/candy-canes.svg"],
    "potato": ["delapouite/potato.svg"],
    "beehive": ["delapouite/beehive.svg"],
    "magnet": ["lorc/magnet.svg"],
    "boomerang": ["delapouite/armored-boomerang.svg"],
    "fishing_rod": ["delapouite/fishing-pole.svg", "delapouite/boat-fishing.svg"],
    "pringles": ["delapouite/tin-can.svg", "delapouite/canned-fish.svg"],
    "co2_canister": ["delapouite/gas-cylinder.svg", "delapouite/fuel-tank.svg"],
    "vacuum": ["delapouite/vacuum-cleaner.svg"],
    "backpack": ["delapouite/backpack.svg"],
    "wire_hanger": ["delapouite/hanger.svg"],
    "zip_ties": ["delapouite/handcuffs.svg", "lorc/handcuffs.svg"],
    "kitchen_knife": ["delapouite/kitchen-knives.svg", "lorc/broad-dagger.svg", "delapouite/bowie-knife.svg"],
    "frying_pan": ["caro-asercion/saucepan.svg"],
    "rolling_pin": ["delapouite/wood-club.svg", "caro-asercion/froe-and-mallet.svg"],
    "cheese_grater": ["lorc/cheese-wedge.svg", "delapouite/cheese-wedge.svg"],
    "meat_cleaver": ["delapouite/cleaver.svg"],
    "hot_sauce": ["delapouite/hot-spices.svg", "delapouite/chili.svg", "lorc/spray.svg"],
    "oven_cleaner": ["lorc/spray.svg"],
    "nail_gun": ["delapouite/coiled-nail.svg", "sbed/rifle.svg"],
    "power_drill": ["delapouite/drill.svg"],
    "propane_tank": ["delapouite/gas-cylinder.svg", "delapouite/fuel-tank.svg"],
    "car_battery": ["delapouite/car-battery.svg"],
    "gasoline": ["delapouite/jerrycan.svg"],
    "crowbar": ["delapouite/crowbar.svg"],
    "screwdriver": ["lorc/screwdriver.svg"],
    "weed_whacker": ["lorc/reaper-scythe.svg", "delapouite/scythe.svg"],
    "slingshot": ["delapouite/slingshot.svg"],
    "water_gun": ["delapouite/water-gun.svg"],
    "super_ball": ["delapouite/bouncing-spring.svg", "delapouite/cricket-ball.svg"],
    "fireworks": ["lorc/firework-rocket.svg"],
    "marbles": ["delapouite/marbles.svg"],
    "yo_yo": ["delapouite/spinning-top.svg", "delapouite/yin-yang.svg", "lorc/wheel.svg"],
    "battery_acid": ["lorc/chemical-drop.svg", "delapouite/chemical-tank.svg"],
    "bug_spray": ["lorc/spray.svg"],
    "glow_sticks": ["delapouite/glowing-artifact.svg", "lorc/glowing-hands.svg"],
    "helium_tank": ["delapouite/gas-cylinder.svg", "delapouite/fuel-tank.svg"],
    "glue": ["lorc/drop.svg", "delapouite/round-bottom-flask.svg"],
    "duct_tape": ["delapouite/crime-scene-tape.svg", "delapouite/adhesive-bandage.svg"],
    "brick": ["delapouite/brick-pile.svg"],
    "mousetrap": ["delapouite/mouse.svg", "caro-asercion/venus-flytrap.svg"],
    "fire_extinguisher": ["delapouite/fire-extinguisher.svg"],
    "leaf_blower": ["delapouite/handheld-fan.svg", "delapouite/computer-fan.svg"],
    "spray_paint": ["lorc/spray.svg"],
    "laser_pointer": ["lorc/laser-blast.svg", "delapouite/laser-precision.svg", "delapouite/laser-turret.svg"],
    "taser": ["lorc/lightning-arc.svg", "delapouite/electrical-resistance.svg"],
    "ice_pack": ["delapouite/ice-cubes.svg"],
    "jumper_cables": ["delapouite/electrical-socket.svg", "lorc/lightning-arc.svg"],
    "bandages": ["delapouite/arm-bandage.svg", "delapouite/bandage-roll.svg"],
    "caffeine_pills": ["delapouite/medicine-pills.svg"],
    "trash_can_lid": ["delapouite/trash-can.svg"],
    "tripod": ["delapouite/cctv-camera.svg", "delapouite/photo-camera.svg"],
    "boombox": ["delapouite/boombox.svg"],
    "raw_meat": ["delapouite/meat.svg", "delapouite/steak.svg", "delapouite/ham-shank.svg"],
}


def _download(path: str, dest: str) -> None:
    with urllib.request.urlopen(RAW + path, timeout=30) as r:
        data = r.read()
    # strip game-icons' full-canvas black background -> white-on-transparent (tintable)
    data = data.replace(b'<path d="M0 0h512v512H0z"/>', b"")
    with open(dest, "wb") as f:
        f.write(data)


def main() -> int:
    with open(os.path.join(ICONS, "_index.txt"), encoding="utf-8") as f:
        index = {ln.strip() for ln in f if ln.strip()}
    chosen: dict[str, str] = {}
    misses: list[str] = []
    authors: set[str] = set()
    for item, candidates in MAPPING.items():
        pick = next((c for c in candidates if c in index), None)
        if pick is None and DEFAULT in index:
            pick = DEFAULT
        if pick is None:
            misses.append(item)
            print(f"  {item:16} <- (NO MATCH)")
            continue
        try:
            _download(pick, os.path.join(ICONS, item + ".svg"))
        except Exception as exc:  # noqa: BLE001
            misses.append(item)
            print(f"  {item:16} <- download failed: {exc}")
            continue
        chosen[item] = pick
        authors.add(pick.split("/", 1)[0])
        print(f"  {item:16} <- {pick}")
    # attribution (CC-BY 3.0)
    with open(os.path.join(ICONS, "CREDITS.md"), "w", encoding="utf-8") as f:
        f.write("# Item icon credits\n\n")
        f.write("Icons from https://game-icons.net — licensed **CC BY 3.0**.\n\n")
        f.write("Authors used: " + ", ".join(sorted(authors)) + "\n\n")
        for item in sorted(chosen):
            f.write(f"- `{item}` <- {chosen[item]}\n")
    print(f"\ndownloaded {len(chosen)} icons; fell back to default: {misses or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
