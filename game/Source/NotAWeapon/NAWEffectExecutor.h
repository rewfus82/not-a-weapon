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
