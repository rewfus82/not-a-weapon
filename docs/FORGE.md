# Forge: a local, CPU-only resolver

Forge is a third `resolver_fn`, alongside `resolver.llm` and `resolver.fallback`. It is a small trained model that runs
on one CPU thread with no API key and no per-craft cost. Its readings are far closer to Sonnet's than the
deterministic fallback's. It slots into the existing pipeline unchanged: the model proposes composition (stages, effect
kinds, targets, relative weights, name and description), and `fill_budget` + `clamp.apply` still own every number.

```
game ──POST /craft──▶ serve.py ─▶ ForgeResolver ─▶ fill_budget ─▶ clamp.apply ─▶ gadget JSON ─▶ game
                                   │  mechanics model (stages, grammar-constrained)
                                   │  writer (name + description for exactly those stages)
                                   │  best-of-8 shippability filter
                                   └ any error ─▶ deterministic fallback (as today)
```

## Quick start

```bash
pip install -e ".[forge]"           # torch, transformers, tokenizers, safetensors, numpy, model2vec
python -m forge.fetch               # weights (~310 MB) -> models/forge/  (git-ignored)

python -m resolver.serve --forge    # the sidecar on the local model: the game and the playground work unchanged
python -m forge                     # or craft in the terminal (Tab completes items, Enter rerolls, 'help')
python -m forge "baseball bat + car battery" --tier LEGENDARY
```

With `--forge`, `/craft` and `/api/roll` report `source: "forge"`. The game shows `crafted: <name> [forge]`, and the
playground shows a `forge` badge. Each call samples a fresh reading, the same contract as the live LLM path: acquisition
is random, and the drawn instance is what gets frozen. `ForgeResolver(deterministic=True)` makes a combo + tier always
return the same reading, which suits tests or pre-baking a library.

## How it fits the invariants

