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
