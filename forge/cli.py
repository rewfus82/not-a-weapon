"""Craft in the terminal with the local Forge model, through the game's own clamp.

  python -m forge                                        # interactive: Tab completes items, Enter rerolls, 'help'
  python -m forge "baseball bat + car battery" --tier EPIC [--json] [--fresh] [--seed N]

The first item is the delivery chassis (like the game's positional /craft). Without --fresh / a reroll, a combo + tier
always gives the same reading (its "library" seed); rerolls and --fresh sample new seeds.
"""
import json
import re
from pathlib import Path

import numpy as np

from forge import quiet
from forge.mechanics import SLOTS, build_from_names, item_text
from resolver.contract import Tier
from resolver.items import CATALOG

BOLD, DIM, CYAN, YELLOW, RED, RESET = "\033[1m", "\033[2m", "\033[36m", "\033[33m", "\033[31m", "\033[0m"


def suggest(query, k=3):
    """Closest catalog items for an unknown name: word matches on names/aliases first, then Model2Vec similarity
    of the query to each item's name + item_text (so 'tomato' finds the produce crate)."""
    from forge.text import ItemEmbedder
    from forge.shippable import ALIASES
    q = query.lower().strip()
    qw = set(re.findall(r"[a-z0-9]+", q))
    hits = [n for n in sorted(CATALOG)
            if qw & set(re.findall(r"[a-z0-9]+", " ".join([n] + ALIASES.get(n, [])).lower()))]
    if len(hits) < k:
        names = sorted(CATALOG)
        vecs = ItemEmbedder()([q] + [f"{n} {item_text(n)}" for n in names])
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
        hits += [names[i] for i in np.argsort(-(vecs[1:] @ vecs[0])) if names[i] not in hits]
    return hits[:k]




def match_item(q):
    """Catalog name for a typed name -> (name, []); exact names, unambiguous aliases or word-matches
    ('bleach' -> 'jug of bleach', 'bat' -> 'baseball bat'). Otherwise (None, suggestions)."""
    from forge.shippable import ALIASES
    q = q.strip().lower()
    if q in CATALOG:
        return q, []
    by_alias = [n for n in CATALOG if q in (a.lower() for a in ALIASES.get(n, []))]
    if len(by_alias) == 1:
        return by_alias[0], []
    pat = re.compile(r"(?<![\w-])" + re.escape(q) + r"(?![\w-])")
    by_word = [n for n in sorted(CATALOG) if pat.search(" | ".join([n] + ALIASES.get(n, [])).lower())]
    if len(by_word) == 1:
        return by_word[0], []
    return None, (by_word or suggest(q))


def parse_items(text):
    """'bat + bleach' -> (['baseball bat', 'jug of bleach'], problems); problems are printable strings."""
    names, problems = [], []
    for part in (p.strip() for p in text.split("+")):
        if not part:
            continue
        n, hints = match_item(part)
        if n:
            names.append(n)
        else:
            problems.append(f"{part!r} is not in the catalog - did you mean: {', '.join(hints[:4])}?")
    if len(names) > len(SLOTS):
        problems.append(f"at most {len(SLOTS)} items (delivery, damage, utility, modifier)")
    return names, problems


def can_be_chassis(name):
    it = CATALOG[name]
    return it.delivery is not None or it.base_use is not None


def craft(fg, names, tier, seed=None, n=8):
    """-> (gadget dict as the game would receive it, ms)."""
    import time
    from resolver.clamp import apply as clamp_apply
    from resolver.serve import gadget_to_dict
    build = build_from_names(names)
    t0 = time.perf_counter()
    draft = fg.resolve(build, tier, seed=seed, n=n)
    resolved = clamp_apply(draft, build, Tier(tier))
    return gadget_to_dict(resolved, "forge"), (time.perf_counter() - t0) * 1000


