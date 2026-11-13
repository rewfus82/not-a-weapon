"""Forge (local resolver) tests. Skipped without the optional extra (pip install -e ".[forge]"); the end-to-end model
tests additionally need the weights (python -m forge.fetch). No network, no API calls."""
import json
import random

import pytest

torch = pytest.importorskip("torch")

from forge import mechanics  # noqa: E402
from forge.grammar import DIRECT, FIRING, MAX_FX, MAX_STAGES, Grammar  # noqa: E402
from forge.mechanics import EOS, SPECIALS, GameCodec, build_from_names, slot_names  # noqa: E402
from forge.sampling import combo_seed  # noqa: E402
from forge.shippable import HARD, Checker, best_of, repeats  # noqa: E402
from forge.text import relex  # noqa: E402
from resolver.bake.schema import ScaffoldSet  # noqa: E402
from resolver.clamp import apply as clamp_apply  # noqa: E402
from resolver.contract import GadgetDraft, Tier  # noqa: E402
from resolver.validate import repair  # noqa: E402

# one build per interesting chassis rule: PLACED fires ON_TRIGGER, GUARD on use/block, SELF kit legality (protective
# vs not), DASH, and the direct-fire forms
BUILDS = [
    ["bear trap", "jug of motor oil"],
    ["riot shield", "car battery"],
    ["firefighter turnout coat", "propane tank"],
    ["adrenaline shot", "case of energy drinks"],
    ["baseball bat", "car battery", "road flare", "bag of marbles"],
    ["m16 rifle", "5.56 rounds"],
    ["jerrycan of gasoline", "road flare"],
    ["t-shirt cannon", "crate of overripe produce", "can of expanding foam"],
]


class _FakeTok:
    """Just enough tokenizer for GameCodec: specials map to their ids, any other id is an ordinary word."""

    def token_to_id(self, s):
        return SPECIALS.index(s)

    def decode(self, ids, skip_special_tokens=False):
        return " ".join(SPECIALS[i] if i < len(SPECIALS) else f"word{i}" for i in ids)


def _sig(d):
    return [(s.trigger.value, [(e.kind.value, e.target.value) for e in s.effects]) for s in d.stages]


def _random_walk(build, rng, extra_words=40):
    ids = {s: i for i, s in enumerate(SPECIALS)}
    text_mask = torch.zeros(len(SPECIALS) + extra_words, dtype=torch.bool)
    text_mask[len(SPECIALS):] = True
    g = Grammar(ids, EOS, text_mask, build)
    out = []
    for _ in range(200):
        tok = rng.choice(g.allowed(out).nonzero().flatten().tolist())
        out.append(tok)
        if tok == EOS:
            break
    return out


@pytest.mark.parametrize("names", BUILDS, ids=lambda n: n[0])
def test_grammar_only_admits_legal_firing_drafts(names):
    """Whatever a model samples under the grammar parses, needs no repair, and has a stage the renderer fires."""
    build = build_from_names(names)
    codec = GameCodec(_FakeTok())
    rng = random.Random(combo_seed(names))
    for _ in range(60):
        out = _random_walk(build, rng)
        assert out[-1] == EOS
        draft = codec.to_draft(out, slot_names(build))
        assert 1 <= len(draft.stages) <= MAX_STAGES
        assert all(1 <= len(s.effects) <= MAX_FX for s in draft.stages)
        assert _sig(repair(draft, build)) == _sig(draft), "grammar let through something repair() changes"
        assert any(s.trigger.value in FIRING.get(build.delivery.value, DIRECT) for s in draft.stages)
        clamp_apply(draft, build, Tier.RARE)  # resolves through the real clamp


def test_grammar_only_lets_descriptions_name_items_in_the_build():
    build = build_from_names(["baseball bat", "car battery"])  # slots 0 and 1 only
    ids = {s: i for i, s in enumerate(SPECIALS)}
    text_mask = torch.zeros(len(SPECIALS) + 5, dtype=torch.bool)
    text_mask[len(SPECIALS):] = True
    g = Grammar(ids, EOS, text_mask, build)
    prefix = [ids["<stage>"], ids["<trig:ON_HIT>"], ids["<fx>"], ids["<k:DAMAGE>"], ids["<t:STRUCK>"],
              ids["<b5>"], ids["<b0>"], ids["<b0>"], ids["<c0>"], ids["<name>"], len(SPECIALS), ids["<desc>"]]
    allowed = g.allowed(prefix)
    assert allowed[ids["<i0>"]] and allowed[ids["<i1>"]]
    assert not allowed[ids["<i2>"]] and not allowed[ids["<i3>"]]


def test_magnitude_buckets_are_monotonic_and_roundtrip_in_order():
    vals = [0, 0.3, 0.9, 1.7, 3.5, 7, 15, 31, 64, 120, 500]
    buckets = [mechanics.bucket(v) for v in vals]
    assert buckets == sorted(buckets) and buckets[0] == 0 and buckets[-1] == len(mechanics.REP) - 1
    reps = [mechanics.REP[b] for b in buckets]
    assert reps == sorted(reps)


