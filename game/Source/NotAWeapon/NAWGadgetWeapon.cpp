#include "NAWGadgetWeapon.h"
#include "NAWEffectExecutor.h"
#include "NAWGadgetPlaced.h"
#include "NAWGadgetProjectile.h"
#include "NotAWeapon.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

ANAWGadgetWeapon::ANAWGadgetWeapon()
{
    PrimaryActorTick.bCanEverTick = false;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(
        TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded())
    {
        Mesh->SetStaticMesh(Cube.Object);
    }
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetRelativeScale3D(FVector(0.4f, 0.15f, 0.15f));
    SetRootComponent(Mesh);
}

void ANAWGadgetWeapon::Init(const FNAWGadget& InGadget)
{
    Gadget = InGadget;
    if (UMaterialInstanceDynamic* Tint = Mesh->CreateAndSetMaterialInstanceDynamic(0))
    {
        Tint->SetVectorParameterValue(TEXT("Color"),
                                      FLinearColor(FColor::FromHex(Gadget.Color)));
    }
    AnnounceUnrenderedTriggers();
}

void ANAWGadgetWeapon::Fire()
{
    if (!GetOwner() || !GetOwner()->HasAuthority())
    {
        return;
    }
    switch (Gadget.Delivery)
    {
    case ENAWDelivery::HITSCAN:
    case ENAWDelivery::BEAM:
    case ENAWDelivery::SPRAY:
        FireHitscan();
        break;
    case ENAWDelivery::PROJECTILE:
        FireProjectile(false);
        break;
    case ENAWDelivery::LOBBED:
    case ENAWDelivery::THROWN:
        FireProjectile(true);
        break;
    case ENAWDelivery::PLACED:
        FirePlaced();
        break;
    case ENAWDelivery::SWING:
    case ENAWDelivery::THRUST:
    case ENAWDelivery::SLAM:
    case ENAWDelivery::WHIP:
        FireMelee();
        break;
    case ENAWDelivery::GUARD:
    case ENAWDelivery::SELF:
    case ENAWDelivery::DASH:
        FireSelf();
        break;
    }
}

FVector ANAWGadgetWeapon::MuzzleLocation() const
{
    return GetActorLocation() + AimDirection() * 60.f;
}

FVector ANAWGadgetWeapon::AimDirection() const
{
    const APawn* Pawn = Cast<APawn>(GetOwner());
    return Pawn ? Pawn->GetControlRotation().Vector() : GetActorForwardVector();
}

void ANAWGadgetWeapon::FireHitscan()
{
    const FVector Start = MuzzleLocation();
    const FVector End = Start + AimDirection() * 100.f * 100.f;  // 100 m
    FHitResult Hit;
    FCollisionQueryParams Params;
    Params.AddIgnoredActor(GetOwner());
    Params.AddIgnoredActor(this);
    GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params);
    DrawDebugLine(GetWorld(), Start, Hit.bBlockingHit ? Hit.Location : End,
                  FColor::FromHex(Gadget.Color), false, 0.3f, 0, 2.f);
    FNAWEffectContext Context;
    Context.World = GetWorld();
    Context.Wielder = GetOwner();
    Context.Struck = Hit.GetActor();
    Context.Location = Hit.bBlockingHit ? Hit.Location : End;
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_USE))
    {
        Context.Location = Start;
        NAWEffects::ExecuteStage(Context, Stage);
    }
    if (Hit.bBlockingHit)
    {
        Context.Location = Hit.Location;
        for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_HIT))
        {
            NAWEffects::ExecuteStage(Context, Stage);
        }
        for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_IMPACT))
        {
            NAWEffects::ExecuteStage(Context, Stage);
        }
    }
}

