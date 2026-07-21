#include "NAWGadgetPlaced.h"
#include "NAWEffectExecutor.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

ANAWGadgetPlaced::ANAWGadgetPlaced()
{
    PrimaryActorTick.bCanEverTick = false;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(
        TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded())
    {
        Mesh->SetStaticMesh(Cube.Object);
    }
    Mesh->SetRelativeScale3D(FVector(0.5f, 0.5f, 0.3f));
    SetRootComponent(Mesh);
    Proximity = CreateDefaultSubobject<USphereComponent>(TEXT("Proximity"));
    Proximity->SetupAttachment(Mesh);
    Proximity->SetSphereRadius(200.f);
    Proximity->SetCollisionObjectType(ECC_WorldDynamic);
    Proximity->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    InitialLifeSpan = 60.f;
}

void ANAWGadgetPlaced::Init(const FNAWGadget& InGadget, AActor* InWielder)
{
    Gadget = InGadget;
    Wielder = InWielder;
    if (UMaterialInstanceDynamic* Tint = Mesh->CreateAndSetMaterialInstanceDynamic(0))
    {
        Tint->SetVectorParameterValue(TEXT("Color"),
                                      FLinearColor(FColor::FromHex(Gadget.Color)));
    }
    // Arm delay so the wielder can step away without triggering it on themself.
    FTimerHandle Handle;
    GetWorldTimerManager().SetTimer(Handle, this, &ANAWGadgetPlaced::Arm, 1.5f, false);
}

void ANAWGadgetPlaced::Arm()
{
    bArmed = true;
    Proximity->OnComponentBeginOverlap.AddDynamic(this, &ANAWGadgetPlaced::OnProximity);
    DrawDebugString(GetWorld(), GetActorLocation() + FVector(0, 0, 80), TEXT("armed"), nullptr,
                    FColor::Orange, 2.f, true);
}

void ANAWGadgetPlaced::OnProximity(UPrimitiveComponent*, AActor* OtherActor,
                                   UPrimitiveComponent*, int32, bool, const FHitResult&)
{
    if (!bArmed || !OtherActor || OtherActor == this)
    {
        return;
    }
    FNAWEffectContext Context;
    Context.World = GetWorld();
    Context.Wielder = Wielder;
    Context.Struck = OtherActor;
    Context.Location = GetActorLocation();
    for (const FNAWStage& Stage : Gadget.StagesFor(ENAWTrigger::ON_TRIGGER))
    {
        NAWEffects::ExecuteStage(Context, Stage);
    }
    Destroy();
}
