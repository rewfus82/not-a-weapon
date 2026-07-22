#include "NAWCraftSpot.h"
#include "NAWCharacter.h"
#include "NAWInventoryComponent.h"
#include "NAWResolverSubsystem.h"
#include "NotAWeapon.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "GameFramework/PlayerController.h"
#include "UObject/ConstructorHelpers.h"

ANAWCraftSpot::ANAWCraftSpot()
{
    PrimaryActorTick.bCanEverTick = false;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(
        TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded())
    {
        Mesh->SetStaticMesh(Cube.Object);
    }
    Mesh->SetRelativeScale3D(FVector(1.f, 1.f, 0.2f));
    SetRootComponent(Mesh);
    Zone = CreateDefaultSubobject<UBoxComponent>(TEXT("Zone"));
    Zone->SetupAttachment(Mesh);
    Zone->SetBoxExtent(FVector(200.f, 200.f, 150.f));
    Zone->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
}

void ANAWCraftSpot::Say(const FString& Text, const FColor& Color) const
{
    if (GEngine)
    {
        GEngine->AddOnScreenDebugMessage(2, 4.f, Color, Text);
    }
}

void ANAWCraftSpot::SetHeadsDown(ANAWCharacter* Crafter, bool bDown)
{
    if (APlayerController* Controller = Cast<APlayerController>(Crafter->GetController()))
    {
        Controller->SetIgnoreMoveInput(bDown);
        Controller->SetIgnoreLookInput(bDown);
    }
}

void ANAWCraftSpot::TryCraft(ANAWCharacter* Crafter)
{
    if (!HasAuthority() || !Crafter)
    {
        return;
    }
    if (bBusy)
    {
        Say(TEXT("crafting already in progress"), FColor::Yellow);
        return;
    }
    const TArray<FString> Items = Crafter->Inventory->SelectedNames();
    if (Items.Num() < 1 || Items.Num() > 4)
    {
        Say(TEXT("select 1-4 items (keys 1-6), then interact"), FColor::Yellow);
        return;
    }
    UNAWResolverSubsystem* Resolver =
        GetGameInstance()->GetSubsystem<UNAWResolverSubsystem>();
    bBusy = true;
    SetHeadsDown(Crafter, true);  // the exposure window - crafting while vulnerable
    Say(TEXT("crafting... (heads down)"), FColor::White);
    Resolver->Craft(Items, TierTarget, FNAWCraftComplete::CreateWeakLambda(this,
        [this, WeakCrafter = TWeakObjectPtr<ANAWCharacter>(Crafter)](
            bool bSuccess, const FNAWGadget& Gadget)
        {
            bBusy = false;
            ANAWCharacter* Crafter = WeakCrafter.Get();
            if (!Crafter)
            {
                return;
            }
            SetHeadsDown(Crafter, false);  // ALWAYS release, success or not
            if (!bSuccess)
            {
                // Spec: failure consumes nothing, locks nothing.
                Say(TEXT("SIM UNRESPONSIVE - junk kept"), FColor::Red);
                return;
            }
            Crafter->Inventory->ConsumeSelected();
            Crafter->EquipGadget(Gadget);
            Say(FString::Printf(TEXT("crafted: %s [%s]"), *Gadget.Name, *Gadget.Source),
                FColor::Green);
        }));
}
