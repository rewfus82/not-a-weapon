# Game-Loop Prototype (In-Game On-Demand Generation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The GAME_IDENTITY §10 loop functions end-to-end in a UE 5.x blockout zone — move, scavenge junk, craft via the live resolver sidecar (deterministic fallback when keyless/refused), the weapon visibly does what its JSON says, extract (roll banked to `extracted.jsonl`) or die (roll lost).

**Architecture:** Two processes, one contract. The Python resolver (`resolver/serve.py`) grows a `GET /api/contract` fingerprint endpoint and a `POST /craft` endpoint (one craft = one resolve). The Unreal game (`game/`, C++ core + Blueprint glue) runs as a listen host whose server calls the sidecar over local HTTP; a hand-written C++ contract mirror plus a startup fingerprint check guards drift; a data-driven GadgetInterpreter executes contract-conforming gadget JSON at blockout grade. The fallback PLACED-chassis bug fix lands first because on-demand crafting puts the fallback in the live path.

**Tech Stack:** Python 3 stdlib (`http.server`, no new deps), pytest; UE 5.x C++ (`HTTP`, `Json` modules), PowerShell dev script.

**Spec:** `docs/superpowers/specs/2026-07-20-game-loop-prototype-design.md` (approved).

## Global Constraints

Copied verbatim from the spec and standing rules. Every task's requirements implicitly include this section.

- **Invariant framing (explicit):** live-LLM-in-the-hot-path is a *dev-mode testing convenience*, not a change of shipping architecture. GAME_IDENTITY §6 stands. Nothing in this design may create a structural dependency on the live path — the deterministic fallback keeps the game fully functional with no API key.
- **The enums are the capability contract — never widen them**; never widen the tag taxonomy in `resolver/interactions.py`. No contract changes.
- Code owns every number; `harmless`/`category` always re-derived; engine-agnostic `resolver/` — zero Unreal references in Python.
- **NEVER introspect why a call was refused. Log rates only. No stop reasons, exception text, or failure classification in records or console output.** The only trace of a failed live call is `source: fallback`.
- API key: presence check only, never print. Windows live runs need `PYTHONUTF8=1`.
- **No live API calls in tests, ever.** The live path gets a hand-run smoke script only. **Pilot/bake spend stays HELD:** never run `python -m resolver.bake run` or `dedup`. Live calls only during the user's play sessions (no schedules, no batches, no CI).
- One craft = one resolve — no best-of-N in the hot path.
- The game **server** (listen host, `HasAuthority` from line one) owns all resolver traffic; clients never call the sidecar. All gameplay mutations behind `HasAuthority`.
- Malformed JSON reaching the game is treated as sidecar-down (reject craft, release player, log), never a crash. Sidecar down: craft neither consumes items nor locks the player.
- Client-side craft timeout ~20s (covers the full retry ladder), after which the craft resolves as sidecar-down.
- Contract fingerprint mismatch at startup → loud on-screen error, refuse to craft. Never silent drift. Mirror constant: `a33fabbb515c220926ed774fed2bbe945b243165392b434a34f3093d22ce31cf`.
- Repo: branch `main` only; **no remote — do not push, do not add one**. `git add` only explicitly named files; commits end `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- `game/` uses a proper UE `.gitignore` (exclude `Binaries/`, `Intermediate/`, `DerivedDataCache/`, `Saved/`). Never commit those.
- TDD applies to the Python brain only. Unreal verification is a written manual checklist per task — no UE test framework, no test-driving feel.

## File Structure

**Phase 1 — Python (Tasks 1–3, TDD):**
- Modify `resolver/fallback.py` — PLACED-chassis stage fix (`_stages_for`).
- Modify `resolver/serve.py` — `GET /api/contract`, `build_from_items()`, `craft()`, `POST /craft`.
- Modify `tests/test_fallback.py`, `tests/test_serve.py` — pin + endpoint tests.

**Phase 2 — Unreal (Tasks 4–10, manual checklists):**
- Create `game/` UE project: `NotAWeapon.uproject`, `Source/` (module, targets), `Config/`, `.gitignore`, `run-sidecar.ps1`, `NAWGameMode`, `NAWCharacter` (first-person pawn; all input binds on the character — no custom PlayerController) (Task 4).
- `game/Source/NotAWeapon/Contract.h/.cpp` — enum mirror + fingerprint + JSON parse (Task 5).
- `game/Source/NotAWeapon/NAWResolverSubsystem.h/.cpp` — HTTP client + fingerprint check (Task 6).
- `game/Source/NotAWeapon/NAWHealthComponent.h/.cpp`, `NAWEffectExecutor.h/.cpp`, `NAWGadgetWeapon.h/.cpp`, `NAWGadgetProjectile.h/.cpp`, `NAWGadgetPlaced.h/.cpp`, `NAWTargetDummy.h/.cpp` — the gadget interpreter (Task 7).
- `game/Source/NotAWeapon/NAWInventoryComponent.h/.cpp`, `NAWJunkPickup.h/.cpp` — pickups + inventory (Task 8).
- `game/Source/NotAWeapon/NAWCraftSpot.h/.cpp` + craft input glue in `NAWCharacter` — craft interaction (Task 9).
- `game/Source/NotAWeapon/NAWExtractVolume.h/.cpp` + health/death + restart wiring in `NAWCharacter` — extract/die loop (Task 10).

Execute tasks strictly in order. Task 1 must land before anything else: the fallback is in the live path from the first in-game craft.

---

### Task 1: Fallback PLACED-chassis fix + pin test

The bug (confirmed live): `_stages_for` treats every delivery-less chassis as a thrown container and emits ON_IMPACT, but a PLACED-base-use chassis (cooler of raw steaks) must fire ON_TRIGGER per the contract — an ON_IMPACT-only PLACED gadget can never fire. Mirror the discrimination `resolver/solo.py` already does.

**Files:**
- Modify: `resolver/fallback.py:51-63` (`_stages_for`)
- Test: `tests/test_fallback.py`

**Interfaces:**
- Consumes: `resolver.contract.{Delivery, Stage, Trigger}`, `Item.base_use.delivery` (a `BaseUse` has `.delivery`, `.armed`).
- Produces: unchanged signature `_stages_for(build: Build, effects: list[Effect]) -> list[Stage]`; PLACED-base-use chassis now yields `[Stage(trigger=Trigger.ON_TRIGGER, ...)]`. Task 3's `/craft` and the game rely on this shape.

- [ ] **Step 1: Write the failing pin test**

Append to `tests/test_fallback.py` (imports `CATALOG`, `Build`, `Tier`, `Trigger` already present at top of file):

```python
def test_placed_chassis_composes_an_on_trigger_stage():
    # a PLACED base-use chassis (bait on the ground) fires ON_TRIGGER per the
    # contract — ON_IMPACT would compose a gadget that can never fire
    draft = fallback.resolve(Build(delivery_item=CATALOG["cooler of raw steaks"]), Tier.COMMON)
    assert [s.trigger for s in draft.stages] == [Trigger.ON_TRIGGER]
    assert all(s.effects for s in draft.stages)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_fallback.py::test_placed_chassis_composes_an_on_trigger_stage -q`
Expected: FAIL — `assert [<Trigger.ON_IMPACT: 'ON_IMPACT'>] == [<Trigger.ON_TRIGGER: 'ON_TRIGGER'>]`

- [ ] **Step 3: Fix `_stages_for`**

In `resolver/fallback.py`, replace the delivery-less branch of `_stages_for` (and extend its docstring):

```python
def _stages_for(build: Build, effects: list[Effect]) -> list[Stage]:
    """Mechanism chassis hit (ON_HIT); a substance chassis follows its base
    use — thrown containers burst (ON_IMPACT; armed payloads burst inert and
    fire on ignition, ON_TRIGGER), placed baits fire on proximity
    (ON_TRIGGER); a self-kit chassis is used on yourself (ON_USE, everything
    lands on the wielder)."""
    chassis = build.delivery_item
    if chassis.delivery is Delivery.SELF:
        for e in effects:
            e.target = Target.SELF
        return [Stage(trigger=Trigger.ON_USE, effects=effects, note="self-kit")]
    if chassis.delivery is None and chassis.base_use is not None:
        if chassis.base_use.delivery is Delivery.PLACED:
            return [Stage(trigger=Trigger.ON_TRIGGER, effects=effects, note="placed")]
        return substance_stages(effects, chassis.base_use.armed)
    return [Stage(trigger=Trigger.ON_HIT, effects=effects, note="composed")]
```

`substance_stages` is untouched — THROWN chassis (bucket of wet cement, jerrycan) keep their exact current shapes.

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `python -m pytest -q`
Expected: 349 passed (348 existing + the new pin test). The budget tests (`test_every_build_fills_the_tier_budget_exactly`, `test_composer_fills_the_weighted_budget_exactly_at_every_tier`) must stay green — the fix changes stage shape, never amounts.

- [ ] **Step 5: Commit**

```bash
git add resolver/fallback.py tests/test_fallback.py
git commit -m "fix: PLACED-base-use chassis composes ON_TRIGGER, not a thrown burst

A delivery-less chassis now keys its stage shape off base_use.delivery,
mirroring solo.py. Pins the steaks-as-chassis case.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `GET /api/contract` fingerprint endpoint

The game's startup drift guard needs the sidecar to report which enum vocabulary it speaks.

**Files:**
- Modify: `resolver/serve.py` (import + `do_GET`)
- Test: `tests/test_serve.py`

**Interfaces:**
- Consumes: `resolver.bake.schema.contract_fingerprint() -> str` (hashes ONLY the four enum vocabularies: delivery/effect/trigger/target).
- Produces: `GET /api/contract` → `200 {"fingerprint": "<64-hex>"}`. Task 6's C++ `CheckContract()` compares this to its compiled-in constant.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_serve.py`. Also add the server-thread helper here — Task 3's HTTP tests reuse it. Ensure these imports exist at the top of the file (add any that are missing): `import json`, `import threading`, `import urllib.request`, `from resolver import fallback`, `from resolver.bake.schema import contract_fingerprint`.

```python
def _serve_on_free_port():
    """A real PlayServer on an OS-assigned port, fallback resolver, daemon thread."""
    server = serve.PlayServer(("127.0.0.1", 0), serve.PlayHandler,
                              fallback.resolve, "fallback (free)")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def test_contract_endpoint_serves_the_enum_fingerprint():
    server, base = _serve_on_free_port()
    try:
        with urllib.request.urlopen(base + "/api/contract") as resp:
            payload = json.loads(resp.read())
        assert payload == {"fingerprint": contract_fingerprint()}
    finally:
        server.shutdown()
        server.server_close()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_serve.py::test_contract_endpoint_serves_the_enum_fingerprint -q`
Expected: FAIL — the 404 branch returns `{"error": "not found"}`, so the equality assert fails.

- [ ] **Step 3: Implement the endpoint**

In `resolver/serve.py`, add to the imports block (after `from resolver.clamp import ...`):

```python
from resolver.bake.schema import contract_fingerprint
```

In `PlayHandler.do_GET`, add a branch before the 404 fallthrough:

```python
        elif self.path == "/api/contract":
            self._json({"fingerprint": contract_fingerprint()})
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_serve.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add resolver/serve.py tests/test_serve.py
git commit -m "feat: GET /api/contract serves the enum fingerprint for the game's drift guard

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: `POST /craft` endpoint

One craft = one resolve. The game sends a flat item-name list; the endpoint maps it positionally onto the existing slot machinery, resolves once (live if the server has a key, deterministic fallback otherwise — and fallback on any live failure), clamps/re-derives, and returns the gadget JSON with an honest `source`.

**Files:**
- Modify: `resolver/serve.py` (two new pure helpers + `do_POST`)
- Test: `tests/test_serve.py`

**Interfaces:**
- Consumes: `build_from_request(sel: dict) -> Build`, `_resolve_once(resolver_fn, build, tier) -> (source, ResolvedGadget)`, `gadget_to_dict(resolved, source) -> dict`, `Tier` (str enum: DUD/COMMON/UNCOMMON/RARE/EPIC/LEGENDARY), `fallback_resolve`, `_serve_on_free_port` (Task 2).
- Produces: `build_from_items(names: list[str]) -> Build`; `craft(resolver_fn, payload: dict) -> dict`; `POST /craft` with request `{"items": ["<name>", ...], "tier_target": "<TIER>", "seed": <optional, accepted-and-unused>}` → `200` gadget dict (keys: `source, name, description, logic, tier, category, harmless, delivery, color, stages`; stage keys `trigger, note, effects`; effect keys `kind, target, amount, duration, radius, count, note`) or `400 {"error": "<message>"}`. **Positional mapping: `items[0]` chairs the delivery slot; `items[1..3]` fill damage/utility/modifier in order (1–4 items).** `source` is `"llm"` only when a live resolver actually served the craft; `"fallback"` when the server is keyless/`--fallback` or the live call degraded. Task 5's C++ parser and Task 9's craft flow depend on exactly these keys and this mapping.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_serve.py`:

```python
def test_build_from_items_maps_positionally():
    build = serve.build_from_items(["bucket of wet cement", "jerrycan"])
    assert build.delivery_item.name == "bucket of wet cement"
    assert build.damage_item.name == "jerrycan"
    assert build.utility_item is None and build.modifier_item is None


def test_build_from_items_rejects_bad_requests():
    with pytest.raises(ValueError):
        serve.build_from_items([])
    with pytest.raises(ValueError):
        serve.build_from_items(["a", "b", "c", "d", "e"])
    with pytest.raises(ValueError):
        serve.build_from_items(["definitely not junk"])


def test_craft_resolves_once_and_reports_an_honest_source():
    payload = {"items": ["cooler of raw steaks"], "tier_target": "COMMON"}
    gadget = serve.craft(fallback.resolve, payload)
    # a keyless server's resolver_fn IS the fallback: never claim a live source
    assert gadget["source"] == "fallback"
    assert gadget["tier"] == "COMMON"
    # the wire contract the C++ mirror parses — pin the exact key sets
    assert set(gadget) == {"source", "name", "description", "logic", "tier",
                           "category", "harmless", "delivery", "color", "stages"}
    for stage in gadget["stages"]:
        assert set(stage) == {"trigger", "note", "effects"}
        for effect in stage["effects"]:
            assert set(effect) == {"kind", "target", "amount", "duration",
                                   "radius", "count", "note"}
    # Task 1's fix, observed on the wire: a PLACED chassis fires ON_TRIGGER
    assert gadget["delivery"] == "PLACED"
    assert [s["trigger"] for s in gadget["stages"]] == ["ON_TRIGGER"]


def test_craft_accepts_and_ignores_a_seed():
    payload = {"items": ["bucket of wet cement"], "tier_target": "COMMON", "seed": 7}
    assert serve.craft(fallback.resolve, payload)["source"] == "fallback"


def test_craft_endpoint_end_to_end_fallback():
    server, base = _serve_on_free_port()
    try:
        body = json.dumps({"items": ["bucket of wet cement", "jerrycan"],
                           "tier_target": "RARE"}).encode("utf-8")
        req = urllib.request.Request(base + "/craft", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            gadget = json.loads(resp.read())
        assert gadget["source"] == "fallback"
        assert gadget["tier"] == "RARE"
        assert gadget["stages"] and all(s["effects"] for s in gadget["stages"])
    finally:
        server.shutdown()
        server.server_close()


def test_craft_endpoint_rejects_unknown_items_with_400():
    server, base = _serve_on_free_port()
    try:
        body = json.dumps({"items": ["not junk"], "tier_target": "COMMON"}).encode("utf-8")
        req = urllib.request.Request(base + "/craft", data=body,
                                     headers={"Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as excinfo:
            urllib.request.urlopen(req)
        assert excinfo.value.code == 400
        assert "error" in json.loads(excinfo.value.read())
    finally:
        server.shutdown()
        server.server_close()
```

Add `import urllib.error` and `import pytest` to the top of the file if missing (the new tests use `pytest.raises`).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_serve.py -q`
Expected: the six new tests FAIL — `AttributeError: module 'resolver.serve' has no attribute 'build_from_items'` (and 404s on the endpoint tests).

- [ ] **Step 3: Implement `build_from_items`, `craft`, and the route**

In `resolver/serve.py`, add after `build_from_request`:

```python
_SLOT_ORDER = ("delivery", "damage", "utility", "modifier")


def build_from_items(names: list[str]) -> Build:
    """Positional craft: names[0] chairs the delivery slot, the rest fill
    damage/utility/modifier in order. Validation (unknown item, ineligible
    chassis) is build_from_request's."""
    if not 1 <= len(names) <= len(_SLOT_ORDER):
        raise ValueError(f"craft takes 1-{len(_SLOT_ORDER)} items, got {len(names)}")
    return build_from_request(dict(zip(_SLOT_ORDER, names)))


def craft(resolver_fn, payload: dict) -> dict:
    """One craft = one resolve — never best-of-N in the hot path. `seed` is
    accepted and unused (reserved; the deterministic path needs none and the
    live path's variance is the model's)."""
    names = payload.get("items")
    if not isinstance(names, list) or not names:
        raise ValueError("items must be a non-empty list of item names")
    build = build_from_items([str(n) for n in names])
    tier = Tier(payload.get("tier_target", "COMMON"))
    source, resolved = _resolve_once(resolver_fn, build, tier)
    if resolver_fn is fallback_resolve:
        source = "fallback"  # keyless/--fallback mode: never claim a live source
    return gadget_to_dict(resolved, source)
```

Replace `PlayHandler.do_POST` with a routed version (same error shapes as today):

```python
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
            if self.path == "/api/roll":
                build = build_from_request(payload.get("slots", {}))
                tier = Tier(payload.get("tier", "COMMON"))
                n = min(4, max(1, int(payload.get("rolls", 1))))
                self._json({"results": roll(self.server.resolver_fn, build, tier, n)})
            elif self.path == "/craft":
                self._json(craft(self.server.resolver_fn, payload))
            else:
                self._json({"error": "not found"}, 404)
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)
        except Exception as exc:  # noqa: BLE001 - surface any server error as JSON
            self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)
```

(A malformed JSON body raises `json.JSONDecodeError`, a `ValueError` subclass → 400. Refusal/exception details from live calls never reach these handlers — `_resolve_once` absorbs them silently, per the standing rule.)

- [ ] **Step 4: Run the full suite to verify everything passes**

Run: `python -m pytest -q`
Expected: all pass (Task 1 count + 7 new serve tests), no network beyond loopback, no API key needed.

- [ ] **Step 5: Hand-run smoke check (fallback mode, free)**

```powershell
$env:PYTHONUTF8 = "1"; python -m resolver.serve --fallback --port 8000
```

In a second shell:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/craft -ContentType application/json -Body '{"items":["cooler of raw steaks"],"tier_target":"COMMON"}'
```

Expected: a gadget with `delivery: PLACED`, one `ON_TRIGGER` stage, `source: fallback`. Stop the server. (Do NOT smoke the live path here — live calls happen only in the user's play sessions.)

- [ ] **Step 6: Commit**

```bash
git add resolver/serve.py tests/test_serve.py
git commit -m "feat: POST /craft - one-shot resolve for in-game on-demand crafting

Positional items->slots mapping, honest source tagging in fallback mode,
same clamp/re-derive pipeline as /api/roll.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

### Task 4: UE project bootstrap in `game/`

Hand-authored minimal UE 5.x C++ project — every file below is text and diffable. **Deliberate substitution from the spec:** the spec says "first-person template base," but the template wizard is interactive and drags in binary assets; a hand-authored project with legacy input forced via `DefaultInput.ini` gives the same first-person pawn with everything agent-authorable. (Flagged to the user at plan handoff.) All input actions the whole prototype needs (Fire, Interact, ToggleSlot1–6) are declared up front so later tasks only bind, never edit config.

**Files:**
- Create: `game/NotAWeapon.uproject`, `game/.gitignore`, `game/run-sidecar.ps1`
- Create: `game/Source/NotAWeapon.Target.cs`, `game/Source/NotAWeaponEditor.Target.cs`
- Create: `game/Source/NotAWeapon/NotAWeapon.Build.cs`, `NotAWeapon.h`, `NotAWeapon.cpp`
- Create: `game/Source/NotAWeapon/NAWGameMode.h/.cpp`, `NAWCharacter.h/.cpp`
- Create: `game/Config/DefaultEngine.ini`, `DefaultGame.ini`, `DefaultInput.ini`
- Manual (editor): `game/Content/Maps/Blockout.umap`

**Interfaces:**
- Produces: `LogNAW` log category (all later tasks log to it); `ANAWGameMode::RestartRun()` (Task 10 calls it); `ANAWCharacter` with a `Camera` member (Task 7 attaches the weapon to it) and `SetupPlayerInputComponent` (Tasks 7–9 add bindings); input names `MoveForward/MoveRight/Turn/LookUp/Jump/Fire/Interact/ToggleSlot1..6`.

- [ ] **Step 1: Discover the installed engine version**

```powershell
$ue = Get-ChildItem "C:\Program Files\Epic Games" -Directory -Filter "UE_5*" | Sort-Object Name | Select-Object -Last 1
$ue.Name
```

Expected: e.g. `UE_5.4`. Use the numeric part (e.g. `5.4`) as `EngineAssociation` below, and `$ue.FullName` in every build/editor command in Tasks 4–10. If nothing is found, STOP — report that UE 5.x is not installed where expected and ask the user where it lives.

- [ ] **Step 2: Write the project, target, and build files**

`game/NotAWeapon.uproject` (replace `5.4` with the discovered version):

```json
{
  "FileVersion": 3,
  "EngineAssociation": "5.4",
  "Category": "Game",
  "Description": "This Is Not A Weapon - blockout prototype",
  "Modules": [
    {
      "Name": "NotAWeapon",
      "Type": "Runtime",
      "LoadingPhase": "Default"
    }
  ]
}
```

`game/Source/NotAWeapon.Target.cs`:

```csharp
using UnrealBuildTool;

public class NotAWeaponTarget : TargetRules
{
    public NotAWeaponTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("NotAWeapon");
    }
}
```

`game/Source/NotAWeaponEditor.Target.cs`:

```csharp
using UnrealBuildTool;

public class NotAWeaponEditorTarget : TargetRules
{
    public NotAWeaponEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("NotAWeapon");
    }
}
```

`game/Source/NotAWeapon/NotAWeapon.Build.cs`:

```csharp
using UnrealBuildTool;

public class NotAWeapon : ModuleRules
{
    public NotAWeapon(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[]
            { "Core", "CoreUObject", "Engine", "InputCore", "HTTP", "Json" });
    }
}
```

- [ ] **Step 3: Write the module, game mode, and character sources**

`game/Source/NotAWeapon/NotAWeapon.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

DECLARE_LOG_CATEGORY_EXTERN(LogNAW, Log, All);

class FNotAWeaponModule : public FDefaultGameModuleImpl
{
public:
    virtual void StartupModule() override;
};
```

`game/Source/NotAWeapon/NotAWeapon.cpp`:

```cpp
#include "NotAWeapon.h"

DEFINE_LOG_CATEGORY(LogNAW);

void FNotAWeaponModule::StartupModule()
{
}

IMPLEMENT_PRIMARY_GAME_MODULE(FNotAWeaponModule, NotAWeapon, "NotAWeapon");
```

`game/Source/NotAWeapon/NAWGameMode.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "NAWGameMode.generated.h"

UCLASS()
class NOTAWEAPON_API ANAWGameMode : public AGameModeBase
{
    GENERATED_BODY()

public:
    ANAWGameMode();

    // Full run reset by reloading the level; extracted.jsonl persists on disk.
    void RestartRun();
};
```

`game/Source/NotAWeapon/NAWGameMode.cpp`:

```cpp
#include "NAWGameMode.h"
#include "NAWCharacter.h"
#include "Kismet/GameplayStatics.h"

ANAWGameMode::ANAWGameMode()
{
    DefaultPawnClass = ANAWCharacter::StaticClass();
}

void ANAWGameMode::RestartRun()
{
    UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)));
}
```

`game/Source/NotAWeapon/NAWCharacter.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "NAWCharacter.generated.h"

UCLASS()
class NOTAWEAPON_API ANAWCharacter : public ACharacter
{
    GENERATED_BODY()

public:
    ANAWCharacter();

protected:
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

    UPROPERTY(VisibleAnywhere)
    class UCameraComponent* Camera;

private:
    void MoveForward(float Value);
    void MoveRight(float Value);
};
```

`game/Source/NotAWeapon/NAWCharacter.cpp`:

```cpp
#include "NAWCharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"

ANAWCharacter::ANAWCharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
    Camera->SetupAttachment(GetCapsuleComponent());
    Camera->SetRelativeLocation(FVector(0.f, 0.f, 64.f));
    Camera->bUsePawnControlRotation = true;
}

void ANAWCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    PlayerInputComponent->BindAxis("MoveForward", this, &ANAWCharacter::MoveForward);
    PlayerInputComponent->BindAxis("MoveRight", this, &ANAWCharacter::MoveRight);
    PlayerInputComponent->BindAxis("Turn", this, &APawn::AddControllerYawInput);
    PlayerInputComponent->BindAxis("LookUp", this, &APawn::AddControllerPitchInput);
    PlayerInputComponent->BindAction("Jump", IE_Pressed, this, &ACharacter::Jump);
    PlayerInputComponent->BindAction("Jump", IE_Released, this, &ACharacter::StopJumping);
}

void ANAWCharacter::MoveForward(float Value)
{
    if (Value != 0.f)
    {
        AddMovementInput(GetActorForwardVector(), Value);
    }
}