- **Code owns balance (#4).** Magnitudes are emitted only as relative buckets. `fill_budget` rescales them to the tier
  budget, and `clamp.apply` re-derives `harmless`/`category` as for any resolver.
- **The enums are the contract (#5).** Decoding runs under a grammar built from `resolver/contract.py`
  (`forge/grammar.py`), so every draft has these properties by construction:
  - It parses into a `GadgetDraft`: 1–4 stages, each with 1–4 effects.
  - It is legal for its chassis, so `repair()` is a no-op. This covers the SELF-kit rules.
  - It has at least one stage on a trigger the renderer actually fires for that delivery form, so no gadget is dead.
  - Its description mentions only items that are in the build.
- **The models embed the contract fingerprint** and refuse to load against a different contract. A contract change
  means retraining (see below).
- **Never a hard LLM dependency (#6).** It runs fully offline, and `serve.py` still falls back to the deterministic
  resolver if the model errors.
- **Engine-agnostic.** It is pure Python with no Unreal references. The Unreal side needs no changes.

## Model

| | Mechanics (`forge/mechanics.py`) | Writer (`forge/writer.py`) |
|---|---|---|
| What | encoder-decoder trained from scratch | `google/flan-t5-small`, fine-tuned |
| Params / disk (fp32) | 9.5M / 37 MB | 77M / 296 MB |
| Input | delivery form, depth, 4 slot-tagged catalog item tokens + a Model2Vec vector of each item's association cloud | the same build as text (form, depth, slots with their association clouds), plus the mechanics model's stages as forced decoder input |
| Output | stages: trigger, then per effect kind@target + relative amount/duration/radius buckets + count | name + description, written for exactly those stages |

- **Delexicalization.** Item mentions in descriptions are trained as slot tokens (`<i0>`…`<i3>`). Short aliases in
  `forge/aliases.json` map partial names ("the jerrycan") to their slot.
- **Best-of-8 shippability filter** (`forge/shippable.py`). A craft keeps the first candidate with no issues.
  - Hard issues: a nonword, a catalog item that isn't in the build, or a name copied verbatim from the training set.
  - Soft issues: LURE without a lure-capable item, an overused teacher idiom, or a repeated word or phrase.
  - On average a craft tries 1.7 candidates.
- **Depth:** the tier sets it. DUD/COMMON give SHALLOW, UNCOMMON/RARE give MEDIUM, EPIC/LEGENDARY give DEEP.

## Results

The test set is the repo's 28 resolved `pre30` combos (the Sonnet bake), at 3 depths and 3 seeds each. The models
never saw these combos.

| | Sonnet 5 (2nd draft) | Deterministic fallback | **Forge** |
|---|---|---|---|
| Legal without repair | 94% | 100% | **100%** |
| Has a trigger the renderer fires | 88% | 89% | **100%** |
| Effect-kind overlap with Sonnet (Jaccard) | n/a* | 0.27 | **0.52** |
| Same derived category as Sonnet | n/a* | 80% | **91%** |
| Effects per reading, SHALLOW / MEDIUM / DEEP | 1.0 / 2.1 / 3.9 | 1.5 / 1.8 / 1.8 | **1.0 / 2.0 / 3.1** |
| Names an item that isn't in the build | 7% | 0% | **0%** |
| Unshippable after best-of-8 (single sample) | — | — | **1%** (21%) |

\*Sonnet's 2nd draft is prompted to read the build differently from its 1st, so its overlap and category agreement
aren't comparable.

**Blind judging.** Three LLM judges (Claude Opus, GPT, Claude Fable) ranked the systems on 84 held-out items, with
candidates anonymized and shuffled. Scores are out of 5. This was the previous hybrid; the text writer has improved
since and hasn't been re-judged.

| | Composition | Text |
|---|---|---|
| Sonnet 5 | 4.02 | 4.23 |
| Forge (hybrid) | 3.71 | 2.54 |
| Deterministic fallback | 2.03 | 1.67 |

Mechanics are close to Sonnet. Text is the gap; see the limitations below.

**Runtime** (Apple M2, one CPU thread, PyTorch eager):
- Load: ~2 s.
- RAM: ~500 MB resident, ~760 MB peak.
- A craft (best-of-8) takes a median of ~0.5 s and a p90 of ~1.4 s. That is well inside the game's 20 s `/craft`
  timeout.
- Neither model is optimized yet. Benchmarks of same-size models suggest an int8 ONNX export would bring a craft to
  about 100 ms and ~250 MB RAM.

Reproduce with `python -m forge.evaluate`, which compares against the fallback and Sonnet on the same set.

## Training data (`data/forge/`)

- **`combos-round0.json`:** 2,000 combos.
  - They were chosen by the repo's own `resolver.bake.select.select_combos` (seed 20261111), which covers every
    catalog item and the shape/coherence strata.
  - Every `pre30` combo was removed, keeping the gold set held out. A test enforces this.
- **`scaffolds-round0.jsonl`:** three readings per combo (SHALLOW/MEDIUM/DEEP), so 6,000 drafts.
  - Teacher LLMs (OpenAI GPT-family models) wrote them from the exact bake user message, following
    `data/forge/WRITER_GUIDE.md`.
  - Each shard was validated with `forge.validate_data`: the `ScaffoldSet` schema, `repair()` as a no-op, `clamp.apply`
    at the depth's tier, and a firing trigger.
  - No bake spend was involved.

## Retraining: catalog waves and contract changes

```bash
python -m forge.make_combos --round round1 --seed <new seed>   # new combos -> data/forge/combos-round1.json + prompts
# a teacher answers runs/forge-teacher/round1/prompts_*.jsonl with one ScaffoldSet line per combo (WRITER_GUIDE.md)
python -m forge.validate_data runs/forge-teacher/round1/shard_00.jsonl --final   # per shard
cat runs/forge-teacher/round1/shard_*.jsonl > data/forge/scaffolds-round1.jsonl
python -m forge.train_mechanics --out runs/forge-mechanics      # ~13 min on an M2 (MPS); defaults = shipped recipe
python -m forge.writer train --out runs/forge-writer            # ~1 h on an M2; defaults = shipped recipe
python -m forge.evaluate hybrid:runs/forge-mechanics+runs/forge-writer
# ship: copy into models/forge/{mechanics,writer}, tar czf forge-models-<tag>.tar.gz -C models forge,
# attach to a release, update URL + SHA256 in forge/fetch.py
```

Training reads every `combos-*.json` / `scaffolds-*.jsonl` pair in `data/forge/`, so rounds accumulate.

## Known limitations

- **Text quality is the main gap**, at about 2.5 vs 4.2 for Sonnet with the judges.
  - The teacher's habits carry over: phrases like "unfriendly greeting", "red invitation" and "the customer" appear
    in roughly 12% of single samples. Sonnet's rate is 0%.
  - Idiom-bearing examples are down-weighted in training, and the shippability filter avoids them when it can.
  - A Sonnet-register rewrite of the training descriptions is the obvious next lever.
- **Variety per combo is narrow.** A 2-item RARE craft tends to land on similar names and the same two effects.
  Higher tiers and more items vary more.
- **`logic` and the effect `note`s are empty.** Players don't see them, and leaving them out halves output length.

## Notes from wiring this up (outside Forge)

- **Dead gadgets in the current pipeline.** About 1 in 9 Sonnet bake readings and deterministic-fallback gadgets
  have no stage on a trigger the renderer fires for their delivery form. The evaluation above counts them, and Forge's
  grammar rules them out. It might be worth a check in `clamp`/`repair` for the other resolvers.
- **macOS.** The game builds and runs unchanged on macOS (UE 5.8.4, Xcode 27.2, Apple Silicon).
  - The only warning is `FCoreDelegates::OnPostEngineInit` in `NotAWeapon.cpp`. It is deprecated in 5.8 (use
    `GetOnPostEngineInit()`) and will stop compiling in the next engine version.
  - The committed `Blockout.umap` has no `NAWCraftSpot`; the craft-spot placement was only in an uncommitted local save.
  - `serve.py` stalled ~30 s at startup on macOS: `HTTPServer.server_bind` reverse-resolves the host. This branch
    fixes that.
