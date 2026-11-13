"""Shippability checks + best-of-N selection for frozen-library generation.

A generated instance is frozen into the game for every player, so the first bar is "nothing unshippable":
  hard: oov       - a nonword: not in the training text nor in the English dictionary, even after stripping
                    inflections (BPE recombination like "Againment", "unwillumes")
        foreign   - names a catalog item that is not in the build (by a distinctive alias)
        copied    - the name is copied verbatim from the training set
  soft: lure      - LURE effect on a build with no item whose tags support luring
        idiom     - an overused teacher idiom ("the customer", "the appointment", ...)
        repeat    - stutter: a repeated word in the name or a repeated 4-word phrase in the description
Generation is offline/lazy (once per combo, then cached), so sampling N candidates and keeping the first clean
one costs nothing at play time.
"""
import json
import re
from pathlib import Path

from resolver.interactions import effects_for  # noqa: E402
from resolver.items import CATALOG  # noqa: E402

ALIASES = {k: v for k, v in json.loads((Path(__file__).with_name("aliases.json")).read_text()).items() if k != "_doc"}
# common nouns that are also used generically in prose - never treated as a foreign-item mention
GENERIC = {"trap", "coat", "tank", "horn", "drill", "shells", "radio", "cables", "cutter", "washer", "hammer",
           "candle", "bottle", "laser", "kit", "foam", "hose", "produce", "sledge", "flare", "block", "fan", "dewar",
           "cannon", "trimmer", "injector", "steak", "steaks", "cement", "propane"}
# GPT-teacher idioms that Sonnet never uses and small students amplify (measured on the pre30 judging packet)
IDIOMS = ("customer", "appointment", "better idea", "visitor", "recipient", "complaint", "invoice", "paperwork",
          "guest", "welcome")
_IDIOM_RE = re.compile(r"\b(" + "|".join(re.escape(i) for i in IDIOMS) + r")s?\b", re.IGNORECASE)


def has_idiom(text):
    return bool(_IDIOM_RE.search(text))


_STOP = {"the", "and", "with", "for", "from", "into", "that", "its", "your", "you"}


def repeats(name, desc):
    """A content word repeated in the name ('The Patient Patient') or a 4-word phrase repeated in the description
    ('the wash strips the finish, the wash strips the finish') - small-model stutter."""
    nw = [w for w in re.findall(r"[a-z']+", name.lower()) if len(w) > 2 and w not in _STOP]
    dw = re.findall(r"[a-z']+", desc.lower())
    grams = [tuple(dw[i:i + 4]) for i in range(len(dw) - 3)]
    return sorted({w for w in nw if nw.count(w) > 1} | {" ".join(g) for g in grams if grams.count(g) > 1})


LURE_ITEMS = {n for n, it in CATALOG.items() if "LURE" in [k.value for k in effects_for(it.tags)]}
_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def _stem(w):
    w = w[:-2] if w.endswith("'s") else w
    return w[:-1] if len(w) > 3 and w.endswith("s") else w


def words(text):
    return [_stem(w) for w in _WORD.findall(text.lower()) if len(w) > 2]


def build_lexicon(texts, names):
    lex = set()
    for t in texts:
        lex.update(words(t))
    for n, al in ALIASES.items():
        lex.update(words(n + " " + " ".join(al)))
    return {"words": sorted(lex), "names": sorted({n.lower() for n in names})}


_DICT = None


def english():
    """System English word list (macOS /usr/share/dict/words), loaded once; empty if unavailable."""
    global _DICT
    if _DICT is None:
        try:
            _DICT = {w.strip().lower() for w in open("/usr/share/dict/words", encoding="utf-8", errors="ignore")}
        except OSError:
            _DICT = set()
    return _DICT


def _lemmas(w):
    """The word plus crude inflection-stripped forms: breaking->break, making->make, wobbled->wobble, ..."""
    out = {w}
    for suf in ("ing", "ed", "es", "s", "er", "est", "ly", "ies", "ied"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            stem = w[: -len(suf)]
            out |= {stem, stem + "e", stem + "y"}
            if len(stem) > 3 and stem[-1] == stem[-2]:
                out.add(stem[:-1])  # stopped -> stop
    return out


class Checker:
    def __init__(self, lexicon):
        self.words = set(lexicon["words"])
        self.names = set(lexicon["names"])
        self.vocab = self.words | english()

    def is_word(self, w):
        return any(x in self.vocab for x in _lemmas(w))

    def issues(self, draft, build):
        present = [it.name for _, it in build.slots() if it is not None]
        text = f"{draft.name} {draft.description}"
        out = {}
        oov = sorted({w for w in words(text) if not self.is_word(w)})
        if oov:
            out["oov"] = oov
        present_words = {_stem(w) for n in present for a in ALIASES.get(n, [n]) + [n] for w in a.lower().split()}
        foreign = []
        for n, al in ALIASES.items():
            if n in present:
                continue
            for a in al:
                if a in GENERIC or {_stem(w) for w in a.split()} & present_words:
                    continue
                if re.search(r"(?<![\w-])" + re.escape(a) + r"(?![\w-])", text, re.IGNORECASE):
                    foreign.append(n)
                    break
        if foreign:
            out["foreign"] = foreign
        if draft.name.strip().lower() in self.names:
            out["copied"] = [draft.name]
        if has_idiom(draft.description):
            out["idiom"] = _IDIOM_RE.findall(draft.description)
        rep = repeats(draft.name, draft.description)
        if rep:
            out["repeat"] = rep
        if any(e.kind.value == "LURE" for s in draft.stages for e in s.effects) and not set(present) & LURE_ITEMS:
            out["lure"] = ["no lure-capable item"]
        return out


HARD = ("oov", "foreign", "copied")


def best_of(n, sample, build, checker):
    """sample(i) -> GadgetDraft. Returns (draft, issues, tries, first_issues): the first candidate with no issues,
    else the one with the fewest hard issues (then soft). first_issues = what a single sample (n=1) would have had."""
    best, first = None, None
    for i in range(n):
        d = sample(i)
        iss = checker.issues(d, build)
        if first is None:
            first = iss
        key = (sum(k in iss for k in HARD), len(iss), i)
        if best is None or key < best[0]:
            best = (key, d, iss, i + 1)
        if not iss:
            break
    return best[1], best[2], best[3], first
