using UnrealBuildTool;

public class NotAWeapon : ModuleRules
{
    public NotAWeapon(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[]
            { "Core", "CoreUObject", "Engine", "InputCore", "HTTP", "Json" });
    }
}
