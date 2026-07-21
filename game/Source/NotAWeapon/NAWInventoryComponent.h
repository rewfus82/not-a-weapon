#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NAWInventoryComponent.generated.h"

// Six slots of catalog item names. Selection marks which slots feed the next
// craft. Names are opaque strings - the resolver owns their meaning.
UCLASS(ClassGroup = (NAW))
class NOTAWEAPON_API UNAWInventoryComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    // False when full - pickup stays in the world.
    bool Add(const FString& ItemName);

    void ToggleSelect(int32 SlotIndex);
    TArray<FString> SelectedNames() const;

    // Removes selected items (only called after a SUCCESSFUL craft - Task 9).
    void ConsumeSelected();

    // "1[x] rusty pipe  2[ ] jerrycan  3-  4-  5-  6-"
    FString DisplayString() const;

    static constexpr int32 MaxItems = 6;

private:
    TArray<FString> Items;
    TArray<bool> Selected;
};
