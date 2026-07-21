#include "NAWResolverSubsystem.h"
#include "NotAWeapon.h"
#include "Engine/Engine.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonWriter.h"
#include "Serialization/JsonSerializer.h"

void UNAWResolverSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    CheckContract();
}

void UNAWResolverSubsystem::CheckContract()
{
    const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(SidecarUrl + TEXT("/api/contract"));
    Request->SetVerb(TEXT("GET"));
    Request->SetTimeout(5.0f);
    Request->OnProcessRequestComplete().BindWeakLambda(this,
        [this](FHttpRequestPtr, FHttpResponsePtr Response, bool bConnected)
        {
            if (!bConnected || !Response.IsValid() || Response->GetResponseCode() != 200)
            {
                ContractState = ENAWContractState::Unreachable;
                UE_LOG(LogNAW, Warning, TEXT("contract check: sidecar unreachable (status %d)"),
                       Response.IsValid() ? Response->GetResponseCode() : 0);
                return;
            }
            TSharedPtr<FJsonObject> Root;
            const TSharedRef<TJsonReader<>> Reader =
                TJsonReaderFactory<>::Create(Response->GetContentAsString());
            FString Fingerprint;
            if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid() ||
                !Root->TryGetStringField(TEXT("fingerprint"), Fingerprint))
            {
                ContractState = ENAWContractState::Unreachable;
                UE_LOG(LogNAW, Warning, TEXT("contract check: malformed response"));
                return;
            }
            if (Fingerprint == NAW_CONTRACT_FINGERPRINT)
            {
                ContractState = ENAWContractState::Ok;
                UE_LOG(LogNAW, Log, TEXT("contract check: fingerprint OK"));
            }
            else
            {
                ContractState = ENAWContractState::Mismatch;
                UE_LOG(LogNAW, Error,
                       TEXT("CONTRACT MISMATCH - game enums drifted from resolver. Crafting disabled. Rebuild against resolver/contract.py."));
                if (GEngine)
                {
                    GEngine->AddOnScreenDebugMessage(0, 3600.f, FColor::Red,
                        TEXT("CONTRACT MISMATCH - crafting disabled (rebuild the game against the resolver contract)"));
                }
            }
        });
    Request->ProcessRequest();
}

void UNAWResolverSubsystem::FailCraft(FNAWCraftComplete& OnComplete)
{
    static const FNAWGadget Empty;
    OnComplete.ExecuteIfBound(false, Empty);
}

void UNAWResolverSubsystem::Craft(const TArray<FString>& Items, const FString& TierTarget,
                                  FNAWCraftComplete OnComplete)
{
    if (ContractState == ENAWContractState::Mismatch)
    {
        UE_LOG(LogNAW, Error, TEXT("craft refused: contract mismatch"));
        FailCraft(OnComplete);
        return;
    }
    if (bCraftInFlight)
    {
        UE_LOG(LogNAW, Warning, TEXT("craft refused: one already in flight"));
        FailCraft(OnComplete);
        return;
    }
    if (ContractState != ENAWContractState::Ok)
    {
        // Sidecar was down (or never seen). Re-probe for next time, fail this one now.
        CheckContract();
        FailCraft(OnComplete);
        return;
    }

    TSharedRef<FJsonObject> Body = MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> ItemValues;
    for (const FString& Item : Items)
    {
        ItemValues.Add(MakeShared<FJsonValueString>(Item));
    }
    Body->SetArrayField(TEXT("items"), ItemValues);
    Body->SetStringField(TEXT("tier_target"), TierTarget);
    FString BodyString;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&BodyString);
    FJsonSerializer::Serialize(Body, Writer);

    const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(SidecarUrl + TEXT("/craft"));
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    Request->SetContentAsString(BodyString);
    Request->SetTimeout(20.0f);  // covers the full live retry ladder (spec: ~20s cap)
    bCraftInFlight = true;
    Request->OnProcessRequestComplete().BindWeakLambda(this,
        [this, OnComplete](FHttpRequestPtr, FHttpResponsePtr Response, bool bConnected) mutable
        {
            bCraftInFlight = false;
            // AUP rule: numeric status only - NEVER log the response body or error text.
            if (!bConnected || !Response.IsValid() || Response->GetResponseCode() != 200)
            {
                UE_LOG(LogNAW, Warning, TEXT("craft failed: status %d"),
                       Response.IsValid() ? Response->GetResponseCode() : 0);
                ContractState = ENAWContractState::Unreachable;
                FailCraft(OnComplete);
                return;
            }
            FNAWGadget Gadget;
            if (!FNAWGadget::ParseJson(Response->GetContentAsString(), Gadget))
            {
                // Malformed JSON reaching the game = treated as sidecar-down (spec).
                UE_LOG(LogNAW, Warning, TEXT("craft failed: malformed gadget JSON"));
                FailCraft(OnComplete);
                return;
            }
            UE_LOG(LogNAW, Log, TEXT("craft OK: '%s' (source=%s)"), *Gadget.Name, *Gadget.Source);
            OnComplete.ExecuteIfBound(true, Gadget);
        });
    Request->ProcessRequest();
}
