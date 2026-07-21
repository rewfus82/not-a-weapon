#include "NAWGameMode.h"
#include "NAWCharacter.h"
#include "Kismet/GameplayStatics.h"

ANAWGameMode::ANAWGameMode()
{
    DefaultPawnClass = ANAWCharacter::StaticClass();
}

void ANAWGameMode::RestartRun()
{
    UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)));
}
