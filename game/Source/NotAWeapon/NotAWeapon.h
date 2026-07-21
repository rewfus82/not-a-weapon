#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

DECLARE_LOG_CATEGORY_EXTERN(LogNAW, Log, All);

class FNotAWeaponModule : public FDefaultGameModuleImpl
{
public:
    virtual void StartupModule() override;
};
