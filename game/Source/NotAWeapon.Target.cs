using UnrealBuildTool;

public class NotAWeaponTarget : TargetRules
{
    public NotAWeaponTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("NotAWeapon");
    }
}