void ANAWCharacter::MoveRight(float Value)
{
    if (Value != 0.f)
    {
        AddMovementInput(GetActorRightVector(), Value);
    }
}
```

- [ ] **Step 4: Write the configs, .gitignore, and sidecar script**

`game/Config/DefaultEngine.ini`:

```ini
[/Script/EngineSettings.GameMapsSettings]
GameDefaultMap=/Game/Maps/Blockout.Blockout
EditorStartupMap=/Game/Maps/Blockout.Blockout
GlobalDefaultGameMode=/Script/NotAWeapon.NAWGameMode
```

`game/Config/DefaultGame.ini`:

```ini
[/Script/EngineSettings.GeneralProjectSettings]
ProjectName=This Is Not A Weapon
```

`game/Config/DefaultInput.ini` — forces **legacy input** so all bindings live in this text file, no Enhanced Input binary assets:

```ini
[/Script/Engine.InputSettings]
DefaultPlayerInputClass=/Script/Engine.PlayerInput
DefaultInputComponentClass=/Script/Engine.InputComponent
+AxisMappings=(AxisName="MoveForward",Scale=1.000000,Key=W)
+AxisMappings=(AxisName="MoveForward",Scale=-1.000000,Key=S)
+AxisMappings=(AxisName="MoveRight",Scale=1.000000,Key=D)
+AxisMappings=(AxisName="MoveRight",Scale=-1.000000,Key=A)
+AxisMappings=(AxisName="Turn",Scale=1.000000,Key=MouseX)
+AxisMappings=(AxisName="LookUp",Scale=-1.000000,Key=MouseY)
+ActionMappings=(ActionName="Jump",Key=SpaceBar)
+ActionMappings=(ActionName="Fire",Key=LeftMouseButton)
+ActionMappings=(ActionName="Interact",Key=E)
+ActionMappings=(ActionName="ToggleSlot1",Key=One)
+ActionMappings=(ActionName="ToggleSlot2",Key=Two)
+ActionMappings=(ActionName="ToggleSlot3",Key=Three)
+ActionMappings=(ActionName="ToggleSlot4",Key=Four)
+ActionMappings=(ActionName="ToggleSlot5",Key=Five)
+ActionMappings=(ActionName="ToggleSlot6",Key=Six)
```

`game/.gitignore`:

```gitignore
Binaries/
Intermediate/
DerivedDataCache/
Saved/
.vs/
*.sln
*.suo
extracted.jsonl
```

`game/run-sidecar.ps1`:

```powershell
$env:PYTHONUTF8 = "1"
Set-Location (Join-Path $PSScriptRoot "..")
python -m resolver.serve @args
```

- [ ] **Step 5: Build**

```powershell
$ue = Get-ChildItem "C:\Program Files\Epic Games" -Directory -Filter "UE_5*" | Sort-Object Name | Select-Object -Last 1
& "$($ue.FullName)\Engine\Build\BatchFiles\Build.bat" NotAWeaponEditor Win64 Development -project="C:\Users\rewfu\repos\not-a-weapon\game\NotAWeapon.uproject" -waitmutex
```

Expected: output ends with `Result: Succeeded` (older UBT prints `BUILD SUCCESSFUL`). First build takes several minutes. Any compile error: fix it before proceeding.

- [ ] **Step 6: Manual checklist (editor)**

Launch the editor:

```powershell
& "$($ue.FullName)\Engine\Binaries\Win64\UnrealEditor.exe" "C:\Users\rewfu\repos\not-a-weapon\game\NotAWeapon.uproject"
```

- [ ] Editor opens (it will warn the startup map is missing — expected, we create it now).
- [ ] File → New Level → **Basic**. Save As → folder `/Game/Maps`, name `Blockout`. (This creates `game/Content/Maps/Blockout.umap` — the one intentional binary asset.)
- [ ] Restart the editor; it opens straight into Blockout.
- [ ] PIE (Play In Editor): WASD walks, mouse looks, Space jumps. You possess an `ANAWCharacter` (check the World Outliner during PIE).
- [ ] Quit editor. `git status --porcelain game/` shows ONLY: the files written in Steps 2–4 plus `Content/Maps/Blockout.umap`. If `Binaries/`, `Intermediate/`, `Saved/`, or `DerivedDataCache/` appear, the `.gitignore` is wrong — fix before committing.

- [ ] **Step 7: Commit**

```bash
git add game/NotAWeapon.uproject game/.gitignore game/run-sidecar.ps1 game/Config/DefaultEngine.ini game/Config/DefaultGame.ini game/Config/DefaultInput.ini game/Source/NotAWeapon.Target.cs game/Source/NotAWeaponEditor.Target.cs game/Source/NotAWeapon/NotAWeapon.Build.cs game/Source/NotAWeapon/NotAWeapon.h game/Source/NotAWeapon/NotAWeapon.cpp game/Source/NotAWeapon/NAWGameMode.h game/Source/NotAWeapon/NAWGameMode.cpp game/Source/NotAWeapon/NAWCharacter.h game/Source/NotAWeapon/NAWCharacter.cpp "game/Content/Maps/Blockout.umap"
git commit -m "feat(game): hand-authored UE project bootstrap - module, first-person pawn, legacy input

Text-diffable substitute for the first-person template; all prototype
input actions declared up front in DefaultInput.ini.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: C++ contract mirror (`Contract.h/.cpp`)

The ONE file pair that moves in lockstep with `resolver/contract.py`. Enum member spellings must match the Python tokens EXACTLY — parsing uses reflection on these names, and Task 6's fingerprint check only guards the *Python* side's vocabulary; this file guards itself via the self-test.

**Files:**
- Create: `game/Source/NotAWeapon/Contract.h`, `Contract.cpp`
- Modify: `game/Source/NotAWeapon/NotAWeapon.cpp` (register self-test)

**Interfaces:**
- Consumes: the wire schema pinned by Task 3 (`gadget_to_dict` keys), `LogNAW`.
- Produces: `ENAWDelivery/ENAWEffectKind/ENAWTrigger/ENAWTarget/ENAWCategory/ENAWTier`; `NAW_CONTRACT_FINGERPRINT`; `FNAWEffect`, `FNAWStage`, `FNAWGadget` with `static bool ParseJson(const FString& Body, FNAWGadget& Out)`, `bool HasTrigger(ENAWTrigger) const`, `TArray<FNAWStage> StagesFor(ENAWTrigger) const`, and `RawJson` (verbatim body — Task 10 banks it). Tasks 6, 7, 10 all consume these.

- [ ] **Step 1: Write `Contract.h`**

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Contract.generated.h"

// Mirror of resolver/contract.py. Member spellings are the contract tokens -
// parsing resolves them by name via StaticEnum. NEVER widen; move in lockstep
// with the Python file and update the fingerprint below when it changes.
inline const TCHAR* NAW_CONTRACT_FINGERPRINT =
    TEXT("a33fabbb515c220926ed774fed2bbe945b243165392b434a34f3093d22ce31cf");

UENUM()
enum class ENAWDelivery : uint8
{
    HITSCAN, PROJECTILE, LOBBED, BEAM, THROWN, SPRAY, PLACED,
    SWING, THRUST, SLAM, WHIP, GUARD, SELF, DASH
};

UENUM()
enum class ENAWEffectKind : uint8
{
    DAMAGE, BURN, EXPLODE, PIERCE, CHAIN, KNOCKBACK, LAUNCH, STAGGER,
    SNARE, SLOW, FREEZE, HEAL, SHIELD, SPEED, SUMMON, LURE
};

UENUM()
enum class ENAWTrigger : uint8
{
    ON_USE, ON_HIT, ON_IMPACT, ON_TRIGGER, ON_EXPIRE, ON_KILL, ON_BLOCK
};

UENUM()
enum class ENAWTarget : uint8
{
    SELF, STRUCK
};

UENUM()
enum class ENAWCategory : uint8
{
    WEAPON, CONTROL, SUPPORT, MOBILITY, UTILITY, TRINKET, DUD
};

UENUM()
enum class ENAWTier : uint8
{
    DUD, COMMON, UNCOMMON, RARE, EPIC, LEGENDARY
};

USTRUCT()
struct FNAWEffect
{
    GENERATED_BODY()

    ENAWEffectKind Kind = ENAWEffectKind::DAMAGE;
    ENAWTarget Target = ENAWTarget::STRUCK;
    float Amount = 0.f;
    float Duration = 0.f;
    float Radius = 0.f;
    int32 Count = 0;
    FString Note;
};

USTRUCT()
struct FNAWStage
{
    GENERATED_BODY()

    ENAWTrigger Trigger = ENAWTrigger::ON_USE;
    TArray<FNAWEffect> Effects;
    FString Note;
};

USTRUCT()
struct FNAWGadget
{
    GENERATED_BODY()

    FString Source;
    FString Name;
    FString Description;
    FString Logic;
    ENAWTier Tier = ENAWTier::COMMON;
    ENAWCategory Category = ENAWCategory::WEAPON;
    bool bHarmless = false;
    ENAWDelivery Delivery = ENAWDelivery::THROWN;
    FString Color;
    TArray<FNAWStage> Stages;
    FString RawJson;  // verbatim response body - extraction banks exactly this

    // Strict parse: unknown enum token, missing required field, empty stages,
    // or a stage with no effects all fail. Malformed = sidecar-down upstream.
    static bool ParseJson(const FString& Body, FNAWGadget& Out);
    bool HasTrigger(ENAWTrigger Trigger) const;
    TArray<FNAWStage> StagesFor(ENAWTrigger Trigger) const;
};

#if !UE_BUILD_SHIPPING
// Registered on OnPostEngineInit (Task 5); logs OK or Error to LogNAW.
void NAWContractSelfTest();
#endif
```

- [ ] **Step 2: Write `Contract.cpp`**

```cpp
#include "Contract.h"
#include "NotAWeapon.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
template <typename TEnum>
bool ParseEnumToken(const TSharedPtr<FJsonObject>& Obj, const FString& Field, TEnum& Out)
{
    FString Token;
    if (!Obj->TryGetStringField(Field, Token))
    {
        return false;
    }
    const int64 Value = StaticEnum<TEnum>()->GetValueByNameString(Token);
    if (Value == INDEX_NONE)
    {
        return false;  // unknown token = outside the contract = malformed
    }
    Out = static_cast<TEnum>(Value);
    return true;
}

float NumberField(const TSharedPtr<FJsonObject>& Obj, const FString& Field)
{
    double Value = 0.0;
    Obj->TryGetNumberField(Field, Value);
    return static_cast<float>(Value);
}
}  // namespace

bool FNAWGadget::ParseJson(const FString& Body, FNAWGadget& Out)
{
    TSharedPtr<FJsonObject> Root;
    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Body);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        return false;
    }
    if (!Root->TryGetStringField(TEXT("source"), Out.Source) ||
        !Root->TryGetStringField(TEXT("name"), Out.Name) ||
        !Root->TryGetStringField(TEXT("description"), Out.Description) ||
        !Root->TryGetStringField(TEXT("logic"), Out.Logic) ||
        !Root->TryGetBoolField(TEXT("harmless"), Out.bHarmless) ||
        !Root->TryGetStringField(TEXT("color"), Out.Color) ||
        !ParseEnumToken(Root, TEXT("tier"), Out.Tier) ||
        !ParseEnumToken(Root, TEXT("category"), Out.Category) ||
        !ParseEnumToken(Root, TEXT("delivery"), Out.Delivery))
    {
        return false;
    }
    const TArray<TSharedPtr<FJsonValue>>* Stages = nullptr;
    if (!Root->TryGetArrayField(TEXT("stages"), Stages) || Stages->Num() == 0)
    {
        return false;
    }
    for (const TSharedPtr<FJsonValue>& StageValue : *Stages)
    {
        const TSharedPtr<FJsonObject>* StageObj = nullptr;
        if (!StageValue->TryGetObject(StageObj))
        {
            return false;
        }
        FNAWStage Stage;
        if (!ParseEnumToken(*StageObj, TEXT("trigger"), Stage.Trigger))
        {
            return false;
        }
        (*StageObj)->TryGetStringField(TEXT("note"), Stage.Note);
        const TArray<TSharedPtr<FJsonValue>>* Effects = nullptr;
        if (!(*StageObj)->TryGetArrayField(TEXT("effects"), Effects) || Effects->Num() == 0)
        {
            return false;
        }
        for (const TSharedPtr<FJsonValue>& EffectValue : *Effects)
        {
            const TSharedPtr<FJsonObject>* EffectObj = nullptr;
            if (!EffectValue->TryGetObject(EffectObj))
            {
                return false;
            }
            FNAWEffect Effect;
            if (!ParseEnumToken(*EffectObj, TEXT("kind"), Effect.Kind) ||
                !ParseEnumToken(*EffectObj, TEXT("target"), Effect.Target))
            {
                return false;
            }
            Effect.Amount = NumberField(*EffectObj, TEXT("amount"));
            Effect.Duration = NumberField(*EffectObj, TEXT("duration"));
            Effect.Radius = NumberField(*EffectObj, TEXT("radius"));
            Effect.Count = static_cast<int32>(NumberField(*EffectObj, TEXT("count")));
            (*EffectObj)->TryGetStringField(TEXT("note"), Effect.Note);
            Stage.Effects.Add(MoveTemp(Effect));
        }
        Out.Stages.Add(MoveTemp(Stage));
    }
    Out.RawJson = Body;
    return true;
}

bool FNAWGadget::HasTrigger(ENAWTrigger Trigger) const
{
    for (const FNAWStage& Stage : Stages)
    {
        if (Stage.Trigger == Trigger)
        {
            return true;
        }
    }
    return false;
}

TArray<FNAWStage> FNAWGadget::StagesFor(ENAWTrigger Trigger) const
{
    TArray<FNAWStage> Result;
    for (const FNAWStage& Stage : Stages)
    {
        if (Stage.Trigger == Trigger)
        {
            Result.Add(Stage);
        }
    }
    return Result;
}

#if !UE_BUILD_SHIPPING
void NAWContractSelfTest()
{
    // A canned Task-1-shaped sample: PLACED chassis, one ON_TRIGGER LURE stage.
    const FString Sample = TEXT("{\"source\":\"fallback\",\"name\":\"Bait Cooler\",\"description\":\"d\",\"logic\":\"l\",\"tier\":\"COMMON\",\"category\":\"UTILITY\",\"harmless\":true,\"delivery\":\"PLACED\",\"color\":\"#FFC04D\",\"stages\":[{\"trigger\":\"ON_TRIGGER\",\"note\":\"placed\",\"effects\":[{\"kind\":\"LURE\",\"target\":\"STRUCK\",\"amount\":0,\"duration\":6.0,\"radius\":4.0,\"count\":0,\"note\":\"\"}]}]}");
    FNAWGadget Gadget;
    const bool bOk = FNAWGadget::ParseJson(Sample, Gadget) &&
        Gadget.Delivery == ENAWDelivery::PLACED &&
        Gadget.bHarmless &&
        Gadget.HasTrigger(ENAWTrigger::ON_TRIGGER) &&
        Gadget.Stages.Num() == 1 &&
        Gadget.Stages[0].Effects.Num() == 1 &&
        Gadget.Stages[0].Effects[0].Kind == ENAWEffectKind::LURE &&
        Gadget.Stages[0].Effects[0].Radius == 4.0f;
    if (bOk)
    {
        UE_LOG(LogNAW, Log, TEXT("contract mirror self-test: parse OK"));
    }
    else
    {
        UE_LOG(LogNAW, Error,
               TEXT("contract mirror self-test FAILED - Contract.h drifted from resolver/contract.py"));
    }
}
#endif
```

- [ ] **Step 3: Register the self-test on OnPostEngineInit**

In `game/Source/NotAWeapon/NotAWeapon.cpp`, replace the file contents with (the self-test must NOT be called directly in `StartupModule` — UENUM reflection data may not be registered yet):

```cpp
#include "NotAWeapon.h"
#include "Contract.h"
#include "Misc/CoreDelegates.h"

DEFINE_LOG_CATEGORY(LogNAW);

void FNotAWeaponModule::StartupModule()
{
#if !UE_BUILD_SHIPPING
    FCoreDelegates::OnPostEngineInit.AddStatic(&NAWContractSelfTest);
#endif
}

