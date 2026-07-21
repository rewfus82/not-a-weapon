#include "NAWJunkPickup.h"
#include "NAWCharacter.h"
#include "NAWInventoryComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "UObject/ConstructorHelpers.h"

ANAWJunkPickup::ANAWJunkPickup()
{
    PrimaryActorTick.bCanEverTick = true;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(
        TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    if (Sphere.Succeeded())
    {
        Mesh->SetStaticMesh(Sphere.Object);
    }
    Mesh->SetRelativeScale3D(FVector(0.35f));
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Mesh->SetCollisionResponseToAllChannels(ECR_Overlap);
    SetRootComponent(Mesh);
}

void ANAWJunkPickup::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    DrawDebugString(GetWorld(), GetActorLocation() + FVector(0, 0, 50), ItemName, nullptr,
                    FColor::White, 0.f, true);
}

void ANAWJunkPickup::NotifyActorBeginOverlap(AActor* OtherActor)
{
    Super::NotifyActorBeginOverlap(OtherActor);
    if (!HasAuthority())
    {
        return;
    }
    if (const ANAWCharacter* Character = Cast<ANAWCharacter>(OtherActor))
    {
        if (Character->Inventory->Add(ItemName))
        {
            Destroy();  // full inventory -> Add returns false, pickup stays
        }
    }
}
