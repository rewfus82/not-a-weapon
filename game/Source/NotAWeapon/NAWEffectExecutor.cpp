#include "NAWEffectExecutor.h"
#include "NAWHealthComponent.h"
#include "NotAWeapon.h"
#include "DrawDebugHelpers.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "Engine/OverlapResult.h"

namespace
{
constexpr float UNITS_PER_METER = 100.f;  // contract radii/amount distances are meters

TArray<AActor*> GatherTargets(const FNAWEffectContext& Context, const FNAWEffect& Effect)
{
    TArray<AActor*> Targets;
    if (Effect.Target == ENAWTarget::SELF)
    {
        if (Context.Wielder)
        {
            Targets.Add(Context.Wielder);
        }
        return Targets;
    }
    if (Effect.Radius > 0.f)
    {
        TArray<FOverlapResult> Overlaps;
        FCollisionShape Sphere = FCollisionShape::MakeSphere(Effect.Radius * UNITS_PER_METER);
        Context.World->OverlapMultiByChannel(Overlaps, Context.Location, FQuat::Identity,
                                             ECC_Pawn, Sphere);
        for (const FOverlapResult& Overlap : Overlaps)
        {
            Targets.AddUnique(Overlap.GetActor());
        }
        DrawDebugSphere(Context.World, Context.Location, Effect.Radius * UNITS_PER_METER,
                        16, FColor::Orange, false, 1.0f);
    }
    else if (Context.Struck)
    {
        Targets.Add(Context.Struck);
    }
    return Targets;
}

void FloatText(const FNAWEffectContext& Context, const FString& Text, const FColor& Color)
{
    DrawDebugString(Context.World, Context.Location + FVector(0, 0, 150), Text, nullptr,
                    Color, 2.5f, true);
}

void ScaleSpeed(AActor* Target, float Multiplier, float Duration)
{
    ACharacter* Character = Cast<ACharacter>(Target);
    if (!Character)
    {
        return;
    }
    UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
    const float Normal = 600.f;  // engine default MaxWalkSpeed; restore to this, not to current
    Movement->MaxWalkSpeed = Normal * Multiplier;
    FTimerHandle Handle;
    Character->GetWorldTimerManager().SetTimer(Handle,
        FTimerDelegate::CreateWeakLambda(Character, [Movement]()
        {
            Movement->MaxWalkSpeed = 600.f;
        }),
        FMath::Max(Duration, 0.5f), false);
}
}  // namespace

void NAWEffects::ExecuteStage(const FNAWEffectContext& Context, const FNAWStage& Stage)
{
    if (!Context.World)
    {
        return;
    }
    for (const FNAWEffect& Effect : Stage.Effects)
    {
        const TArray<AActor*> Targets = GatherTargets(Context, Effect);
        const FString KindName = StaticEnum<ENAWEffectKind>()->GetNameStringByValue(
            static_cast<int64>(Effect.Kind));
        switch (Effect.Kind)
        {
        case ENAWEffectKind::DAMAGE:
        case ENAWEffectKind::BURN:
        case ENAWEffectKind::PIERCE:
        case ENAWEffectKind::CHAIN:
        case ENAWEffectKind::EXPLODE:
            for (AActor* Target : Targets)
            {
                UGameplayStatics::ApplyDamage(Target, Effect.Amount, nullptr, Context.Wielder,
                                              nullptr);
            }
            if (Effect.Kind == ENAWEffectKind::EXPLODE)
            {
                DrawDebugSphere(Context.World, Context.Location,
                                FMath::Max(Effect.Radius, 1.f) * UNITS_PER_METER, 24,
                                FColor::Red, false, 1.5f);
            }
            break;
        case ENAWEffectKind::KNOCKBACK:
        case ENAWEffectKind::LAUNCH:
            for (AActor* Target : Targets)
            {
                if (ACharacter* Character = Cast<ACharacter>(Target))
                {
                    FVector Away = (Target->GetActorLocation() - Context.Location).GetSafeNormal();
                    if (Effect.Kind == ENAWEffectKind::LAUNCH)
                    {
                        Away = FVector::UpVector;
                    }
                    Character->LaunchCharacter(Away * Effect.Amount * 50.f, true, true);
                }
            }
            break;
        case ENAWEffectKind::STAGGER:
        case ENAWEffectKind::SNARE:
        case ENAWEffectKind::FREEZE:
            for (AActor* Target : Targets)
            {
                ScaleSpeed(Target, 0.f, Effect.Duration);
            }
            FloatText(Context, KindName, FColor::Blue);
            break;
        case ENAWEffectKind::SLOW:
            for (AActor* Target : Targets)
            {
                ScaleSpeed(Target, 0.4f, Effect.Duration);
            }
            FloatText(Context, KindName, FColor::Blue);
            break;
        case ENAWEffectKind::SPEED:
            for (AActor* Target : Targets)
            {
                ScaleSpeed(Target, 1.f + Effect.Amount / 100.f, Effect.Duration);
            }
            FloatText(Context, KindName, FColor::Green);
            break;
        case ENAWEffectKind::HEAL:
            for (AActor* Target : Targets)
            {
                if (UNAWHealthComponent* HealthComp =
                        Target->FindComponentByClass<UNAWHealthComponent>())
                {
                    HealthComp->Heal(Effect.Amount);
                }
            }
            break;
        case ENAWEffectKind::SHIELD:
            for (AActor* Target : Targets)
            {
                if (UNAWHealthComponent* HealthComp =
                        Target->FindComponentByClass<UNAWHealthComponent>())
                {
                    HealthComp->AddShield(Effect.Amount);
                }
            }
            break;
        case ENAWEffectKind::SUMMON:
        case ENAWEffectKind::LURE:
            // No bots in the blockout - announce so the stage is visibly not lost.
            FloatText(Context,
                      FString::Printf(TEXT("%s x%d (needs bots - announced only)"), *KindName,
                                      FMath::Max(Effect.Count, 1)),
                      FColor::Yellow);
            break;
        }
        UE_LOG(LogNAW, Log, TEXT("effect %s amount=%.1f targets=%d"), *KindName, Effect.Amount,
               Targets.Num());
    }
}
