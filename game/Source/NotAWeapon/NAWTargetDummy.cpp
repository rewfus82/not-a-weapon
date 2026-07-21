#include "NAWTargetDummy.h"
#include "NAWHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "UObject/ConstructorHelpers.h"

ANAWTargetDummy::ANAWTargetDummy()
{
    PrimaryActorTick.bCanEverTick = false;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(
        TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    if (Cylinder.Succeeded())
    {
        Mesh->SetStaticMesh(Cylinder.Object);
    }
    Mesh->SetCollisionObjectType(ECC_Pawn);  // so radius effects find it
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    SetRootComponent(Mesh);
    Health = CreateDefaultSubobject<UNAWHealthComponent>(TEXT("Health"));
    Health->OnDead.AddUObject(this, &ANAWTargetDummy::HandleDead);
}

void ANAWTargetDummy::HandleDead()
{
    Destroy();
}
