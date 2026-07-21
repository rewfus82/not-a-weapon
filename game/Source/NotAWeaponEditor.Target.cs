using UnrealBuildTool;

public class NotAWeaponEditorTarget : TargetRules
{
    public NotAWeaponEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("NotAWeapon");
    }
}