void ANAWGadgetWeapon::FireProjectile(bool bArc)
{
    FActorSpawnParameters Params;
    Params.Owner = GetOwner();
    Params.SpawnCollisionHandlingOverride =
        ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    ANAWGadgetProjectile* Projectile = GetWorld()->SpawnActor<ANAWGadgetProjectile>(
        MuzzleLocation(), AimDirection().Rotation(), Params);
    if (Projectile)
    {
        Projectile->Init(Gadget, GetOwner(), bArc);
    }
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_USE))
    {
        FNAWEffectContext Context;
        Context.World = GetWorld();
        Context.Wielder = GetOwner();
        Context.Location = MuzzleLocation();
        NAWEffects::ExecuteStage(Context, Stage);
    }
}

void ANAWGadgetWeapon::FirePlaced()
{
    FActorSpawnParameters Params;
    Params.Owner = GetOwner();
    Params.SpawnCollisionHandlingOverride =
        ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    const FVector Spot = GetOwner()->GetActorLocation() + AimDirection() * 150.f;
    ANAWGadgetPlaced* Placed = GetWorld()->SpawnActor<ANAWGadgetPlaced>(
        Spot, FRotator::ZeroRotator, Params);
    if (Placed)
    {
        Placed->Init(Gadget, GetOwner());
    }
}

void ANAWGadgetWeapon::FireMelee()
{
    // Blockout melee: a short forward sphere sweep.
    const FVector Start = GetOwner()->GetActorLocation();
    const FVector End = Start + AimDirection() * 250.f;
    TArray<FHitResult> Hits;
    FCollisionQueryParams Params;
    Params.AddIgnoredActor(GetOwner());
    Params.AddIgnoredActor(this);
    GetWorld()->SweepMultiByChannel(Hits, Start, End, FQuat::Identity, ECC_Pawn,
                                    FCollisionShape::MakeSphere(80.f), Params);
    DrawDebugCapsule(GetWorld(), (Start + End) / 2, 125.f, 80.f,
                     AimDirection().ToOrientationQuat(), FColor::FromHex(Gadget.Color),
                     false, 0.3f);
    FNAWEffectContext Context;
    Context.World = GetWorld();
    Context.Wielder = GetOwner();
    Context.Location = End;
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_USE))
    {
        NAWEffects::ExecuteStage(Context, Stage);
    }
    for (const FHitResult& Hit : Hits)
    {
        Context.Struck = Hit.GetActor();
        Context.Location = Hit.ImpactPoint;
        for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_HIT))
        {
            NAWEffects::ExecuteStage(Context, Stage);
        }
        for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_IMPACT))
        {
            NAWEffects::ExecuteStage(Context, Stage);
        }
    }
}

void ANAWGadgetWeapon::FireSelf()
{
    FNAWEffectContext Context;
    Context.World = GetWorld();
    Context.Wielder = GetOwner();
    Context.Location = GetOwner()->GetActorLocation();
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_USE))
    {
        NAWEffects::ExecuteStage(Context, Stage);
    }
    // GUARD's ON_BLOCK has no block input in the blockout - fire it on use so
    // the stage is at least visible, and say so.
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_BLOCK))
    {
        NAWEffects::ExecuteStage(Context, Stage);
        DrawDebugString(GetWorld(), Context.Location + FVector(0, 0, 200),
                        TEXT("ON_BLOCK fired on use (no block input in blockout)"), nullptr,
                        FColor::Yellow, 3.f, true);
    }
}

void ANAWGadgetWeapon::AnnounceUnrenderedTriggers()
{
    for (const ENAWTrigger Trigger : {ENAWTrigger::ON_KILL, ENAWTrigger::ON_EXPIRE})
    {
        if (Gadget.HasTrigger(Trigger))
        {
            const FString Name = StaticEnum<ENAWTrigger>()->GetNameStringByValue(
                static_cast<int64>(Trigger));
            UE_LOG(LogNAW, Log, TEXT("gadget '%s': stage armed: %s (not rendered in blockout)"),
                   *Gadget.Name, *Name);
            DrawDebugString(GetWorld(), GetActorLocation() + FVector(0, 0, 250),
                            FString::Printf(TEXT("stage armed: %s (not rendered in blockout)"),
                                            *Name),
                            nullptr, FColor::Yellow, 4.f, true);
        }
    }
}
