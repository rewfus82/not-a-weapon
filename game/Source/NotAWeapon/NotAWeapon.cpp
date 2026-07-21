#include "NotAWeapon.h"
#include "Contract.h"
#include "Misc/CoreDelegates.h"

DEFINE_LOG_CATEGORY(LogNAW);

void FNotAWeaponModule::StartupModule()
{
#if !UE_BUILD_SHIPPING
    FCoreDelegates::OnPostEngineInit.AddStatic(&NAWContractSelfTest);
#endif
}

IMPLEMENT_PRIMARY_GAME_MODULE(FNotAWeaponModule, NotAWeapon, "NotAWeapon");