IMPLEMENT_PRIMARY_GAME_MODULE(FNotAWeaponModule, NotAWeapon, "NotAWeapon");
```

- [ ] **Step 4: Build**

Same command as Task 4 Step 5. Expected: `Result: Succeeded`.

- [ ] **Step 5: Manual checklist**

- [ ] Launch the editor. In Output Log (Window → Output Log), filter `LogNAW`: exactly one line `contract mirror self-test: parse OK`. An Error line means the mirror is wrong — fix before committing.

- [ ] **Step 6: Commit**

```bash
git add game/Source/NotAWeapon/Contract.h game/Source/NotAWeapon/Contract.cpp game/Source/NotAWeapon/NotAWeapon.cpp
git commit -m "feat(game): C++ contract mirror - enums, gadget parse, fingerprint constant, self-test

Strict reflection-based parse: unknown tokens fail (outside the contract
= malformed). Self-test runs on OnPostEngineInit in non-shipping builds.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Resolver subsystem (`UNAWResolverSubsystem`)

Server-only async HTTP client over `FHttpModule`: startup fingerprint check, then `Craft()`. All failure modes collapse to "sidecar down" for the caller. **Standing AUP rule applies here:** on HTTP failure, log the numeric status code ONLY — never response bodies, never error text from the wire (a live-path refusal must leave no introspectable trace in the game logs).

**Files:**
- Create: `game/Source/NotAWeapon/NAWResolverSubsystem.h`, `NAWResolverSubsystem.cpp`

**Interfaces:**
- Consumes: `FNAWGadget::ParseJson`, `NAW_CONTRACT_FINGERPRINT`, `LogNAW` (Tasks 4–5); sidecar endpoints `GET /api/contract` and `POST /craft` (Tasks 2–3).
- Produces: `ENAWContractState`, `FNAWCraftComplete` delegate, `UNAWResolverSubsystem::Craft(const TArray<FString>& Items, const FString& TierTarget, FNAWCraftComplete OnComplete)`, `ENAWContractState GetContractState() const`. Task 9's craft spot is the only gameplay caller; Task 7's debug exec commands also call it.

- [ ] **Step 1: Write `NAWResolverSubsystem.h`**

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Contract.h"
#include "NAWResolverSubsystem.generated.h"

enum class ENAWContractState : uint8
{
    Unknown,      // check not yet answered
    Ok,           // fingerprints match - crafting allowed
    Mismatch,     // vocabulary drift - crafting permanently refused this session
    Unreachable   // sidecar down at last check - re-checked on next craft
};

// bSuccess=false => "sim unresponsive" (Gadget is default-constructed, ignore it).
DECLARE_DELEGATE_TwoParams(FNAWCraftComplete, bool /*bSuccess*/, const FNAWGadget& /*Gadget*/);

UCLASS(Config = Game)
class NOTAWEAPON_API UNAWResolverSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    // One craft at a time. Refuses immediately (bSuccess=false) on contract
    // mismatch or if a craft is already in flight.
    void Craft(const TArray<FString>& Items, const FString& TierTarget, FNAWCraftComplete OnComplete);

    ENAWContractState GetContractState() const { return ContractState; }

    UPROPERTY(Config)
    FString SidecarUrl = TEXT("http://127.0.0.1:8000");

private:
    void CheckContract();
    void FailCraft(FNAWCraftComplete& OnComplete);

    ENAWContractState ContractState = ENAWContractState::Unknown;
    bool bCraftInFlight = false;
};
```

- [ ] **Step 2: Write `NAWResolverSubsystem.cpp`**

```cpp
#include "NAWResolverSubsystem.h"
#include "NotAWeapon.h"
#include "Engine/Engine.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonWriter.h"
#include "Serialization/JsonSerializer.h"

void UNAWResolverSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    CheckContract();
}

void UNAWResolverSubsystem::CheckContract()
{
    const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(SidecarUrl + TEXT("/api/contract"));
    Request->SetVerb(TEXT("GET"));
    Request->SetTimeout(5.0f);
    Request->OnProcessRequestComplete().BindWeakLambda(this,
        [this](FHttpRequestPtr, FHttpResponsePtr Response, bool bConnected)
        {
            if (!bConnected || !Response.IsValid() || Response->GetResponseCode() != 200)
            {
                ContractState = ENAWContractState::Unreachable;
                UE_LOG(LogNAW, Warning, TEXT("contract check: sidecar unreachable (status %d)"),
                       Response.IsValid() ? Response->GetResponseCode() : 0);
                return;
            }
            TSharedPtr<FJsonObject> Root;
            const TSharedRef<TJsonReader<>> Reader =
                TJsonReaderFactory<>::Create(Response->GetContentAsString());
            FString Fingerprint;
            if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid() ||
                !Root->TryGetStringField(TEXT("fingerprint"), Fingerprint))
            {
                ContractState = ENAWContractState::Unreachable;
                UE_LOG(LogNAW, Warning, TEXT("contract check: malformed response"));
                return;
            }
            if (Fingerprint == NAW_CONTRACT_FINGERPRINT)
            {
                ContractState = ENAWContractState::Ok;
                UE_LOG(LogNAW, Log, TEXT("contract check: fingerprint OK"));
            }
            else
            {
                ContractState = ENAWContractState::Mismatch;
                UE_LOG(LogNAW, Error,
                       TEXT("CONTRACT MISMATCH - game enums drifted from resolver. Crafting disabled. Rebuild against resolver/contract.py."));
                if (GEngine)
                {
                    GEngine->AddOnScreenDebugMessage(0, 3600.f, FColor::Red,
                        TEXT("CONTRACT MISMATCH - crafting disabled (rebuild the game against the resolver contract)"));
                }
            }
        });
    Request->ProcessRequest();
}

void UNAWResolverSubsystem::FailCraft(FNAWCraftComplete& OnComplete)
{
    static const FNAWGadget Empty;
    OnComplete.ExecuteIfBound(false, Empty);
}

void UNAWResolverSubsystem::Craft(const TArray<FString>& Items, const FString& TierTarget,
                                  FNAWCraftComplete OnComplete)
{
    if (ContractState == ENAWContractState::Mismatch)
    {
        UE_LOG(LogNAW, Error, TEXT("craft refused: contract mismatch"));
        FailCraft(OnComplete);
        return;
    }
    if (bCraftInFlight)
    {
        UE_LOG(LogNAW, Warning, TEXT("craft refused: one already in flight"));
        FailCraft(OnComplete);
        return;
    }
    if (ContractState != ENAWContractState::Ok)
    {
        // Sidecar was down (or never seen). Re-probe for next time, fail this one now.
        CheckContract();
        FailCraft(OnComplete);
        return;
    }

    TSharedRef<FJsonObject> Body = MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> ItemValues;
    for (const FString& Item : Items)
    {
        ItemValues.Add(MakeShared<FJsonValueString>(Item));
    }
    Body->SetArrayField(TEXT("items"), ItemValues);
    Body->SetStringField(TEXT("tier_target"), TierTarget);
    FString BodyString;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&BodyString);
    FJsonSerializer::Serialize(Body, Writer);

    const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(SidecarUrl + TEXT("/craft"));
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    Request->SetContentAsString(BodyString);
    Request->SetTimeout(20.0f);  // covers the full live retry ladder (spec: ~20s cap)
    bCraftInFlight = true;
    Request->OnProcessRequestComplete().BindWeakLambda(this,
        [this, OnComplete](FHttpRequestPtr, FHttpResponsePtr Response, bool bConnected) mutable
        {
            bCraftInFlight = false;
            // AUP rule: numeric status only - NEVER log the response body or error text.
            if (!bConnected || !Response.IsValid() || Response->GetResponseCode() != 200)
            {
                UE_LOG(LogNAW, Warning, TEXT("craft failed: status %d"),
                       Response.IsValid() ? Response->GetResponseCode() : 0);
                ContractState = ENAWContractState::Unreachable;
                FailCraft(OnComplete);
                return;
            }
            FNAWGadget Gadget;
            if (!FNAWGadget::ParseJson(Response->GetContentAsString(), Gadget))
            {
                // Malformed JSON reaching the game = treated as sidecar-down (spec).
                UE_LOG(LogNAW, Warning, TEXT("craft failed: malformed gadget JSON"));
                FailCraft(OnComplete);
                return;
            }
            UE_LOG(LogNAW, Log, TEXT("craft OK: '%s' (source=%s)"), *Gadget.Name, *Gadget.Source);
            OnComplete.ExecuteIfBound(true, Gadget);
        });
    Request->ProcessRequest();
}
```

- [ ] **Step 3: Build**

Same command as Task 4 Step 5. Expected: `Result: Succeeded`.

- [ ] **Step 4: Manual checklist**

Start the sidecar in a separate terminal first:

```powershell
powershell -File C:\Users\rewfu\repos\not-a-weapon\game\run-sidecar.ps1 --fallback
```

- [ ] With the sidecar RUNNING: launch the editor, PIE. Output Log filter `LogNAW` shows `contract check: fingerprint OK`.
- [ ] Stop the sidecar, restart PIE: log shows `contract check: sidecar unreachable (status 0)`. No crash, no hang.
- [ ] (Mismatch path is exercised in Task 9's checklist by temporarily editing the fingerprint constant — deferred there so a craft attempt exists to refuse.)

- [ ] **Step 5: Commit**

```bash
git add game/Source/NotAWeapon/NAWResolverSubsystem.h game/Source/NotAWeapon/NAWResolverSubsystem.cpp
git commit -m "feat(game): resolver subsystem - fingerprint check, async /craft client

All failures collapse to sidecar-down for callers; HTTP status codes
logged numerically only, never response bodies (standing AUP rule).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Gadget interpreter + weapon actors

The heart. Takes a parsed `FNAWGadget` and makes it *visibly do what its JSON says* at blockout grade. Ugly is fine; **legible is the bar**. Everything renders as debug draw + floating text + tinted primitives — no art. Triggers the blockout can't render (ON_KILL with no bots, ON_BLOCK with no guard input) get announced as floating text, never silently dropped.

**Files:**
- Create: `game/Source/NotAWeapon/NAWHealthComponent.h/.cpp`
- Create: `game/Source/NotAWeapon/NAWEffectExecutor.h/.cpp`
- Create: `game/Source/NotAWeapon/NAWGadgetWeapon.h/.cpp`
- Create: `game/Source/NotAWeapon/NAWGadgetProjectile.h/.cpp`
- Create: `game/Source/NotAWeapon/NAWGadgetPlaced.h/.cpp`
- Create: `game/Source/NotAWeapon/NAWTargetDummy.h/.cpp`
- Modify: `game/Source/NotAWeapon/NAWCharacter.h/.cpp` (equip + fire + debug exec commands)

**Interfaces:**
- Consumes: `FNAWGadget`/`FNAWStage`/`FNAWEffect` + enums (Task 5); `UNAWResolverSubsystem::Craft` + `FNAWCraftComplete` (Task 6, debug commands only).
- Produces: `UNAWHealthComponent` (`Damage(float, AActor*)`, `Heal(float)`, `AddShield(float)`, `IsDead()`, `FNAWOnDead OnDead` multicast — Task 10 binds it); `FNAWEffectContext` + `NAWEffects::ExecuteStage`; `ANAWGadgetWeapon` with `Init(const FNAWGadget&)` and `Fire()`; `ANAWCharacter::EquipGadget(const FNAWGadget&)` (Task 9 calls it after a successful craft).

- [ ] **Step 1: Write the health component**

`game/Source/NotAWeapon/NAWHealthComponent.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NAWHealthComponent.generated.h"

DECLARE_MULTICAST_DELEGATE(FNAWOnDead);

UCLASS(ClassGroup = (NAW), meta = (BlueprintSpawnableComponent))
class NOTAWEAPON_API UNAWHealthComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UNAWHealthComponent();

    void Damage(float Amount, AActor* Instigator);
    void Heal(float Amount);
    void AddShield(float Amount);
    bool IsDead() const { return Health <= 0.f; }

    FNAWOnDead OnDead;

    UPROPERTY(EditAnywhere)
    float MaxHealth = 100.f;

protected:
    virtual void BeginPlay() override;

private:
    UFUNCTION()
    void HandleTakeAnyDamage(AActor* DamagedActor, float Damage, const UDamageType* DamageType,
                             AController* InstigatedBy, AActor* DamageCauser);
    void Popup(const FString& Text, const FColor& Color) const;

    float Health = 100.f;
    float Shield = 0.f;
};
```

`game/Source/NotAWeapon/NAWHealthComponent.cpp`:

```cpp
#include "NAWHealthComponent.h"
#include "NotAWeapon.h"
#include "DrawDebugHelpers.h"
#include "GameFramework/Actor.h"

UNAWHealthComponent::UNAWHealthComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UNAWHealthComponent::BeginPlay()
{
    Super::BeginPlay();
    Health = MaxHealth;
    if (AActor* Owner = GetOwner())
    {
        Owner->OnTakeAnyDamage.AddDynamic(this, &UNAWHealthComponent::HandleTakeAnyDamage);
    }
}

void UNAWHealthComponent::HandleTakeAnyDamage(AActor*, float DamageAmount, const UDamageType*,
                                              AController*, AActor* DamageCauser)
{
    Damage(DamageAmount, DamageCauser);
}

void UNAWHealthComponent::Damage(float Amount, AActor* /*Instigator*/)
{
    if (IsDead() || Amount <= 0.f)
    {
        return;
    }
    const float Soaked = FMath::Min(Shield, Amount);
    Shield -= Soaked;
    const float ToHealth = Amount - Soaked;
    Health = FMath::Max(0.f, Health - ToHealth);
    Popup(FString::Printf(TEXT("-%.0f%s"), Amount, Soaked > 0.f ? TEXT(" (shielded)") : TEXT("")),
          FColor::Red);
    if (Health <= 0.f)
    {
        OnDead.Broadcast();
    }
}

void UNAWHealthComponent::Heal(float Amount)
{
    if (IsDead() || Amount <= 0.f)
    {
        return;
    }
    Health = FMath::Min(MaxHealth, Health + Amount);
    Popup(FString::Printf(TEXT("+%.0f"), Amount), FColor::Green);
}

void UNAWHealthComponent::AddShield(float Amount)
{
    if (IsDead() || Amount <= 0.f)
    {
        return;
    }
    Shield += Amount;
    Popup(FString::Printf(TEXT("shield +%.0f"), Amount), FColor::Cyan);
}

void UNAWHealthComponent::Popup(const FString& Text, const FColor& Color) const
{
    if (const AActor* Owner = GetOwner())
    {
        DrawDebugString(Owner->GetWorld(), Owner->GetActorLocation() + FVector(0, 0, 100),
                        Text, nullptr, Color, 1.5f, true);
    }
}
```

