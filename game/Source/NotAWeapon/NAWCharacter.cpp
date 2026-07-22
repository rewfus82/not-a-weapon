#include "NAWCharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Engine/Engine.h"
#include "NAWCraftSpot.h"
#include "NAWGadgetWeapon.h"
#include "NAWInventoryComponent.h"
#include "NAWResolverSubsystem.h"

DECLARE_DELEGATE_OneParam(FNAWSlotDelegate, int32);

ANAWCharacter::ANAWCharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
    Camera->SetupAttachment(GetCapsuleComponent());
    Camera->SetRelativeLocation(FVector(0.f, 0.f, 64.f));
    Camera->bUsePawnControlRotation = true;
    Inventory = CreateDefaultSubobject<UNAWInventoryComponent>(TEXT("Inventory"));
}

void ANAWCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    PlayerInputComponent->BindAxis("MoveForward", this, &ANAWCharacter::MoveForward);
    PlayerInputComponent->BindAxis("MoveRight", this, &ANAWCharacter::MoveRight);
    PlayerInputComponent->BindAxis("Turn", this, &APawn::AddControllerYawInput);
    PlayerInputComponent->BindAxis("LookUp", this, &APawn::AddControllerPitchInput);
    PlayerInputComponent->BindAction("Jump", IE_Pressed, this, &ACharacter::Jump);
    PlayerInputComponent->BindAction("Jump", IE_Released, this, &ACharacter::StopJumping);
    PlayerInputComponent->BindAction("Fire", IE_Pressed, this, &ANAWCharacter::Fire);
    PlayerInputComponent->BindAction("Interact", IE_Pressed, this, &ANAWCharacter::Interact);

    for (int32 Slot = 0; Slot < UNAWInventoryComponent::MaxItems; ++Slot)
    {
        PlayerInputComponent->BindAction<FNAWSlotDelegate>(
            *FString::Printf(TEXT("ToggleSlot%d"), Slot + 1), IE_Pressed, this,
            &ANAWCharacter::ToggleSlot, Slot);
    }
}

void ANAWCharacter::MoveForward(float Value)
{
    if (Value != 0.f)
    {
        AddMovementInput(GetActorForwardVector(), Value);
    }
}

void ANAWCharacter::MoveRight(float Value)
{
    if (Value != 0.f)
    {
        AddMovementInput(GetActorRightVector(), Value);
    }
}

void ANAWCharacter::EquipGadget(const FNAWGadget& Gadget)
{
    if (!HasAuthority())
    {
        return;
    }
    if (EquippedWeapon)
    {
        EquippedWeapon->Destroy();
        EquippedWeapon = nullptr;
    }
    FActorSpawnParameters Params;
    Params.Owner = this;
    EquippedWeapon = GetWorld()->SpawnActor<ANAWGadgetWeapon>(Params);
    if (EquippedWeapon)
    {
        EquippedWeapon->Init(Gadget);
        EquippedWeapon->AttachToComponent(Camera,
            FAttachmentTransformRules::SnapToTargetNotIncludingScale);
        EquippedWeapon->SetActorRelativeLocation(FVector(60.f, 25.f, -20.f));
    }
}

void ANAWCharacter::Fire()
{
    if (EquippedWeapon)
    {
        EquippedWeapon->Fire();
    }
}

void ANAWCharacter::DebugCraft(const TArray<FString>& Items, const FString& TierTarget)
{
    UNAWResolverSubsystem* Resolver = GetGameInstance()->GetSubsystem<UNAWResolverSubsystem>();
    Resolver->Craft(Items, TierTarget, FNAWCraftComplete::CreateWeakLambda(this,
        [this](bool bSuccess, const FNAWGadget& Gadget)
        {
            if (bSuccess)
            {
                EquipGadget(Gadget);
            }
            else if (GEngine)
            {
                GEngine->AddOnScreenDebugMessage(-1, 4.f, FColor::Red,
                                                 TEXT("debug craft failed - sidecar down?"));
            }
        }));
}

void ANAWCharacter::DebugCraftPlaced()
{
    DebugCraft({TEXT("cooler of raw steaks")}, TEXT("COMMON"));
}

void ANAWCharacter::DebugCraftThrown()
{
    DebugCraft({TEXT("bucket of wet cement"), TEXT("jerrycan of gasoline")}, TEXT("RARE"));
}

void ANAWCharacter::ToggleSlot(int32 SlotIndex)
{
    Inventory->ToggleSelect(SlotIndex);
}

void ANAWCharacter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (GEngine && IsPlayerControlled())
    {
        GEngine->AddOnScreenDebugMessage(1, 0.f, FColor::White, Inventory->DisplayString());
    }
}

void ANAWCharacter::Interact()
{
    TArray<AActor*> Overlapping;
    GetOverlappingActors(Overlapping, ANAWCraftSpot::StaticClass());
    if (Overlapping.Num() > 0)
    {
        Cast<ANAWCraftSpot>(Overlapping[0])->TryCraft(this);
    }
}