def render(names, g, tier, ms, fg, n, seed=None):
    print(f"{CYAN}⚒  {' + '.join(names)}  →  {g['delivery']} · {tier}{RESET}")
    print(f"  {BOLD}{YELLOW}{g['name']}{RESET}  {DIM}[{g['category']}{' · harmless' if g['harmless'] else ''}]{RESET}")
    print(f"  {g['description']}")
    for s in g["stages"]:
        fx = ", ".join(f"{e['kind']}@{e['target']} {e['amount']:.1f}"
                       + (f" {e['duration']:.1f}s" if e['duration'] else "")
                       + (f" r{e['radius']:.1f}" if e['radius'] else "")
                       + (f" ×{e['count']}" if e['count'] else "") for e in s["effects"])
        print(f"    {s['trigger']:<10} {fx}")
    note = f"; issues {fg.last_issues}" if fg.last_issues else ""
    src = "library seed" if seed is None else f"seed {seed}"
    print(f"  {DIM}({ms:.0f} ms, 1 CPU thread, candidate {fg.last_tries}/{n}, {src}{note}){RESET}")


HELP = f"""{DIM}  baseball bat + car battery       craft (first item = delivery chassis; up to 4 items)
  bat + battery @ epic             craft at a tier just this once (short names work when unambiguous)
  <enter>  or  r                   reroll the last craft with a new seed
  fresh                            toggle: every new craft gets a random seed (default off: the same combo
                                   always gives its one "library" result, like the shipped game would)
  ladder                           the last craft at COMMON / RARE / LEGENDARY
  epic  (or: tier epic)            set the default tier: {' '.join(t.value.lower() for t in Tier)}
  random                           a random build
  items                            list the catalog
  help · q                         this help · quit (or Ctrl-D)
  Tab completes item names after each '+'.{RESET}"""


def _readline_setup():
    try:
        import readline
    except ImportError:
        return
    names = sorted(CATALOG)
    cmds = ["ladder", "random", "fresh", "items", "help", "quit", "tier "] + [t.value.lower() for t in Tier]

    def complete(text, state):
        lead = text[: len(text) - len(text.lstrip())]
        frag = text.lstrip().lower()
        buf = readline.get_line_buffer()
        if "@" in buf:  # after '@' only tiers make sense
            opts = [lead + t.value.lower() for t in Tier if t.value.lower().startswith(frag)]
            return opts[state] if state < len(opts) else None
        first = "+" not in buf
        opts = [lead + c for c in names + (cmds if first else []) if c.startswith(frag)]
        if not opts:  # a single word-start match is safe to substitute ('bleach' -> 'jug of bleach')
            ws = [n for n in names if re.search(r"(?<![\w])" + re.escape(frag), n)]
            opts = [lead + ws[0]] if len(ws) == 1 else []
        return opts[state] if state < len(opts) else None

    readline.set_completer(complete)
    readline.set_completer_delims("+@")
    readline.parse_and_bind("bind ^I rl_complete" if "libedit" in (readline.__doc__ or "") else "tab: complete")
    hist = Path.home() / ".forge_history"
    try:
        readline.read_history_file(hist)
    except OSError:
        pass
    import atexit
    atexit.register(lambda: _save_history(readline, hist))


def _save_history(readline, hist):
    try:
        readline.set_history_length(1000)
        readline.write_history_file(hist)
    except OSError:
        pass


