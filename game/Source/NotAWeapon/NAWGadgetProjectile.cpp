#include "NAWGadgetProjectile.h"
#include "NAWEffectExecutor.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

ANAWGadgetProjectile::ANAWGadgetProjectile()
{
    PrimaryActorTick.bCanEverTick = false;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(
        TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    if (Sphere.Succeeded())
    {
        Mesh->SetStaticMesh(Sphere.Object);
    }
    Mesh->SetRelativeScale3D(FVector(0.2f));
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Mesh->SetCollisionResponseToAllChannels(ECR_Block);
    Mesh->SetNotifyRigidBodyCollision(true);
    SetRootComponent(Mesh);
    Movement = CreateDefaultSubobject<UProjectileMovementComponent>(TEXT("Movement"));
    Movement->InitialSpeed = 2500.f;
    Movement->MaxSpeed = 2500.f;
    InitialLifeSpan = 8.f;
}

void ANAWGadgetProjectile::Init(const FNAWGadget& InGadget, AActor* InWielder, bool bArc)
{
    Gadget = InGadget;
    Wielder = InWielder;
    Movement->ProjectileGravityScale = bArc ? 1.f : 0.f;
    if (bArc)
    {
        Movement->InitialSpeed = 1500.f;
        Movement->Velocity = GetActorForwardVector() * 1500.f + FVector(0, 0, 300.f);
    }
    if (UMaterialInstanceDynamic* Tint = Mesh->CreateAndSetMaterialInstanceDynamic(0))
    {
        Tint->SetVectorParameterValue(TEXT("Color"),
                                      FLinearColor(FColor::FromHex(Gadget.Color)));
    }
    Mesh->OnComponentHit.AddDynamic(this, &ANAWGadgetProjectile::OnHit);
    if (Wielder)
    {
        Mesh->IgnoreActorWhenMoving(Wielder, true);
    }
}

void ANAWGadgetProjectile::OnHit(UPrimitiveComponent*, AActor* OtherActor, UPrimitiveComponent*,
                                 FVector, const FHitResult& Hit)
{
    FNAWEffectContext Context;
    Context.World = GetWorld();
    Context.Wielder = Wielder;
    Context.Struck = OtherActor;
    Context.Location = Hit.ImpactPoint;
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_IMPACT))
    {
        NAWEffects::ExecuteStage(Context, Stage);
    }
    if (OtherActor && OtherActor != Wielder)
    {
        for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_HIT))
        {
            NAWEffects::ExecuteStage(Context, Stage);
        }
    }
    Destroy();
}
