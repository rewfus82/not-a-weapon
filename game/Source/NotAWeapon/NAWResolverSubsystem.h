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