def interactive(fg, tier, n, fresh=False):
    import random
    from resolver.contract import Tier as T
    tiers = {t.value.lower(): t.value for t in T}
    _readline_setup()
    print(f"{BOLD}Forge{RESET} {DIM}- crafting with the trained model, through the game's own clamp "
          f"(epoch {fg.ck['epoch']}). Type 'help' for commands.{RESET}")
    print(HELP)
    last = None  # (names, tier)
    pick = lambda: random.randrange(1 << 30) if fresh else None  # noqa: E731
    while True:
        try:
            print()
            line = input(f"forge [{tier}]> ").strip()  # plain prompt: color codes here confuse line editing
        except (EOFError, KeyboardInterrupt):
            print()
            return
        low = line.lower()
        seed, jobs = None, []
        if low in ("q", "quit", "exit"):
            return
        if low == "fresh":
            fresh = not fresh
            print(f"{DIM}  fresh seeds {'on: every craft is a new roll' if fresh else 'off: same combo -> same library result'}{RESET}")
            continue
        if low in ("help", "?", "h"):
            print(HELP)
            continue
        if low in ("items", "ls", "list"):
            names = sorted(CATALOG)
            w = max(map(len, names)) + 2
            cols = max(1, 100 // w)
            for i in range(0, len(names), cols):
                print("  " + "".join(f"{x:<{w}}" for x in names[i:i + cols]))
            print(f"{DIM}  chassis-capable items can go first; others only as damage/utility/modifier{RESET}")
            continue
        if low.removeprefix("tier ").strip() in tiers:
            tier = tiers[low.removeprefix("tier ").strip()]
            print(f"{DIM}  default tier -> {tier}{RESET}")
            continue
        if low in ("", "r", "reroll", "ladder"):
            if last is None:
                print(f"{DIM}  nothing to reroll yet - type some items, e.g.  baseball bat + car battery{RESET}")
                continue
            if low == "ladder":
                jobs = [(last[0], t, None) for t in ("COMMON", "RARE", "LEGENDARY")]
            else:
                jobs = [(last[0], last[1], random.randrange(1 << 30))]
        elif low == "random":
            chassis = random.choice([x for x in CATALOG if can_be_chassis(x)])
            rest = random.sample([x for x in CATALOG if x != chassis], random.randint(1, 3))
            jobs = [([chassis] + rest, tier, pick())]
        else:
            body, _, at = line.partition("@")
            t = tier
            if at.strip():
                if at.strip().lower() not in tiers:
                    print(f"{RED}  unknown tier {at.strip()!r}; tiers: {', '.join(tiers.values())}{RESET}")
                    continue
                t = tiers[at.strip().lower()]
            names, problems = parse_items(body)
            if names and not can_be_chassis(names[0]):
                problems.append(f"{names[0]!r} can't be a delivery chassis - put a tool or weapon first")
            if problems or not names:
                for p in problems or ["type some items, e.g.  baseball bat + car battery   (or 'help')"]:
                    print(f"{RED}  {p}{RESET}")
                continue
            jobs = [(names, t, pick())]
        if low not in ("", "r", "reroll", "ladder"):
            last = jobs[0][:2]
        for names, t, seed in jobs:
            print(f"{DIM}  forging…{RESET}", end="\r", flush=True)
            try:
                g, ms = craft(fg, names, t, seed=seed, n=n)
            except Exception as e:  # keep the session alive on a bad build
                print(f"\033[K{RED}  could not craft: {e}{RESET}")
                break
            print("\033[K", end="")
            render(names, g, t, ms, fg, n, seed)


def main():
    import argparse
    quiet()
    ap = argparse.ArgumentParser(description="Craft with the game-format Forge model, through the game's own clamp. "
                                             "No items = interactive mode.")
    ap.add_argument("items", nargs="*", help='e.g. "baseball bat + car battery" (first item = delivery chassis)')
    ap.add_argument("--tier", default="RARE", choices=[t.value for t in Tier])
    ap.add_argument("--run", default=None, help="model dir (default: models/forge), or hybrid:<mechanics run>+<writer run>")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--n", type=int, default=8, help="best-of-n candidates (first shippable wins)")
    ap.add_argument("--fresh", action="store_true", help="random seed for every craft instead of the library seed")
    a = ap.parse_args()
    names, problems = parse_items(" ".join(a.items)) if a.items else ([], [])
    if problems:
        raise SystemExit("\n".join(problems) + f"\nfull catalog: {', '.join(sorted(CATALOG))}")
    from forge.writer import load_resolver
    fg = load_resolver(a.run)
    if not names:
        return interactive(fg, a.tier, a.n, a.fresh)
    if a.fresh and a.seed is None:
        import random
        a.seed = random.randrange(1 << 30)
    g, ms = craft(fg, names, a.tier, seed=a.seed, n=a.n)
    if a.json:
        print(json.dumps({**g, "latency_ms": round(ms, 1)}))
        return
    render(names, g, a.tier, ms, fg, a.n, a.seed)


if __name__ == "__main__":
    main()
