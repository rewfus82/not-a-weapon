#include "NAWInventoryComponent.h"

bool UNAWInventoryComponent::Add(const FString& ItemName)
{
    if (Items.Num() >= MaxItems)
    {
        return false;
    }
    Items.Add(ItemName);
    Selected.Add(false);
    return true;
}

void UNAWInventoryComponent::ToggleSelect(int32 SlotIndex)
{
    if (Selected.IsValidIndex(SlotIndex))
    {
        Selected[SlotIndex] = !Selected[SlotIndex];
    }
}

TArray<FString> UNAWInventoryComponent::SelectedNames() const
{
    TArray<FString> Names;
    for (int32 i = 0; i < Items.Num(); ++i)
    {
        if (Selected[i])
        {
            Names.Add(Items[i]);
        }
    }
    return Names;
}

void UNAWInventoryComponent::ConsumeSelected()
{
    for (int32 i = Items.Num() - 1; i >= 0; --i)
    {
        if (Selected[i])
        {
            Items.RemoveAt(i);
            Selected.RemoveAt(i);
        }
    }
}

FString UNAWInventoryComponent::DisplayString() const
{
    FString Out;
    for (int32 i = 0; i < MaxItems; ++i)
    {
        if (Items.IsValidIndex(i))
        {
            Out += FString::Printf(TEXT("%d[%s] %s  "), i + 1,
                                   Selected[i] ? TEXT("x") : TEXT(" "), *Items[i]);
        }
        else
        {
            Out += FString::Printf(TEXT("%d-  "), i + 1);
        }
    }
    return Out;
}
