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
