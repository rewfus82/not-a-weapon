#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "NAWGameMode.generated.h"

UCLASS()
class NOTAWEAPON_API ANAWGameMode : public AGameModeBase
{
    GENERATED_BODY()

public:
    ANAWGameMode();

    // Full run reset by reloading the level; extracted.jsonl persists on disk.
    void RestartRun();
};