- [ ] **Step 2: Write the effect executor**

`game/Source/NotAWeapon/NAWEffectExecutor.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Contract.h"

struct FNAWEffectContext
{
    UWorld* World = nullptr;
    AActor* Wielder = nullptr;   // SELF target; also the damage instigator
    AActor* Struck = nullptr;    // direct-hit victim; may be null (radius-only stages)
    FVector Location = FVector::ZeroVector;  // where the stage happens
};

namespace NAWEffects
{
// Executes every effect in the stage at blockout grade. Radius > 0 on a
// STRUCK effect gathers ECC_Pawn actors in a sphere; radius 0 hits Struck only.
void ExecuteStage(const FNAWEffectContext& Context, const FNAWStage& Stage);
}
```

`game/Source/NotAWeapon/NAWEffectExecutor.cpp`:

```cpp
#include "NAWEffectExecutor.h"
#include "NAWHealthComponent.h"
#include "NotAWeapon.h"
#include "DrawDebugHelpers.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

namespace
{
constexpr float UNITS_PER_METER = 100.f;  // contract radii/amount distances are meters

TArray<AActor*> GatherTargets(const FNAWEffectContext& Context, const FNAWEffect& Effect)
{
    TArray<AActor*> Targets;
    if (Effect.Target == ENAWTarget::SELF)
    {
        if (Context.Wielder)
        {
            Targets.Add(Context.Wielder);
        }
        return Targets;
    }
    if (Effect.Radius > 0.f)
    {
        TArray<FOverlapResult> Overlaps;
        FCollisionShape Sphere = FCollisionShape::MakeSphere(Effect.Radius * UNITS_PER_METER);
        Context.World->OverlapMultiByChannel(Overlaps, Context.Location, FQuat::Identity,
                                             ECC_Pawn, Sphere);
        for (const FOverlapResult& Overlap : Overlaps)
        {
            Targets.AddUnique(Overlap.GetActor());
        }
        DrawDebugSphere(Context.World, Context.Location, Effect.Radius * UNITS_PER_METER,
                        16, FColor::Orange, false, 1.0f);
    }
    else if (Context.Struck)
    {
        Targets.Add(Context.Struck);
    }
    return Targets;
}

void FloatText(const FNAWEffectContext& Context, const FString& Text, const FColor& Color)
{
    DrawDebugString(Context.World, Context.Location + FVector(0, 0, 150), Text, nullptr,
                    Color, 2.5f, true);
}

void ScaleSpeed(AActor* Target, float Multiplier, float Duration)
{
    ACharacter* Character = Cast<ACharacter>(Target);
    if (!Character)
    {
        return;
    }
    UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
    const float Normal = 600.f;  // engine default MaxWalkSpeed; restore to this, not to current
    Movement->MaxWalkSpeed = Normal * Multiplier;
    FTimerHandle Handle;
    Character->GetWorldTimerManager().SetTimer(Handle,
        FTimerDelegate::CreateWeakLambda(Character, [Movement]()
        {
            Movement->MaxWalkSpeed = 600.f;
        }),
        FMath::Max(Duration, 0.5f), false);
}
}  // namespace

void NAWEffects::ExecuteStage(const FNAWEffectContext& Context, const FNAWStage& Stage)
{
    if (!Context.World)
    {
        return;
    }
    for (const FNAWEffect& Effect : Stage.Effects)
    {
        const TArray<AActor*> Targets = GatherTargets(Context, Effect);
        const FString KindName = StaticEnum<ENAWEffectKind>()->GetNameStringByValue(
            static_cast<int64>(Effect.Kind));
        switch (Effect.Kind)
        {
        case ENAWEffectKind::DAMAGE:
        case ENAWEffectKind::BURN:
        case ENAWEffectKind::PIERCE:
        case ENAWEffectKind::CHAIN:
        case ENAWEffectKind::EXPLODE:
            for (AActor* Target : Targets)
            {
                UGameplayStatics::ApplyDamage(Target, Effect.Amount, nullptr, Context.Wielder,
                                              nullptr);
            }
            if (Effect.Kind == ENAWEffectKind::EXPLODE)
            {
                DrawDebugSphere(Context.World, Context.Location,
                                FMath::Max(Effect.Radius, 1.f) * UNITS_PER_METER, 24,
                                FColor::Red, false, 1.5f);
            }
            break;
        case ENAWEffectKind::KNOCKBACK:
        case ENAWEffectKind::LAUNCH:
            for (AActor* Target : Targets)
            {
                if (ACharacter* Character = Cast<ACharacter>(Target))
                {
                    FVector Away = (Target->GetActorLocation() - Context.Location).GetSafeNormal();
                    if (Effect.Kind == ENAWEffectKind::LAUNCH)
                    {
                        Away = FVector::UpVector;
                    }
                    Character->LaunchCharacter(Away * Effect.Amount * 50.f, true, true);
                }
            }
            break;
        case ENAWEffectKind::STAGGER:
        case ENAWEffectKind::SNARE:
        case ENAWEffectKind::FREEZE:
            for (AActor* Target : Targets)
            {
                ScaleSpeed(Target, 0.f, Effect.Duration);
            }
            FloatText(Context, KindName, FColor::Blue);
            break;
        case ENAWEffectKind::SLOW:
            for (AActor* Target : Targets)
            {
                ScaleSpeed(Target, 0.4f, Effect.Duration);
            }
            FloatText(Context, KindName, FColor::Blue);
            break;
        case ENAWEffectKind::SPEED:
            for (AActor* Target : Targets)
            {
                ScaleSpeed(Target, 1.f + Effect.Amount / 100.f, Effect.Duration);
            }
            FloatText(Context, KindName, FColor::Green);
            break;
        case ENAWEffectKind::HEAL:
            for (AActor* Target : Targets)
            {
                if (UNAWHealthComponent* HealthComp =
                        Target->FindComponentByClass<UNAWHealthComponent>())
                {
                    HealthComp->Heal(Effect.Amount);
                }
            }
            break;
        case ENAWEffectKind::SHIELD:
            for (AActor* Target : Targets)
            {
                if (UNAWHealthComponent* HealthComp =
                        Target->FindComponentByClass<UNAWHealthComponent>())
                {
                    HealthComp->AddShield(Effect.Amount);
                }
            }
            break;
        case ENAWEffectKind::SUMMON:
        case ENAWEffectKind::LURE:
            // No bots in the blockout - announce so the stage is visibly not lost.
            FloatText(Context,
                      FString::Printf(TEXT("%s x%d (needs bots - announced only)"), *KindName,
                                      FMath::Max(Effect.Count, 1)),
                      FColor::Yellow);
            break;
        }
        UE_LOG(LogNAW, Log, TEXT("effect %s amount=%.1f targets=%d"), *KindName, Effect.Amount,
               Targets.Num());
    }
}
```

- [ ] **Step 3: Write the target dummy**

`game/Source/NotAWeapon/NAWTargetDummy.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NAWTargetDummy.generated.h"

// Static punching bag for verifying effects without bots. Place a few in Blockout.
UCLASS()
class NOTAWEAPON_API ANAWTargetDummy : public AActor
{
    GENERATED_BODY()

public:
    ANAWTargetDummy();

private:
    UPROPERTY(VisibleAnywhere)
    class UStaticMeshComponent* Mesh;

    UPROPERTY(VisibleAnywhere)
    class UNAWHealthComponent* Health;

    void HandleDead();
};
```

`game/Source/NotAWeapon/NAWTargetDummy.cpp`:

```cpp
#include "NAWTargetDummy.h"
#include "NAWHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "UObject/ConstructorHelpers.h"

ANAWTargetDummy::ANAWTargetDummy()
{
    PrimaryActorTick.bCanEverTick = false;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(
        TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    if (Cylinder.Succeeded())
    {
        Mesh->SetStaticMesh(Cylinder.Object);
    }
    Mesh->SetCollisionObjectType(ECC_Pawn);  // so radius effects find it
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    SetRootComponent(Mesh);
    Health = CreateDefaultSubobject<UNAWHealthComponent>(TEXT("Health"));
    Health->OnDead.AddUObject(this, &ANAWTargetDummy::HandleDead);
}

void ANAWTargetDummy::HandleDead()
{
    Destroy();
}
```

- [ ] **Step 4: Write the weapon, projectile, and placed actors**

`game/Source/NotAWeapon/NAWGadgetWeapon.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Contract.h"
#include "NAWGadgetWeapon.generated.h"

// The held weapon: a tinted cube attached to the camera. Fire() dispatches on
// the gadget's delivery form and executes stages via NAWEffects::ExecuteStage.
UCLASS()
class NOTAWEAPON_API ANAWGadgetWeapon : public AActor
{
    GENERATED_BODY()

public:
    ANAWGadgetWeapon();

    void Init(const FNAWGadget& InGadget);
    void Fire();

    FNAWGadget Gadget;

private:
    UPROPERTY(VisibleAnywhere)
    class UStaticMeshComponent* Mesh;

    void FireHitscan();
    void FireProjectile(bool bArc);
    void FirePlaced();
    void FireMelee();
    void FireSelf();
    void AnnounceUnrenderedTriggers();
    FVector MuzzleLocation() const;
    FVector AimDirection() const;
};
```

`game/Source/NotAWeapon/NAWGadgetWeapon.cpp`:

```cpp
#include "NAWGadgetWeapon.h"
#include "NAWEffectExecutor.h"
#include "NAWGadgetPlaced.h"
#include "NAWGadgetProjectile.h"
#include "NotAWeapon.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

ANAWGadgetWeapon::ANAWGadgetWeapon()
{
    PrimaryActorTick.bCanEverTick = false;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(
        TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded())
    {
        Mesh->SetStaticMesh(Cube.Object);
    }
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetRelativeScale3D(FVector(0.4f, 0.15f, 0.15f));
    SetRootComponent(Mesh);
}

void ANAWGadgetWeapon::Init(const FNAWGadget& InGadget)
{
    Gadget = InGadget;
    if (UMaterialInstanceDynamic* Tint = Mesh->CreateAndSetMaterialInstanceDynamic(0))
    {
        Tint->SetVectorParameterValue(TEXT("Color"),
                                      FLinearColor(FColor::FromHex(Gadget.Color)));
    }
    AnnounceUnrenderedTriggers();
}

void ANAWGadgetWeapon::Fire()
{
    if (!GetOwner() || !GetOwner()->HasAuthority())
    {
        return;
    }
    switch (Gadget.Delivery)
    {
    case ENAWDelivery::HITSCAN:
    case ENAWDelivery::BEAM:
    case ENAWDelivery::SPRAY:
        FireHitscan();
        break;
    case ENAWDelivery::PROJECTILE:
        FireProjectile(false);
        break;
    case ENAWDelivery::LOBBED:
    case ENAWDelivery::THROWN:
        FireProjectile(true);
        break;
    case ENAWDelivery::PLACED:
        FirePlaced();
        break;
    case ENAWDelivery::SWING:
    case ENAWDelivery::THRUST:
    case ENAWDelivery::SLAM:
    case ENAWDelivery::WHIP:
        FireMelee();
        break;
    case ENAWDelivery::GUARD:
    case ENAWDelivery::SELF:
    case ENAWDelivery::DASH:
        FireSelf();
        break;
    }
}

FVector ANAWGadgetWeapon::MuzzleLocation() const
{
    return GetActorLocation() + AimDirection() * 60.f;
}

FVector ANAWGadgetWeapon::AimDirection() const
{
    const APawn* Pawn = Cast<APawn>(GetOwner());
    return Pawn ? Pawn->GetControlRotation().Vector() : GetActorForwardVector();
}

void ANAWGadgetWeapon::FireHitscan()
{
    const FVector Start = MuzzleLocation();
    const FVector End = Start + AimDirection() * 100.f * 100.f;  // 100 m
    FHitResult Hit;
    FCollisionQueryParams Params;
    Params.AddIgnoredActor(GetOwner());
    Params.AddIgnoredActor(this);
    GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params);
    DrawDebugLine(GetWorld(), Start, Hit.bBlockingHit ? Hit.Location : End,
                  FColor::FromHex(Gadget.Color), false, 0.3f, 0, 2.f);
    FNAWEffectContext Context;
    Context.World = GetWorld();
    Context.Wielder = GetOwner();
    Context.Struck = Hit.GetActor();
    Context.Location = Hit.bBlockingHit ? Hit.Location : End;
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_USE))
    {
        Context.Location = Start;
        NAWEffects::ExecuteStage(Context, Stage);
    }
    if (Hit.bBlockingHit)
    {
        Context.Location = Hit.Location;
        for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_HIT))
        {
            NAWEffects::ExecuteStage(Context, Stage);
        }
        for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_IMPACT))
        {
            NAWEffects::ExecuteStage(Context, Stage);
        }
    }
}

void ANAWGadgetWeapon::FireProjectile(bool bArc)
{
    FActorSpawnParameters Params;
    Params.Owner = GetOwner();
    Params.SpawnCollisionHandlingOverride =
        ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    ANAWGadgetProjectile* Projectile = GetWorld()->SpawnActor<ANAWGadgetProjectile>(
        MuzzleLocation(), AimDirection().Rotation(), Params);
    if (Projectile)
    {
        Projectile->Init(Gadget, GetOwner(), bArc);
    }
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_USE))
    {
        FNAWEffectContext Context;
        Context.World = GetWorld();
        Context.Wielder = GetOwner();
        Context.Location = MuzzleLocation();
        NAWEffects::ExecuteStage(Context, Stage);
    }
}

void ANAWGadgetWeapon::FirePlaced()
{
    FActorSpawnParameters Params;
    Params.Owner = GetOwner();
    Params.SpawnCollisionHandlingOverride =
        ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    const FVector Spot = GetOwner()->GetActorLocation() + AimDirection() * 150.f;
    ANAWGadgetPlaced* Placed = GetWorld()->SpawnActor<ANAWGadgetPlaced>(
        Spot, FRotator::ZeroRotator, Params);
    if (Placed)
    {
        Placed->Init(Gadget, GetOwner());
    }
}

void ANAWGadgetWeapon::FireMelee()
{
    // Blockout melee: a short forward sphere sweep.
    const FVector Start = GetOwner()->GetActorLocation();
    const FVector End = Start + AimDirection() * 250.f;
    TArray<FHitResult> Hits;
    FCollisionQueryParams Params;
    Params.AddIgnoredActor(GetOwner());
    Params.AddIgnoredActor(this);
    GetWorld()->SweepMultiByChannel(Hits, Start, End, FQuat::Identity, ECC_Pawn,
                                    FCollisionShape::MakeSphere(80.f), Params);
    DrawDebugCapsule(GetWorld(), (Start + End) / 2, 125.f, 80.f,
                     AimDirection().ToOrientationQuat(), FColor::FromHex(Gadget.Color),
                     false, 0.3f);
    FNAWEffectContext Context;
    Context.World = GetWorld();
    Context.Wielder = GetOwner();
    Context.Location = End;
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_USE))
    {
        NAWEffects::ExecuteStage(Context, Stage);
    }
    for (const FHitResult& Hit : Hits)
    {
        Context.Struck = Hit.GetActor();
        Context.Location = Hit.ImpactPoint;
        for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_HIT))
        {
            NAWEffects::ExecuteStage(Context, Stage);
        }
        for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_IMPACT))
        {
            NAWEffects::ExecuteStage(Context, Stage);
        }
    }
}

void ANAWGadgetWeapon::FireSelf()
{
    FNAWEffectContext Context;
    Context.World = GetWorld();
    Context.Wielder = GetOwner();
    Context.Location = GetOwner()->GetActorLocation();
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_USE))
    {
        NAWEffects::ExecuteStage(Context, Stage);
    }
    // GUARD's ON_BLOCK has no block input in the blockout - fire it on use so
    // the stage is at least visible, and say so.
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_BLOCK))
    {
        NAWEffects::ExecuteStage(Context, Stage);
        DrawDebugString(GetWorld(), Context.Location + FVector(0, 0, 200),
                        TEXT("ON_BLOCK fired on use (no block input in blockout)"), nullptr,
                        FColor::Yellow, 3.f, true);
    }
}

void ANAWGadgetWeapon::AnnounceUnrenderedTriggers()
{
    for (const ENAWTrigger Trigger : {ENAWTrigger::ON_KILL, ENAWTrigger::ON_EXPIRE})
    {
        if (Gadget.HasTrigger(Trigger))
        {
            const FString Name = StaticEnum<ENAWTrigger>()->GetNameStringByValue(
                static_cast<int64>(Trigger));
            UE_LOG(LogNAW, Log, TEXT("gadget '%s': stage armed: %s (not rendered in blockout)"),
                   *Gadget.Name, *Name);
            DrawDebugString(GetWorld(), GetActorLocation() + FVector(0, 0, 250),
                            FString::Printf(TEXT("stage armed: %s (not rendered in blockout)"),
                                            *Name),
                            nullptr, FColor::Yellow, 4.f, true);
        }
    }
}
```

