#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NAWHealthComponent.generated.h"

DECLARE_MULTICAST_DELEGATE(FNAWOnDead);

UCLASS(ClassGroup = (NAW), meta = (BlueprintSpawnableComponent))
class NOTAWEAPON_API UNAWHealthComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UNAWHealthComponent();

    void Damage(float Amount, AActor* Instigator);
    void Heal(float Amount);
    void AddShield(float Amount);
    bool IsDead() const { return Health <= 0.f; }

    FNAWOnDead OnDead;

    UPROPERTY(EditAnywhere)
    float MaxHealth = 100.f;

protected:
    virtual void BeginPlay() override;

private:
    UFUNCTION()
    void HandleTakeAnyDamage(AActor* DamagedActor, float Damage, const UDamageType* DamageType,
                             AController* InstigatedBy, AActor* DamageCauser);
    void Popup(const FString& Text, const FColor& Color) const;

    float Health = 100.f;
    float Shield = 0.f;
};
