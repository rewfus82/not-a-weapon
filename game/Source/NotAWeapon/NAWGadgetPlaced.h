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