`game/Source/NotAWeapon/NAWGadgetProjectile.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Contract.h"
#include "NAWGadgetProjectile.generated.h"

// Straight or arcing projectile; runs ON_IMPACT + ON_HIT stages where it lands.
UCLASS()
class NOTAWEAPON_API ANAWGadgetProjectile : public AActor
{
    GENERATED_BODY()

public:
    ANAWGadgetProjectile();

    void Init(const FNAWGadget& InGadget, AActor* InWielder, bool bArc);

private:
    UPROPERTY(VisibleAnywhere)
    class UStaticMeshComponent* Mesh;

    UPROPERTY(VisibleAnywhere)
    class UProjectileMovementComponent* Movement;

    UFUNCTION()
    void OnHit(UPrimitiveComponent* HitComponent, AActor* OtherActor,
               UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit);

    FNAWGadget Gadget;

    UPROPERTY()
    AActor* Wielder = nullptr;
};
```

`game/Source/NotAWeapon/NAWGadgetProjectile.cpp`:

```cpp
#include "NAWGadgetProjectile.h"
#include "NAWEffectExecutor.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

ANAWGadgetProjectile::ANAWGadgetProjectile()
{
    PrimaryActorTick.bCanEverTick = false;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(
        TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    if (Sphere.Succeeded())
    {
        Mesh->SetStaticMesh(Sphere.Object);
    }
    Mesh->SetRelativeScale3D(FVector(0.2f));
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Mesh->SetCollisionResponseToAllChannels(ECR_Block);
    Mesh->SetNotifyRigidBodyCollision(true);
    SetRootComponent(Mesh);
    Movement = CreateDefaultSubobject<UProjectileMovementComponent>(TEXT("Movement"));
    Movement->InitialSpeed = 2500.f;
    Movement->MaxSpeed = 2500.f;
    InitialLifeSpan = 8.f;
}

void ANAWGadgetProjectile::Init(const FNAWGadget& InGadget, AActor* InWielder, bool bArc)
{
    Gadget = InGadget;
    Wielder = InWielder;
    Movement->ProjectileGravityScale = bArc ? 1.f : 0.f;
    if (bArc)
    {
        Movement->InitialSpeed = 1500.f;
        Movement->Velocity = GetActorForwardVector() * 1500.f + FVector(0, 0, 300.f);
    }
    if (UMaterialInstanceDynamic* Tint = Mesh->CreateAndSetMaterialInstanceDynamic(0))
    {
        Tint->SetVectorParameterValue(TEXT("Color"),
                                      FLinearColor(FColor::FromHex(Gadget.Color)));
    }
    Mesh->OnComponentHit.AddDynamic(this, &ANAWGadgetProjectile::OnHit);
    if (Wielder)
    {
        Mesh->IgnoreActorWhenMoving(Wielder, true);
    }
}

void ANAWGadgetProjectile::OnHit(UPrimitiveComponent*, AActor* OtherActor, UPrimitiveComponent*,
                                 FVector, const FHitResult& Hit)
{
    FNAWEffectContext Context;
    Context.World = GetWorld();
    Context.Wielder = Wielder;
    Context.Struck = OtherActor;
    Context.Location = Hit.ImpactPoint;
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_IMPACT))
    {
        NAWEffects::ExecuteStage(Context, Stage);
    }
    if (OtherActor && OtherActor != Wielder)
    {
        for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_HIT))
        {
            NAWEffects::ExecuteStage(Context, Stage);
        }
    }
    Destroy();
}
```

`game/Source/NotAWeapon/NAWGadgetPlaced.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Contract.h"
#include "NAWGadgetPlaced.generated.h"

// Placed gadget: arms after a short delay, fires its ON_TRIGGER stages when a
// pawn (or dummy) enters the proximity sphere. The Task 1 fix exists so
// PLACED-chassis fallback gadgets reach THIS code path with an ON_TRIGGER stage.
UCLASS()
class NOTAWEAPON_API ANAWGadgetPlaced : public AActor
{
    GENERATED_BODY()

public:
    ANAWGadgetPlaced();

    void Init(const FNAWGadget& InGadget, AActor* InWielder);

private:
    UPROPERTY(VisibleAnywhere)
    class UStaticMeshComponent* Mesh;

    UPROPERTY(VisibleAnywhere)
    class USphereComponent* Proximity;

    UFUNCTION()
    void OnProximity(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
                     UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep,
                     const FHitResult& SweepResult);
    void Arm();

    FNAWGadget Gadget;

    UPROPERTY()
    AActor* Wielder = nullptr;

    bool bArmed = false;
};
```

`game/Source/NotAWeapon/NAWGadgetPlaced.cpp`:

```cpp
#include "NAWGadgetPlaced.h"
#include "NAWEffectExecutor.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

ANAWGadgetPlaced::ANAWGadgetPlaced()
{
    PrimaryActorTick.bCanEverTick = false;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(
        TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded())
    {
        Mesh->SetStaticMesh(Cube.Object);
    }
    Mesh->SetRelativeScale3D(FVector(0.5f, 0.5f, 0.3f));
    SetRootComponent(Mesh);
    Proximity = CreateDefaultSubobject<USphereComponent>(TEXT("Proximity"));
    Proximity->SetupAttachment(Mesh);
    Proximity->SetSphereRadius(200.f);
    Proximity->SetCollisionObjectType(ECC_WorldDynamic);
    Proximity->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    InitialLifeSpan = 60.f;
}

void ANAWGadgetPlaced::Init(const FNAWGadget& InGadget, AActor* InWielder)
{
    Gadget = InGadget;
    Wielder = InWielder;
    if (UMaterialInstanceDynamic* Tint = Mesh->CreateAndSetMaterialInstanceDynamic(0))
    {
        Tint->SetVectorParameterValue(TEXT("Color"),
                                      FLinearColor(FColor::FromHex(Gadget.Color)));
    }
    // Arm delay so the wielder can step away without triggering it on themself.
    FTimerHandle Handle;
    GetWorldTimerManager().SetTimer(Handle, this, &ANAWGadgetPlaced::Arm, 1.5f, false);
}

void ANAWGadgetPlaced::Arm()
{
    bArmed = true;
    Proximity->OnComponentBeginOverlap.AddDynamic(this, &ANAWGadgetPlaced::OnProximity);
    DrawDebugString(GetWorld(), GetActorLocation() + FVector(0, 0, 80), TEXT("armed"), nullptr,
                    FColor::Orange, 2.f, true);
}

void ANAWGadgetPlaced::OnProximity(UPrimitiveComponent*, AActor* OtherActor,
                                   UPrimitiveComponent*, int32, bool, const FHitResult&)
{
    if (!bArmed || !OtherActor || OtherActor == this)
    {
        return;
    }
    FNAWEffectContext Context;
    Context.World = GetWorld();
    Context.Wielder = Wielder;
    Context.Struck = OtherActor;
    Context.Location = GetActorLocation();
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_TRIGGER))
    {
        NAWEffects::ExecuteStage(Context, Stage);
    }
    Destroy();
}
```

- [ ] **Step 5: Wire equip + fire + debug exec commands into the character**

`NAWCharacter.h` — add to the class (keep everything from Task 4):

```cpp
public:
    void EquipGadget(const struct FNAWGadget& Gadget);

    // Console commands (` then type name) - dev-only craft without pickups.
    // These DO hit the live resolver when the sidecar has a key.
    UFUNCTION(Exec)
    void DebugCraftPlaced();

    UFUNCTION(Exec)
    void DebugCraftThrown();

protected:
    UPROPERTY()
    class ANAWGadgetWeapon* EquippedWeapon = nullptr;

private:
    void Fire();
    void DebugCraft(const TArray<FString>& Items, const FString& TierTarget);
```

`NAWCharacter.cpp` — add includes, one binding, and the implementations:

```cpp
#include "NAWGadgetWeapon.h"
#include "NAWResolverSubsystem.h"
```

In `SetupPlayerInputComponent`, append:

```cpp
    PlayerInputComponent->BindAction("Fire", IE_Pressed, this, &ANAWCharacter::Fire);
```

New functions:

```cpp
void ANAWCharacter::EquipGadget(const FNAWGadget& Gadget)
{
    if (!HasAuthority())
    {
        return;
    }
    if (EquippedWeapon)
    {
        EquippedWeapon->Destroy();
        EquippedWeapon = nullptr;
    }
    FActorSpawnParameters Params;
    Params.Owner = this;
    EquippedWeapon = GetWorld()->SpawnActor<ANAWGadgetWeapon>(Params);
    if (EquippedWeapon)
    {
        EquippedWeapon->Init(Gadget);
        EquippedWeapon->AttachToComponent(Camera,
            FAttachmentTransformRules::SnapToTargetNotIncludingScale);
        EquippedWeapon->SetActorRelativeLocation(FVector(60.f, 25.f, -20.f));
    }
}

void ANAWCharacter::Fire()
{
    if (EquippedWeapon)
    {
        EquippedWeapon->Fire();
    }
}

void ANAWCharacter::DebugCraft(const TArray<FString>& Items, const FString& TierTarget)
{
    UNAWResolverSubsystem* Resolver = GetGameInstance()->GetSubsystem<UNAWResolverSubsystem>();
    Resolver->Craft(Items, TierTarget, FNAWCraftComplete::CreateWeakLambda(this,
        [this](bool bSuccess, const FNAWGadget& Gadget)
        {
            if (bSuccess)
            {
                EquipGadget(Gadget);
            }
            else if (GEngine)
            {
                GEngine->AddOnScreenDebugMessage(-1, 4.f, FColor::Red,
                                                 TEXT("debug craft failed - sidecar down?"));
            }
        }));
}

void ANAWCharacter::DebugCraftPlaced()
{
    DebugCraft({TEXT("cooler of raw steaks")}, TEXT("COMMON"));
}

void ANAWCharacter::DebugCraftThrown()
{
    DebugCraft({TEXT("bucket of wet cement"), TEXT("jerrycan")}, TEXT("RARE"));
}
```

- [ ] **Step 6: Build**

Same command as Task 4 Step 5. Expected: `Result: Succeeded`.

- [ ] **Step 7: Manual checklist**

Sidecar running in fallback mode (`run-sidecar.ps1 --fallback` — no API spend for this checklist). In the editor, drag 2–3 `NAWTargetDummy` actors into Blockout from the Place Actors panel (search "NAW"), save the map.

- [ ] PIE → console (`` ` ``) → `DebugCraftThrown`. A tinted cube appears bottom-right of the view within ~1s.
- [ ] Left-click: an arcing tinted sphere flies out; where it lands, effects visibly happen (damage popups on a dummy hit, debug spheres for radius effects, floating text for announced kinds). `LogNAW` lines show each effect with its amount.
- [ ] `DebugCraftPlaced`: fire places a slab that floats "armed" after ~1.5s; walk a dummy's way... walk INTO the proximity radius yourself: the ON_TRIGGER stage fires (the steaks are harmless LURE — expect yellow "LURE ... (needs bots - announced only)" text, NOT damage). **This is the Task 1 fix visible in-game.**
- [ ] Hit a dummy enough times: popups count down and the dummy disappears at 0.
- [ ] No crash on firing with nothing in view, on rapid re-crafts, or on letting a projectile time out (8s lifespan).