def test_combo_seed_is_stable_across_machines():
    assert combo_seed(["d:baseball bat|dmg:-|u:-|m:car battery", "RARE"]) == 3149013869


def test_relex_fixes_articles_and_capitalization():
    assert relex("<i0> meets an <i1>.", ["bat", "extinguisher"]) == "Bat meets an extinguisher."
    assert relex("a <i0> hums", ["airhorn"]) == "An airhorn hums"


def _draft(name, desc, kind="DAMAGE"):
    return GadgetDraft.model_validate({"name": name, "description": desc, "logic": "", "stages": [
        {"trigger": "ON_HIT", "note": "", "effects": [
            {"kind": kind, "target": "STRUCK", "amount": 1, "duration": 0, "radius": 0, "count": 0, "note": ""}]}]})


def test_checker_flags_nonwords_foreign_items_and_copied_names():
    build = build_from_names(["baseball bat", "car battery"])
    # explicit lexicons: the system word list (macOS /usr/share/dict/words) is absent on Windows
    checker = Checker({"words": ["the", "and", "bat", "battery", "swing", "hum"], "names": ["the last charge"]})
    assert not checker.issues(_draft("Battery Swing", "The bat swings and the battery hums."), build)
    assert "oov" in checker.issues(_draft("Againment", "The bat swings."), build)
    assert "foreign" in checker.issues(_draft("Saw Swing", "The chainsaw revs."), build)
    assert "copied" in checker.issues(_draft("The Last Charge", "The bat swings."), build)


def test_checker_soft_issues_lure_idiom_and_repeats():
    build = build_from_names(["baseball bat", "car battery"])
    checker = Checker({"words": ["the", "patient", "customer", "get", "swing"], "names": []})
    issues = checker.issues(_draft("The Patient Patient", "The customer gets a swing.", kind="LURE"), build)
    assert {"lure", "idiom", "repeat"} <= set(issues) and not set(issues) & set(HARD)
    assert repeats("Wash", "the wash strips the finish, the wash strips the finish") == \
        ["the wash strips the", "wash strips the finish"]


def test_best_of_keeps_the_first_clean_candidate_and_reports_the_first_sample():
    build = build_from_names(["baseball bat", "car battery"])
    checker = Checker({"words": ["the", "bat", "swing"], "names": []})
    pool = [_draft("Zzqx", "The bat swings."), _draft("Bat Swings", "The bat swings."), _draft("X", "never")]
    draft, issues, tries, first = best_of(3, lambda i: pool[i], build, checker)
    assert draft.name == "Bat Swings" and not issues and tries == 2 and "oov" in first


def test_training_data_is_valid_and_disjoint_from_the_gold_set():
    from forge.train_mechanics import DATA, load_examples
    root = DATA.parent.parent
    lines = (DATA / "scaffolds-round0.jsonl").read_text().splitlines()
    for line in lines[:200]:
        sc = json.loads(line)["scaffolds"]
        ScaffoldSet.model_validate({"shallow": sc["SHALLOW"], "medium": sc["MEDIUM"], "deep": sc["DEEP"]})
    examples, bad = load_examples()
    assert bad == 0 and len(examples) == 3 * len(lines)
    gold = {c["combo_id"] for c in json.loads((root / "data/bake/combos-pre30.json").read_text())["combos"]}
    assert not gold & {e[0] for e in examples}, "held-out Sonnet combos leaked into training data"


# ---------------------------------------------------------------- end to end with the shipped weights

def _models_present():
    return (mechanics.MODELS / "mechanics").is_dir() and (mechanics.MODELS / "writer").is_dir()


needs_weights = pytest.mark.skipif(not _models_present(), reason="no weights: python -m forge.fetch")


@pytest.fixture(scope="module")
def forge_resolver():
    from forge.resolver import ForgeResolver
    return ForgeResolver(deterministic=True)


@needs_weights
@pytest.mark.parametrize("names,tier", [(BUILDS[0], "COMMON"), (BUILDS[2], "RARE"), (BUILDS[4], "LEGENDARY")],
                         ids=["placed", "self-kit", "four-items"])
def test_forge_resolver_drafts_are_legal_firing_and_deterministic(forge_resolver, names, tier):
    build = build_from_names(names)
    draft = forge_resolver(build, Tier(tier))
    assert _sig(repair(draft, build)) == _sig(draft)
    assert any(s.trigger.value in FIRING.get(build.delivery.value, DIRECT) for s in draft.stages)
    assert draft.name.strip() and len(draft.description.split()) >= 4
    assert clamp_apply(draft, build, Tier(tier)).tier == Tier(tier)
    assert forge_resolver(build, Tier(tier)).model_dump() == draft.model_dump()


@needs_weights
def test_serve_craft_with_forge_reports_source_forge(forge_resolver):
    from resolver import serve
    gadget = serve.craft(forge_resolver, {"items": ["fire extinguisher", "jerrycan of gasoline"], "tier_target": "RARE"})
    assert gadget["source"] == "forge" and gadget["stages"]
