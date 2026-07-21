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