- [ ] **Step 8: Commit**

```bash
git add game/Source/NotAWeapon/NAWHealthComponent.h game/Source/NotAWeapon/NAWHealthComponent.cpp game/Source/NotAWeapon/NAWEffectExecutor.h game/Source/NotAWeapon/NAWEffectExecutor.cpp game/Source/NotAWeapon/NAWGadgetWeapon.h game/Source/NotAWeapon/NAWGadgetWeapon.cpp game/Source/NotAWeapon/NAWGadgetProjectile.h game/Source/NotAWeapon/NAWGadgetProjectile.cpp game/Source/NotAWeapon/NAWGadgetPlaced.h game/Source/NotAWeapon/NAWGadgetPlaced.cpp game/Source/NotAWeapon/NAWTargetDummy.h game/Source/NotAWeapon/NAWTargetDummy.cpp game/Source/NotAWeapon/NAWCharacter.h game/Source/NotAWeapon/NAWCharacter.cpp game/Content/Maps/Blockout.umap
git commit -m "feat(game): gadget interpreter - delivery dispatch, staged effects, blockout rendering

Every effect kind renders legibly (popups, debug draw, floating text);
unrenderable triggers are announced, never silently dropped.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Inventory + junk pickups

Six-slot inventory of item *names* (strings straight from the catalog — the game never interprets them), pickup actors to fill it, number-key selection, and a persistent HUD line so you always see what you're carrying and what's selected for the next craft.

**Files:**
- Create: `game/Source/NotAWeapon/NAWInventoryComponent.h/.cpp`
- Create: `game/Source/NotAWeapon/NAWJunkPickup.h/.cpp`
- Modify: `game/Source/NotAWeapon/NAWCharacter.h/.cpp` (inventory component, slot-toggle bindings, HUD tick)

**Interfaces:**
- Consumes: input actions `ToggleSlot1..6` (declared in Task 4's `DefaultInput.ini`).
- Produces: `UNAWInventoryComponent` with `bool Add(const FString& ItemName)`, `void ToggleSelect(int32 SlotIndex)`, `TArray<FString> SelectedNames() const`, `void ConsumeSelected()`, `FString DisplayString() const`; `ANAWCharacter::Inventory` (Task 9's craft spot reads `SelectedNames()` and calls `ConsumeSelected()` on success).

- [ ] **Step 1: Write the inventory component**

`game/Source/NotAWeapon/NAWInventoryComponent.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NAWInventoryComponent.generated.h"

// Six slots of catalog item names. Selection marks which slots feed the next
// craft. Names are opaque strings - the resolver owns their meaning.
UCLASS(ClassGroup = (NAW))
class NOTAWEAPON_API UNAWInventoryComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    // False when full - pickup stays in the world.
    bool Add(const FString& ItemName);

    void ToggleSelect(int32 SlotIndex);
    TArray<FString> SelectedNames() const;

    // Removes selected items (only called after a SUCCESSFUL craft - Task 9).
    void ConsumeSelected();

    // "1[x] rusty pipe  2[ ] jerrycan  3-  4-  5-  6-"
    FString DisplayString() const;

    static constexpr int32 MaxItems = 6;

private:
    TArray<FString> Items;
    TArray<bool> Selected;
};
```

`game/Source/NotAWeapon/NAWInventoryComponent.cpp`:

```cpp
#include "NAWInventoryComponent.h"

bool UNAWInventoryComponent::Add(const FString& ItemName)
{
    if (Items.Num() >= MaxItems)
    {
        return false;
    }
    Items.Add(ItemName);
    Selected.Add(false);
    return true;
}

void UNAWInventoryComponent::ToggleSelect(int32 SlotIndex)
{
    if (Selected.IsValidIndex(SlotIndex))
    {
        Selected[SlotIndex] = !Selected[SlotIndex];
    }
}

TArray<FString> UNAWInventoryComponent::SelectedNames() const
{
    TArray<FString> Names;
    for (int32 i = 0; i < Items.Num(); ++i)
    {
        if (Selected[i])
        {
            Names.Add(Items[i]);
        }
    }
    return Names;
}

void UNAWInventoryComponent::ConsumeSelected()
{
    for (int32 i = Items.Num() - 1; i >= 0; --i)
    {
        if (Selected[i])
        {
            Items.RemoveAt(i);
            Selected.RemoveAt(i);
        }
    }
}

FString UNAWInventoryComponent::DisplayString() const
{
    FString Out;
    for (int32 i = 0; i < MaxItems; ++i)
    {
        if (Items.IsValidIndex(i))
        {
            Out += FString::Printf(TEXT("%d[%s] %s  "), i + 1,
                                   Selected[i] ? TEXT("x") : TEXT(" "), *Items[i]);
        }
        else
        {
            Out += FString::Printf(TEXT("%d-  "), i + 1);
        }
    }
    return Out;
}
```

- [ ] **Step 2: Write the junk pickup**

`game/Source/NotAWeapon/NAWJunkPickup.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NAWJunkPickup.generated.h"

// Walk-over pickup carrying one catalog item name (set per-instance in the
// editor - must EXACTLY match a name from GET /api/catalog).
UCLASS()
class NOTAWEAPON_API ANAWJunkPickup : public AActor
{
    GENERATED_BODY()

public:
    ANAWJunkPickup();

    UPROPERTY(EditAnywhere, Category = "NAW")
    FString ItemName = TEXT("rusty pipe");

protected:
    virtual void NotifyActorBeginOverlap(AActor* OtherActor) override;
    virtual void Tick(float DeltaSeconds) override;

private:
    UPROPERTY(VisibleAnywhere)
    class UStaticMeshComponent* Mesh;
};
```

`game/Source/NotAWeapon/NAWJunkPickup.cpp`:

```cpp
#include "NAWJunkPickup.h"
#include "NAWCharacter.h"
#include "NAWInventoryComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "UObject/ConstructorHelpers.h"

ANAWJunkPickup::ANAWJunkPickup()
{
    PrimaryActorTick.bCanEverTick = true;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(
        TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    if (Sphere.Succeeded())
    {
        Mesh->SetStaticMesh(Sphere.Object);
    }
    Mesh->SetRelativeScale3D(FVector(0.35f));
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Mesh->SetCollisionResponseToAllChannels(ECR_Overlap);
    SetRootComponent(Mesh);
}

void ANAWJunkPickup::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    DrawDebugString(GetWorld(), GetActorLocation() + FVector(0, 0, 50), ItemName, nullptr,
                    FColor::White, 0.f, true);
}

void ANAWJunkPickup::NotifyActorBeginOverlap(AActor* OtherActor)
{
    Super::NotifyActorBeginOverlap(OtherActor);
    if (!HasAuthority())
    {
        return;
    }
    if (const ANAWCharacter* Character = Cast<ANAWCharacter>(OtherActor))
    {
        if (Character->Inventory->Add(ItemName))
        {
            Destroy();  // full inventory -> Add returns false, pickup stays
        }
    }
}
```

- [ ] **Step 3: Wire inventory, slot toggles, and HUD into the character**

`NAWCharacter.h` — add:

```cpp
public:
    UPROPERTY(VisibleAnywhere)
    class UNAWInventoryComponent* Inventory;

    virtual void Tick(float DeltaSeconds) override;

private:
    void ToggleSlot(int32 SlotIndex);
```

`NAWCharacter.cpp` — add include `#include "NAWInventoryComponent.h"` and `#include "Engine/Engine.h"`; in the constructor:

```cpp
    Inventory = CreateDefaultSubobject<UNAWInventoryComponent>(TEXT("Inventory"));
```

Slot bindings need a payload; declare the delegate above the class-member usage in `NAWCharacter.cpp` (file scope, before `SetupPlayerInputComponent`):

```cpp
DECLARE_DELEGATE_OneParam(FNAWSlotDelegate, int32);
```

In `SetupPlayerInputComponent`, append:

```cpp
    for (int32 Slot = 0; Slot < UNAWInventoryComponent::MaxItems; ++Slot)
    {
        PlayerInputComponent->BindAction<FNAWSlotDelegate>(
            *FString::Printf(TEXT("ToggleSlot%d"), Slot + 1), IE_Pressed, this,
            &ANAWCharacter::ToggleSlot, Slot);
    }
```

New functions:

```cpp
void ANAWCharacter::ToggleSlot(int32 SlotIndex)
{
    Inventory->ToggleSelect(SlotIndex);
}

void ANAWCharacter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (GEngine && IsPlayerControlled())
    {
        GEngine->AddOnScreenDebugMessage(1, 0.f, FColor::White, Inventory->DisplayString());
    }
}
```

- [ ] **Step 4: Build**

Same command as Task 4 Step 5. Expected: `Result: Succeeded`.

- [ ] **Step 5: Manual checklist**

First, get real catalog names (sidecar running):

```powershell
(Invoke-RestMethod http://127.0.0.1:8000/api/catalog).items | Select-Object -ExpandProperty name
```

In the editor: place 4–6 `NAWJunkPickup` actors in Blockout; set each one's `ItemName` (Details panel) to a name copied EXACTLY from the catalog output — include at least `cooler of raw steaks` and two combinable others (e.g. `bucket of wet cement`, `jerrycan`). Save the map.

- [ ] PIE: each pickup floats its item name; walking over one removes it and the HUD line top-left updates (`1[ ] jerrycan  2-  ...`).
- [ ] Keys 1–6 toggle `[ ]`/`[x]` per filled slot; toggling an empty slot does nothing.
- [ ] Fill all 6 slots (re-PIE and gather) — a 7th pickup refuses to collect and stays in the world.

- [ ] **Step 6: Commit**

```bash
git add game/Source/NotAWeapon/NAWInventoryComponent.h game/Source/NotAWeapon/NAWInventoryComponent.cpp game/Source/NotAWeapon/NAWJunkPickup.h game/Source/NotAWeapon/NAWJunkPickup.cpp game/Source/NotAWeapon/NAWCharacter.h game/Source/NotAWeapon/NAWCharacter.cpp game/Content/Maps/Blockout.umap
git commit -m "feat(game): six-slot inventory, junk pickups, slot-select HUD

Item names are opaque catalog strings; the resolver owns their meaning.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: Craft spot — the exposed-crafting moment

The spec's craft interaction: stand in the zone, select 1–4 items, press Interact, get locked heads-down while the resolver call runs (1–5s live — the latency IS the exposure window, diegetically correct), weapon spawns in hand. Failure never costs items and never leaves the player locked.

**Files:**
- Create: `game/Source/NotAWeapon/NAWCraftSpot.h/.cpp`
- Modify: `game/Source/NotAWeapon/NAWCharacter.h/.cpp` (Interact binding)

**Interfaces:**
- Consumes: `UNAWResolverSubsystem::Craft` + `FNAWCraftComplete` (Task 6); `UNAWInventoryComponent::SelectedNames/ConsumeSelected` (Task 8); `ANAWCharacter::EquipGadget` (Task 7); input action `Interact` (Task 4).
- Produces: `ANAWCraftSpot::TryCraft(ANAWCharacter* Crafter)`.

- [ ] **Step 1: Write the craft spot**

`game/Source/NotAWeapon/NAWCraftSpot.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NAWCraftSpot.generated.h"

// The exposed-crafting moment: locks the crafter heads-down for the round-trip.
// Items are consumed ONLY on success; any failure releases the player with
// "SIM UNRESPONSIVE" and their junk intact.
UCLASS()
class NOTAWEAPON_API ANAWCraftSpot : public AActor
{
    GENERATED_BODY()

public:
    ANAWCraftSpot();

    void TryCraft(class ANAWCharacter* Crafter);

    UPROPERTY(EditAnywhere, Category = "NAW")
    FString TierTarget = TEXT("RARE");

private:
    UPROPERTY(VisibleAnywhere)
    class UBoxComponent* Zone;

    UPROPERTY(VisibleAnywhere)
    class UStaticMeshComponent* Mesh;

    void SetHeadsDown(ANAWCharacter* Crafter, bool bDown);
    void Say(const FString& Text, const FColor& Color) const;

    bool bBusy = false;
};
```

`game/Source/NotAWeapon/NAWCraftSpot.cpp`:

```cpp
#include "NAWCraftSpot.h"
#include "NAWCharacter.h"
#include "NAWInventoryComponent.h"
#include "NAWResolverSubsystem.h"
#include "NotAWeapon.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "GameFramework/PlayerController.h"
#include "UObject/ConstructorHelpers.h"

ANAWCraftSpot::ANAWCraftSpot()
{
    PrimaryActorTick.bCanEverTick = false;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(
        TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded())
    {
        Mesh->SetStaticMesh(Cube.Object);
    }
    Mesh->SetRelativeScale3D(FVector(1.f, 1.f, 0.2f));
    SetRootComponent(Mesh);
    Zone = CreateDefaultSubobject<UBoxComponent>(TEXT("Zone"));
    Zone->SetupAttachment(Mesh);
    Zone->SetBoxExtent(FVector(200.f, 200.f, 150.f));
    Zone->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
}

void ANAWCraftSpot::Say(const FString& Text, const FColor& Color) const
{
    if (GEngine)
    {
        GEngine->AddOnScreenDebugMessage(2, 4.f, Color, Text);
    }
}

void ANAWCraftSpot::SetHeadsDown(ANAWCharacter* Crafter, bool bDown)
{
    if (APlayerController* Controller = Cast<APlayerController>(Crafter->GetController()))
    {
        Controller->SetIgnoreMoveInput(bDown);
        Controller->SetIgnoreLookInput(bDown);
    }
}

