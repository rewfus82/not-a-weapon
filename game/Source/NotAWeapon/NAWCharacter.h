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

    void EquipGadget(const struct FNAWGadget& Gadget);

    // Console commands (` then type name) - dev-only craft without pickups.
    // These DO hit the live resolver when the sidecar has a key.
    UFUNCTION(Exec)
    void DebugCraftPlaced();

    UFUNCTION(Exec)
    void DebugCraftThrown();

    UPROPERTY(VisibleAnywhere)
    class UNAWInventoryComponent* Inventory;

    virtual void Tick(float DeltaSeconds) override;

protected:
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

    UPROPERTY(VisibleAnywhere)
    class UCameraComponent* Camera;

    UPROPERTY()
    class ANAWGadgetWeapon* EquippedWeapon = nullptr;

private:
    void MoveForward(float Value);
    void MoveRight(float Value);
    void Fire();
    void DebugCraft(const TArray<FString>& Items, const FString& TierTarget);
    void ToggleSlot(int32 SlotIndex);
    void Interact();
};
