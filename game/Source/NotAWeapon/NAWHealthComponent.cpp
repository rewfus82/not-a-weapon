#include "NAWHealthComponent.h"
#include "NotAWeapon.h"
#include "DrawDebugHelpers.h"
#include "GameFramework/Actor.h"

UNAWHealthComponent::UNAWHealthComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UNAWHealthComponent::BeginPlay()
{
    Super::BeginPlay();
    Health = MaxHealth;
    if (AActor* Owner = GetOwner())
    {
        Owner->OnTakeAnyDamage.AddDynamic(this, &UNAWHealthComponent::HandleTakeAnyDamage);
    }
}

void UNAWHealthComponent::HandleTakeAnyDamage(AActor*, float DamageAmount, const UDamageType*,
                                              AController*, AActor* DamageCauser)
{
    Damage(DamageAmount, DamageCauser);
}

void UNAWHealthComponent::Damage(float Amount, AActor* /*Instigator*/)
{
    if (IsDead() || Amount <= 0.f)
    {
        return;
    }
    const float Soaked = FMath::Min(Shield, Amount);
    Shield -= Soaked;
    const float ToHealth = Amount - Soaked;
    Health = FMath::Max(0.f, Health - ToHealth);
    Popup(FString::Printf(TEXT("-%.0f%s"), Amount, Soaked > 0.f ? TEXT(" (shielded)") : TEXT("")),
          FColor::Red);
    if (Health <= 0.f)
    {
        OnDead.Broadcast();
    }
}

void UNAWHealthComponent::Heal(float Amount)
{
    if (IsDead() || Amount <= 0.f)
    {
        return;
    }
    Health = FMath::Min(MaxHealth, Health + Amount);
    Popup(FString::Printf(TEXT("+%.0f"), Amount), FColor::Green);
}

void UNAWHealthComponent::AddShield(float Amount)
{
    if (IsDead() || Amount <= 0.f)
    {
        return;
    }
    Shield += Amount;
    Popup(FString::Printf(TEXT("shield +%.0f"), Amount), FColor::Cyan);
}

void UNAWHealthComponent::Popup(const FString& Text, const FColor& Color) const
{
    if (const AActor* Owner = GetOwner())
    {
        DrawDebugString(Owner->GetWorld(), Owner->GetActorLocation() + FVector(0, 0, 100),
                        Text, nullptr, Color, 1.5f, true);
    }
}