void ANAWCraftSpot::TryCraft(ANAWCharacter* Crafter)
{
    if (!HasAuthority() || !Crafter)
    {
        return;
    }
    if (bBusy)
    {
        Say(TEXT("crafting already in progress"), FColor::Yellow);
        return;
    }
    const TArray<FString> Items = Crafter->Inventory->SelectedNames();
    if (Items.Num() < 1 || Items.Num() > 4)
    {
        Say(TEXT("select 1-4 items (keys 1-6), then interact"), FColor::Yellow);
        return;
    }
    UNAWResolverSubsystem* Resolver =
        GetGameInstance()->GetSubsystem<UNAWResolverSubsystem>();
    bBusy = true;
    SetHeadsDown(Crafter, true);  // the exposure window - crafting while vulnerable
    Say(TEXT("crafting... (heads down)"), FColor::White);
    Resolver->Craft(Items, TierTarget, FNAWCraftComplete::CreateWeakLambda(this,
        [this, WeakCrafter = TWeakObjectPtr<ANAWCharacter>(Crafter)](
            bool bSuccess, const FNAWGadget& Gadget)
        {
            bBusy = false;
            ANAWCharacter* Crafter = WeakCrafter.Get();
            if (!Crafter)
            {
                return;
            }
            SetHeadsDown(Crafter, false);  // ALWAYS release, success or not
            if (!bSuccess)
            {
                // Spec: failure consumes nothing, locks nothing.
                Say(TEXT("SIM UNRESPONSIVE - junk kept"), FColor::Red);
                return;
            }
            Crafter->Inventory->ConsumeSelected();
            Crafter->EquipGadget(Gadget);
            Say(FString::Printf(TEXT("crafted: %s [%s]"), *Gadget.Name, *Gadget.Source),
                FColor::Green);
        }));
}
```

- [ ] **Step 2: Wire Interact into the character**

`NAWCharacter.h` — add:

```cpp
private:
    void Interact();
```

`NAWCharacter.cpp` — add `#include "NAWCraftSpot.h"`; in `SetupPlayerInputComponent`, append:

```cpp
    PlayerInputComponent->BindAction("Interact", IE_Pressed, this, &ANAWCharacter::Interact);
```

New function:

```cpp
void ANAWCharacter::Interact()
{
    TArray<AActor*> Overlapping;
    GetOverlappingActors(Overlapping, ANAWCraftSpot::StaticClass());
    if (Overlapping.Num() > 0)
    {
        Cast<ANAWCraftSpot>(Overlapping[0])->TryCraft(this);
    }
}
```

- [ ] **Step 3: Build**

Same command as Task 4 Step 5. Expected: `Result: Succeeded`.

- [ ] **Step 4: Manual checklist**

In the editor: place one `NAWCraftSpot` in Blockout, save the map. Sidecar running in **fallback mode** for the failure tests; the live test at the end is optional and only with the user present (their key, their spend).

- [ ] PIE: gather junk, stand on the spot, select 2 items (number keys), press E: movement and look lock, "crafting..." shows, then (fallback = near-instant) a weapon spawns, HUD shows the 2 items gone, message `crafted: <name> [fallback]`.
- [ ] Press E with 0 selected: yellow "select 1-4 items" message, no lock.
- [ ] **Stop the sidecar mid-run**, select items, press E: within ~5s the message `SIM UNRESPONSIVE - junk kept` appears in red, the player is released, HUD still shows all items. No crash, no permanent lock.
- [ ] Restart the sidecar, craft again WITHOUT restarting PIE: succeeds (the subsystem re-probed).
- [ ] **Mismatch drill (deferred from Task 6):** change one character of `NAW_CONTRACT_FINGERPRINT` in `Contract.h`, rebuild, PIE with sidecar up: red CONTRACT MISMATCH banner at startup, crafting refused. **Revert the constant and rebuild** before continuing.
- [ ] *(Optional, user-run, live spend approved for play sessions only)*: restart the sidecar WITHOUT `--fallback` and with `ANTHROPIC_API_KEY` set in that terminal; craft once; message shows `[llm]` and the gadget is model-composed. This is per-craft spend during a play session — the only approved live spend.

- [ ] **Step 5: Commit**

```bash
git add game/Source/NotAWeapon/NAWCraftSpot.h game/Source/NotAWeapon/NAWCraftSpot.cpp game/Source/NotAWeapon/NAWCharacter.h game/Source/NotAWeapon/NAWCharacter.cpp game/Content/Maps/Blockout.umap
git commit -m "feat(game): craft spot - heads-down exposed crafting, failure keeps junk

Items consumed only on success; any failure releases the player with
SIM UNRESPONSIVE and inventory intact.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 10: Run state — extract or die

Closes the loop: reach the extract volume with a weapon → its verbatim gadget JSON is appended to `game/extracted.jsonl` (the prototype's signature bank — knowledge persists, per the invariant) → run restarts. Die → nothing banked → run restarts. This task ends with the finish-line checklist for the whole prototype.

**Files:**
- Create: `game/Source/NotAWeapon/NAWExtractVolume.h/.cpp`
- Modify: `game/Source/NotAWeapon/NAWCharacter.h/.cpp` (health component + death)

**Interfaces:**
- Consumes: `UNAWHealthComponent` + `FNAWOnDead` (Task 7); `ANAWGameMode::RestartRun` (Task 4); `ANAWGadgetWeapon::Gadget.RawJson` (Tasks 5/7).
- Produces: `ANAWExtractVolume`; `ANAWCharacter::Die()`. Nothing downstream — this is the last task.

- [ ] **Step 1: Give the character health and death**

`NAWCharacter.h` — add:

```cpp
public:
    void Die();

protected:
    UPROPERTY(VisibleAnywhere)
    class UNAWHealthComponent* Health;

    virtual void FellOutOfWorld(const UDamageType& DmgType) override;
```

`NAWCharacter.cpp` — add includes `#include "NAWHealthComponent.h"`, `#include "NAWGameMode.h"`, `#include "GameFramework/CharacterMovementComponent.h"`, `#include "TimerManager.h"`, `#include "Kismet/GameplayStatics.h"`; in the constructor:

```cpp
    Health = CreateDefaultSubobject<UNAWHealthComponent>(TEXT("Health"));
```

Add a `BeginPlay` override (declare `virtual void BeginPlay() override;` in the header's `protected:` section) to bind death:

```cpp
void ANAWCharacter::BeginPlay()
{
    Super::BeginPlay();
    Health->OnDead.AddUObject(this, &ANAWCharacter::Die);
}
```

New functions:

```cpp
void ANAWCharacter::Die()
{
    if (!HasAuthority())
    {
        return;
    }
    if (EquippedWeapon)
    {
        EquippedWeapon->Destroy();  // die = the roll is lost, nothing banked
        EquippedWeapon = nullptr;
    }
    if (GEngine)
    {
        GEngine->AddOnScreenDebugMessage(3, 3.f, FColor::Red, TEXT("YOU DIED - nothing banked"));
    }
    DisableInput(Cast<APlayerController>(GetController()));
    GetCharacterMovement()->DisableMovement();
    FTimerHandle Handle;
    GetWorldTimerManager().SetTimer(Handle, FTimerDelegate::CreateWeakLambda(this, [this]()
    {
        if (ANAWGameMode* Mode = Cast<ANAWGameMode>(GetWorld()->GetAuthGameMode()))
        {
            Mode->RestartRun();
        }
    }), 3.f, false);
}

void ANAWCharacter::FellOutOfWorld(const UDamageType& DmgType)
{
    Die();  // instead of Super's silent Destroy - falling off the map is a death
}
```

- [ ] **Step 2: Write the extract volume**

`game/Source/NotAWeapon/NAWExtractVolume.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NAWExtractVolume.generated.h"

// Reach it with a weapon -> its verbatim gadget JSON is appended to
// game/extracted.jsonl (the prototype's bank: knowledge persists, power
// doesn't - the weapon actor itself is destroyed with the run).
UCLASS()
class NOTAWEAPON_API ANAWExtractVolume : public AActor
{
    GENERATED_BODY()

public:
    ANAWExtractVolume();

protected:
    virtual void NotifyActorBeginOverlap(AActor* OtherActor) override;

private:
    UPROPERTY(VisibleAnywhere)
    class UBoxComponent* Zone;

    bool bExtracting = false;
};
```

`game/Source/NotAWeapon/NAWExtractVolume.cpp`:

```cpp
#include "NAWExtractVolume.h"
#include "NAWCharacter.h"
#include "NAWGadgetWeapon.h"
#include "NAWGameMode.h"
#include "NotAWeapon.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "TimerManager.h"

ANAWExtractVolume::ANAWExtractVolume()
{
    PrimaryActorTick.bCanEverTick = false;
    Zone = CreateDefaultSubobject<UBoxComponent>(TEXT("Zone"));
    Zone->SetBoxExtent(FVector(200.f, 200.f, 200.f));
    Zone->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    SetRootComponent(Zone);
}

void ANAWExtractVolume::NotifyActorBeginOverlap(AActor* OtherActor)
{
    Super::NotifyActorBeginOverlap(OtherActor);
    if (!HasAuthority() || bExtracting)
    {
        return;
    }
    ANAWCharacter* Character = Cast<ANAWCharacter>(OtherActor);
    if (!Character)
    {
        return;
    }
    ANAWGadgetWeapon* Weapon = Character->GetEquippedWeapon();
    if (!Weapon)
    {
        if (GEngine)
        {
            GEngine->AddOnScreenDebugMessage(3, 3.f, FColor::Yellow,
                TEXT("nothing to extract - craft a weapon first"));
        }
        return;
    }
    bExtracting = true;
    // ProjectDir resolves to game/ - the bank sits next to the .uproject and
    // is git-ignored (Task 4).
    const FString BankPath = FPaths::ProjectDir() / TEXT("extracted.jsonl");
    FFileHelper::SaveStringToFile(Weapon->Gadget.RawJson + LINE_TERMINATOR, *BankPath,
                                  FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,
                                  &IFileManager::Get(), FILEWRITE_Append);
    UE_LOG(LogNAW, Log, TEXT("extracted '%s' -> %s"), *Weapon->Gadget.Name, *BankPath);
    if (GEngine)
    {
        GEngine->AddOnScreenDebugMessage(3, 3.f, FColor::Green,
            FString::Printf(TEXT("EXTRACTED: %s - banked"), *Weapon->Gadget.Name));
    }
    FTimerHandle Handle;
    GetWorldTimerManager().SetTimer(Handle, FTimerDelegate::CreateWeakLambda(this, [this]()
    {
        if (ANAWGameMode* Mode = Cast<ANAWGameMode>(GetWorld()->GetAuthGameMode()))
        {
            Mode->RestartRun();
        }
    }), 2.f, false);
}
```

`NAWCharacter.h` — the extract volume needs read access to the weapon; add:

```cpp
public:
    class ANAWGadgetWeapon* GetEquippedWeapon() const { return EquippedWeapon; }
```

- [ ] **Step 3: Build**

Same command as Task 4 Step 5. Expected: `Result: Succeeded`.

- [ ] **Step 4: Finish-line checklist — the whole loop**

In the editor: place one `NAWExtractVolume` at the far end of Blockout, save the map. Sidecar running (`run-sidecar.ps1 --fallback` — or live, user's call per Task 9's spend note).

The spec's finish line, in order:

- [ ] **Move** — walk, look, jump around Blockout.
- [ ] **Scavenge** — pick up junk; HUD tracks it.
- [ ] **Craft** — select items at the craft spot, heads-down window, weapon spawns.
- [ ] **The weapon visibly does its JSON** — fire it; effects match the stages (check a `LogNAW` line against what you saw).
- [ ] **Extract** — carry it into the extract volume: green EXTRACTED message, run restarts. Then:

```powershell
Get-Content C:\Users\rewfu\repos\not-a-weapon\game\extracted.jsonl -Tail 1 | python -c "import json,sys; g=json.load(sys.stdin); print(g['name'], g['tier'], g['source'])"
```

Expected: the extracted gadget's name/tier/source — valid JSON, one line per extraction.

- [ ] **Die** — craft something with a damaging EXPLODE/DAMAGE radius stage (re-roll until you get one; `DebugCraftThrown` combos usually explode), fire it at your own feet repeatedly: health popups, then "YOU DIED - nothing banked", 3s, run restarts. Weapon gone, nothing appended to `extracted.jsonl` (verify line count unchanged: `(Get-Content C:\Users\rewfu\repos\not-a-weapon\game\extracted.jsonl | Measure-Object -Line).Lines`).
- [ ] **Loop** — after both endings the level reloads cleanly: junk pickups are back, inventory empty, no weapon, no crash.
- [ ] `git status --porcelain game/` — `extracted.jsonl` does NOT appear (git-ignored).

- [ ] **Step 5: Final suite check (Python untouched since Task 3, but verify)**

```powershell
$env:PYTHONUTF8 = "1"; python -m pytest -q
```

Expected: **355 passed** (348 baseline + 1 Task 1 + 6 Task 3). Zero failures.

- [ ] **Step 6: Commit**

```bash
git add game/Source/NotAWeapon/NAWExtractVolume.h game/Source/NotAWeapon/NAWExtractVolume.cpp game/Source/NotAWeapon/NAWCharacter.h game/Source/NotAWeapon/NAWCharacter.cpp game/Content/Maps/Blockout.umap
git commit -m "feat(game): extract volume + death - the loop closes

Extract banks the verbatim gadget JSON to extracted.jsonl; death banks
nothing. Knowledge persists, power never does.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Execution notes

- **Task order is strict**: 1→2→3 (Python, TDD) then 4→5→6→7→8→9→10 (Unreal, manual checklists). Every Unreal task needs Task 4's project; 6 needs 5; 7 needs 6 (debug commands); 9 needs 6+7+8; 10 needs 7.
- **Manual checklist steps require the user** (editor interaction, PIE). An implementing agent writes the code, builds, and hands the checklist to the user; the task is not complete until the user confirms the checklist passed.
- **The optional live-craft check (Task 9) and any live crafting in Task 10 are the user's spend decision in the moment** — agents never start the sidecar in live mode.



