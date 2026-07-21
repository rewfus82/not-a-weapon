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
