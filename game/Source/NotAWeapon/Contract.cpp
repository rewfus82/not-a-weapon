#include "Contract.h"
#include "NotAWeapon.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
template <typename TEnum>
bool ParseEnumToken(const TSharedPtr<FJsonObject>& Obj, const FString& Field, TEnum& Out)
{
    FString Token;
    if (!Obj->TryGetStringField(Field, Token))
    {
        return false;
    }
    const int64 Value = StaticEnum<TEnum>()->GetValueByNameString(Token);
    if (Value == INDEX_NONE)
    {
        return false;  // unknown token = outside the contract = malformed
    }
    Out = static_cast<TEnum>(Value);
    return true;
}

float NumberField(const TSharedPtr<FJsonObject>& Obj, const FString& Field)
{
    double Value = 0.0;
    Obj->TryGetNumberField(Field, Value);
    return static_cast<float>(Value);
}
}  // namespace

bool FNAWGadget::ParseJson(const FString& Body, FNAWGadget& Out)
{
    TSharedPtr<FJsonObject> Root;
    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Body);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        return false;
    }
    if (!Root->TryGetStringField(TEXT("source"), Out.Source) ||
        !Root->TryGetStringField(TEXT("name"), Out.Name) ||
        !Root->TryGetStringField(TEXT("description"), Out.Description) ||
        !Root->TryGetStringField(TEXT("logic"), Out.Logic) ||
        !Root->TryGetBoolField(TEXT("harmless"), Out.bHarmless) ||
        !Root->TryGetStringField(TEXT("color"), Out.Color) ||
        !ParseEnumToken(Root, TEXT("tier"), Out.Tier) ||
        !ParseEnumToken(Root, TEXT("category"), Out.Category) ||
        !ParseEnumToken(Root, TEXT("delivery"), Out.Delivery))
    {
        return false;
    }
    const TArray<TSharedPtr<FJsonValue>>* Stages = nullptr;
    if (!Root->TryGetArrayField(TEXT("stages"), Stages) || Stages->Num() == 0)
    {
        return false;
    }
    for (const TSharedPtr<FJsonValue>& StageValue : *Stages)
    {
        const TSharedPtr<FJsonObject>* StageObj = nullptr;
        if (!StageValue->TryGetObject(StageObj))
        {
            return false;
        }
        FNAWStage Stage;
        if (!ParseEnumToken(*StageObj, TEXT("trigger"), Stage.Trigger))
        {
            return false;
        }
        (*StageObj)->TryGetStringField(TEXT("note"), Stage.Note);
        const TArray<TSharedPtr<FJsonValue>>* Effects = nullptr;
        if (!(*StageObj)->TryGetArrayField(TEXT("effects"), Effects) || Effects->Num() == 0)
        {
            return false;
        }
        for (const TSharedPtr<FJsonValue>& EffectValue : *Effects)
        {
            const TSharedPtr<FJsonObject>* EffectObj = nullptr;
            if (!EffectValue->TryGetObject(EffectObj))
            {
                return false;
            }
            FNAWEffect Effect;
            if (!ParseEnumToken(*EffectObj, TEXT("kind"), Effect.Kind) ||
                !ParseEnumToken(*EffectObj, TEXT("target"), Effect.Target))
            {
                return false;
            }
            Effect.Amount = NumberField(*EffectObj, TEXT("amount"));
            Effect.Duration = NumberField(*EffectObj, TEXT("duration"));
            Effect.Radius = NumberField(*EffectObj, TEXT("radius"));
            Effect.Count = static_cast<int32>(NumberField(*EffectObj, TEXT("count")));
            (*EffectObj)->TryGetStringField(TEXT("note"), Effect.Note);
            Stage.Effects.Add(MoveTemp(Effect));
        }
        Out.Stages.Add(MoveTemp(Stage));
    }
    Out.RawJson = Body;
    return true;
}

bool FNAWGadget::HasTrigger(ENAWTrigger Trigger) const
{
    for (const FNAWStage& Stage : Stages)
    {
        if (Stage.Trigger == Trigger)
        {
            return true;
        }
    }
    return false;
}

TArray<FNAWStage> FNAWGadget::StagesFor(ENAWTrigger Trigger) const
{
    TArray<FNAWStage> Result;
    for (const FNAWStage& Stage : Stages)
    {
        if (Stage.Trigger == Trigger)
        {
            Result.Add(Stage);
        }
    }
    return Result;
}

#if !UE_BUILD_SHIPPING
void NAWContractSelfTest()
{
    // A canned Task-1-shaped sample: PLACED chassis, one ON_TRIGGER LURE stage.
    const FString Sample = TEXT("{\"source\":\"fallback\",\"name\":\"Bait Cooler\",\"description\":\"d\",\"logic\":\"l\",\"tier\":\"COMMON\",\"category\":\"UTILITY\",\"harmless\":true,\"delivery\":\"PLACED\",\"color\":\"#FFC04D\",\"stages\":[{\"trigger\":\"ON_TRIGGER\",\"note\":\"placed\",\"effects\":[{\"kind\":\"LURE\",\"target\":\"STRUCK\",\"amount\":0,\"duration\":6.0,\"radius\":4.0,\"count\":0,\"note\":\"\"}]}]}");
    FNAWGadget Gadget;
    const bool bOk = FNAWGadget::ParseJson(Sample, Gadget) &&
        Gadget.Delivery == ENAWDelivery::PLACED &&
        Gadget.bHarmless &&
        Gadget.HasTrigger(ENAWTrigger::ON_TRIGGER) &&
        Gadget.Stages.Num() == 1 &&
        Gadget.Stages[0].Effects.Num() == 1 &&
        Gadget.Stages[0].Effects[0].Kind == ENAWEffectKind::LURE &&
        Gadget.Stages[0].Effects[0].Radius == 4.0f;
    if (bOk)
    {
        UE_LOG(LogNAW, Log, TEXT("contract mirror self-test: parse OK"));
    }
    else
    {
        UE_LOG(LogNAW, Error,
               TEXT("contract mirror self-test FAILED - Contract.h drifted from resolver/contract.py"));
    }
}
#endif
