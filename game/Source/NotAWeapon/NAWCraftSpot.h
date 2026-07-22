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
