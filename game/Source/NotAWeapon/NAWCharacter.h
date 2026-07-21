#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "NAWCharacter.generated.h"

UCLASS()
class NOTAWEAPON_API ANAWCharacter : public ACharacter
{
    GENERATED_BODY()

public:
    ANAWCharacter();

protected:
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

    UPROPERTY(VisibleAnywhere)
    class UCameraComponent* Camera;

private:
    void MoveForward(float Value);
    void MoveRight(float Value);
};
