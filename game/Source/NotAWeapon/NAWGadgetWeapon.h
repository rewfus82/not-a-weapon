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
